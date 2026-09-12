"""Common interface for interchangeable garment segmentation backends."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import Enum
from math import isfinite

from chromalens.contracts import FramePacket, GarmentRegion


class SegmenterUnavailableError(RuntimeError):
    """Raised when a requested segmentation backend cannot perform inference."""


class SegmentationMaskSource(str, Enum):
    """Truthful origin of the mask aligned with the displayed frame."""

    SYNCHRONOUS = "synchronous"
    WARMING_UP = "warming-up"
    INFERRED = "inferred"
    PROPAGATED = "propagated"
    STALE = "stale"
    UNAVAILABLE = "unavailable"


@dataclass(frozen=True, slots=True)
class SegmentationFrameTelemetry:
    """Per-frame segmentation provenance, separate from model confidence."""

    frame_id: int
    mask_source: SegmentationMaskSource
    keyframe_id: int | None = None
    mask_age_ms: float | None = None
    inference_fps: float | None = None
    inference_latency_ms: float | None = None
    dropped_pending_frames: int = 0
    message: str | None = None

    def __post_init__(self) -> None:
        if self.frame_id < 0:
            raise ValueError("frame_id must be non-negative")
        if self.keyframe_id is not None and self.keyframe_id < 0:
            raise ValueError("keyframe_id must be non-negative when provided")
        for field_name in ("mask_age_ms", "inference_fps", "inference_latency_ms"):
            value = getattr(self, field_name)
            if value is not None and (not isfinite(value) or value < 0.0):
                raise ValueError(f"{field_name} must be finite and non-negative")
        if self.dropped_pending_frames < 0:
            raise ValueError("dropped_pending_frames must be non-negative")
        if self.message is not None and not self.message.strip():
            raise ValueError("message must not be blank")


class Segmenter(ABC):
    """Backend-independent garment segmentation contract."""

    @property
    @abstractmethod
    def backend_name(self) -> str:
        """Return a stable user-visible backend identifier."""

    @property
    @abstractmethod
    def device_info(self) -> str:
        """Return a human-readable backend + device string for UI and logs.

        Examples:
            ``"mediapipe-selfie-torso/cpu"``
            ``"schp-atr/cuda:0"``
        """

    @property
    def frame_telemetry(self) -> SegmentationFrameTelemetry | None:
        """Return optional provenance for the most recent ``segment`` call."""

        return None

    @property
    def manages_stage_timing(self) -> bool:
        """Whether this adapter times inference/propagation internally."""

        return False

    @abstractmethod
    def segment(self, packet: FramePacket) -> tuple[GarmentRegion, ...]:
        """Return garment masks aligned with ``packet.original_bgr``.

        Args:
            packet: Source frame packet; ``original_bgr`` must not be mutated.

        Returns:
            Zero or more :class:`~chromalens.contracts.GarmentRegion` objects,
            each with a boolean mask of the same spatial dimensions as the
            source frame.
        """

    def close(self) -> None:
        """Release backend resources. Safe to call multiple times."""

    def __enter__(self) -> "Segmenter":
        return self

    def __exit__(self, *args: object) -> None:
        self.close()
