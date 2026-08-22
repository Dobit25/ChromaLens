"""Generate reviewable T02 overlays and machine-readable runtime evidence."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from time import monotonic_ns

import cv2

from chromalens.contracts import FramePacket
from chromalens.segmentation import (
    MediaPipeBackendUnavailableError,
    MediaPipeSegmenter,
    draw_mask_overlay,
)

DEFAULT_INPUT_DIR = Path("tests/samples/t02")
DEFAULT_OUTPUT_DIR = Path("artifacts/t02-segmentation")
SUPPORTED_SUFFIXES = {".jpg", ".jpeg", ".png"}


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Run the locked MediaPipe backend on licensed T02 fixtures and "
            "write overlay images plus evidence.json."
        )
    )
    parser.add_argument("--input-dir", type=Path, default=DEFAULT_INPUT_DIR)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    return parser


def run(input_dir: Path, output_dir: Path) -> list[dict[str, object]]:
    paths = sorted(
        path
        for path in input_dir.iterdir()
        if path.is_file() and path.suffix.lower() in SUPPORTED_SUFFIXES
    )
    if len(paths) < 5:
        raise ValueError(
            f"Expected at least five image fixtures in {input_dir}; got {len(paths)}"
        )

    output_dir.mkdir(parents=True, exist_ok=True)
    evidence: list[dict[str, object]] = []
    with MediaPipeSegmenter() as segmenter:
        for frame_id, path in enumerate(paths):
            frame = cv2.imread(str(path), cv2.IMREAD_COLOR)
            if frame is None:
                raise ValueError(f"Could not decode fixture: {path}")
            packet = FramePacket(
                frame_id=frame_id,
                timestamp_ns=monotonic_ns(),
                original_bgr=frame,
            )
            regions = segmenter.segment(packet)
            if not regions:
                raise RuntimeError(f"Real backend returned no mask for {path.name}")
            overlay = draw_mask_overlay(
                frame,
                regions,
                backend_info=segmenter.device_info,
            )
            output_path = output_dir / f"overlay-{path.stem}.jpg"
            if not cv2.imwrite(str(output_path), overlay):
                raise OSError(f"Could not write overlay: {output_path}")

            evidence.append(
                {
                    "fixture": path.name,
                    "frame_shape": list(frame.shape),
                    "mask_shape": list(regions[0].mask.shape),
                    "mask_dtype": str(regions[0].mask.dtype),
                    "mask_coverage": float(regions[0].mask.mean()),
                    "mask_confidence": regions[0].mask_confidence,
                    "backend": segmenter.backend_name,
                    "device": segmenter.device_info,
                    "overlay": output_path.as_posix(),
                }
            )

    report_path = output_dir / "evidence.json"
    report_path.write_text(
        json.dumps(evidence, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return evidence


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        evidence = run(args.input_dir, args.output_dir)
    except (MediaPipeBackendUnavailableError, OSError, RuntimeError, ValueError) as exc:
        print(f"T02 evidence failed: {exc}", file=sys.stderr)
        return 2

    print(
        f"T02 evidence complete: {len(evidence)} scenes -> {args.output_dir}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
