"""T03/T04-to-T07 test proving matching uses original corrected color."""

from __future__ import annotations

import cv2
import numpy as np
import pytest

from chromalens.color_extraction import DominantColorExtractor
from chromalens.contracts import FramePacket, GarmentRegion
from chromalens.matching import MatchingStatus, RuleBasedMatcher
from chromalens.white_balance import GrayWorldWhiteBalancer


def test_matching_consumes_t04_original_cluster_without_display_color_input() -> None:
    corrected_rgb = np.full((48, 64, 3), 128, dtype=np.uint8)
    garment_mask = np.zeros((48, 64), dtype=np.bool_)
    garment_mask[8:40, 12:52] = True
    corrected_rgb[garment_mask] = (218, 38, 38)
    source_bgr = cv2.cvtColor(corrected_rgb, cv2.COLOR_RGB2BGR)
    source_snapshot = source_bgr.copy()
    packet = FramePacket(frame_id=17, timestamp_ns=99, original_bgr=source_bgr)

    GrayWorldWhiteBalancer().process(packet, estimation_mask=~garment_mask)
    (original_cluster,) = DominantColorExtractor().extract(
        packet,
        GarmentRegion(5, "upper-clothes", garment_mask, 0.9),
    )
    result = RuleBasedMatcher().suggest_from_original_cluster(original_cluster)

    assert original_cluster.original_name == "red"
    assert result.status is MatchingStatus.READY
    assert result.source_original_lab == original_cluster.lab
    assert result.source_original_rgb == original_cluster.rgb
    assert all(
        suggestion.source_original_lab == original_cluster.lab
        and suggestion.source_original_rgb == original_cluster.rgb
        for suggestion in result.suggestions
    )
    assert np.array_equal(packet.original_bgr, source_snapshot)

    # A T06-like display tuple cannot enter the T07 contract in place of T04.
    with pytest.raises(TypeError, match="T04 ColorCluster"):
        RuleBasedMatcher().suggest_from_original_cluster(  # type: ignore[arg-type]
            result.suggestions[0].target_rgb
        )
