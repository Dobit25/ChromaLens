"""Fail-fast placeholder for the optional SCHP-ATR backend.

SCHP-ATR (Self-Correction for Human Parsing, ATR dataset) is deferred under
the T02 four-hour decision gate. It may be reconsidered only in T10 after the
working vertical slice and evaluation protocol exist.

See models/README.md for weight source, license, and download steps.
"""

from __future__ import annotations

from chromalens.contracts import FramePacket, GarmentRegion
from chromalens.segmentation.base import Segmenter, SegmenterUnavailableError


class SCHPBackendUnavailableError(SegmenterUnavailableError):
    """Raised because the SCHP-ATR comparison backend is deferred to T10."""


class SCHPSegmenter(Segmenter):
    """Fail-fast T10 placeholder that never fabricates inference output."""

    @property
    def backend_name(self) -> str:
        return "schp-atr"

    @property
    def device_info(self) -> str:
        return "schp-atr/unavailable"

    def segment(self, packet: FramePacket) -> tuple[GarmentRegion, ...]:
        """Raise immediately because no verified SCHP runtime is installed."""
        del packet
        raise SCHPBackendUnavailableError(
            "SCHP-ATR was deferred by the T02 decision gate and has no "
            "verified runtime or approved weights. Reconsider it in T10; "
            "use MediaPipeSegmenter for the current P0 baseline."
        )
