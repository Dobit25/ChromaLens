from __future__ import annotations

import cv2
import numpy as np

from chromalens.color_extraction import ColorExtractionMode, DominantColorExtractor
from chromalens.config import CVDProfile
from chromalens.contracts import FramePacket, GarmentRegion
from chromalens.risk_detection import RelationalRiskDetector


def test_t04_clusters_feed_t05_relational_risk_without_source_mutation() -> None:
    corrected_rgb = np.empty((24, 40, 3), dtype=np.uint8)
    corrected_rgb[:, :20] = (220, 40, 40)
    corrected_rgb[:, 20:] = (120, 120, 30)
    original_bgr = cv2.cvtColor(corrected_rgb, cv2.COLOR_RGB2BGR)
    original_snapshot = original_bgr.copy()
    packet = FramePacket(
        frame_id=7,
        timestamp_ns=123,
        original_bgr=original_bgr,
        corrected_rgb=corrected_rgb,
    )
    region = GarmentRegion(
        track_id=4,
        class_name="upper-clothes",
        mask=np.ones(corrected_rgb.shape[:2], dtype=np.bool_),
        mask_confidence=0.9,
    )

    clusters = DominantColorExtractor().extract(
        packet,
        region,
        mode=ColorExtractionMode.KMEANS_2,
    )
    assessments = RelationalRiskDetector().assess_cluster_pairs(
        clusters,
        garment_id="track-4:upper-clothes",
        profile=CVDProfile.DEUTAN,
        severity=1.0,
    )

    assert len(clusters) == 2
    assert len(assessments) == 1
    assert assessments[0].delta_e_original > assessments[0].delta_e_cvd
    assert assessments[0].risk_score > 0.0
    assert np.array_equal(packet.original_bgr, original_snapshot)
    assert np.array_equal(packet.corrected_rgb, corrected_rgb)
