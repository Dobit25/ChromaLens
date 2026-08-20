"""Command-line entry point for preview and the T08 live pipeline."""

from __future__ import annotations

import argparse
import sys
from collections.abc import Sequence
from dataclasses import dataclass
from math import isfinite
from pathlib import Path
from time import monotonic, monotonic_ns
from typing import Protocol

import cv2

from chromalens import __version__
from chromalens.camera import (
    FrameSource,
    FrameSourceError,
    LatestFrameReader,
    LatestFrameTimeout,
    open_video,
    open_webcam,
)
from chromalens.config import CVDProfile
from chromalens.contracts import ColorFrame, FramePacket
from chromalens.metrics import RuntimeMetricsSnapshot, RuntimeMetricsTracker
from chromalens.pipeline import ChromaLensPipeline, PipelineSettings
from chromalens.renderer import (
    PipelineDisplayState,
    PipelineView,
    PreviewMetricsTracker,
    PreviewTelemetry,
    render_pipeline_view,
    render_preview,
)
from chromalens.segmentation.base import SegmenterUnavailableError


class RenderFunction(Protocol):
    """Callable contract used by the T01 preview loop and isolated tests."""

    def __call__(
        self,
        packet: FramePacket,
        *,
        source_name: str,
        telemetry: PreviewTelemetry,
    ) -> ColorFrame:
        """Render one packet without mutating its original frame."""


@dataclass(frozen=True, slots=True)
class PreviewResult:
    """Summary of one completed source-preview session."""

    source_name: str
    frames_processed: int
    elapsed_seconds: float
    stop_reason: str
    resolution: tuple[int, int] | None


@dataclass(slots=True)
class RuntimeControls:
    """Mutable, reversible controls owned by the UI boundary."""

    profile: CVDProfile = CVDProfile.DEUTAN
    severity: float = 1.0
    recolor_enabled: bool = True
    view: PipelineView = PipelineView.ASSISTIVE
    severity_step: float = 0.1

    def __post_init__(self) -> None:
        if not isinstance(self.profile, CVDProfile):
            raise TypeError("profile must be a CVDProfile")
        if not 0.0 <= self.severity <= 1.0:
            raise ValueError("severity must be within [0, 1]")
        if not isinstance(self.recolor_enabled, bool):
            raise TypeError("recolor_enabled must be boolean")
        if not isinstance(self.view, PipelineView):
            raise TypeError("view must be a PipelineView")
        if not 0.0 < self.severity_step <= 1.0:
            raise ValueError("severity_step must be within (0, 1]")

    @property
    def settings(self) -> PipelineSettings:
        """Create an immutable analytical snapshot for the next frame."""

        return PipelineSettings(
            profile=self.profile,
            severity=self.severity,
            recolor_enabled=self.recolor_enabled,
        )

    def display_state(self, *, dropped_capture_frames: int) -> PipelineDisplayState:
        """Create an immutable renderer snapshot for the current frame."""

        return PipelineDisplayState(
            profile=self.profile,
            severity=self.severity,
            recolor_enabled=self.recolor_enabled,
            view=self.view,
            dropped_capture_frames=dropped_capture_frames,
        )

    def apply_key(self, key: int) -> bool:
        """Apply one OpenCV key code; return whether a setting changed."""

        if key == ord("p"):
            profiles = tuple(CVDProfile)
            self.profile = profiles[(profiles.index(self.profile) + 1) % len(profiles)]
        elif key == ord("["):
            self.severity = max(0.0, round(self.severity - self.severity_step, 2))
        elif key == ord("]"):
            self.severity = min(1.0, round(self.severity + self.severity_step, 2))
        elif key == ord("r"):
            self.recolor_enabled = not self.recolor_enabled
        elif key == ord("v"):
            views = tuple(PipelineView)
            self.view = views[(views.index(self.view) + 1) % len(views)]
        elif ord("1") <= key <= ord("5"):
            self.view = tuple(PipelineView)[key - ord("1")]
        else:
            return False
        return True


@dataclass(frozen=True, slots=True)
class PipelineSessionResult:
    """Measured outcome of one full T08 source session."""

    source_name: str
    frames_processed: int
    elapsed_seconds: float
    stop_reason: str
    resolution: tuple[int, int] | None
    backend_name: str
    metrics: RuntimeMetricsSnapshot


