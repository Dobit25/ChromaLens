"""Gray-world white balance and explainable lighting diagnostics.

OpenCV frames enter this module in BGR order. Corrected frames leave it in RGB
order for the downstream color pipeline. The source array is never modified.
"""

from __future__ import annotations

from dataclasses import dataclass
from math import ceil

import cv2
import numpy as np
from numpy.typing import NDArray

from chromalens.contracts import (
    BinaryMask,
    ColorFrame,
    FramePacket,
    LightingQuality,
    LightingQualityLevel,
)

GainArray = NDArray[np.float64]


@dataclass(frozen=True, slots=True)
class WhiteBalanceConfig:
    """Validated thresholds for Gray-world estimation and quality mapping."""

    valid_brightness_min: int = 16
    valid_brightness_max: int = 245
    valid_saturation_max: int = 220
    minimum_valid_fraction: float = 0.05
    ema_alpha: float = 0.25
    gain_min: float = 0.5
    gain_max: float = 2.0
    dark_threshold: int = 32
    clipped_threshold: int = 250
    medium_dark_fraction: float = 0.20
    poor_dark_fraction: float = 0.60
    medium_clipped_fraction: float = 0.05
    poor_clipped_fraction: float = 0.30
    medium_gain_extremity: float = 0.25
    poor_gain_extremity: float = 0.60
    medium_temporal_gain_variation: float = 0.08
    poor_temporal_gain_variation: float = 0.20

    def __post_init__(self) -> None:
        _validate_byte_threshold(
            self.valid_brightness_min,
            "valid_brightness_min",
        )
        _validate_byte_threshold(
            self.valid_brightness_max,
            "valid_brightness_max",
        )
        _validate_byte_threshold(
            self.valid_saturation_max,
            "valid_saturation_max",
        )
        _validate_byte_threshold(self.dark_threshold, "dark_threshold")
        _validate_byte_threshold(self.clipped_threshold, "clipped_threshold")
        if self.valid_brightness_min >= self.valid_brightness_max:
            raise ValueError(
                "valid_brightness_min must be less than valid_brightness_max"
            )
        if not 0.0 < self.minimum_valid_fraction <= 1.0:
            raise ValueError("minimum_valid_fraction must be within (0, 1]")
        if not 0.0 < self.ema_alpha <= 1.0:
            raise ValueError("ema_alpha must be within (0, 1]")
        if not 0.0 < self.gain_min <= 1.0 <= self.gain_max:
            raise ValueError("gain bounds must be positive and contain 1.0")
        _validate_quality_pair(
            self.medium_dark_fraction,
            self.poor_dark_fraction,
            "dark_fraction",
            upper_bound=1.0,
        )
        _validate_quality_pair(
            self.medium_clipped_fraction,
            self.poor_clipped_fraction,
            "clipped_fraction",
            upper_bound=1.0,
        )
        _validate_quality_pair(
            self.medium_gain_extremity,
            self.poor_gain_extremity,
            "gain_extremity",
        )
        _validate_quality_pair(
            self.medium_temporal_gain_variation,
            self.poor_temporal_gain_variation,
            "temporal_gain_variation",
        )


@dataclass(frozen=True, slots=True)
class WhiteBalanceResult:
    """One corrected RGB frame and the values used to explain the result.

    Gains use OpenCV's BGR channel order. ``raw_gains_bgr`` is the current
    Gray-world estimate, while ``gains_bgr`` is the bounded, EMA-smoothed value
    actually applied to the frame.
    """

    corrected_rgb: ColorFrame
    lighting_quality: LightingQuality
    raw_gains_bgr: tuple[float, float, float]
    gains_bgr: tuple[float, float, float]
    valid_fraction: float
    used_fallback: bool


