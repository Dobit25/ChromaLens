"""Prepare the reproducible, ignored T11 offline-demo evidence package."""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
from pathlib import Path
from time import monotonic_ns

import cv2
import numpy as np

from chromalens.config import CVDProfile
from chromalens.contracts import FramePacket
from chromalens.pipeline import ChromaLensPipeline, PipelineSettings
from chromalens.renderer import (
    PipelineDisplayState,
    PipelineView,
    PreviewMetricsTracker,
    render_pipeline_view,
)
from chromalens.segmentation.mediapipe_backend import MediaPipeSegmenter

DEFAULT_OUTPUT_DIR = Path("artifacts/t11-handoff")
DEFAULT_FIXTURE = Path("tests/samples/t02/astronaut.png")
FIXTURE_SHA256 = "88431cd9653ccd539741b555fb0a46b61558b301d4110412b5bc28b5e3ea6cb5"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--fixture", type=Path, default=DEFAULT_FIXTURE)
    parser.add_argument("--duration-seconds", type=float, default=15.0)
    parser.add_argument("--fps", type=float, default=12.0)
    return parser


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def git_commit() -> str:
    result = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        check=True,
        capture_output=True,
        text=True,
    )
    return result.stdout.strip()


def prepare_canvas(frame: np.ndarray, *, width: int = 640, height: int = 480) -> np.ndarray:
    """Fit a source image on a fixed canvas without changing its aspect ratio."""

    if frame.dtype != np.uint8 or frame.ndim != 3 or frame.shape[2] != 3:
        raise ValueError("frame must be a uint8 H x W x 3 BGR image")
    source_height, source_width = frame.shape[:2]
    scale = min(width / source_width, height / source_height)
    resized_width = max(1, round(source_width * scale))
    resized_height = max(1, round(source_height * scale))
    resized = cv2.resize(frame, (resized_width, resized_height), cv2.INTER_AREA)
    canvas = np.full((height, width, 3), 24, dtype=np.uint8)
    x0 = (width - resized_width) // 2
    y0 = (height - resized_height) // 2
    canvas[y0 : y0 + resized_height, x0 : x0 + resized_width] = resized
    return canvas


def build_engineered_demo_frame(frame: np.ndarray) -> np.ndarray:
    """Add a declared deutan-risk pair to the public fixture's torso area."""

    demo = prepare_canvas(frame)
    # BGR inputs are derived from the frozen T05 deutan RGB sanity pair and
    # adjusted so the complete deterministic pipeline exercises risk/recolour.
    demo[180:360, 145:320] = (11, 48, 164)
    demo[180:360, 320:495] = (9, 145, 90)
    return demo


def write_fallback_video(
    path: Path,
    frame: np.ndarray,
    *,
    duration_seconds: float = 15.0,
    fps: float = 12.0,
) -> tuple[int, tuple[int, int]]:
    """Write a deterministic camera-free MJPG video from a licensed image."""

    if not np.isfinite(duration_seconds) or duration_seconds <= 0:
        raise ValueError("duration_seconds must be positive and finite")
    if not np.isfinite(fps) or fps <= 0:
        raise ValueError("fps must be positive and finite")
    base = prepare_canvas(frame)
    height, width = base.shape[:2]
    frame_count = max(1, round(duration_seconds * fps))
    path.parent.mkdir(parents=True, exist_ok=True)
    writer = cv2.VideoWriter(
        str(path), cv2.VideoWriter_fourcc(*"MJPG"), fps, (width, height)
    )
    if not writer.isOpened():
        raise RuntimeError(f"could not create fallback video: {path}")
    try:
        for index in range(frame_count):
            phase = 2.0 * np.pi * index / frame_count
            shift = round(8.0 * np.sin(phase))
            matrix = np.float32([[1.0, 0.0, shift], [0.0, 1.0, 0.0]])
            rendered = cv2.warpAffine(
                base,
                matrix,
                (width, height),
                borderMode=cv2.BORDER_REFLECT_101,
            )
            cv2.putText(
                rendered,
                "OFFLINE FALLBACK - PUBLIC NASA FIXTURE",
                (12, height - 16),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.58,
                (255, 255, 255),
                2,
                cv2.LINE_AA,
            )
            writer.write(rendered)
    finally:
        writer.release()
    capture = cv2.VideoCapture(str(path))
    try:
        decoded_count = round(capture.get(cv2.CAP_PROP_FRAME_COUNT))
        decoded_size = (
            round(capture.get(cv2.CAP_PROP_FRAME_WIDTH)),
            round(capture.get(cv2.CAP_PROP_FRAME_HEIGHT)),
        )
        if not capture.isOpened() or decoded_count != frame_count:
            raise RuntimeError("fallback video failed decode/count validation")
    finally:
        capture.release()
    return frame_count, decoded_size