def build_parser() -> argparse.ArgumentParser:
    """Build the CLI parser without opening camera or model backends."""

    parser = argparse.ArgumentParser(
        prog="chromalens",
        description=(
            "ChromaLens AI local end-to-end color-vision assistance for a "
            "webcam or local video."
        ),
    )
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    source_group = parser.add_mutually_exclusive_group()
    source_group.add_argument(
        "--webcam",
        action="store_true",
        help="run the local live pipeline on a webcam (explicit opt-in)",
    )
    source_group.add_argument(
        "--video",
        type=Path,
        metavar="PATH",
        help="run the same local pipeline on a video file",
    )
    parser.add_argument(
        "--preview-only",
        action="store_true",
        help="run the T01 capture preview without loading a segmentation backend",
    )
    parser.add_argument(
        "--profile",
        choices=tuple(profile.value for profile in CVDProfile),
        default=CVDProfile.DEUTAN.value,
        help="user-selected CVD assistance profile (default: deutan)",
    )
    parser.add_argument(
        "--severity",
        type=_severity,
        default=1.0,
        help="user-selected simulation severity from 0 to 1 (default: 1.0)",
    )
    parser.add_argument(
        "--disable-recolor",
        action="store_true",
        help="keep analytical overlays but disable assistive recoloring",
    )
    parser.add_argument(
        "--view",
        choices=tuple(view.value for view in PipelineView),
        default=PipelineView.ASSISTIVE.value,
        help="initial display view (default: assistive)",
    )
    parser.add_argument(
        "--camera-index",
        type=_non_negative_int,
        default=0,
        help="OpenCV webcam index used with --webcam (default: 0)",
    )
    parser.add_argument("--width", type=_positive_int, help="requested webcam width")
    parser.add_argument("--height", type=_positive_int, help="requested webcam height")
    parser.add_argument(
        "--max-frames",
        type=_positive_int,
        help="stop after this many successfully rendered frames",
    )
    parser.add_argument(
        "--duration-seconds",
        type=_positive_float,
        help="stop after this wall-clock duration",
    )
    parser.add_argument(
        "--no-display",
        action="store_true",
        help="process and render frames without creating a GUI window",
    )
    parser.add_argument(
        "--window-title",
        default="ChromaLens AI - T08 Live Pipeline",
        help="OpenCV window title",
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    """Execute only an explicitly selected local source."""

    parser = build_parser()
    args = parser.parse_args(list(argv) if argv is not None else None)
    if not args.webcam and args.video is None:
        parser.print_help()
        return 0

    source: FrameSource | None = None
    pipeline: ChromaLensPipeline | None = None
    try:
        source = (
            open_webcam(args.camera_index, width=args.width, height=args.height)
            if args.webcam
            else open_video(args.video)
        )
        if args.preview_only:
            preview = run_preview(
                source,
                display=not args.no_display,
                max_frames=args.max_frames,
                duration_seconds=args.duration_seconds,
                window_title=args.window_title,
            )
            print(_preview_summary(preview))
            return 0

        # Lazy construction keeps --help and the explicit capture-only path
        # independent of model packages and special hardware.
        from chromalens.segmentation.mediapipe_backend import MediaPipeSegmenter

        pipeline = ChromaLensPipeline(MediaPipeSegmenter(), stream_id=source.name)
        controls = RuntimeControls(
            profile=CVDProfile(args.profile),
            severity=args.severity,
            recolor_enabled=not args.disable_recolor,
            view=PipelineView(args.view),
        )
        result = run_pipeline_session(
            source,
            pipeline,
            controls=controls,
            display=not args.no_display,
            max_frames=args.max_frames,
            duration_seconds=args.duration_seconds,
            window_title=args.window_title,
        )
    except SegmenterUnavailableError as error:
        if source is not None:
            source.close()
        print(f"chromalens: segmentation backend unavailable: {error}", file=sys.stderr)
        return 4
    except FrameSourceError as error:
        print(f"chromalens: source error: {error}", file=sys.stderr)
        return 2
    except cv2.error as error:
        print(
            "chromalens: display error: OpenCV could not create or update the window. "
            f"Use --no-display for headless execution. Details: {error}",
            file=sys.stderr,
        )
        return 3
    except KeyboardInterrupt:
        if pipeline is not None:
            pipeline.close()
        elif source is not None:
            source.close()
        print("Pipeline interrupted; resources released.")
        return 130

    print(_pipeline_summary(result))
    return 0


def run_pipeline_session(
    source: FrameSource,
    pipeline: ChromaLensPipeline,
    *,
    controls: RuntimeControls | None = None,
    display: bool = True,
    max_frames: int | None = None,
    duration_seconds: float | None = None,
    window_title: str = "ChromaLens AI - T08 Live Pipeline",
) -> PipelineSessionResult:
    """Run the same analytical pipeline for a latest-frame webcam or video."""

    _validate_session_limits(max_frames, duration_seconds, window_title)
    active_controls = controls or RuntimeControls()
    preview_metrics = PreviewMetricsTracker()
    runtime_metrics = RuntimeMetricsTracker()
    started_at = monotonic()
    frames_processed = 0
    degraded_frames = 0
    stop_reason = "unknown"
    window_created = False
    latest_reader = LatestFrameReader(source).start() if source.is_live else None
    dropped_frames = 0
    video_frame_period_seconds = (
        1.0 / source.nominal_fps
        if display and not source.is_live and source.nominal_fps is not None
        else None
    )
    next_video_frame_at = started_at

    try:
        while True:
            if duration_seconds is not None and monotonic() - started_at >= duration_seconds:
                stop_reason = "duration_limit"
                break
            try:
                packet = (
                    latest_reader.read_latest(timeout_seconds=0.25)
                    if latest_reader is not None
                    else source.read()
                )
            except LatestFrameTimeout:
                # A live camera may briefly pause; the bounded wait also lets
                # duration and interruption controls remain responsive.
                continue
            if packet is None:
                stop_reason = "source_finished" if source.is_live else "end_of_video"
                break

            processing_started_ns = monotonic_ns()
            analysis = pipeline.process(packet, active_controls.settings)
            rendered_at_ns = monotonic_ns()
            telemetry = preview_metrics.observe(packet, observed_ns=rendered_at_ns)
            dropped_frames = latest_reader.dropped_frames if latest_reader else 0
            rendered = render_pipeline_view(
                analysis,
                source_name=source.name,
                telemetry=telemetry,
                display_state=active_controls.display_state(
                    dropped_capture_frames=dropped_frames
                ),
            )
            completed_ns = monotonic_ns()
            runtime_metrics.observe(
                capture_to_render_ms=(completed_ns - packet.timestamp_ns) / 1_000_000.0,
                processing_ms=(completed_ns - processing_started_ns) / 1_000_000.0,
                observed_ns=completed_ns,
            )
            frames_processed += 1
            degraded_frames += int(analysis.degraded)

            if display:
                cv2.imshow(window_title, rendered)
                window_created = True
                wait_ms = 1
                if video_frame_period_seconds is not None:
                    next_video_frame_at += video_frame_period_seconds
                    wait_ms = max(1, round((next_video_frame_at - monotonic()) * 1_000.0))
                key = cv2.waitKey(wait_ms) & 0xFF
                if key in (27, ord("q")):
                    stop_reason = "user_exit"
                    break
                active_controls.apply_key(key)
                try:
                    visible = cv2.getWindowProperty(window_title, cv2.WND_PROP_VISIBLE)
                except cv2.error:
                    visible = 0.0
                if visible < 1:
                    stop_reason = "window_closed"
                    break

            if max_frames is not None and frames_processed >= max_frames:
                stop_reason = "frame_limit"
                break
    finally:
        if latest_reader is not None:
            latest_reader.close()
            dropped_frames = latest_reader.dropped_frames
        else:
            source.close()
        pipeline.close()
        if window_created:
            try:
                cv2.destroyWindow(window_title)
            except cv2.error:
                pass

    completed_at_ns = monotonic_ns()
    metrics = runtime_metrics.snapshot(
        dropped_capture_frames=dropped_frames,
        degraded_frames=degraded_frames,
        observed_ns=completed_at_ns,
    )
    return PipelineSessionResult(
        source_name=source.name,
        frames_processed=frames_processed,
        elapsed_seconds=monotonic() - started_at,
        stop_reason=stop_reason,
        resolution=source.resolution,
        backend_name=pipeline.backend_name,
        metrics=metrics,
    )


def run_preview(
    source: FrameSource,
    *,
    display: bool = True,
    max_frames: int | None = None,
    duration_seconds: float | None = None,
    window_title: str = "ChromaLens AI - T01 Preview",
    render_frame: RenderFunction = render_preview,
) -> PreviewResult:
    """Read, render, and discard one frame at a time with no application queue."""

    _validate_session_limits(max_frames, duration_seconds, window_title)
    tracker = PreviewMetricsTracker()
    started_at = monotonic()
    frames_processed = 0
    stop_reason = "unknown"
    window_created = False
    video_frame_period_seconds = (
        1.0 / source.nominal_fps
        if display and not source.is_live and source.nominal_fps is not None
        else None
    )
    next_video_frame_at = started_at

    try:
        while True:
            if duration_seconds is not None and monotonic() - started_at >= duration_seconds:
                stop_reason = "duration_limit"
                break
            packet = source.read()
            if packet is None:
                stop_reason = "end_of_video"
                break
            telemetry = tracker.observe(packet, observed_ns=monotonic_ns())
            rendered = render_frame(packet, source_name=source.name, telemetry=telemetry)
            frames_processed += 1
            if display:
                cv2.imshow(window_title, rendered)
                window_created = True
                wait_ms = 1
                if video_frame_period_seconds is not None:
                    next_video_frame_at += video_frame_period_seconds
                    wait_ms = max(1, round((next_video_frame_at - monotonic()) * 1_000.0))
                key = cv2.waitKey(wait_ms) & 0xFF
                if key in (27, ord("q")):
                    stop_reason = "user_exit"
                    break
                try:
                    visible = cv2.getWindowProperty(window_title, cv2.WND_PROP_VISIBLE)
                except cv2.error:
                    visible = 0.0
                if visible < 1:
                    stop_reason = "window_closed"
                    break
            if max_frames is not None and frames_processed >= max_frames:
                stop_reason = "frame_limit"
                break
    finally:
        source.close()
        if window_created:
            try:
                cv2.destroyWindow(window_title)
            except cv2.error:
                pass

    return PreviewResult(
        source_name=source.name,
        frames_processed=frames_processed,
        elapsed_seconds=monotonic() - started_at,
        stop_reason=stop_reason,
        resolution=source.resolution,
    )


def _validate_session_limits(
    max_frames: int | None,
    duration_seconds: float | None,
    window_title: str,
) -> None:
    if max_frames is not None and max_frames <= 0:
        raise ValueError("max_frames must be positive when provided")
    if duration_seconds is not None and duration_seconds <= 0.0:
        raise ValueError("duration_seconds must be positive when provided")
    if not window_title.strip():
        raise ValueError("window_title must not be empty")


def _preview_summary(result: PreviewResult) -> str:
    resolution = (
        "unknown"
        if result.resolution is None
        else f"{result.resolution[0]}x{result.resolution[1]}"
    )
    return (
        f"Preview complete: source={result.source_name} frames={result.frames_processed} "
        f"resolution={resolution} elapsed={result.elapsed_seconds:.2f}s "
        f"reason={result.stop_reason}"
    )


def _pipeline_summary(result: PipelineSessionResult) -> str:
    metrics = result.metrics
    resolution = (
        "unknown"
        if result.resolution is None
        else f"{result.resolution[0]}x{result.resolution[1]}"
    )
    return (
        f"Pipeline complete: source={result.source_name} backend={result.backend_name} "
        f"frames={result.frames_processed} resolution={resolution} "
        f"elapsed={result.elapsed_seconds:.2f}s reason={result.stop_reason} "
        f"fps={_optional_number(metrics.processed_fps)} "
        f"latency_p50_ms={_optional_number(metrics.capture_to_render_p50_ms)} "
        f"latency_p95_ms={_optional_number(metrics.capture_to_render_p95_ms)} "
        f"rss_start_mib={_optional_number(metrics.rss_start_mib)} "
        f"rss_end_mib={_optional_number(metrics.rss_end_mib)} "
        f"rss_peak_mib={_optional_number(metrics.rss_peak_mib)} "
        f"rss_delta_mib={_optional_number(metrics.rss_delta_mib)} "
        f"rss_steady_delta_mib="
        f"{_optional_number(metrics.rss_steady_state_delta_mib)} "
        f"rss_steady_slope_mib_per_min="
        f"{_optional_number(metrics.rss_steady_state_slope_mib_per_minute)} "
        f"latency_slope_ms_per_min="
        f"{_optional_number(metrics.capture_to_render_slope_ms_per_minute)} "
        f"dropped={metrics.dropped_capture_frames} degraded={metrics.degraded_frames}"
    )


def _optional_number(value: float | None) -> str:
    return "unavailable" if value is None else f"{value:.2f}"


def _positive_int(value: str) -> int:
    parsed = int(value)
    if parsed <= 0:
        raise argparse.ArgumentTypeError("must be a positive integer")
    return parsed


def _non_negative_int(value: str) -> int:
    parsed = int(value)
    if parsed < 0:
        raise argparse.ArgumentTypeError("must be a non-negative integer")
    return parsed


def _positive_float(value: str) -> float:
    parsed = float(value)
    if not isfinite(parsed) or parsed <= 0.0:
        raise argparse.ArgumentTypeError("must be finite and positive")
    return parsed


def _severity(value: str) -> float:
    parsed = float(value)
    if not 0.0 <= parsed <= 1.0:
        raise argparse.ArgumentTypeError("must be within [0, 1]")
    return parsed
