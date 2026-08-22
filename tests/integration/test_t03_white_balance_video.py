"""T03 integration evidence through the real T01 local-video source."""

from __future__ import annotations

from pathlib import Path

import cv2
import numpy as np

from chromalens.camera import open_video
from chromalens.white_balance import GrayWorldWhiteBalancer, WhiteBalanceConfig


def test_short_video_uses_smoothed_gains_without_source_mutation(
    tmp_path: Path,
) -> None:
    video_path = tmp_path / "lighting-sequence.avi"
    _write_cast_sequence(video_path)
    source = open_video(video_path)
    balancer = GrayWorldWhiteBalancer(WhiteBalanceConfig(ema_alpha=0.20))
    raw_gains: list[np.ndarray] = []
    smoothed_gains: list[np.ndarray] = []
    corrected_means: list[np.ndarray] = []
    source_means: list[np.ndarray] = []

    try:
        while (packet := source.read()) is not None:
            source_copy = packet.original_bgr.copy()
            result = balancer.process(packet)
            raw_gains.append(np.asarray(result.raw_gains_bgr))
            smoothed_gains.append(np.asarray(result.gains_bgr))
            source_means.append(
                np.mean(
                    cv2.cvtColor(packet.original_bgr, cv2.COLOR_BGR2RGB),
                    axis=(0, 1),
                )
            )
            corrected_means.append(np.mean(result.corrected_rgb, axis=(0, 1)))
            np.testing.assert_array_equal(packet.original_bgr, source_copy)
    finally:
        source.close()

    raw_jumps = _gain_jumps(raw_gains)
    smoothed_jumps = _gain_jumps(smoothed_gains)
    source_jumps = _mean_jumps(source_means)
    corrected_jumps = _mean_jumps(corrected_means)

    assert len(raw_gains) == 13
    assert max(smoothed_jumps) < max(raw_jumps) * 0.30
    assert max(smoothed_jumps) < 0.03
    assert max(corrected_jumps) < max(source_jumps)


def _write_cast_sequence(path: Path) -> None:
    writer = cv2.VideoWriter(
        str(path),
        cv2.VideoWriter_fourcc(*"MJPG"),
        12.0,
        (64, 48),
    )
    assert writer.isOpened(), "OpenCV MJPG writer is required for the T03 smoke test"
    try:
        writer.write(_cast_frame())
        for index in range(12):
            writer.write(
                _cast_frame(
                    red_scale=1.08 if index % 2 == 0 else 1.0,
                    blue_scale=1.08 if index % 2 == 1 else 1.0,
                )
            )
    finally:
        writer.release()


def _cast_frame(
    *,
    red_scale: float = 1.0,
    blue_scale: float = 1.0,
) -> np.ndarray:
    levels = np.array([[64, 96], [144, 192]], dtype=np.float64)
    gray = np.repeat(np.repeat(levels, 24, axis=0), 32, axis=1)
    rgb = np.stack((gray * red_scale, gray, gray * blue_scale), axis=2)
    return cv2.cvtColor(
        np.clip(rgb, 0.0, 244.0).astype(np.uint8),
        cv2.COLOR_RGB2BGR,
    )


def _gain_jumps(gains: list[np.ndarray]) -> list[float]:
    return [
        float(np.max(np.abs(np.log2(current / previous))))
        for previous, current in zip(gains, gains[1:])
    ]


def _mean_jumps(means: list[np.ndarray]) -> list[float]:
    return [
        float(np.max(np.abs(current - previous)))
        for previous, current in zip(means, means[1:])
    ]
