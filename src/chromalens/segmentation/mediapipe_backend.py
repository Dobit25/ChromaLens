"""Fail-fast T00 placeholder for the future MediaPipe backend."""

from __future__ import annotations

from chromalens.contracts import FramePacket, GarmentRegion
from chromalens.segmentation.base import Segmenter, SegmenterUnavailableError


class MediaPipeBackendUnavailableError(SegmenterUnavailableError):
    """Raised because MediaPipe inference is intentionally absent in T00."""


class MediaPipeSegmenter(Segmenter):
    """T00 contract placeholder; implemented and validated in T02."""

    @property
    def backend_name(self) -> str:
        return "mediapipe"

    def segment(self, packet: FramePacket) -> tuple[GarmentRegion, ...]:
        del packet
        raise MediaPipeBackendUnavailableError(
            "MediaPipe garment segmentation is not implemented in T00; use T02 setup."
        )
