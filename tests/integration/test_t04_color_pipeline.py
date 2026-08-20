"""Hardware-independent T03-to-T04 channel/contract integration smoke test."""

from __future__ import annotations

import cv2
import numpy as np

from chromalens.color_extraction import DominantColorExtractor
from chromalens.contracts import FramePacket, GarmentRegion, LightingQualityLevel
from chromalens.white_balance import GrayWorldWhiteBalancer


def test_white_balance_output_flows_to_original_color_extraction() -> None:
    source_rgb = np.full((40, 40, 3), 128, dtype=np.uint8)
    garment_mask = np.zeros((40, 40), dtype=np.bool_)
    garment_mask[10:30, 10:30] = True
    source_rgb[garment_mask] = (210, 40, 40)
    source_bgr = cv2.cvtColor(source_rgb, cv2.COLOR_RGB2BGR)
    source_copy = source_bgr.copy()
    packet = FramePacket(frame_id=9, timestamp_ns=10, original_bgr=source_bgr)
    neutral_background = ~garment_mask

    white_balance = GrayWorldWhiteBalancer().process(
        packet,
        estimation_mask=neutral_background,
    )
    (cluster,) = DominantColorExtractor().extract(
        packet,
        GarmentRegion(2, "upper-clothes", garment_mask, 0.9),
    )

    assert white_balance.lighting_quality.level is LightingQualityLevel.GOOD
    assert cluster.original_name == "red"
    assert cluster.rgb == (210, 40, 40)
    assert cluster.submask.shape == garment_mask.shape
    assert not np.any(cluster.submask & ~garment_mask)
    np.testing.assert_array_equal(packet.original_bgr, source_copy)
