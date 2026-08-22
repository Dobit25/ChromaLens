"""Deterministic T04 tests for erosion, filtering, median, and K=2."""

from __future__ import annotations

import cv2
import numpy as np
import pytest

from chromalens.color_extraction import (
    ColorExtractionConfig,
    ColorExtractionMode,
    CorrectedFrameUnavailableError,
    DominantColorExtractor,
    InsufficientColorPixelsError,
    build_valid_color_mask,
    erode_garment_mask,
)
from chromalens.color_naming import BASIC_COLOR_NAMES
from chromalens.contracts import FramePacket, GarmentRegion


def test_mask_erosion_removes_the_uncertain_boundary() -> None:
    mask = np.zeros((10, 10), dtype=np.bool_)
    mask[2:8, 2:8] = True

    eroded = erode_garment_mask(mask, kernel_size=3, iterations=1)

    expected = np.zeros_like(mask)
    expected[3:7, 3:7] = True
    np.testing.assert_array_equal(eroded, expected)


def test_invalid_dark_clipped_and_low_confidence_pixels_are_rejected() -> None:
    rgb = np.full((9, 15, 3), 120, dtype=np.uint8)
    garment_mask = np.ones((9, 15), dtype=np.bool_)
    confidence = np.ones((9, 15), dtype=np.float32)
    rgb[3, 3] = (8, 8, 8)
    rgb[3, 4] = (250, 120, 120)
    confidence[3, 5] = 0.49

    valid = build_valid_color_mask(
        rgb,
        garment_mask,
        pixel_confidence=confidence,
    )

    assert not valid[3, 3]
    assert not valid[3, 4]
    assert not valid[3, 5]
    assert valid[3, 6]
    assert not np.any(valid[[0, -1], :])
    assert not np.any(valid[:, [0, -1]])


def test_robust_median_ignores_outliers_and_preserves_inputs() -> None:
    rgb = np.full((24, 24, 3), (10, 10, 10), dtype=np.uint8)
    mask = np.zeros((24, 24), dtype=np.bool_)
    mask[2:22, 2:22] = True
    rgb[mask] = (210, 40, 40)
    rgb[5:9, 5:9] = (30, 180, 50)
    packet = _packet(rgb)
    region = GarmentRegion(None, "upper-clothes", mask, 0.9)
    original_copy = packet.original_bgr.copy()
    corrected_copy = packet.corrected_rgb.copy()

    (cluster,) = DominantColorExtractor().extract(packet, region)

    assert cluster.original_name == "red"
    np.testing.assert_allclose(cluster.rgb, (210, 40, 40), atol=3)
    assert cluster.ratio == pytest.approx(1.0)
    assert set(cluster.name_scores) == set(BASIC_COLOR_NAMES)
    assert sum(cluster.name_scores.values()) == pytest.approx(1.0)
    assert cluster.color_margin is not None and cluster.color_margin > 0.0
    assert not np.any(cluster.submask & ~mask)
    np.testing.assert_array_equal(packet.original_bgr, original_copy)
    np.testing.assert_array_equal(packet.corrected_rgb, corrected_copy)


