"""Unit tests for T02 segmentation — no model, camera, or network required.

All tests use synthetic NumPy arrays and follow the AAA pattern:
    Arrange → Act → Assert
"""

from __future__ import annotations

import numpy as np
import pytest

from chromalens.contracts import FramePacket, GarmentRegion
from chromalens.segmentation.debug import draw_mask_overlay
from chromalens.segmentation.mediapipe_backend import (
    MediaPipeBackendUnavailableError,
    MediaPipeSegmenterConfig,
    apply_mask_cleanup,
    compute_mask_confidence,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_confidence_map(h: int, w: int, fill: float = 0.0) -> np.ndarray:
    """Return a float32 H×W array filled with ``fill``."""
    return np.full((h, w), fill, dtype=np.float32)


def _make_bgr_frame(h: int = 240, w: int = 320) -> np.ndarray:
    """Return a random uint8 BGR frame."""
    rng = np.random.default_rng(seed=42)
    return rng.integers(0, 256, (h, w, 3), dtype=np.uint8)


def _make_binary_mask(h: int, w: int, fill: bool = False) -> np.ndarray:
    return np.full((h, w), fill, dtype=np.bool_)


# ---------------------------------------------------------------------------
# apply_mask_cleanup — mask pipeline (pure, no MediaPipe)
# ---------------------------------------------------------------------------

class TestApplyMaskCleanup:
    """Tests for the standalone mask cleanup utility."""

    def test_all_zero_confidence_returns_empty_mask(self) -> None:
        # Arrange
        h, w = 480, 640
        cmap = _make_confidence_map(h, w, fill=0.0)

        # Act
        result = apply_mask_cleanup(cmap, threshold=0.5)

        # Assert
        assert result.dtype == np.bool_
        assert result.shape == (h, w)
        assert not result.any(), "Zero confidence should produce an empty mask"

    def test_large_foreground_blob_is_retained(self) -> None:
        # Arrange
        h, w = 480, 640
        cmap = _make_confidence_map(h, w, fill=0.0)
        # Large blob in upper half — covers ~20% of frame
        cmap[50:200, 100:400] = 0.9

        # Act
        result = apply_mask_cleanup(cmap, threshold=0.5, min_area_ratio=0.01)

        # Assert
        assert result[105, 205], "Large component must be retained"
        assert result.sum() > 0

    def test_small_noise_blob_is_removed(self) -> None:
        # Arrange
        h, w = 480, 640
        cmap = _make_confidence_map(h, w, fill=0.0)
        # Tiny 5×5 blob — 0.008% of frame, below default min_area_ratio=0.5%
        cmap[10:15, 10:15] = 0.9

        # Act
        result = apply_mask_cleanup(cmap, threshold=0.5, min_area_ratio=0.005)

        # Assert
        assert not result.any(), "Noise blob below min_area_ratio must be removed"

    def test_upper_body_filter_clears_bottom_rows(self) -> None:
        # Arrange
        h, w = 480, 640
        cmap = _make_confidence_map(h, w, fill=0.0)
        # High confidence only in the bottom 30% of the frame
        cmap[int(h * 0.75):, :] = 0.9

        # Act
        result = apply_mask_cleanup(cmap, threshold=0.5, upper_body_ratio=0.75)

        # Assert
        assert not result.any(), (
            "Blob entirely below upper_body_ratio cutoff must be removed"
        )

    def test_upper_body_filter_retains_top_region(self) -> None:
        # Arrange
        h, w = 480, 640
        cmap = _make_confidence_map(h, w, fill=0.0)
        # Large blob in upper 50% (well within upper_body_ratio=0.75)
        cmap[60:220, 80:560] = 0.9

        # Act
        result = apply_mask_cleanup(cmap, threshold=0.5, upper_body_ratio=0.75)

        # Assert
        assert result.sum() > 0, "Upper-body blob must be retained"

    def test_output_is_boolean_dtype(self) -> None:
        # Arrange
        cmap = _make_confidence_map(240, 320, fill=0.8)

        # Act
        result = apply_mask_cleanup(cmap)

        # Assert
        assert result.dtype == np.bool_

    def test_invalid_input_raises_value_error(self) -> None:
        # Arrange — wrong dtype
        bad_input = np.zeros((240, 320), dtype=np.uint8)

        # Act / Assert
        with pytest.raises(ValueError, match="float32"):
            apply_mask_cleanup(bad_input)  # type: ignore[arg-type]

    def test_3d_input_raises_value_error(self) -> None:
        # Arrange — wrong ndim
        bad_input = np.zeros((240, 320, 3), dtype=np.float32)

        # Act / Assert
        with pytest.raises(ValueError):
            apply_mask_cleanup(bad_input)  # type: ignore[arg-type]


# ---------------------------------------------------------------------------
# compute_mask_confidence
# ---------------------------------------------------------------------------

class TestComputeMaskConfidence:
    def test_empty_mask_returns_none(self) -> None:
        # Arrange
        cmap = _make_confidence_map(240, 320, fill=0.9)
        mask = _make_binary_mask(240, 320, fill=False)

        # Act
        result = compute_mask_confidence(cmap, mask)

        # Assert
        assert result is None

    def test_full_mask_returns_mean_confidence(self) -> None:
        # Arrange
        cmap = _make_confidence_map(10, 10, fill=0.8)
        mask = _make_binary_mask(10, 10, fill=True)

        # Act
        result = compute_mask_confidence(cmap, mask)

        # Assert
        assert result is not None
        assert abs(result - 0.8) < 1e-5

    def test_confidence_is_within_valid_range(self) -> None:
        # Arrange
        rng = np.random.default_rng(seed=7)
        cmap = rng.random((240, 320)).astype(np.float32)
        mask = cmap > 0.5

        # Act
        result = compute_mask_confidence(cmap, mask)

        # Assert
        assert result is not None
        assert 0.0 <= result <= 1.0


# ---------------------------------------------------------------------------
# GarmentRegion contract
# ---------------------------------------------------------------------------

class TestGarmentRegionContract:
    def test_valid_region_passes_contract(self) -> None:
        # Arrange
        mask = _make_binary_mask(240, 320, fill=True)

        # Act / Assert — must not raise
        region = GarmentRegion(
            track_id=None,
            class_name="upper-clothes",
            mask=mask,
            mask_confidence=0.87,
        )
        assert region.class_name == "upper-clothes"
        assert 0.0 <= region.mask_confidence <= 1.0  # type: ignore[operator]

    def test_confidence_out_of_range_raises(self) -> None:
        mask = _make_binary_mask(10, 10, fill=True)
        with pytest.raises(ValueError, match="mask_confidence"):
            GarmentRegion(
                track_id=None,
                class_name="upper-clothes",
                mask=mask,
                mask_confidence=1.5,
            )

    def test_empty_class_name_raises(self) -> None:
        mask = _make_binary_mask(10, 10, fill=True)
        with pytest.raises(ValueError, match="class_name"):
            GarmentRegion(
                track_id=None,
                class_name="   ",
                mask=mask,
            )


# ---------------------------------------------------------------------------
# MediaPipe unavailable — lazy import
# ---------------------------------------------------------------------------

class TestMediaPipeUnavailable:
    def test_unavailable_error_has_install_hint(self) -> None:
        # Arrange
        err = MediaPipeBackendUnavailableError(
            "MediaPipe is not installed. "
            "Run: pip install \"chromalens-ai[segment-mediapipe]\""
        )

        # Assert
        assert "segment-mediapipe" in str(err)
        assert "pip install" in str(err)


# ---------------------------------------------------------------------------
# draw_mask_overlay — debug utility
# ---------------------------------------------------------------------------

class TestDrawMaskOverlay:
    def test_output_does_not_mutate_original_frame(self) -> None:
        # Arrange
        frame = _make_bgr_frame(240, 320)
        original_copy = frame.copy()
        mask = _make_binary_mask(240, 320, fill=True)
        regions = (GarmentRegion(track_id=None, class_name="upper-clothes", mask=mask),)

        # Act
        draw_mask_overlay(frame, regions)

        # Assert
        np.testing.assert_array_equal(
            frame, original_copy, err_msg="Original frame must not be mutated"
        )

    def test_output_shape_matches_input(self) -> None:
        # Arrange
        h, w = 360, 480
        frame = _make_bgr_frame(h, w)
        mask = _make_binary_mask(h, w, fill=True)
        regions = (GarmentRegion(track_id=None, class_name="upper-clothes", mask=mask),)

        # Act
        result = draw_mask_overlay(frame, regions)

        # Assert
        assert result.shape == (h, w, 3)
        assert result.dtype == np.uint8

    def test_empty_regions_returns_frame_copy(self) -> None:
        # Arrange
        frame = _make_bgr_frame(240, 320)

        # Act
        result = draw_mask_overlay(frame, ())

        # Assert — should still return a frame (not identical due to text panel)
        assert result.shape == frame.shape
        assert result.dtype == np.uint8

    def test_invalid_alpha_raises(self) -> None:
        frame = _make_bgr_frame(240, 320)
        with pytest.raises(ValueError, match="alpha"):
            draw_mask_overlay(frame, (), alpha=1.5)

    def test_unknown_class_uses_fallback_color(self) -> None:
        # Arrange — unknown class should not raise
        frame = _make_bgr_frame(240, 320)
        mask = _make_binary_mask(240, 320, fill=True)
        regions = (GarmentRegion(track_id=None, class_name="unknown-garment", mask=mask),)

        # Act / Assert — must not raise
        result = draw_mask_overlay(frame, regions)
        assert result.shape == frame.shape


# ---------------------------------------------------------------------------
# MediaPipeSegmenterConfig defaults
# ---------------------------------------------------------------------------

class TestMediaPipeSegmenterConfig:
    def test_default_config_values_are_within_valid_ranges(self) -> None:
        config = MediaPipeSegmenterConfig()
        assert config.model_selection in (0, 1)
        assert 0.0 < config.confidence_threshold < 1.0
        assert 0.0 < config.upper_body_ratio <= 1.0
        assert 0.0 < config.min_area_ratio < 1.0
        assert config.morph_kernel_size >= 1
