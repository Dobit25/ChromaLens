"""Generate deterministic, ignored T03 lighting-correction evidence."""

from __future__ import annotations

import argparse
import json
from dataclasses import asdict
from pathlib import Path

import cv2
import numpy as np

from chromalens.white_balance import GrayWorldWhiteBalancer, WhiteBalanceConfig


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("artifacts/t03-lighting"),
        help="ignored output directory (default: artifacts/t03-lighting)",
    )
    args = parser.parse_args()
    args.output_dir.mkdir(parents=True, exist_ok=True)

    config = WhiteBalanceConfig()
    cast_bgr = _cast_chart(red_scale=1.35)
    still_result = GrayWorldWhiteBalancer(config).correct(cast_bgr)
    corrected_bgr = cv2.cvtColor(still_result.corrected_rgb, cv2.COLOR_RGB2BGR)
    comparison = np.hstack(
        (
            _label(cast_bgr, "Synthetic red cast (BGR input)"),
            _label(corrected_bgr, "Gray-world corrected (RGB output)"),
        )
    )
    _write_image(args.output_dir / "neutrality_comparison.png", comparison)

    sequence_balancer = GrayWorldWhiteBalancer(config)
    sequence_frames = [_cast_chart()]
    for index in range(12):
        sequence_frames.append(
            _cast_chart(
                red_scale=1.08 if index % 2 == 0 else 1.0,
                blue_scale=1.08 if index % 2 == 1 else 1.0,
            )
        )
    sequence_results = [
        sequence_balancer.correct(frame) for frame in sequence_frames
    ]
    raw_jumps = _gain_jumps(
        [np.asarray(result.raw_gains_bgr) for result in sequence_results]
    )
    smoothed_jumps = _gain_jumps(
        [np.asarray(result.gains_bgr) for result in sequence_results]
    )

    lighting_cases: dict[str, dict[str, float | str | bool]] = {}
    for name, frame in (
        ("neutral", _affected_frame(0.0, 0)),
        ("medium_dark", _affected_frame(0.25, 8)),
        ("poor_dark", _affected_frame(0.70, 8)),
        ("medium_clipped", _affected_frame(0.10, 255)),
        ("poor_clipped", _affected_frame(0.40, 255)),
    ):
        result = GrayWorldWhiteBalancer(config).correct(frame)
        lighting_cases[name] = {
            "level": result.lighting_quality.level.value,
            "dark_fraction": result.lighting_quality.dark_fraction,
            "clipped_fraction": result.lighting_quality.clipped_fraction,
            "gain_extremity": result.lighting_quality.gain_extremity,
            "temporal_gain_variation": (
                result.lighting_quality.temporal_gain_variation
            ),
            "valid_fraction": result.valid_fraction,
            "used_fallback": result.used_fallback,
        }

    before_rgb = cv2.cvtColor(cast_bgr, cv2.COLOR_BGR2RGB)
    evidence = {
        "method": "bounded Gray-world gains with per-stream EMA",
        "channel_contract": "input BGR uint8; output RGB uint8",
        "config": asdict(config),
        "neutrality_channel_mean_spread": {
            "before": _channel_mean_spread(before_rgb),
            "after": _channel_mean_spread(still_result.corrected_rgb),
        },
        "still_result": {
            "raw_gains_bgr": still_result.raw_gains_bgr,
            "applied_gains_bgr": still_result.gains_bgr,
            "valid_fraction": still_result.valid_fraction,
            "quality": still_result.lighting_quality.level.value,
        },
        "short_sequence": {
            "frame_count": len(sequence_frames),
            "maximum_raw_gain_jump_log2": max(raw_jumps),
            "maximum_smoothed_gain_jump_log2": max(smoothed_jumps),
        },
        "lighting_cases": lighting_cases,
    }
    evidence_path = args.output_dir / "evidence.json"
    evidence_path.write_text(
        json.dumps(evidence, indent=2, sort_keys=True),
        encoding="utf-8",
    )
    print(f"Wrote T03 evidence to {args.output_dir.resolve()}")
    print(json.dumps(evidence, indent=2, sort_keys=True))
    return 0


def _cast_chart(
    *,
    red_scale: float = 1.0,
    blue_scale: float = 1.0,
) -> np.ndarray:
    levels = np.array([[64, 96], [144, 192]], dtype=np.float64)
    gray = np.repeat(np.repeat(levels, 120, axis=0), 160, axis=1)
    rgb = np.stack((gray * red_scale, gray, gray * blue_scale), axis=2)
    rgb = np.clip(rgb, 0.0, 244.0).astype(np.uint8)
    return cv2.cvtColor(rgb, cv2.COLOR_RGB2BGR)


def _affected_frame(affected_fraction: float, affected_value: int) -> np.ndarray:
    frame = np.full((100, 100, 3), 128, dtype=np.uint8)
    affected_count = round(affected_fraction * 10_000)
    frame.reshape((-1, 3))[:affected_count] = affected_value
    return frame


def _gain_jumps(gains: list[np.ndarray]) -> list[float]:
    return [
        float(np.max(np.abs(np.log2(current / previous))))
        for previous, current in zip(gains, gains[1:])
    ]


def _channel_mean_spread(rgb: np.ndarray) -> float:
    return float(np.ptp(np.mean(rgb, axis=(0, 1))))


def _label(frame_bgr: np.ndarray, text: str) -> np.ndarray:
    output = frame_bgr.copy()
    cv2.rectangle(output, (0, 0), (output.shape[1], 32), (20, 20, 20), -1)
    cv2.putText(
        output,
        text,
        (8, 22),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.48,
        (255, 255, 255),
        1,
        cv2.LINE_AA,
    )
    return output


def _write_image(path: Path, image: np.ndarray) -> None:
    if not cv2.imwrite(str(path), image):
        raise RuntimeError(f"OpenCV could not write evidence image: {path}")


if __name__ == "__main__":
    raise SystemExit(main())
