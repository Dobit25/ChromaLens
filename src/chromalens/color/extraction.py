"""Compose preprocessing, color estimation, naming, and aligned submasks."""

from __future__ import annotations

from dataclasses import dataclass, field
from math import isfinite
from typing import Literal

import numpy as np

from chromalens.color.clustering import (
    ClusterEstimate,
    ClusteringConfig,
    deterministic_k2_estimates,
    robust_median_estimate,
)
from chromalens.color.naming import (
    ColorNamingConfig,
    name_cielab,
)
from chromalens.color.preprocessing import (
    PixelSelectionConfig,
    select_valid_garment_pixels,
)
from chromalens.contracts import (
    BinaryMask,
    ColorCluster,
    ColorFrame,
    GarmentRegion,
)

ExtractionMode = Literal["median", "k2"]


class InsufficientColorDataError(ValueError):
    """Raised when a garment lacks enough reliable pixels for color analysis."""


@dataclass(frozen=True, slots=True)
class ColorExtractionConfig:
    """Validated configuration for the complete T04 extraction pipeline."""

    mode: ExtractionMode = "k2"
    minimum_valid_pixels: int = 16
    minimum_valid_fraction: float = 0.10
    minimum_mask_confidence: float | None = None
    pixel_selection: PixelSelectionConfig = field(
        default_factory=PixelSelectionConfig
    )
    clustering: ClusteringConfig = field(
        default_factory=ClusteringConfig
    )
    naming: ColorNamingConfig = field(
        default_factory=ColorNamingConfig
    )

    def __post_init__(self) -> None:
        if self.mode not in ("median", "k2"):
            raise ValueError("mode must be either 'median' or 'k2'")

        if (
            isinstance(self.minimum_valid_pixels, bool)
            or not isinstance(self.minimum_valid_pixels, int)
            or self.minimum_valid_pixels < 1
        ):
            raise ValueError(
                "minimum_valid_pixels must be a positive integer"
            )

        if (
            not isfinite(self.minimum_valid_fraction)
            or not 0.0 <= self.minimum_valid_fraction <= 1.0
        ):
            raise ValueError(
                "minimum_valid_fraction must be within [0, 1]"
            )

        if self.minimum_mask_confidence is not None:
            if (
                not isfinite(self.minimum_mask_confidence)
                or not 0.0 <= self.minimum_mask_confidence <= 1.0
            ):
                raise ValueError(
                    "minimum_mask_confidence must be within [0, 1]"
                )


def extract_garment_colors(
    corrected_rgb: ColorFrame,
    garment: GarmentRegion,
    config: ColorExtractionConfig | None = None,
) -> tuple[ColorCluster, ...]:
    """Extract named original-color clusters from one garment region.

    The input must be corrected RGB from T03, not the original OpenCV BGR
    frame and not an assistive recolored frame.
    """

    selected_config = config or ColorExtractionConfig()
    _validate_known_mask_confidence(garment, selected_config)

    selection = select_valid_garment_pixels(
        corrected_rgb,
        garment.mask,
        selected_config.pixel_selection,
    )

    if selection.valid_count < selected_config.minimum_valid_pixels:
        raise InsufficientColorDataError(
            "garment does not contain enough valid pixels: "
            f"{selection.valid_count} available, "
            f"{selected_config.minimum_valid_pixels} required"
        )

    if selection.valid_fraction < selected_config.minimum_valid_fraction:
        raise InsufficientColorDataError(
            "valid garment-pixel fraction is below the configured minimum: "
            f"{selection.valid_fraction:.6f} available, "
            f"{selected_config.minimum_valid_fraction:.6f} required"
        )

    estimates = _estimate_colors(
        selection.pixels_rgb,
        selected_config,
    )

    return tuple(
        _build_color_cluster(
            estimate=estimate,
            valid_mask=selection.valid_mask,
            frame_shape=corrected_rgb.shape[:2],
            naming_config=selected_config.naming,
        )
        for estimate in estimates
    )


def _estimate_colors(
    pixels_rgb: np.ndarray,
    config: ColorExtractionConfig,
) -> tuple[ClusterEstimate, ...]:
    if config.mode == "median":
        return (robust_median_estimate(pixels_rgb),)

    return deterministic_k2_estimates(
        pixels_rgb,
        config.clustering,
    )


def _build_color_cluster(
    *,
    estimate: ClusterEstimate,
    valid_mask: BinaryMask,
    frame_shape: tuple[int, int],
    naming_config: ColorNamingConfig,
) -> ColorCluster:
    if estimate.members.shape != (int(np.count_nonzero(valid_mask)),):
        raise RuntimeError(
            "cluster membership does not align with selected valid pixels"
        )

    submask = np.zeros(frame_shape, dtype=np.bool_)
    submask[valid_mask] = estimate.members

    naming = name_cielab(
        estimate.lab,
        naming_config,
    )

    return ColorCluster(
        lab=estimate.lab,
        rgb=estimate.rgb,
        ratio=estimate.ratio,
        submask=submask,
        original_name=naming.name,
        name_scores=dict(naming.scores),
        color_margin=naming.margin,
    )


def _validate_known_mask_confidence(
    garment: GarmentRegion,
    config: ColorExtractionConfig,
) -> None:
    threshold = config.minimum_mask_confidence

    if (
        threshold is not None
        and garment.mask_confidence is not None
        and garment.mask_confidence < threshold
    ):
        raise InsufficientColorDataError(
            "garment mask confidence is below the configured minimum: "
            f"{garment.mask_confidence:.6f} available, "
            f"{threshold:.6f} required"
        )