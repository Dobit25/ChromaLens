"""Common interface for interchangeable garment segmentation backends."""

from __future__ import annotations

from abc import ABC, abstractmethod

from chromalens.contracts import FramePacket, GarmentRegion


class SegmenterUnavailableError(RuntimeError):
    """Raised when a requested segmentation backend cannot perform inference."""


class Segmenter(ABC):
    """Backend-independent garment segmentation contract."""

    @property
    @abstractmethod
    def backend_name(self) -> str:
        """Return a stable user-visible backend identifier."""

    @abstractmethod
    def segment(self, packet: FramePacket) -> tuple[GarmentRegion, ...]:
        """Return garment masks aligned with ``packet.original_bgr``."""
