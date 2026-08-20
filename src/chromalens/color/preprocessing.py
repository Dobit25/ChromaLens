"""Mask erosion and valid-pixel selection for corrected RGB garments."""

from __future__ import annotations

from dataclasses import dataclass

import cv2
import numpy as np
from numpy.typing import NDArray

from chromalens.contracts import BinaryMask, ColorFrame

RGBPixels = NDArray[np.uint8]


@dataclass(frozen=True, slots=True)
class PixelSelectionConfig:
    """Thresholds used before estimating garment colors."""

    erosion_kernel_size: int = 3
    erosion_iterations: int = 1
    minimum_brightness: int = 16
    clipped_threshold: int = 250

    def __post_init__(self) -> None:
        if (
            isinstance(self.erosion_kernel_size, bool)
            or not isinstance(self.erosion_kernel_size, int)
            or self.erosion_kernel_size < 1
            or self.erosion_kernel_size % 2 == 0
        ):
            raise ValueError("erosion_kernel_size must be a positive odd integer")
        if (
            isinstance(self.erosion_iterations, bool)
            or not isinstance(self.erosion_iterations, int)
            or self.erosion_iterations < 0
        ):
            raise ValueError("erosion_iterations must be a non-negative integer")

        _validate_byte_threshold(self.minimum_brightness, "minimum_brightness")
        _validate_byte_threshold(self.clipped_threshold, "clipped_threshold")

        if self.minimum_brightness >= self.clipped_threshold:
            raise ValueError(
                "minimum_brightness must be less than clipped_threshold"
            )


@dataclass(frozen=True, slots=True)
class PixelSelection:
    """Explainable masks and RGB pixels retained for color estimation."""

    eroded_mask: BinaryMask
    valid_mask: BinaryMask
    pixels_rgb: RGBPixels

    @property
    def eligible_count(self) -> int:
        return int(np.count_nonzero(self.eroded_mask))

    @property
    def valid_count(self) -> int:
        return int(np.count_nonzero(self.valid_mask))

    @property
    def valid_fraction(self) -> float:
        if self.eligible_count == 0:
            return 0.0
        return self.valid_count / self.eligible_count


def select_valid_garment_pixels(
    corrected_rgb: ColorFrame,
    garment_mask: BinaryMask,
    config: PixelSelectionConfig | None = None,
) -> PixelSelection:
    """Erode an aligned garment mask and exclude invalid RGB pixels.

    Brightness is the maximum RGB channel. A pixel is clipped when any channel
    reaches ``clipped_threshold``. The input image and mask are never modified.
    """

    selected_config = config or PixelSelectionConfig()
    _validate_corrected_rgb(corrected_rgb)
    _validate_garment_mask(garment_mask, corrected_rgb.shape)

    eroded_mask = _erode_mask(garment_mask, selected_config)
    brightness = np.max(corrected_rgb, axis=2)
    bright_enough = brightness >= selected_config.minimum_brightness
    not_clipped = np.all(
        corrected_rgb < selected_config.clipped_threshold,
        axis=2,
    )
    valid_mask = eroded_mask & bright_enough & not_clipped
    pixels_rgb = corrected_rgb[valid_mask].copy()

    return PixelSelection(
        eroded_mask=eroded_mask,
        valid_mask=valid_mask,
        pixels_rgb=pixels_rgb,
    )


def _erode_mask(
    garment_mask: BinaryMask,
    config: PixelSelectionConfig,
) -> BinaryMask:
    if config.erosion_iterations == 0:
        return garment_mask.copy()

    kernel = np.ones(
        (config.erosion_kernel_size, config.erosion_kernel_size),
        dtype=np.uint8,
    )
    eroded = cv2.erode(
        garment_mask.astype(np.uint8),
        kernel,
        iterations=config.erosion_iterations,
        borderType=cv2.BORDER_CONSTANT,
        borderValue=0,
    )
    return eroded.astype(np.bool_)


def _validate_corrected_rgb(frame: ColorFrame) -> None:
    if frame.dtype != np.uint8 or frame.ndim != 3 or frame.shape[2] != 3:
        raise ValueError("corrected_rgb must be a uint8 H x W x 3 RGB frame")
    if frame.shape[0] == 0 or frame.shape[1] == 0:
        raise ValueError("corrected_rgb dimensions must be non-empty")


def _validate_garment_mask(
    mask: BinaryMask,
    frame_shape: tuple[int, ...],
) -> None:
    if mask.dtype != np.bool_ or mask.ndim != 2:
        raise ValueError("garment_mask must be a boolean H x W mask")
    if mask.shape != frame_shape[:2]:
        raise ValueError("garment_mask must align with corrected_rgb")


def _validate_byte_threshold(value: int, field_name: str) -> None:
    if (
        isinstance(value, bool)
        or not isinstance(value, int)
        or not 0 <= value <= 255
    ):
        raise ValueError(f"{field_name} must be an integer within [0, 255]")