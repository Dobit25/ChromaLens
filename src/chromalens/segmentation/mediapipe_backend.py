"""MediaPipe person segmentation adapted into a torso-mask baseline.

MediaPipe Selfie Segmentation produces a person/background confidence map, not
semantic garment classes. ChromaLens combines that map with MediaPipe face
detection and explicit vertical bounds to obtain a documented, heuristic torso
mask for the T02 P0 vertical slice. It must not be described as calibrated
garment parsing; SCHP or another human parser remains a later comparison gate.

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
        model_selection: Selfie Segmentation model. ``0`` is the general
            model; ``1`` is the landscape model.
        face_model_selection: Face Detection model. ``0`` targets faces within
            2 metres; ``1`` is the full-range model.
        face_min_detection_confidence: MediaPipe face detector threshold.
        face_margin_ratio: Extra fraction of detected face height excluded
            below the face box to avoid retaining the chin/neck.
        confidence_threshold: Minimum per-pixel probability to classify as
            foreground. Default 0.5 is the recommended starting point.
        head_skip_ratio: Fallback fraction of frame height excluded when face
            detection does not return a usable box.
        upper_body_ratio: Fraction of frame height (from top) that defines the
            lower boundary of the valid garment region. Limits false positives
            from floor/background.
        min_area_ratio: Components smaller than this fraction of total frame
            pixels are discarded as segmentation noise.
        morph_kernel_size: Square kernel size for morphological open/close.
    """

    model_selection: int = 1
    face_model_selection: int = 1
    face_min_detection_confidence: float = 0.40
    face_margin_ratio: float = 0.10
    confidence_threshold: float = 0.5
    head_skip_ratio: float = 0.22
    upper_body_ratio: float = 0.80
    min_area_ratio: float = 0.005
    morph_kernel_size: int = 5

    def __post_init__(self) -> None:
        if self.model_selection not in (0, 1):
            raise ValueError("model_selection must be 0 or 1")
        if self.face_model_selection not in (0, 1):
            raise ValueError("face_model_selection must be 0 or 1")
        for name in (
            "face_min_detection_confidence",
            "face_margin_ratio",
            "confidence_threshold",
            "head_skip_ratio",
            "upper_body_ratio",
            "min_area_ratio",
        ):
            value = getattr(self, name)
            if not 0.0 <= value <= 1.0:
                raise ValueError(f"{name} must be within [0, 1]")
        if self.head_skip_ratio >= self.upper_body_ratio:
            raise ValueError("head_skip_ratio must be below upper_body_ratio")
        if self.morph_kernel_size < 1 or self.morph_kernel_size % 2 == 0:
            raise ValueError("morph_kernel_size must be a positive odd integer")


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
    head_cutoff_row: int | None = None,
) -> BinaryMask:
    """Threshold, filter, and clean a MediaPipe confidence map.

    Steps:
        1. Threshold at ``threshold`` -> raw boolean mask.
        2. Apply head exclusion using ``head_cutoff_row`` when face detection
           succeeded, otherwise use ``head_skip_ratio`` as a fallback.
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
        head_cutoff_row: Optional absolute row immediately below a detected
            face. When supplied, this overrides ``head_skip_ratio``.

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
    if not 0.0 <= threshold <= 1.0:
        raise ValueError("threshold must be within [0, 1]")
    if not 0.0 <= head_skip_ratio <= upper_body_ratio <= 1.0:
        raise ValueError(
            "head_skip_ratio and upper_body_ratio must satisfy "
            "0 <= head_skip_ratio <= upper_body_ratio <= 1"
        )
    if not 0.0 <= min_area_ratio <= 1.0:
        raise ValueError("min_area_ratio must be within [0, 1]")
    if morph_kernel_size < 1 or morph_kernel_size % 2 == 0:
        raise ValueError("morph_kernel_size must be a positive odd integer")
    if head_cutoff_row is not None and not 0 <= head_cutoff_row <= h:
        raise ValueError(f"head_cutoff_row must be within [0, {h}]")
    total_pixels = h * w

    # Step 1 -- threshold
    raw_mask = confidence_map >= threshold

    # Step 2 -- head/face exclusion (top region)
    head_cutoff = (
        head_cutoff_row
        if head_cutoff_row is not None
        else int(h * head_skip_ratio)
    )
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
    """Torso-mask baseline backed by MediaPipe Selfie Segmentation.

    This backend produces one person-derived ``"upper-clothes"`` region per
    frame. It is not semantic clothing parsing and cannot distinguish a shirt
    from skin or a foreground object included in the person silhouette.

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
            MediaPipeBackendUnavailableError: If MediaPipe cannot be imported
                or either required solution cannot be initialised.
        """
        self._config = config or MediaPipeSegmenterConfig()
        mp = _import_mediapipe()
        self._selfie = None
        try:
            self._selfie = mp.solutions.selfie_segmentation.SelfieSegmentation(
                model_selection=self._config.model_selection
            )
            self._face = mp.solutions.face_detection.FaceDetection(
                model_selection=self._config.face_model_selection,
                min_detection_confidence=(
                    self._config.face_min_detection_confidence
                ),
            )
        except Exception as exc:
            if self._selfie is not None:
                self._selfie.close()
            raise MediaPipeBackendUnavailableError(
                "MediaPipe segmentation models could not be initialised. "
                "Verify the locked segment-mediapipe environment and retry."
            ) from exc
        self._closed = False
        _logger.info(
            "MediaPipeSegmenter initialised (model_selection=%d)",
            self._config.model_selection,
        )

    # -- Segmenter interface -------------------------------------------------

    @property
    def backend_name(self) -> str:
        return "mediapipe-selfie-torso"

    @property
    def device_info(self) -> str:
        return "mediapipe-selfie-torso/cpu"

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

        # MediaPipe normally returns an aligned float32 H x W map. Normalize
        # explicitly so the public Segmenter contract remains true if a
        # runtime revision returns a different dtype or resolution.
        confidence_map = np.asarray(result.segmentation_mask, dtype=np.float32)
        frame_height, frame_width = packet.original_bgr.shape[:2]
        if confidence_map.shape != (frame_height, frame_width):
            confidence_map = cv2.resize(
                confidence_map,
                (frame_width, frame_height),
                interpolation=cv2.INTER_LINEAR,
            ).astype(np.float32, copy=False)

        face_result = self._face.process(frame_rgb)
        head_cutoff_row = _face_exclusion_row(
            face_result.detections,
            frame_height=frame_height,
            margin_ratio=self._config.face_margin_ratio,
        )

        mask = apply_mask_cleanup(
            confidence_map,
            threshold=self._config.confidence_threshold,
            head_skip_ratio=self._config.head_skip_ratio,
            upper_body_ratio=self._config.upper_body_ratio,
            min_area_ratio=self._config.min_area_ratio,
            morph_kernel_size=self._config.morph_kernel_size,
            head_cutoff_row=head_cutoff_row,
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
            try:
                self._face.close()
            finally:
                self._selfie.close()
                self._closed = True
            _logger.debug("MediaPipeSegmenter closed")


def _face_exclusion_row(
    detections: object,
    *,
    frame_height: int,
    margin_ratio: float,
) -> int | None:
    """Return a conservative global row below all detected face boxes."""
    if not detections:
        return None

    cutoffs: list[int] = []
    for detection in detections:  # type: ignore[union-attr]
        box = detection.location_data.relative_bounding_box
        if box.height <= 0:
            continue
        relative_bottom = box.ymin + box.height * (1.0 + margin_ratio)
        cutoffs.append(round(relative_bottom * frame_height))

    if not cutoffs:
        return None
    return max(0, min(frame_height, max(cutoffs)))
