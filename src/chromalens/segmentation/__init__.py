"""Public exports for the chromalens.segmentation package."""

from chromalens.segmentation.async_keyframes import (
    AsyncKeyframeConfig,
    AsyncKeyframeSegmenter,
)
from chromalens.segmentation.base import (
    SegmentationFrameTelemetry,
    SegmentationMaskSource,
    Segmenter,
    SegmenterUnavailableError,
)
from chromalens.segmentation.debug import draw_mask_overlay
from chromalens.segmentation.mediapipe_backend import (
    MediaPipeBackendUnavailableError,
    MediaPipeSegmenter,
    MediaPipeSegmenterConfig,
    apply_mask_cleanup,
    compute_mask_confidence,
)
from chromalens.segmentation.schp_backend import (
    SCHP_ATR_CHECKPOINT_SHA256,
    SCHPBackendUnavailableError,
    SCHPSegmenter,
    SCHPSegmenterConfig,
)

__all__ = [
    "Segmenter",
    "SegmenterUnavailableError",
    "SegmentationFrameTelemetry",
    "SegmentationMaskSource",
    "AsyncKeyframeConfig",
    "AsyncKeyframeSegmenter",
    "draw_mask_overlay",
    "apply_mask_cleanup",
    "compute_mask_confidence",
    "MediaPipeSegmenter",
    "MediaPipeSegmenterConfig",
    "MediaPipeBackendUnavailableError",
    "SCHPSegmenter",
    "SCHPSegmenterConfig",
    "SCHPBackendUnavailableError",
    "SCHP_ATR_CHECKPOINT_SHA256",
]
