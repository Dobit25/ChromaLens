"""Integration-style unit tests for the complete T04 extraction pipeline."""

from __future__ import annotations

import math

import numpy as np
import pytest

from chromalens.color.extraction import (
    ColorExtractionConfig,
    InsufficientColorDataError,
    extract_garment_colors,
)
from chromalens.color.preprocessing import PixelSelectionConfig
from chromalens.contracts import GarmentRegion


def _garment(
    mask: np.ndarray,
    confidence: float | None = 0.9,
) -> GarmentRegion:
    return GarmentRegion(
        track_id=None,
        class_name="upper-clothes",
        mask=mask,
        mask_confidence=confidence,
    )


def _no_erosion_config(
    *,
    mode: str = "k2",
    minimum_valid_pixels: int = 1,
    minimum_valid_fraction: float = 0.0,
    minimum_mask_confidence: float | None = None,
) -> ColorExtractionConfig:
    return ColorExtractionConfig(
        mode=mode,  # type: ignore[arg-type]
        minimum_valid_pixels=minimum_valid_pixels,
        minimum_valid_fraction=minimum_valid_fraction,
        minimum_mask_confidence=minimum_mask_confidence,
        pixel_selection=PixelSelectionConfig(
            erosion_iterations=0,
        ),
    )


def test_uniform_red_pipeline_returns_complete_color_cluster() -> None:
    corrected_rgb = np.full(
        (20, 20, 3),
        (249, 0, 0),
        dtype=np.uint8,
    )
    garment_mask = np.ones((20, 20), dtype=np.bool_)
    original = corrected_rgb.copy()

    clusters = extract_garment_colors(
        corrected_rgb,
        _garment(garment_mask),
    )

    assert len(clusters) == 1

    cluster = clusters[0]
    assert cluster.original_name == "đỏ"
    assert cluster.rgb == pytest.approx((249, 0, 0), abs=1)
    assert cluster.ratio == pytest.approx(1.0)
    assert cluster.submask.shape == garment_mask.shape
    assert cluster.submask.dtype == np.bool_
    assert np.count_nonzero(cluster.submask) == 324
    assert len(cluster.name_scores) == 11
    assert sum(cluster.name_scores.values()) == pytest.approx(1.0)
    assert cluster.color_margin is not None
    assert cluster.color_margin > 0.0

    np.testing.assert_array_equal(corrected_rgb, original)


def test_k2_creates_disjoint_aligned_submasks() -> None:
    red = np.tile(
        np.array([[200, 30, 30]], dtype=np.uint8),
        (70, 1),
    )
    blue = np.tile(
        np.array([[30, 30, 200]], dtype=np.uint8),
        (30, 1),
    )
    corrected_rgb = np.vstack((red, blue)).reshape((10, 10, 3))
    garment_mask = np.ones((10, 10), dtype=np.bool_)

    clusters = extract_garment_colors(
        corrected_rgb,
        _garment(garment_mask),
        _no_erosion_config(),
    )

    assert len(clusters) == 2
    assert clusters[0].ratio == pytest.approx(0.70)
    assert clusters[1].ratio == pytest.approx(0.30)

    np.testing.assert_allclose(
        clusters[0].rgb,
        (200, 30, 30),
        atol=1,
    )
    np.testing.assert_allclose(
        clusters[1].rgb,
        (30, 30, 200),
        atol=1,
    )

    overlap = clusters[0].submask & clusters[1].submask
    combined = clusters[0].submask | clusters[1].submask

    assert not np.any(overlap)
    np.testing.assert_array_equal(combined, garment_mask)


def test_invalid_pixels_never_enter_cluster_submask() -> None:
    corrected_rgb = np.full(
        (10, 10, 3),
        (180, 50, 40),
        dtype=np.uint8,
    )
    corrected_rgb.reshape((-1, 3))[:10] = (0, 0, 0)
    corrected_rgb.reshape((-1, 3))[10:20] = (250, 20, 20)

    garment_mask = np.ones((10, 10), dtype=np.bool_)

    clusters = extract_garment_colors(
        corrected_rgb,
        _garment(garment_mask),
        _no_erosion_config(),
    )

    assert len(clusters) == 1

    expected_valid_mask = np.ones((10, 10), dtype=np.bool_)
    expected_valid_mask.reshape(-1)[:20] = False

    np.testing.assert_array_equal(
        clusters[0].submask,
        expected_valid_mask,
    )
    assert np.count_nonzero(clusters[0].submask) == 80