def test_kmeans_two_is_deterministic_complete_and_background_safe() -> None:
    rgb = np.full((30, 40, 3), (80, 110, 80), dtype=np.uint8)
    mask = np.zeros((30, 40), dtype=np.bool_)
    mask[3:27, 3:37] = True
    rgb[3:27, 3:24] = (210, 40, 40)
    rgb[3:27, 24:37] = (30, 80, 220)
    packet = _packet(rgb)
    region = GarmentRegion(4, "upper-clothes", mask, 0.9)
    extractor = DominantColorExtractor()

    first = extractor.extract(packet, region, mode=ColorExtractionMode.KMEANS_2)
    second = extractor.extract(packet, region, mode=ColorExtractionMode.KMEANS_2)

    assert [cluster.original_name for cluster in first] == ["red", "blue"]
    assert [cluster.ratio for cluster in first] == pytest.approx([0.625, 0.375])
    for first_cluster, second_cluster in zip(first, second):
        assert first_cluster.lab == pytest.approx(second_cluster.lab)
        assert first_cluster.rgb == second_cluster.rgb
        assert first_cluster.ratio == pytest.approx(second_cluster.ratio)
        assert first_cluster.name_scores == pytest.approx(second_cluster.name_scores)
        assert first_cluster.color_margin == pytest.approx(second_cluster.color_margin)
        np.testing.assert_array_equal(first_cluster.submask, second_cluster.submask)
        assert first_cluster.submask.dtype == np.bool_
        assert first_cluster.submask.shape == mask.shape
        assert not np.any(first_cluster.submask & ~mask)
        assert set(first_cluster.name_scores) == set(BASIC_COLOR_NAMES)
        assert first_cluster.color_margin is not None
    assert not np.any(first[0].submask & first[1].submask)
    retained_union = first[0].submask | first[1].submask
    assert not np.any(retained_union[3, 3:37])
    assert not np.any(retained_union[26, 3:37])


def test_small_kmeans_cluster_is_filtered_without_inflating_ratio() -> None:
    rgb = np.full((20, 100, 3), (210, 40, 40), dtype=np.uint8)
    mask = np.ones((20, 100), dtype=np.bool_)
    rgb[:, 94:] = (30, 80, 220)
    packet = _packet(rgb)
    region = GarmentRegion(None, "upper-clothes", mask)

    clusters = DominantColorExtractor().extract(
        packet,
        region,
        mode=ColorExtractionMode.KMEANS_2,
    )

    assert len(clusters) == 1
    assert clusters[0].original_name == "red"
    assert 0.90 < clusters[0].ratio < 1.0


def test_missing_corrected_frame_and_too_few_pixels_fail_actionably() -> None:
    original = np.zeros((8, 8, 3), dtype=np.uint8)
    packet = FramePacket(0, 1, original)
    region = GarmentRegion(None, "upper-clothes", np.ones((8, 8), dtype=np.bool_))

    with pytest.raises(CorrectedFrameUnavailableError, match="run T03"):
        DominantColorExtractor().extract(packet, region)

    packet.corrected_rgb = np.full_like(original, 8)
    with pytest.raises(InsufficientColorPixelsError, match="valid garment pixels"):
        DominantColorExtractor().extract(packet, region)


def test_confidence_map_validation_is_explicit() -> None:
    rgb = np.full((10, 10, 3), 100, dtype=np.uint8)
    mask = np.ones((10, 10), dtype=np.bool_)

    with pytest.raises(ValueError, match="floating-point"):
        build_valid_color_mask(
            rgb,
            mask,
            pixel_confidence=np.ones((10, 10), dtype=np.uint8),
        )
    invalid_confidence = np.ones((10, 10), dtype=np.float32)
    invalid_confidence[4, 4] = 1.1
    with pytest.raises(ValueError, match=r"\[0, 1\]"):
        build_valid_color_mask(rgb, mask, pixel_confidence=invalid_confidence)


@pytest.mark.parametrize(
    "config_kwargs",
    [
        {"erosion_kernel_size": 2},
        {"erosion_iterations": 0},
        {"dark_threshold": 250, "clipped_threshold": 250},
        {"minimum_valid_pixels": 0},
        {"minimum_cluster_ratio": 0.0},
        {"kmeans_seed": -1},
        {"kmeans_tolerance": 0.0},
    ],
)
def test_invalid_configuration_fails_fast(config_kwargs: dict[str, float]) -> None:
    with pytest.raises(ValueError):
        ColorExtractionConfig(**config_kwargs)  # type: ignore[arg-type]


def _packet(corrected_rgb: np.ndarray) -> FramePacket:
    original_bgr = cv2.cvtColor(corrected_rgb, cv2.COLOR_RGB2BGR)
    return FramePacket(
        frame_id=3,
        timestamp_ns=4,
        original_bgr=original_bgr,
        corrected_rgb=corrected_rgb.copy(),
    )