def write_real_pipeline_screenshots(
    output_dir: Path,
    frame: np.ndarray,
) -> tuple[list[Path], dict[str, object]]:
    """Render all T08 views using the real locked MediaPipe backend."""

    packet = FramePacket(
        frame_id=0,
        timestamp_ns=monotonic_ns(),
        original_bgr=prepare_canvas(frame),
    )
    pipeline = ChromaLensPipeline(
        MediaPipeSegmenter(), stream_id="t11-public-fixture"
    )
    try:
        result = pipeline.process(
            packet,
            PipelineSettings(profile=CVDProfile.DEUTAN, severity=1.0),
        )
        if result.primary_region is None:
            raise RuntimeError("real MediaPipe backend returned no region")
        telemetry = PreviewMetricsTracker().observe(
            result.packet, observed_ns=monotonic_ns()
        )
        paths: list[Path] = []
        for view in PipelineView:
            image = render_pipeline_view(
                result,
                source_name="public NASA astronaut fixture",
                telemetry=telemetry,
                display_state=PipelineDisplayState(
                    profile=CVDProfile.DEUTAN,
                    severity=1.0,
                    recolor_enabled=True,
                    view=view,
                ),
            )
            path = output_dir / "screenshots" / f"{view.value}.png"
            path.parent.mkdir(parents=True, exist_ok=True)
            if not cv2.imwrite(str(path), image):
                raise RuntimeError(f"could not write screenshot: {path}")
            paths.append(path)
        summary = {
            "backend": result.backend_name,
            "frame_id": result.analysis_frame_id,
            "region_count": len(result.regions),
            "mask_pixels": int(np.count_nonzero(result.primary_region.mask)),
            "original_colors": [
                {"name": cluster.original_name, "rgb": list(cluster.rgb)}
                for cluster in result.clusters
            ],
            "risk_level": result.risk.risk_level if result.risk is not None else None,
            "recolor_applied": bool(
                result.recolor is not None and result.recolor.debug.applied
            ),
            "degraded_reasons": list(result.degraded_reasons),
        }
        return paths, summary
    finally:
        pipeline.close()


def artifact_record(path: Path, *, purpose: str) -> dict[str, object]:
    return {
        "path": path.as_posix(),
        "purpose": purpose,
        "bytes": path.stat().st_size,
        "sha256": sha256_file(path),
    }


def main() -> int:
    args = build_parser().parse_args()
    script_path = Path(__file__).resolve()
    repository_root = script_path.parents[1]
    if not args.fixture.is_file():
        raise FileNotFoundError(f"fixture not found: {args.fixture}")
    fixture_hash = sha256_file(args.fixture)
    if args.fixture == DEFAULT_FIXTURE and fixture_hash != FIXTURE_SHA256:
        raise RuntimeError("default fixture checksum does not match its rights record")
    source_frame = cv2.imread(str(args.fixture), cv2.IMREAD_COLOR)
    if source_frame is None:
        raise RuntimeError(f"could not decode fixture: {args.fixture}")
    demo_frame = build_engineered_demo_frame(source_frame)

    args.output_dir.mkdir(parents=True, exist_ok=True)
    video_path = args.output_dir / "fallback_mediapipe.avi"
    frame_count, resolution = write_fallback_video(
        video_path,
        demo_frame,
        duration_seconds=args.duration_seconds,
        fps=args.fps,
    )
    screenshot_paths, pipeline_summary = write_real_pipeline_screenshots(
        args.output_dir, demo_frame
    )
    artifacts = [
        artifact_record(video_path, purpose="camera-free offline demo input"),
        *[
            artifact_record(path, purpose="real MediaPipe pipeline screenshot")
            for path in screenshot_paths
        ],
    ]
    manifest = {
        "schema_version": "1.0.0",
        "scope": (
            "T11 handoff evidence on a licensed public fixture; not a physical "
            "color-accuracy, target-user, clinical, or demo-hardware claim"
        ),
        "generated_by": {
            "script": script_path.relative_to(repository_root).as_posix(),
            "script_sha256": sha256_file(script_path),
            "git_commit": git_commit(),
        },
        "source": {
            "path": args.fixture.as_posix(),
            "bytes": args.fixture.stat().st_size,
            "sha256": fixture_hash,
            "provenance": "scikit-image astronaut sample; Eileen Collins/NASA",
            "rights": "public-domain NASA image redistributed by scikit-image",
            "consent": "NOT_APPLICABLE_PUBLIC_DOMAIN_FIXTURE",
            "transformation": (
                "ChromaLens overlays declared BGR patches derived from the "
                "frozen T05 deutan red/olive pair and adjusted so the complete "
                "pipeline exercises risk/recolour; this is an engineered demo "
                "case, not a physical observation"
            ),
        },
        "fallback_video": {
            "codec": "MJPG/AVI",
            "fps": args.fps,
            "frames": frame_count,
            "resolution": list(resolution),
            "duration_seconds": frame_count / args.fps,
        },
        "pipeline": pipeline_summary,
        "artifacts": artifacts,
        "runtime_command": (
            "python -m chromalens --video "
            "artifacts/t11-handoff/fallback_mediapipe.avi"
        ),
    }
    manifest_path = args.output_dir / "manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    print(f"T11 handoff package written to {args.output_dir}")
    print(json.dumps(manifest, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
