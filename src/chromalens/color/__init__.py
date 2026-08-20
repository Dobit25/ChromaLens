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

from chromalens.color.clustering import (
    ClusterEstimate,
    ClusteringConfig,
    deterministic_k2_estimates,
    robust_median_estimate,
)

from chromalens.color.extraction import (
    ColorExtractionConfig,
    ExtractionMode,
    InsufficientColorDataError,
    extract_garment_colors,
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
    "ClusterEstimate",
    "ClusteringConfig",
    "deterministic_k2_estimates",
    "robust_median_estimate",
    "ColorExtractionConfig",
    "ExtractionMode",
    "InsufficientColorDataError",
    "extract_garment_colors",
]