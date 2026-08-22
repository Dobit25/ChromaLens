"""Deterministic T03 tests with no camera, network, or model dependency."""

from __future__ import annotations

import cv2
import numpy as np
import pytest

from chromalens.contracts import FramePacket, LightingQualityLevel
from chromalens.white_balance import GrayWorldWhiteBalancer, WhiteBalanceConfig


def test_synthetic_channel_cast_moves_toward_neutral_without_source_mutation() -> None:
    source_bgr = _cast_neutral_chart(red_scale=1.35)
    original_copy = source_bgr.copy()
    before_rgb = cv2.cvtColor(source_bgr, cv2.COLOR_BGR2RGB)

    result = GrayWorldWhiteBalancer().correct(source_bgr)

    before_spread = float(np.ptp(np.mean(before_rgb, axis=(0, 1))))
    after_spread = float(np.ptp(np.mean(result.corrected_rgb, axis=(0, 1))))
    assert after_spread < before_spread * 0.15
    assert result.corrected_rgb.dtype == np.uint8
    assert result.corrected_rgb.shape == source_bgr.shape
    assert not result.used_fallback
    np.testing.assert_array_equal(source_bgr, original_copy)


@pytest.mark.parametrize(
    ("affected_fraction", "expected_level"),
    [
        (0.0, LightingQualityLevel.GOOD),
        (0.25, LightingQualityLevel.MEDIUM),
        (0.70, LightingQualityLevel.POOR),
    ],
)
def test_darkness_severity_changes_quality_level(
    affected_fraction: float,
    expected_level: LightingQualityLevel,
) -> None:
    frame = _partially_affected_frame(affected_fraction, pixel_value=8)

    quality = GrayWorldWhiteBalancer().correct(frame).lighting_quality

    assert quality.level is expected_level
    assert quality.dark_fraction == pytest.approx(affected_fraction)
    assert quality.clipped_fraction == pytest.approx(0.0)


@pytest.mark.parametrize(
    ("affected_fraction", "expected_level"),
    [
        (0.0, LightingQualityLevel.GOOD),
        (0.10, LightingQualityLevel.MEDIUM),
        (0.40, LightingQualityLevel.POOR),
    ],
)
def test_clipping_severity_changes_quality_level(
    affected_fraction: float,
    expected_level: LightingQualityLevel,
) -> None:
    frame = _partially_affected_frame(affected_fraction, pixel_value=255)

    quality = GrayWorldWhiteBalancer().correct(frame).lighting_quality

    assert quality.level is expected_level
    assert quality.dark_fraction == pytest.approx(0.0)
    assert quality.clipped_fraction == pytest.approx(affected_fraction)


def test_consecutive_gain_estimates_are_smoothed_for_short_sequence() -> None:
    balancer = GrayWorldWhiteBalancer(WhiteBalanceConfig(ema_alpha=0.20))
    frames = [_cast_neutral_chart()]
    for index in range(12):
        frames.append(
            _cast_neutral_chart(
                red_scale=1.08 if index % 2 == 0 else 1.0,
                blue_scale=1.08 if index % 2 == 1 else 1.0,
            )
        )

    results = [balancer.correct(frame) for frame in frames]
    raw_jumps = [
        _gain_jump(results[index].raw_gains_bgr, results[index - 1].raw_gains_bgr)
        for index in range(1, len(results))
    ]
    smoothed_jumps = [
        _gain_jump(results[index].gains_bgr, results[index - 1].gains_bgr)
        for index in range(1, len(results))
    ]
    source_means = [
        np.mean(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB), axis=(0, 1))
        for frame in frames
    ]
    corrected_means = [
        np.mean(result.corrected_rgb, axis=(0, 1)) for result in results
    ]
    source_mean_jumps = [
        float(np.max(np.abs(source_means[index] - source_means[index - 1])))
        for index in range(1, len(source_means))
    ]
    corrected_mean_jumps = [
        float(np.max(np.abs(corrected_means[index] - corrected_means[index - 1])))
        for index in range(1, len(corrected_means))
    ]

    assert max(smoothed_jumps) < max(raw_jumps) * 0.30
    assert max(corrected_mean_jumps) < max(source_mean_jumps)
    assert all(
        result.lighting_quality.temporal_gain_variation >= 0.0
        for result in results
    )


