"""Generate reproducible T08 composition, real-backend, and stability evidence."""

from __future__ import annotations

import argparse
import json
from dataclasses import asdict
from pathlib import Path
from threading import Event
from time import monotonic_ns

import cv2
import numpy as np

from chromalens.app import RuntimeControls, run_pipeline_session
from chromalens.camera import FrameSource
from chromalens.config import CVDProfile
from chromalens.contracts import FramePacket, GarmentRegion
from chromalens.pipeline import ChromaLensPipeline, PipelineFrameResult, PipelineSettings
from chromalens.renderer import (
    PipelineDisplayState,
    PipelineView,
    PreviewMetricsTracker,
    render_pipeline_view,
)
from chromalens.segmentation.base import Segmenter
from chromalens.segmentation.mediapipe_backend import MediaPipeSegmenter

DEFAULT_OUTPUT_DIR = Path("artifacts/t08-pipeline")
REAL_FIXTURE = Path("tests/samples/t02/astronaut.png")


class ControlledTorsoSegmenter(Segmenter):
    """Deterministic evidence double; clearly not a production backend."""

    @property
    def backend_name(self) -> str:
        return "controlled-t08-evidence"

    @property
    def device_info(self) -> str:
        return "controlled-t08-evidence/cpu"

    def segment(self, packet: FramePacket) -> tuple[GarmentRegion, ...]:
        height, width = packet.original_bgr.shape[:2]
        mask = np.zeros((height, width), dtype=np.bool_)
        mask[height // 4 : 3 * height // 4, width // 5 : 4 * width // 5] = True
        return (
            GarmentRegion(
                track_id=1,
                class_name="controlled-upper-clothes",
                mask=mask,
                mask_confidence=0.82,
            ),
        )


class TimedSyntheticLiveSource(FrameSource):
    """Private-free 30 FPS live source used only for bounded-runtime evidence."""

    def __init__(self, frame: np.ndarray, *, fps: float = 30.0) -> None:
        self._frame = frame.copy()
        self._period = 1.0 / fps
        self._frame_id = 0
        self._closed = Event()

    @property
    def name(self) -> str:
        return "synthetic-live:controlled-two-color"

    @property
    def is_live(self) -> bool:
        return True

    @property
    def resolution(self) -> tuple[int, int]:
        return self._frame.shape[1], self._frame.shape[0]

    @property
    def nominal_fps(self) -> float:
        return 30.0

    def read(self) -> FramePacket | None:
        if self._closed.wait(timeout=self._period):
            return None
        packet = FramePacket(
            frame_id=self._frame_id,
            timestamp_ns=monotonic_ns(),
            original_bgr=self._frame.copy(),
        )
        self._frame_id += 1
        return packet

    def close(self) -> None:
        self._closed.set()


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument(
        "--stability-seconds",
        type=float,
        default=0.0,
        help="run a bounded synthetic-live stability measurement for N seconds",
    )
    return parser


def main() -> int:
    args = build_parser().parse_args()
    if args.stability_seconds < 0.0:
        raise ValueError("--stability-seconds must be non-negative")
    args.output_dir.mkdir(parents=True, exist_ok=True)

    controlled_packet = _controlled_packet()
    controlled_pipeline = ChromaLensPipeline(
        ControlledTorsoSegmenter(), stream_id="controlled-evidence"
    )
    controlled = controlled_pipeline.process(
        controlled_packet,
        PipelineSettings(profile=CVDProfile.DEUTAN, severity=1.0),
    )
    if controlled.primary_region is None or len(controlled.clusters) != 2:
        raise RuntimeError("controlled end-to-end evidence did not retain mask/two colors")
    if controlled.risk is None or controlled.risk.risk_score < 0.25:
        raise RuntimeError("controlled evidence did not produce relational risk")
    if controlled.recolor is None or not controlled.recolor.debug.applied:
        raise RuntimeError("controlled evidence did not trigger selective recolor")
    outside = ~controlled.primary_region.mask
    if not np.array_equal(
        controlled.assistive_bgr[outside], controlled.packet.original_bgr[outside]
    ):
        raise RuntimeError("controlled recolor changed pixels outside garment mask")

    controlled_views = _write_views(
        controlled,
        output_dir=args.output_dir,
        prefix="controlled",
        source_name="controlled two-color fixture",
    )

    real_image = cv2.imread(str(REAL_FIXTURE), cv2.IMREAD_COLOR)
    if real_image is None:
        raise RuntimeError(f"could not read licensed fixture: {REAL_FIXTURE}")
    sample_video_path = args.output_dir / "sample_mediapipe.avi"
    _write_sample_video(sample_video_path, real_image)
    real_packet = FramePacket(0, monotonic_ns(), real_image)
    real_pipeline = ChromaLensPipeline(
        MediaPipeSegmenter(), stream_id="real-mediapipe-fixture"
    )
    real = real_pipeline.process(real_packet, PipelineSettings())
    if real.primary_region is None:
        raise RuntimeError("real MediaPipe backend returned no region on fixture")
    real_views = _write_views(
        real,
        output_dir=args.output_dir,
        prefix="real_mediapipe",
        source_name=REAL_FIXTURE.as_posix(),
    )
    real_pipeline.close()
    controlled_pipeline.close()

    stability = _previous_stability(args.output_dir / "evidence.json")
    if args.stability_seconds > 0.0:
        live_source = TimedSyntheticLiveSource(_controlled_packet().original_bgr)
        live_pipeline = ChromaLensPipeline(
            ControlledTorsoSegmenter(), stream_id=live_source.name
        )
        session = run_pipeline_session(
            live_source,
            live_pipeline,
            controls=RuntimeControls(),
            display=False,
            duration_seconds=args.stability_seconds,
        )
        stability = asdict(session.metrics)
        stability.update(
            {
                "requested_duration_seconds": args.stability_seconds,
                "stop_reason": session.stop_reason,
                "backend": session.backend_name,
                "source": session.source_name,
                "resolution": session.resolution,
            }
        )

    report = {
        "scope": (
            "T08 controlled contract + real MediaPipe integration; not a T09 "
            "accuracy study, clinical claim, or official demo-hardware result"
        ),
        "controlled": {
            "frame_id": controlled.analysis_frame_id,
            "backend": controlled.backend_name,
            "regions": len(controlled.regions),
            "clusters": [cluster.original_name for cluster in controlled.clusters],
            "risk_level": controlled.risk.risk_level,
            "risk_score": controlled.risk.risk_score,
            "recolor_applied": controlled.recolor.debug.applied,
            "outside_mask_byte_identical": True,
            "matching_source": controlled.matching.source_original_name,
            "views": controlled_views,
        },
        "real_backend": {
            "fixture": REAL_FIXTURE.as_posix(),
            "generated_sample_video": sample_video_path.as_posix(),
            "backend": real.backend_name,
            "regions": len(real.regions),
            "mask_pixels": int(np.count_nonzero(real.primary_region.mask)),
            "degraded_reasons": real.degraded_reasons,
            "views": real_views,
        },
        "stability": stability,
    }
    report_path = args.output_dir / "evidence.json"
    report_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(f"T08 evidence written to {args.output_dir}")
    print(json.dumps(report, indent=2))
    return 0


def _controlled_packet() -> FramePacket:
    height, width = 240, 360
    frame = np.full((height, width, 3), 128, dtype=np.uint8)
    y0, y1 = height // 4, 3 * height // 4
    x0, x1 = width // 5, 4 * width // 5
    split = x0 + round((x1 - x0) * 0.62)
    frame[y0:y1, x0:split] = (30, 30, 210)
    frame[y0:y1, split:x1] = (20, 130, 130)
    return FramePacket(0, monotonic_ns(), frame)


def _write_views(
    result: PipelineFrameResult,
    *,
    output_dir: Path,
    prefix: str,
    source_name: str,
) -> list[str]:
    telemetry = PreviewMetricsTracker().observe(
        result.packet, observed_ns=monotonic_ns()
    )
    paths: list[str] = []
    for view in PipelineView:
        image = render_pipeline_view(
            result,
            source_name=source_name,
            telemetry=telemetry,
            display_state=PipelineDisplayState(
                profile=CVDProfile.DEUTAN,
                severity=1.0,
                recolor_enabled=True,
                view=view,
                dropped_capture_frames=0,
            ),
        )
        path = output_dir / f"{prefix}_{view.value}.png"
        if not cv2.imwrite(str(path), image):
            raise RuntimeError(f"could not write evidence image: {path}")
        paths.append(path.as_posix())
    return paths


def _write_sample_video(path: Path, frame: np.ndarray) -> None:
    height, width = frame.shape[:2]
    writer = cv2.VideoWriter(
        str(path), cv2.VideoWriter_fourcc(*"MJPG"), 12.0, (width, height)
    )
    if not writer.isOpened():
        raise RuntimeError(f"could not create sample video: {path}")
    try:
        for _ in range(8):
            writer.write(frame)
    finally:
        writer.release()


def _previous_stability(report_path: Path) -> dict[str, object] | None:
    """Retain a completed long-run record when refreshing visual evidence."""

    if not report_path.is_file():
        return None
    try:
        previous = json.loads(report_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    stability = previous.get("stability")
    return stability if isinstance(stability, dict) else None


if __name__ == "__main__":
    raise SystemExit(main())
