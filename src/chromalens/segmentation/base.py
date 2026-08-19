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
        """Return a stable user-visible backend identifier (e.g. 'mediapipe')."""

    @property
    @abstractmethod
    def device_info(self) -> str:
        """Return a human-readable backend + device string for UI and logs.

        Examples:
            ``"mediapipe/cpu"``
            ``"schp-atr/cuda:0"``
        """

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
