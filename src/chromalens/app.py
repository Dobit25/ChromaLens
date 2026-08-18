"""Command-line entry point for the T01 camera/video preview."""

from __future__ import annotations

import argparse
import sys
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path
from time import monotonic, monotonic_ns
from typing import Protocol

import cv2

from chromalens import __version__
from chromalens.camera import FrameSource, FrameSourceError, open_video, open_webcam
from chromalens.contracts import ColorFrame, FramePacket
from chromalens.renderer import PreviewMetricsTracker, PreviewTelemetry, render_preview


class RenderFunction(Protocol):
    """Callable contract used by the preview loop and isolated tests."""

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


def build_parser() -> argparse.ArgumentParser:
    """Build the CLI parser without opening camera or model backends."""

    parser = argparse.ArgumentParser(
        prog="chromalens",
        description=(
            "ChromaLens AI local color-vision assistance. "
            "T01 previews a webcam or local video with basic diagnostics."
        ),
    )
    parser.add_argument(
        "--version",
        action="version",
        version=f"%(prog)s {__version__}",
    )
    source_group = parser.add_mutually_exclusive_group()
    source_group.add_argument(
        "--webcam",
        action="store_true",
        help="preview a local webcam (disabled unless explicitly selected)",
    )
    source_group.add_argument(
        "--video",
        type=Path,
        metavar="PATH",
        help="preview a local video file without opening a webcam",
    )
    parser.add_argument(
        "--camera-index",
        type=_non_negative_int,
        default=0,
        help="OpenCV webcam index used with --webcam (default: 0)",
    )
    parser.add_argument(
        "--width",
        type=_positive_int,
        help="requested webcam width in pixels",
    )
    parser.add_argument(
        "--height",
        type=_positive_int,
        help="requested webcam height in pixels",
    )
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
        default="ChromaLens AI — T01 Preview",
        help="OpenCV preview-window title",
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    """Parse CLI arguments, execute an explicitly selected source, and exit."""

    parser = build_parser()
    arguments = list(argv) if argv is not None else None
    args = parser.parse_args(arguments)
    if not args.webcam and args.video is None:
        parser.print_help()
        return 0

    try:
        if args.webcam:
            source = open_webcam(
                args.camera_index,
                width=args.width,
                height=args.height,
            )
        else:
            source = open_video(args.video)
        result = run_preview(
            source,
            display=not args.no_display,
            max_frames=args.max_frames,
            duration_seconds=args.duration_seconds,
            window_title=args.window_title,
        )
    except FrameSourceError as error:
        print(f"chromalens: source error: {error}", file=sys.stderr)
        return 2
    except cv2.error as error:
        print(
            "chromalens: display error: OpenCV could not create or update the preview "
            f"window. Use --no-display for headless execution. Details: {error}",
            file=sys.stderr,
        )
        return 3
    except KeyboardInterrupt:
        print("Preview interrupted; source released.")
        return 130

    resolution_text = (
        "unknown"
        if result.resolution is None
        else f"{result.resolution[0]}x{result.resolution[1]}"
    )
    print(
        f"Preview complete: source={result.source_name} "
        f"frames={result.frames_processed} resolution={resolution_text} "
        f"elapsed={result.elapsed_seconds:.2f}s reason={result.stop_reason}"
    )
    return 0


def run_preview(
    source: FrameSource,
    *,
    display: bool = True,
    max_frames: int | None = None,
    duration_seconds: float | None = None,
    window_title: str = "ChromaLens AI — T01 Preview",
    render_frame: RenderFunction = render_preview,
) -> PreviewResult:
    """Read, render, and discard one frame at a time with no application queue."""

    if max_frames is not None and max_frames <= 0:
        raise ValueError("max_frames must be positive when provided")
    if duration_seconds is not None and duration_seconds <= 0.0:
        raise ValueError("duration_seconds must be positive when provided")
    if not window_title.strip():
        raise ValueError("window_title must not be empty")

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
            rendered = render_frame(
                packet,
                source_name=source.name,
                telemetry=telemetry,
            )
            frames_processed += 1

            if display:
                cv2.imshow(window_title, rendered)
                window_created = True
                wait_ms = 1
                if video_frame_period_seconds is not None:
                    next_video_frame_at += video_frame_period_seconds
                    remaining_seconds = next_video_frame_at - monotonic()
                    wait_ms = max(1, round(remaining_seconds * 1_000.0))
                key = cv2.waitKey(wait_ms) & 0xFF
                if key in (27, ord("q")):
                    stop_reason = "user_exit"
                    break
                try:
                    window_visible = cv2.getWindowProperty(
                        window_title,
                        cv2.WND_PROP_VISIBLE,
                    )
                except cv2.error:
                    window_visible = 0.0
                if window_visible < 1:
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
                # A user-closing the native window is already a clean exit.
                pass

    return PreviewResult(
        source_name=source.name,
        frames_processed=frames_processed,
        elapsed_seconds=monotonic() - started_at,
        stop_reason=stop_reason,
        resolution=source.resolution,
    )


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
    if parsed <= 0.0:
        raise argparse.ArgumentTypeError("must be positive")
    return parsed
