"""Fail-fast T00 placeholder for the optional future SCHP-ATR backend."""

from __future__ import annotations

from chromalens.contracts import FramePacket, GarmentRegion
from chromalens.segmentation.base import Segmenter, SegmenterUnavailableError


class SCHPBackendUnavailableError(SegmenterUnavailableError):
    """Raised because SCHP inference is intentionally absent in T00."""


class SCHPSegmenter(Segmenter):
    """T00 contract placeholder; optional integration belongs to T02/T10."""

    @property
    def backend_name(self) -> str:
        return "schp-atr"

    def segment(self, packet: FramePacket) -> tuple[GarmentRegion, ...]:
        del packet
        raise SCHPBackendUnavailableError(
            "SCHP-ATR garment segmentation is not implemented in T00; use T02 setup."
        )
