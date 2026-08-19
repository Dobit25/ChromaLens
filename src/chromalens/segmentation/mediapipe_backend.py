"""MediaPipe Selfie Segmentation backend for garment masking.

This backend uses MediaPipe's SelfieSegmentation (model_selection=1, full-body)
to produce an upper-clothes binary mask aligned with the source frame.

Dependency group: segment-mediapipe
Install:  pip install "chromalens-ai[segment-mediapipe]"
License:  MediaPipe — Apache-2.0 (https://github.com/google/mediapipe)
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from types import ModuleType
from typing import TYPE_CHECKING

import cv2
import numpy as np
from numpy.typing import NDArray

from chromalens.contracts import BinaryMask, ColorFrame, FramePacket, GarmentRegion
from chromalens.segmentation.base import Segmenter, SegmenterUnavailableError

if TYPE_CHECKING:
    pass  # mediapipe imported lazily at runtime

_logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Error
# ---------------------------------------------------------------------------

class MediaPipeBackendUnavailableError(SegmenterUnavailableError):
    """Raised when MediaPipe is not installed or cannot be initialised."""


# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

@dataclass(frozen=True, slots=True)
class MediaPipeSegmenterConfig:
    """Immutable configuration for the MediaPipe segmentation backend.

    All thresholds are intentional heuristics, not calibrated probabilities.
    Document changes to these values in codinglog.md.

    Attributes:
        model_selection: 0 = general (faster), 1 = landscape/full-body (better).
        confidence_threshold: Minimum per-pixel probability to classify as
            foreground. Default 0.5 is the recommended starting point.
        head_skip_ratio: Fraction of frame height (from top) to exclude.
            Removes face/head region which SelfieSegmentation includes in the
            silhouette but is not a garment. Default 0.20 skips top 20%.
        upper_body_ratio: Fraction of frame height (from top) that defines the
            lower boundary of the valid garment region. Limits false positives
            from floor/background.
        min_area_ratio: Components smaller than this fraction of total frame
            pixels are discarded as segmentation noise.
        morph_kernel_size: Square kernel size for morphological open/close.
    """

    model_selection: int = 1
    confidence_threshold: float = 0.5
    head_skip_ratio: float = 0.22        # skip top 22% -- excludes face/head
    upper_body_ratio: float = 0.80       # keep up to 80% height -- torso region
    min_area_ratio: float = 0.005
    morph_kernel_size: int = 5


# ---------------------------------------------------------------------------
# Lazy import
# ---------------------------------------------------------------------------

def _import_mediapipe() -> ModuleType:
    """Import mediapipe or raise a clear, actionable error.

    Returns:
        The ``mediapipe`` module.

    Raises:
        MediaPipeBackendUnavailableError: If mediapipe is not installed.
    """
    try:
        import mediapipe as mp  # noqa: PLC0415
        return mp
    except ImportError as exc:
        raise MediaPipeBackendUnavailableError(
            "MediaPipe is not installed. "
            "Run: pip install \"chromalens-ai[segment-mediapipe]\""
        ) from exc


# ---------------------------------------------------------------------------
# Mask utilities (pure functions — testable without MediaPipe)
# ---------------------------------------------------------------------------

def apply_mask_cleanup(
    confidence_map: NDArray[np.float32],
    *,
    threshold: float = 0.5,
    head_skip_ratio: float = 0.22,
    upper_body_ratio: float = 0.80,
    min_area_ratio: float = 0.005,
    morph_kernel_size: int = 5,
) -> BinaryMask:
    """Threshold, filter, and clean a MediaPipe confidence map.

    Steps:
        1. Threshold at ``threshold`` -> raw boolean mask.
        2. Apply head exclusion: zero out the top ``head_skip_ratio`` rows
           to remove face/hair which SelfieSegmentation includes in the
           person silhouette but are not garments.
        3. Apply lower body cutoff: zero out rows below ``upper_body_ratio``
           to remove legs/floor false positives.
        4. Morphological open then close to remove noise and fill small holes.
        5. Retain only the largest connected component; discard it entirely
           if it is smaller than ``min_area_ratio`` of total frame pixels.

    Args:
        confidence_map: Float32 array of shape ``H x W`` with values in
            ``[0, 1]`` as returned by MediaPipe SelfieSegmentation.
        threshold: Per-pixel foreground probability cutoff.
        head_skip_ratio: Fraction of frame height (from top) to exclude
            (face/head region).
        upper_body_ratio: Fraction of frame height (from top) defining the
            lower boundary of the garment region.
        min_area_ratio: Minimum component size as a fraction of frame area.
        morph_kernel_size: Square structuring element size in pixels.

    Returns:
        Boolean ``H x W`` mask aligned with the source frame.

    Raises:
        ValueError: If ``confidence_map`` is not a 2-D float32 array.
    """
    if confidence_map.ndim != 2 or confidence_map.dtype != np.float32:
        raise ValueError(
            "confidence_map must be a 2-D float32 array; "
            f"got shape={confidence_map.shape} dtype={confidence_map.dtype}"
        )

    h, w = confidence_map.shape
    total_pixels = h * w

    # Step 1 -- threshold
    raw_mask = confidence_map >= threshold

    # Step 2 -- head/face exclusion (top region)
    head_cutoff = int(h * head_skip_ratio)
    raw_mask[:head_cutoff, :] = False

    # Step 3 -- lower body cutoff
    lower_cutoff = int(h * upper_body_ratio)
    raw_mask[lower_cutoff:, :] = False

    # Step 4 -- morphological open (remove noise) then close (fill holes)
    kernel = cv2.getStructuringElement(
        cv2.MORPH_ELLIPSE,
        (morph_kernel_size, morph_kernel_size),
    )
    uint8_mask = raw_mask.astype(np.uint8) * 255
    uint8_mask = cv2.morphologyEx(uint8_mask, cv2.MORPH_OPEN, kernel)
    uint8_mask = cv2.morphologyEx(uint8_mask, cv2.MORPH_CLOSE, kernel)

    # Step 5 -- keep largest connected component
    num_labels, labels, stats, _ = cv2.connectedComponentsWithStats(
        uint8_mask, connectivity=8
    )

    if num_labels <= 1:
        # Only background label exists
        _logger.debug("apply_mask_cleanup: no foreground component found")
        return np.zeros((h, w), dtype=np.bool_)

    # stats[0] is background; find largest foreground component
    foreground_stats = stats[1:]  # shape (N, 5)
    largest_idx = int(np.argmax(foreground_stats[:, cv2.CC_STAT_AREA])) + 1
    largest_area = int(stats[largest_idx, cv2.CC_STAT_AREA])

    min_area = int(total_pixels * min_area_ratio)
    if largest_area < min_area:
        _logger.debug(
            "apply_mask_cleanup: largest component (%d px) below min_area (%d px); "
            "returning empty mask",
            largest_area,
            min_area,
        )
        return np.zeros((h, w), dtype=np.bool_)

    result: BinaryMask = (labels == largest_idx).astype(np.bool_)
    kept = int(result.sum())
    _logger.debug(
        "apply_mask_cleanup: kept %d / %d pixels (%.1f%%)",
        kept,
        total_pixels,
        100.0 * kept / total_pixels,
    )
    return result


def compute_mask_confidence(
    confidence_map: NDArray[np.float32],
    mask: BinaryMask,
) -> float | None:
    """Compute mean confidence over masked pixels.

    Args:
        confidence_map: Float32 ``H × W`` confidence map.
        mask: Boolean ``H × W`` mask; must align with ``confidence_map``.

    Returns:
        Mean confidence in ``[0, 1]``, or ``None`` if the mask is empty.
    """
    if not mask.any():
        return None
    return float(confidence_map[mask].mean())


# ---------------------------------------------------------------------------
# Backend
# ---------------------------------------------------------------------------

class MediaPipeSegmenter(Segmenter):
    """Garment segmenter backed by MediaPipe SelfieSegmentation.

    This backend produces a single ``"upper-clothes"`` region per frame.
    It is the P0 baseline for T02; SCHP-ATR (T02 P1) adds per-class labels.

    Example::

        config = MediaPipeSegmenterConfig()
        with MediaPipeSegmenter(config) as seg:
            regions = seg.segment(packet)

    Raises:
        MediaPipeBackendUnavailableError: If mediapipe is not installed.
    """

    def __init__(self, config: MediaPipeSegmenterConfig | None = None) -> None:
        """Initialise the backend and load the MediaPipe model.

        Args:
            config: Backend configuration. Uses defaults if not provided.

        Raises:
            MediaPipeBackendUnavailableError: If mediapipe cannot be imported.
        """
        self._config = config or MediaPipeSegmenterConfig()
        mp = _import_mediapipe()
        self._selfie = mp.solutions.selfie_segmentation.SelfieSegmentation(
            model_selection=self._config.model_selection
        )
        self._closed = False
        _logger.info(
            "MediaPipeSegmenter initialised (model_selection=%d)",
            self._config.model_selection,
        )

    # -- Segmenter interface -------------------------------------------------

    @property
    def backend_name(self) -> str:
        return "mediapipe"

    @property
    def device_info(self) -> str:
        return "mediapipe/cpu"

    def segment(self, packet: FramePacket) -> tuple[GarmentRegion, ...]:
        """Segment a single frame and return upper-clothes region.

        Args:
            packet: Source frame packet. ``original_bgr`` is read-only here.

        Returns:
            A tuple containing one :class:`~chromalens.contracts.GarmentRegion`
            with class ``"upper-clothes"``, or an empty tuple if no foreground
            is detected.

        Raises:
            RuntimeError: If ``close()`` was already called.
        """
        if self._closed:
            raise RuntimeError(
                "MediaPipeSegmenter.segment() called after close()"
            )

        # MediaPipe expects RGB uint8; original_bgr is OpenCV BGR uint8.
        frame_rgb: ColorFrame = cv2.cvtColor(
            packet.original_bgr, cv2.COLOR_BGR2RGB
        )

        result = self._selfie.process(frame_rgb)

        if result.segmentation_mask is None:
            _logger.warning(
                "frame_id=%d: MediaPipe returned no segmentation mask",
                packet.frame_id,
            )
            return ()

        # segmentation_mask is float32 H×W in [0, 1]
        confidence_map: NDArray[np.float32] = result.segmentation_mask

        mask = apply_mask_cleanup(
            confidence_map,
            threshold=self._config.confidence_threshold,
            head_skip_ratio=self._config.head_skip_ratio,
            upper_body_ratio=self._config.upper_body_ratio,
            min_area_ratio=self._config.min_area_ratio,
            morph_kernel_size=self._config.morph_kernel_size,
        )

        if not mask.any():
            return ()

        confidence = compute_mask_confidence(confidence_map, mask)

        region = GarmentRegion(
            track_id=None,
            class_name="upper-clothes",
            mask=mask,
            mask_confidence=confidence,
        )
        return (region,)

    def close(self) -> None:
        """Release MediaPipe resources. Safe to call multiple times."""
        if not self._closed:
            self._selfie.close()
            self._closed = True
            _logger.debug("MediaPipeSegmenter closed")
