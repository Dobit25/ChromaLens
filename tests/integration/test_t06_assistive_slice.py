from __future__ import annotations

import cv2
import numpy as np

from chromalens.color_extraction import ColorExtractionMode, DominantColorExtractor
from chromalens.config import CVDProfile
from chromalens.contracts import (
    FramePacket,
    GarmentRegion,
    LightingQuality,
    LightingQualityLevel,
)
from chromalens.recolor import SelectiveRecolorer
from chromalens.renderer import (
    AssistiveOverlayData,
    OverlayView,
    build_assistive_overlay_lines,
    render_assistive_overlay,
)
from chromalens.risk_detection import RelationalRiskDetector


def test_t04_t05_t06_assistive_slice_is_contained_stable_and_explicit() -> None:
    height, width = 80, 120
    corrected_rgb = np.full((height, width, 3), 145, dtype=np.uint8)
    garment_mask = np.zeros((height, width), dtype=np.bool_)
    garment_mask[8:72, 12:108] = True
    corrected_rgb[garment_mask & (np.indices((height, width))[1] < 60)] = (
        220,
        40,
        40,
    )
    corrected_rgb[garment_mask & (np.indices((height, width))[1] >= 60)] = (
        120,
        120,
        30,
    )
    source_bgr = cv2.cvtColor(corrected_rgb, cv2.COLOR_RGB2BGR)
    source_snapshot = source_bgr.copy()
    corrected_snapshot = corrected_rgb.copy()
    lighting = LightingQuality(
        level=LightingQualityLevel.GOOD,
        dark_fraction=0.0,
        clipped_fraction=0.0,
        gain_extremity=0.0,
        temporal_gain_variation=0.0,
    )
    packet = FramePacket(
        frame_id=12,
        timestamp_ns=456,
        original_bgr=source_bgr,
        corrected_rgb=corrected_rgb,
        lighting_quality=lighting,
    )
    region = GarmentRegion(
        track_id=3,
        class_name="upper-clothes",
        mask=garment_mask,
        mask_confidence=0.91,
    )
    clusters = DominantColorExtractor().extract(
        packet,
        region,
        mode=ColorExtractionMode.KMEANS_2,
    )
    source_cluster = next(cluster for cluster in clusters if cluster.original_name == "red")
    comparison_cluster = next(cluster for cluster in clusters if cluster is not source_cluster)
    risk = RelationalRiskDetector().assess_pair(
        source_cluster.rgb,
        comparison_cluster.rgb,
        source_id="track-3:red",
        comparison_id="track-3:comparison",
        profile=CVDProfile.DEUTAN,
        severity=1.0,
    )
    recolorer = SelectiveRecolorer()
    results = [
        recolorer.recolor(
            packet.original_bgr,
            garment_mask=region.mask,
            cluster=source_cluster,
            risk_mask=source_cluster.submask,
            comparison_rgb=comparison_cluster.rgb,
            risk=risk,
            profile=CVDProfile.DEUTAN,
            severity=1.0,
            state_key="video:track-3:red",
        )
        for _ in range(12)
    ]
    result = results[-1]
    overlay_data = AssistiveOverlayData(
        frame_id=packet.frame_id,
        original_color_name=result.debug.original_color_name,
        original_corrected_rgb=result.debug.original_corrected_rgb,
        assistive_display_rgb=result.debug.assistive_display_rgb,
        color_margin=source_cluster.color_margin,
        risk=risk,
        lighting_quality=packet.lighting_quality,
        profile=CVDProfile.DEUTAN,
        severity=1.0,
        backend_name="test-mask/cpu + chromalens-cielch-candidate-v1",
        recolor_applied=result.debug.applied,
        view=OverlayView.ASSISTIVE,
    )
    rendered = render_assistive_overlay(
        result.assistive_bgr,
        region.mask,
        overlay_data,
    )
    changed_before_overlay = np.any(
        result.assistive_bgr != packet.original_bgr,
        axis=2,
    )

    assert result.debug.applied
    assert result.debug.original_corrected_rgb != result.debug.assistive_display_rgb
    assert np.count_nonzero(changed_before_overlay & ~result.recolor_mask) == 0
    assert np.count_nonzero(changed_before_overlay & result.recolor_mask) > 0
    assert len({item.debug.assistive_display_rgb for item in results}) == 1
    assert sum(item.debug.switched for item in results) == 0
    assert build_assistive_overlay_lines(overlay_data)[0] == "VIEW: ASSISTIVE RESULT"
    assert not np.shares_memory(rendered, result.assistive_bgr)
    assert np.array_equal(packet.original_bgr, source_snapshot)
    assert np.array_equal(packet.corrected_rgb, corrected_snapshot)