def test_median_mode_returns_exactly_one_cluster() -> None:
    first_color = np.tile(
        np.array([[180, 50, 40]], dtype=np.uint8),
        (60, 1),
    )
    second_color = np.tile(
        np.array([[30, 40, 190]], dtype=np.uint8),
        (40, 1),
    )
    corrected_rgb = np.vstack(
        (first_color, second_color)
    ).reshape((10, 10, 3))

    clusters = extract_garment_colors(
        corrected_rgb,
        _garment(np.ones((10, 10), dtype=np.bool_)),
        _no_erosion_config(mode="median"),
    )

    assert len(clusters) == 1
    assert clusters[0].ratio == pytest.approx(1.0)
    assert np.all(clusters[0].submask)


def test_known_low_mask_confidence_fails_fast() -> None:
    corrected_rgb = np.full(
        (10, 10, 3),
        (180, 50, 40),
        dtype=np.uint8,
    )
    garment_mask = np.ones((10, 10), dtype=np.bool_)

    with pytest.raises(
        InsufficientColorDataError,
        match="mask confidence",
    ):
        extract_garment_colors(
            corrected_rgb,
            _garment(garment_mask, confidence=0.39),
            _no_erosion_config(
                minimum_mask_confidence=0.40,
            ),
        )


def test_unknown_mask_confidence_is_not_fabricated_as_failure() -> None:
    corrected_rgb = np.full(
        (10, 10, 3),
        (180, 50, 40),
        dtype=np.uint8,
    )
    garment_mask = np.ones((10, 10), dtype=np.bool_)

    clusters = extract_garment_colors(
        corrected_rgb,
        _garment(garment_mask, confidence=None),
        _no_erosion_config(
            minimum_mask_confidence=0.90,
        ),
    )

    assert len(clusters) == 1


def test_too_few_valid_pixels_fails_clearly() -> None:
    corrected_rgb = np.full(
        (3, 3, 3),
        (180, 50, 40),
        dtype=np.uint8,
    )
    garment_mask = np.ones((3, 3), dtype=np.bool_)

    with pytest.raises(
        InsufficientColorDataError,
        match="enough valid pixels",
    ):
        extract_garment_colors(
            corrected_rgb,
            _garment(garment_mask),
            _no_erosion_config(
                minimum_valid_pixels=16,
            ),
        )


def test_low_valid_fraction_fails_clearly() -> None:
    corrected_rgb = np.full(
        (10, 10, 3),
        (250, 250, 250),
        dtype=np.uint8,
    )
    corrected_rgb.reshape((-1, 3))[:9] = (180, 50, 40)
    garment_mask = np.ones((10, 10), dtype=np.bool_)

    with pytest.raises(
        InsufficientColorDataError,
        match="fraction",
    ):
        extract_garment_colors(
            corrected_rgb,
            _garment(garment_mask),
            _no_erosion_config(
                minimum_valid_pixels=1,
                minimum_valid_fraction=0.10,
            ),
        )


def test_misaligned_mask_fails_fast() -> None:
    corrected_rgb = np.full(
        (10, 10, 3),
        (180, 50, 40),
        dtype=np.uint8,
    )
    garment_mask = np.ones((9, 10), dtype=np.bool_)

    with pytest.raises(
        ValueError,
        match="align",
    ):
        extract_garment_colors(
            corrected_rgb,
            _garment(garment_mask),
        )


@pytest.mark.parametrize(
    "config_kwargs",
    [
        {"mode": "k3"},
        {"minimum_valid_pixels": 0},
        {"minimum_valid_pixels": True},
        {"minimum_valid_fraction": -0.1},
        {"minimum_valid_fraction": 1.1},
        {"minimum_valid_fraction": math.nan},
        {"minimum_mask_confidence": -0.1},
        {"minimum_mask_confidence": 1.1},
    ],
)
def test_invalid_extraction_configuration_fails_fast(
    config_kwargs: dict[str, object],
) -> None:
    with pytest.raises(ValueError):
        ColorExtractionConfig(
            **config_kwargs,  # type: ignore[arg-type]
        )