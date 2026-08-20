"""Dominant-color extraction and naming components for T04."""

from chromalens.color.preprocessing import (
    PixelSelection,
    PixelSelectionConfig,
    select_valid_garment_pixels,
)

__all__ = [
    "PixelSelection",
    "PixelSelectionConfig",
    "select_valid_garment_pixels",
]