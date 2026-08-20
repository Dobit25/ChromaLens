"""Dominant-color extraction and naming components for T04."""

from chromalens.color.naming import (
    BASIC_COLOR_PROTOTYPES,
    ColorNameResult,
    ColorNamingConfig,
    ColorPrototype,
    name_cielab,
    name_rgb,
    rgb_to_cielab,
)

from chromalens.color.preprocessing import (
    PixelSelection,
    PixelSelectionConfig,
    select_valid_garment_pixels,
)

__all__ = [
    "PixelSelection",
    "PixelSelectionConfig",
    "select_valid_garment_pixels",
    "BASIC_COLOR_PROTOTYPES",
    "ColorNameResult",
    "ColorNamingConfig",
    "ColorPrototype",
    "name_cielab",
    "name_rgb",
    "rgb_to_cielab",
]