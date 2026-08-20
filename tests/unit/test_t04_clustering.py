"""Deterministic tests for T04 median and K=2 color estimation."""

from __future__ import annotations

import numpy as np
import pytest

from chromalens.color.clustering import (
    ClusteringConfig,
    deterministic_k2_estimates,
    robust_median_estimate,
)


def test_median_is_robust_to_minority_outliers() -> None:
    garment_color = np.array([[180, 60, 40]], dtype=np.uint8)
    outlier_color = np.array([[20, 20, 220]], dtype=np.uint8)

    pixels = np.vstack(
        (
            np.tile(garment_color, (91, 1)),
            np.tile(outlier_color, (9, 1)),
        )
    )
    original = pixels.copy()

    estimate = robust_median_estimate(pixels)

    np.testing.assert_allclose(
        estimate.rgb,
        garment_color[0],
        atol=1,
    )
    assert estimate.ratio == pytest.approx(1.0)
    assert estimate.members.shape == (100,)
    assert np.all(estimate.members)
    np.testing.assert_array_equal(pixels, original)


def test_k2_separates_two_colors_and_preserves_ratios() -> None:
    red = np.tile(
        np.array([[200, 30, 30]], dtype=np.uint8),
        (70, 1),
    )
    blue = np.tile(
        np.array([[30, 30, 200]], dtype=np.uint8),
        (30, 1),
    )

    estimates = deterministic_k2_estimates(
        np.vstack((red, blue))
    )

    assert len(estimates) == 2
    assert estimates[0].ratio == pytest.approx(0.70)
    assert estimates[1].ratio == pytest.approx(0.30)
    np.testing.assert_allclose(
        estimates[0].rgb,
        (200, 30, 30),
        atol=1,
    )
    np.testing.assert_allclose(
        estimates[1].rgb,
        (30, 30, 200),
        atol=1,
    )

    memberships = np.vstack(
        [estimate.members for estimate in estimates]
    )
    np.testing.assert_array_equal(
        np.sum(memberships, axis=0),
        np.ones(100, dtype=np.int64),
    )


def test_k2_is_deterministic_across_repeated_runs() -> None:
    pixels = np.vstack(
        (
            np.tile(
                np.array([[190, 40, 30]], dtype=np.uint8),
                (60, 1),
            ),
            np.tile(
                np.array([[40, 50, 190]], dtype=np.uint8),
                (40, 1),
            ),
        )
    )

    first = deterministic_k2_estimates(pixels)

    for _ in range(5):
        repeated = deterministic_k2_estimates(pixels)

        assert len(repeated) == len(first)
        for expected, actual in zip(first, repeated):
            assert actual.rgb == expected.rgb
            assert actual.lab == pytest.approx(expected.lab)
            assert actual.ratio == pytest.approx(expected.ratio)
            np.testing.assert_array_equal(
                actual.members,
                expected.members,
            )


def test_result_order_is_stable_for_equal_size_clusters() -> None:
    red = np.tile(
        np.array([[200, 30, 30]], dtype=np.uint8),
        (50, 1),
    )
    blue = np.tile(
        np.array([[30, 30, 200]], dtype=np.uint8),
        (50, 1),
    )

    forward = deterministic_k2_estimates(
        np.vstack((red, blue))
    )
    reversed_input = deterministic_k2_estimates(
        np.vstack((blue, red))
    )

    assert [item.rgb for item in forward] == [
        item.rgb for item in reversed_input
    ]
    assert [item.ratio for item in forward] == pytest.approx(
        [item.ratio for item in reversed_input]
    )


def test_small_cluster_is_filtered_without_changing_its_ratio() -> None:
    majority = np.tile(
        np.array([[180, 50, 40]], dtype=np.uint8),
        (95, 1),
    )
    outliers = np.tile(
        np.array([[30, 30, 210]], dtype=np.uint8),
        (5, 1),
    )

    estimates = deterministic_k2_estimates(
        np.vstack((majority, outliers)),
        ClusteringConfig(minimum_cluster_ratio=0.10),
    )

    assert len(estimates) == 1
    assert estimates[0].ratio == pytest.approx(0.95)
    assert np.count_nonzero(estimates[0].members) == 95


def test_cluster_at_minimum_ratio_is_retained() -> None:
    majority = np.tile(
        np.array([[180, 50, 40]], dtype=np.uint8),
        (90, 1),
    )
    minority = np.tile(
        np.array([[30, 30, 210]], dtype=np.uint8),
        (10, 1),
    )

    estimates = deterministic_k2_estimates(
        np.vstack((majority, minority)),
        ClusteringConfig(minimum_cluster_ratio=0.10),
    )

    assert len(estimates) == 2
    assert estimates[0].ratio == pytest.approx(0.90)
    assert estimates[1].ratio == pytest.approx(0.10)


def test_uniform_pixels_fall_back_to_one_cluster() -> None:
    pixels = np.tile(
        np.array([[80, 120, 160]], dtype=np.uint8),
        (40, 1),
    )

    estimates = deterministic_k2_estimates(pixels)

    assert len(estimates) == 1
    assert estimates[0].ratio == pytest.approx(1.0)
    assert np.all(estimates[0].members)


@pytest.mark.parametrize(
    "invalid_pixels",
    [
        np.empty((0, 3), dtype=np.uint8),
        np.ones((4, 4), dtype=np.uint8),
        np.ones((4, 3), dtype=np.float32),
    ],
    ids=["empty", "wrong-shape", "wrong-dtype"],
)
def test_invalid_pixel_array_fails_fast(
    invalid_pixels: np.ndarray,
) -> None:
    with pytest.raises(ValueError):
        robust_median_estimate(invalid_pixels)

    with pytest.raises(ValueError):
        deterministic_k2_estimates(invalid_pixels)


@pytest.mark.parametrize(
    "config_kwargs",
    [
        {"maximum_iterations": 0},
        {"convergence_tolerance": -1.0},
        {"minimum_cluster_ratio": 0.0},
        {"minimum_cluster_ratio": 0.51},
    ],
)
def test_invalid_clustering_configuration_fails_fast(
    config_kwargs: dict[str, float],
) -> None:
    with pytest.raises(ValueError):
        ClusteringConfig(**config_kwargs)  # type: ignore[arg-type]