def test_process_populates_only_derived_packet_fields() -> None:
    source_bgr = _cast_neutral_chart(red_scale=1.25)
    original_copy = source_bgr.copy()
    packet = FramePacket(frame_id=7, timestamp_ns=1234, original_bgr=source_bgr)

    result = GrayWorldWhiteBalancer().process(packet)

    assert packet.corrected_rgb is result.corrected_rgb
    assert packet.lighting_quality is result.lighting_quality
    assert packet.frame_id == 7
    assert packet.timestamp_ns == 1234
    np.testing.assert_array_equal(packet.original_bgr, original_copy)


def test_optional_mask_limits_gain_estimation_and_must_align() -> None:
    frame = np.empty((20, 40, 3), dtype=np.uint8)
    frame[:, :20] = (80, 80, 120)
    frame[:, 20:] = (160, 80, 80)
    left_mask = np.zeros((20, 40), dtype=np.bool_)
    left_mask[:, :20] = True

    masked = GrayWorldWhiteBalancer().correct(frame, estimation_mask=left_mask)
    unmasked = GrayWorldWhiteBalancer().correct(frame)

    assert masked.valid_fraction == pytest.approx(1.0)
    assert masked.raw_gains_bgr != pytest.approx(unmasked.raw_gains_bgr)
    with pytest.raises(ValueError, match="align"):
        GrayWorldWhiteBalancer().correct(
            frame,
            estimation_mask=np.ones((19, 40), dtype=np.bool_),
        )
    with pytest.raises(ValueError, match="boolean"):
        GrayWorldWhiteBalancer().correct(
            frame,
            estimation_mask=np.ones((20, 40), dtype=np.uint8),
        )


def test_insufficient_valid_pixels_fail_safe_and_reset_clears_temporal_state() -> None:
    balancer = GrayWorldWhiteBalancer()
    initial = balancer.correct(_cast_neutral_chart(red_scale=1.20))
    saturated = np.full((20, 20, 3), (0, 0, 255), dtype=np.uint8)

    fallback = balancer.correct(saturated)

    assert fallback.used_fallback
    assert fallback.valid_fraction == pytest.approx(0.0)
    assert fallback.gains_bgr == pytest.approx(initial.gains_bgr)
    assert fallback.lighting_quality.level is LightingQualityLevel.POOR
    balancer.reset()
    assert balancer.previous_gains_bgr is None
    after_reset = balancer.correct(_cast_neutral_chart(blue_scale=1.15))
    assert after_reset.gains_bgr == pytest.approx(after_reset.raw_gains_bgr)
    assert after_reset.lighting_quality.temporal_gain_variation == pytest.approx(0.0)


@pytest.mark.parametrize(
    "config_kwargs",
    [
        {"valid_brightness_min": 245, "valid_brightness_max": 16},
        {"minimum_valid_fraction": 0.0},
        {"ema_alpha": 1.1},
        {"gain_min": 1.1},
        {"medium_dark_fraction": 0.7, "poor_dark_fraction": 0.6},
    ],
)
def test_invalid_configuration_fails_fast(config_kwargs: dict[str, float]) -> None:
    with pytest.raises(ValueError):
        WhiteBalanceConfig(**config_kwargs)  # type: ignore[arg-type]


def _cast_neutral_chart(
    *,
    red_scale: float = 1.0,
    blue_scale: float = 1.0,
) -> np.ndarray:
    levels = np.array([[64, 96], [144, 192]], dtype=np.float64)
    gray = np.repeat(np.repeat(levels, 16, axis=0), 16, axis=1)
    rgb = np.stack((gray * red_scale, gray, gray * blue_scale), axis=2)
    rgb = np.clip(rgb, 0.0, 244.0).astype(np.uint8)
    return cv2.cvtColor(rgb, cv2.COLOR_RGB2BGR)


def _partially_affected_frame(affected_fraction: float, pixel_value: int) -> np.ndarray:
    frame = np.full((10, 10, 3), 128, dtype=np.uint8)
    affected_count = round(affected_fraction * 100)
    frame.reshape((-1, 3))[:affected_count] = pixel_value
    return frame


def _gain_jump(
    first: tuple[float, float, float],
    second: tuple[float, float, float],
) -> float:
    first_array = np.asarray(first)
    second_array = np.asarray(second)
    return float(np.max(np.abs(np.log2(first_array / second_array))))
