"""Typed, backend-independent data contracts for the ChromaLens pipeline."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

import numpy as np
from numpy.typing import NDArray

ColorFrame = NDArray[np.uint8]
BinaryMask = NDArray[np.bool_]


class LightingQualityLevel(str, Enum):
    """Coarse lighting diagnostic shown separately from confidence and risk."""

    GOOD = "good"
    MEDIUM = "medium"
    POOR = "poor"


@dataclass(frozen=True, slots=True)
class LightingQuality:
    """Lighting label plus raw, explainable diagnostics."""

    level: LightingQualityLevel
    dark_fraction: float
    clipped_fraction: float
    gain_extremity: float
    temporal_gain_variation: float

    def __post_init__(self) -> None:
        for field_name in ("dark_fraction", "clipped_fraction"):
            value = getattr(self, field_name)
            if not 0.0 <= value <= 1.0:
                raise ValueError(f"{field_name} must be within [0, 1]")
        if self.gain_extremity < 0.0:
            raise ValueError("gain_extremity must be non-negative")
        if self.temporal_gain_variation < 0.0:
            raise ValueError("temporal_gain_variation must be non-negative")


@dataclass(slots=True)
class FramePacket:
    """One source frame and analysis products tied to its identity and time."""

    frame_id: int
    timestamp_ns: int
    original_bgr: ColorFrame
    corrected_rgb: ColorFrame | None = None
    lighting_quality: LightingQuality | None = None

    def __post_init__(self) -> None:
        if self.frame_id < 0:
            raise ValueError("frame_id must be non-negative")
        if self.timestamp_ns < 0:
            raise ValueError("timestamp_ns must be non-negative")
        _validate_color_frame(self.original_bgr, "original_bgr")
        if self.corrected_rgb is not None:
            _validate_color_frame(self.corrected_rgb, "corrected_rgb")
            if self.corrected_rgb.shape != self.original_bgr.shape:
                raise ValueError("corrected_rgb must align with original_bgr")


@dataclass(slots=True)
class GarmentRegion:
    """A semantic garment mask aligned with its source frame."""

    track_id: int | None
    class_name: str
    mask: BinaryMask
    mask_confidence: float | None = None

    def __post_init__(self) -> None:
        _validate_binary_mask(self.mask, "mask")
        if not self.class_name.strip():
            raise ValueError("class_name must not be empty")
        if self.mask_confidence is not None and not 0.0 <= self.mask_confidence <= 1.0:
            raise ValueError("mask_confidence must be within [0, 1]")


@dataclass(slots=True)
class ColorCluster:
    """One retained estimate of an original corrected garment color."""

    lab: tuple[float, float, float]
    rgb: tuple[int, int, int]
    ratio: float
    submask: BinaryMask
    original_name: str
    name_scores: dict[str, float]
    color_margin: float | None = None

    def __post_init__(self) -> None:
        if not 0.0 <= self.ratio <= 1.0:
            raise ValueError("ratio must be within [0, 1]")
        if any(channel < 0 or channel > 255 for channel in self.rgb):
            raise ValueError("rgb channels must be within [0, 255]")
        _validate_binary_mask(self.submask, "submask")
        if not self.original_name.strip():
            raise ValueError("original_name must not be empty")


@dataclass(frozen=True, slots=True)
class RiskAssessment:
    """Explainable relational color risk, separate from all confidences."""

    source_id: str
    comparison_id: str
    delta_e_original: float
    delta_e_cvd: float
    risk_score: float
    risk_level: str

    def __post_init__(self) -> None:
        if self.delta_e_original < 0.0 or self.delta_e_cvd < 0.0:
            raise ValueError("Delta-E values must be non-negative")
        if not 0.0 <= self.risk_score <= 1.0:
            raise ValueError("risk_score must be within [0, 1]")
        if not self.source_id or not self.comparison_id:
            raise ValueError("risk comparison identifiers must not be empty")
        if not self.risk_level:
            raise ValueError("risk_level must not be empty")


def _validate_color_frame(frame: ColorFrame, field_name: str) -> None:
    if frame.dtype != np.uint8 or frame.ndim != 3 or frame.shape[2] != 3:
        raise ValueError(f"{field_name} must be a uint8 H x W x 3 color frame")


def _validate_binary_mask(mask: BinaryMask, field_name: str) -> None:
    if mask.dtype != np.bool_ or mask.ndim != 2:
        raise ValueError(f"{field_name} must be a boolean H x W mask")
