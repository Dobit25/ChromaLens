"""Integration tests for T02 — require MediaPipe to be installed.

All tests are skipped automatically if mediapipe is not available,
so they are safe to run in the base CI environment.

Install before running:
    pip install "chromalens-ai[segment-mediapipe]"
"""

from __future__ import annotations

import time

import numpy as np
import pytest

from chromalens.contracts import FramePacket

# ---------------------------------------------------------------------------
# Skip guard — skip entire module if mediapipe is not installed
# ---------------------------------------------------------------------------

mediapipe = pytest.importorskip(
    "mediapipe",
    reason="mediapipe not installed; run: pip install 'chromalens-ai[segment-mediapipe]'",
)

from chromalens.segmentation.mediapipe_backend import (  # noqa: E402
    MediaPipeSegmenter,
    MediaPipeSegmenterConfig,
)
from chromalens.segmentation.debug import draw_mask_overlay  # noqa: E402


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_packet(h: int = 480, w: int = 640, seed: int = 0) -> FramePacket:
    """Return a synthetic BGR FramePacket for integration testing."""
    rng = np.random.default_rng(seed=seed)
    frame = rng.integers(0, 256, (h, w, 3), dtype=np.uint8)
    return FramePacket(
        frame_id=seed,
        timestamp_ns=time.monotonic_ns(),
        original_bgr=frame,
    )


def _make_blank_packet(h: int = 480, w: int = 640) -> FramePacket:
    """Return a pure-white frame (worst case for segmentation)."""
    frame = np.full((h, w, 3), 255, dtype=np.uint8)
    return FramePacket(
        frame_id=999,
        timestamp_ns=time.monotonic_ns(),
        original_bgr=frame,
    )


# ---------------------------------------------------------------------------
# Integration tests
# ---------------------------------------------------------------------------

class TestMediaPipeSegmenterIntegration:
    """End-to-end tests using the real MediaPipe runtime."""

    def test_segment_returns_tuple(self) -> None:
        # Arrange
        config = MediaPipeSegmenterConfig()
        packet = _make_packet()

        # Act
        with MediaPipeSegmenter(config) as seg:
            result = seg.segment(packet)

        # Assert
        assert isinstance(result, tuple)

    def test_mask_shape_matches_input_frame(self) -> None:
        # Arrange
        h, w = 480, 640
        packet = _make_packet(h, w)

        # Act
        with MediaPipeSegmenter() as seg:
            regions = seg.segment(packet)

        # Assert — if any region is returned, its mask must align with the frame
        for region in regions:
            assert region.mask.shape == (h, w), (
                f"Mask shape {region.mask.shape} does not match frame ({h}, {w})"
            )

    def test_mask_dtype_is_boolean(self) -> None:
        # Arrange
        packet = _make_packet()

        # Act
        with MediaPipeSegmenter() as seg:
            regions = seg.segment(packet)

        # Assert
        for region in regions:
            assert region.mask.dtype == np.bool_, (
                f"Expected bool mask, got {region.mask.dtype}"
            )

    def test_backend_name_is_exposed(self) -> None:
        # Arrange / Act
        with MediaPipeSegmenter() as seg:
            name = seg.backend_name

        # Assert
        assert name == "mediapipe"

    def test_device_info_is_non_empty_string(self) -> None:
        # Arrange / Act
        with MediaPipeSegmenter() as seg:
            info = seg.device_info

        # Assert
        assert isinstance(info, str)
        assert len(info) > 0

    def test_confidence_is_within_valid_range_when_present(self) -> None:
        # Arrange
        packet = _make_packet(seed=1)

        # Act
        with MediaPipeSegmenter() as seg:
            regions = seg.segment(packet)

        # Assert
        for region in regions:
            if region.mask_confidence is not None:
                assert 0.0 <= region.mask_confidence <= 1.0, (
                    f"mask_confidence={region.mask_confidence} out of [0, 1]"
                )

    def test_original_frame_not_mutated_by_segment(self) -> None:
        # Arrange
        packet = _make_packet()
        original_copy = packet.original_bgr.copy()

        # Act
        with MediaPipeSegmenter() as seg:
            seg.segment(packet)

        # Assert
        np.testing.assert_array_equal(
            packet.original_bgr,
            original_copy,
            err_msg="segment() must not mutate original_bgr",
        )

    def test_blank_white_frame_produces_no_or_minimal_mask(self) -> None:
        # Arrange — pure white, no person
        packet = _make_blank_packet()

        # Act
        with MediaPipeSegmenter() as seg:
            regions = seg.segment(packet)

        # Assert — blank frame should produce no regions or very sparse mask
        total_pixels = packet.original_bgr.shape[0] * packet.original_bgr.shape[1]
        total_masked = sum(int(r.mask.sum()) for r in regions)
        ratio = total_masked / total_pixels
        assert ratio < 0.30, (
            f"Blank white frame produced a large mask ({ratio:.1%}); "
            "expected < 30% coverage"
        )

    def test_five_synthetic_scenes_all_produce_overlay(self) -> None:
        # Arrange — 5 different random frames
        packets = [_make_packet(seed=i) for i in range(5)]

        # Act
        with MediaPipeSegmenter() as seg:
            for i, packet in enumerate(packets):
                regions = seg.segment(packet)
                overlay = draw_mask_overlay(
                    packet.original_bgr,
                    regions,
                    backend_info=seg.device_info,
                )
                # Assert per scene — overlay must have same shape as source
                assert overlay.shape == packet.original_bgr.shape, (
                    f"Scene {i}: overlay shape mismatch"
                )
                assert overlay.dtype == np.uint8

    def test_context_manager_releases_resources(self) -> None:
        # Arrange / Act — use as context manager and verify no error on exit
        with MediaPipeSegmenter() as seg:
            assert seg.backend_name == "mediapipe"
        # Act again after close — must not raise on second close
        seg.close()

    def test_segment_after_close_raises_runtime_error(self) -> None:
        # Arrange
        seg = MediaPipeSegmenter()
        seg.close()
        packet = _make_packet()

        # Act / Assert
        with pytest.raises(RuntimeError, match="close"):
            seg.segment(packet)
