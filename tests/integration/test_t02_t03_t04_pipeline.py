"""Integration test for the T02 -> T03 -> T04 analytical pipeline."""

from __future__ import annotations

import numpy as np
import pytest

from chromalens.color import extract_garment_colors
from chromalens.contracts import (
    FramePacket,
    GarmentRegion,
    LightingQualityLevel,
)
from chromalens.segmentation import Segmenter
from chromalens.white_balance import GrayWorldWhiteBalancer


class SyntheticGarmentSegmenter(Segmenter):
    """Deterministic test backend without model or hardware dependencies."""

    def __init__(self, garment: GarmentRegion) -> None:
        self._garment = garment

    @property
    def backend_name(self) -> str:
        return "synthetic-test"

    @property
    def device_info(self) -> str:
        return "synthetic-test/cpu"

    def segment(
        self,
        packet: FramePacket,
    ) -> tuple[GarmentRegion, ...]:
        assert self._garment.mask.shape == packet.original_bgr.shape[:2]
        return (self._garment,)


def test_t02_t03_t04_preserves_channel_order_and_mask_alignment() -> None:
    # OpenCV input is BGR. The neutral background allows Gray-world to apply
    # identity gains, while the garment is red when converted into RGB.
    original_bgr = np.full(
        (24, 24, 3),
        (128, 128, 128),
        dtype=np.uint8,
    )
    garment_mask = np.zeros((24, 24), dtype=np.bool_)
    garment_mask[4:20, 4:20] = True

    # BGR (0, 0, 249) must become RGB (249, 0, 0), not blue.
    original_bgr[garment_mask] = (0, 0, 249)
    original_copy = original_bgr.copy()

    packet = FramePacket(
        frame_id=7,
        timestamp_ns=123_456_789,
        original_bgr=original_bgr,
    )
    expected_garment = GarmentRegion(
        track_id=3,
        class_name="upper-clothes",
        mask=garment_mask,
        mask_confidence=0.95,
    )

    segmenter = SyntheticGarmentSegmenter(expected_garment)
    garments = segmenter.segment(packet)

    assert segmenter.backend_name == "synthetic-test"
    assert segmenter.device_info == "synthetic-test/cpu"
    assert len(garments) == 1
    assert garments[0] is expected_garment

    # Estimate Gray-world gains from neutral background rather than the
    # strongly chromatic garment.
    white_balancer = GrayWorldWhiteBalancer()
    balance_result = white_balancer.process(
        packet,
        estimation_mask=~garment_mask,
    )

    assert packet.corrected_rgb is not None
    assert packet.lighting_quality is not None
    assert packet.lighting_quality.level == LightingQualityLevel.GOOD
    assert balance_result.used_fallback is False
    assert balance_result.valid_fraction == pytest.approx(1.0)
    assert balance_result.gains_bgr == pytest.approx((1.0, 1.0, 1.0))

    np.testing.assert_array_equal(
        packet.corrected_rgb[10, 10],
        np.array((249, 0, 0), dtype=np.uint8),
    )
    np.testing.assert_array_equal(packet.original_bgr, original_copy)

    clusters = extract_garment_colors(
        packet.corrected_rgb,
        garments[0],
    )

    assert len(clusters) == 1

    cluster = clusters[0]
    assert cluster.original_name == "đỏ"
    assert cluster.rgb == pytest.approx((249, 0, 0), abs=1)
    assert cluster.ratio == pytest.approx(1.0)
    assert cluster.submask.shape == garment_mask.shape
    assert cluster.submask.dtype == np.bool_

    # The default 3x3 erosion removes one pixel from every garment edge:
    # 16x16 becomes 14x14 = 196 retained pixels.
    assert np.count_nonzero(cluster.submask) == 196
    assert not np.any(cluster.submask & ~garment_mask)

    expected_submask = np.zeros_like(garment_mask)
    expected_submask[5:19, 5:19] = True
    np.testing.assert_array_equal(cluster.submask, expected_submask)