class GrayWorldWhiteBalancer:
    """Stateful Gray-world correction with per-stream EMA gain smoothing."""

    def __init__(self, config: WhiteBalanceConfig | None = None) -> None:
        self.config = config or WhiteBalanceConfig()
        self._previous_gains_bgr: GainArray | None = None

    @property
    def previous_gains_bgr(self) -> tuple[float, float, float] | None:
        """Return the last applied gains without exposing mutable state."""

        if self._previous_gains_bgr is None:
            return None
        return _gain_tuple(self._previous_gains_bgr)

    def reset(self) -> None:
        """Clear temporal state before processing a new, unrelated stream."""

        self._previous_gains_bgr = None

    def correct(
        self,
        original_bgr: ColorFrame,
        *,
        estimation_mask: BinaryMask | None = None,
    ) -> WhiteBalanceResult:
        """Correct one BGR frame and return a new RGB frame plus diagnostics.

        ``estimation_mask`` optionally limits which pixels inform Gray-world
        gains. Lighting diagnostics still describe the complete camera frame.
        """

        _validate_color_frame(original_bgr)
        eligible_mask = _validate_estimation_mask(
            estimation_mask,
            original_bgr.shape,
        )
        valid_mask, valid_fraction, has_enough_pixels = _valid_estimation_pixels(
            original_bgr,
            eligible_mask,
            self.config,
        )

        previous_gains = self._previous_gains_bgr
        if has_enough_pixels:
            raw_gains = _estimate_gray_world_gains(
                original_bgr,
                valid_mask,
                self.config,
            )
            if previous_gains is None:
                applied_gains = raw_gains
            else:
                alpha = self.config.ema_alpha
                applied_gains = alpha * raw_gains + (1.0 - alpha) * previous_gains
            used_fallback = False
        else:
            raw_gains = (
                previous_gains.copy()
                if previous_gains is not None
                else np.ones(3, dtype=np.float64)
            )
            applied_gains = raw_gains.copy()
            used_fallback = True

        temporal_variation = (
            0.0
            if previous_gains is None
            else _maximum_log2_ratio(applied_gains, previous_gains)
        )
        self._previous_gains_bgr = applied_gains.copy()

        dark_fraction = float(
            np.mean(np.max(original_bgr, axis=2) <= self.config.dark_threshold)
        )
        clipped_fraction = float(
            np.mean(np.any(original_bgr >= self.config.clipped_threshold, axis=2))
        )
        gain_extremity = _maximum_log2_ratio(
            applied_gains,
            np.ones(3, dtype=np.float64),
        )
        quality = LightingQuality(
            level=_map_quality_level(
                dark_fraction=dark_fraction,
                clipped_fraction=clipped_fraction,
                gain_extremity=gain_extremity,
                temporal_gain_variation=temporal_variation,
                used_fallback=used_fallback,
                config=self.config,
            ),
            dark_fraction=dark_fraction,
            clipped_fraction=clipped_fraction,
            gain_extremity=gain_extremity,
            temporal_gain_variation=temporal_variation,
        )

        corrected_bgr = np.clip(
            original_bgr.astype(np.float64)
            * applied_gains.reshape((1, 1, 3)),
            0.0,
            255.0,
        ).astype(np.uint8)
        corrected_rgb = cv2.cvtColor(corrected_bgr, cv2.COLOR_BGR2RGB)

        return WhiteBalanceResult(
            corrected_rgb=corrected_rgb,
            lighting_quality=quality,
            raw_gains_bgr=_gain_tuple(raw_gains),
            gains_bgr=_gain_tuple(applied_gains),
            valid_fraction=valid_fraction,
            used_fallback=used_fallback,
        )

    def process(
        self,
        packet: FramePacket,
        *,
        estimation_mask: BinaryMask | None = None,
    ) -> WhiteBalanceResult:
        """Populate only derived packet fields and preserve ``original_bgr``."""

        result = self.correct(
            packet.original_bgr,
            estimation_mask=estimation_mask,
        )
        packet.corrected_rgb = result.corrected_rgb
        packet.lighting_quality = result.lighting_quality
        return result


