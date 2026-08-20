"""Deterministic tests for T04 garment-pixel preprocessing."""

from __future__ import annotations

import numpy as np
import pytest

from chromalens.color.preprocessing import (
    PixelSelectionConfig,
    select_valid_garment_pixels,
)


def test_erosion_removes_boundary_contamination_without_mutating_inputs() -> None:
    background = np.array([20, 180, 20], dtype=np.uint8)
    garment = np.array([200, 30, 30], dtype=np.uint8)

    frame = np.full((9, 9, 3), background, dtype=np.uint8)
    mask = np.zeros((9, 9), dtype=np.bool_)
    mask[1:8, 1:8] = True
    frame[2:7, 2:7] = garment

    frame_copy = frame.copy()
    mask_copy = mask.copy()

    selection = select_valid_garment_pixels(frame, mask)

    expected_mask = np.zeros((9, 9), dtype=np.bool_)
    expected_mask[2:7, 2:7] = True

    np.testing.assert_array_equal(selection.eroded_mask, expected_mask)
    np.testing.assert_array_equal(selection.valid_mask, expected_mask)
    assert selection.eligible_count == 25
    assert selection.valid_count == 25
    assert selection.valid_fraction == pytest.approx(1.0)
    assert np.all(selection.pixels_rgb == garment)
    np.testing.assert_array_equal(frame, frame_copy)
    np.testing.assert_array_equal(mask, mask_copy)


def test_dark_and_clipped_pixels_are_rejected() -> None:
    frame = np.full((7, 7, 3), [80, 100, 120], dtype=np.uint8)
    mask = np.ones((7, 7), dtype=np.bool_)
    frame[0, 0] = [8, 8, 8]
    frame[0, 1] = [250, 80, 80]

    selection = select_valid_garment_pixels(
        frame,
        mask,
        PixelSelectionConfig(erosion_iterations=0),
    )

    assert selection.eligible_count == 49
    assert selection.valid_count == 47
    assert not selection.valid_mask[0, 0]
    assert not selection.valid_mask[0, 1]
    assert selection.valid_mask[0, 2]


def test_empty_mask_returns_an_empty_selection() -> None:
    frame = np.full((5, 5, 3), 100, dtype=np.uint8)
    mask = np.zeros((5, 5), dtype=np.bool_)

    selection = select_valid_garment_pixels(frame, mask)

    assert selection.eligible_count == 0
    assert selection.valid_count == 0
    assert selection.valid_fraction == 0.0
    assert selection.pixels_rgb.shape == (0, 3)


def test_mask_must_be_boolean_and_align_with_frame() -> None:
    frame = np.full((5, 5, 3), 100, dtype=np.uint8)

    with pytest.raises(ValueError, match="boolean"):
        select_valid_garment_pixels(
            frame,
            np.ones((5, 5), dtype=np.uint8),
        )

    with pytest.raises(ValueError, match="align"):
        select_valid_garment_pixels(
            frame,
            np.ones((4, 5), dtype=np.bool_),
        )


@pytest.mark.parametrize(
    "config_kwargs",
    [
        {"erosion_kernel_size": 2},
        {"erosion_iterations": -1},
        {"minimum_brightness": -1},
        {"minimum_brightness": 250, "clipped_threshold": 250},
    ],
)
def test_invalid_configuration_fails_fast(
    config_kwargs: dict[str, int],
) -> None:
    with pytest.raises(ValueError):
        PixelSelectionConfig(**config_kwargs)