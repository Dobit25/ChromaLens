"""Fail-fast placeholder for the optional SCHP-ATR backend.

SCHP-ATR (Self-Correction for Human Parsing, ATR dataset) is the P1
segmentation backend for T02. Full implementation is gated on the
MediaPipe P0 baseline being DONE and model weights being available.

See models/README.md for weight source, license, and download steps.
"""

from __future__ import annotations

from chromalens.contracts import FramePacket, GarmentRegion
from chromalens.segmentation.base import Segmenter, SegmenterUnavailableError


class SCHPBackendUnavailableError(SegmenterUnavailableError):
    """Raised because SCHP-ATR inference is not yet implemented."""


class SCHPSegmenter(Segmenter):
    """T02 P1 placeholder; full implementation belongs to T02 SCHP gate."""

    @property
    def backend_name(self) -> str:
        return "schp-atr"

    @property
    def device_info(self) -> str:
        return "schp-atr/unavailable"

    def segment(self, packet: FramePacket) -> tuple[GarmentRegion, ...]:
        """Not implemented — raises immediately with setup instructions."""
        del packet
        raise SCHPBackendUnavailableError(
            "SCHP-ATR is not yet implemented. "
            "See models/README.md for weight download steps. "
            "Use MediaPipeSegmenter as the current baseline."
        )