def _valid_estimation_pixels(
    frame_bgr: ColorFrame,
    eligible_mask: BinaryMask,
    config: WhiteBalanceConfig,
) -> tuple[BinaryMask, float, bool]:
    hsv = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2HSV)
    saturation = hsv[:, :, 1]
    brightness = hsv[:, :, 2]
    valid_mask = (
        eligible_mask
        & (brightness >= config.valid_brightness_min)
        & (brightness <= config.valid_brightness_max)
        & (saturation <= config.valid_saturation_max)
    )
    eligible_count = int(np.count_nonzero(eligible_mask))
    valid_count = int(np.count_nonzero(valid_mask))
    valid_fraction = valid_count / eligible_count
    required_count = max(1, ceil(config.minimum_valid_fraction * eligible_count))
    return valid_mask, valid_fraction, valid_count >= required_count


def _estimate_gray_world_gains(
    frame_bgr: ColorFrame,
    valid_mask: BinaryMask,
    config: WhiteBalanceConfig,
) -> GainArray:
    channel_means = np.mean(frame_bgr[valid_mask], axis=0, dtype=np.float64)
    gray_target = float(np.mean(channel_means))
    raw_gains = np.divide(
        gray_target,
        channel_means,
        out=np.ones(3, dtype=np.float64),
        where=channel_means > 0.0,
    )
    return np.clip(raw_gains, config.gain_min, config.gain_max)


def _map_quality_level(
    *,
    dark_fraction: float,
    clipped_fraction: float,
    gain_extremity: float,
    temporal_gain_variation: float,
    used_fallback: bool,
    config: WhiteBalanceConfig,
) -> LightingQualityLevel:
    if used_fallback or any(
        (
            dark_fraction >= config.poor_dark_fraction,
            clipped_fraction >= config.poor_clipped_fraction,
            gain_extremity >= config.poor_gain_extremity,
            temporal_gain_variation >= config.poor_temporal_gain_variation,
        )
    ):
        return LightingQualityLevel.POOR
    if any(
        (
            dark_fraction >= config.medium_dark_fraction,
            clipped_fraction >= config.medium_clipped_fraction,
            gain_extremity >= config.medium_gain_extremity,
            temporal_gain_variation >= config.medium_temporal_gain_variation,
        )
    ):
        return LightingQualityLevel.MEDIUM
    return LightingQualityLevel.GOOD


def _validate_color_frame(frame: ColorFrame) -> None:
    if frame.dtype != np.uint8 or frame.ndim != 3 or frame.shape[2] != 3:
        raise ValueError("original_bgr must be a uint8 H x W x 3 color frame")
    if frame.shape[0] == 0 or frame.shape[1] == 0:
        raise ValueError("original_bgr dimensions must be non-empty")


def _validate_estimation_mask(
    mask: BinaryMask | None,
    frame_shape: tuple[int, ...],
) -> BinaryMask:
    if mask is None:
        return np.ones(frame_shape[:2], dtype=np.bool_)
    if mask.dtype != np.bool_ or mask.ndim != 2:
        raise ValueError("estimation_mask must be a boolean H x W mask")
    if mask.shape != frame_shape[:2]:
        raise ValueError("estimation_mask must align with original_bgr")
    if not np.any(mask):
        raise ValueError("estimation_mask must contain at least one selected pixel")
    return mask


def _maximum_log2_ratio(first: GainArray, second: GainArray) -> float:
    return float(np.max(np.abs(np.log2(first / second))))


def _gain_tuple(gains: GainArray) -> tuple[float, float, float]:
    return (float(gains[0]), float(gains[1]), float(gains[2]))


def _validate_byte_threshold(value: int, field_name: str) -> None:
    if not isinstance(value, int) or not 0 <= value <= 255:
        raise ValueError(f"{field_name} must be an integer within [0, 255]")


def _validate_quality_pair(
    medium: float,
    poor: float,
    field_name: str,
    *,
    upper_bound: float | None = None,
) -> None:
    if medium < 0.0 or poor < medium:
        raise ValueError(
            f"{field_name} quality thresholds must satisfy 0 <= medium <= poor"
        )
    if upper_bound is not None and poor > upper_bound:
        raise ValueError(
            f"{field_name} quality thresholds must not exceed {upper_bound}"
        )
