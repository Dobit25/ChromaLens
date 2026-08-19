"""Public exports for the chromalens.segmentation package."""

from chromalens.segmentation.base import Segmenter, SegmenterUnavailableError
from chromalens.segmentation.debug import draw_mask_overlay
from chromalens.segmentation.mediapipe_backend import (
    MediaPipeBackendUnavailableError,
    MediaPipeSegmenter,
    MediaPipeSegmenterConfig,
    apply_mask_cleanup,
    compute_mask_confidence,
)
from chromalens.segmentation.schp_backend import SCHPSegmenter

__all__ = [
    "Segmenter",
    "SegmenterUnavailableError",
    "draw_mask_overlay",
    "apply_mask_cleanup",
    "compute_mask_confidence",
    "MediaPipeSegmenter",
    "MediaPipeSegmenterConfig",
    "MediaPipeBackendUnavailableError",
    "SCHPSegmenter",
]
