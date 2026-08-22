from __future__ import annotations

import numpy as np
import pytest

from chromalens.config import CVDProfile
from chromalens.contracts import (
    LightingQuality,
    LightingQualityLevel,
    RiskAssessment,
)
from chromalens.renderer import (
    AssistiveOverlayData,
    AssistiveOverlayStyle,
    OverlayView,
    build_assistive_overlay_lines,
    render_assistive_overlay,
    render_cvd_simulation_debug_overlay,
)


def _overlay_data(*, view: OverlayView = OverlayView.ASSISTIVE) -> AssistiveOverlayData:
    return AssistiveOverlayData(
        frame_id=17,
        original_color_name="red",
        original_corrected_rgb=(220, 40, 40),
        assistive_display_rgb=(0, 120, 251),
        color_margin=0.421,
        risk=RiskAssessment(
            source_id="garment:red",
            comparison_id="garment:olive",
            delta_e_original=45.7,
            delta_e_cvd=4.6,
            risk_score=0.693,
            risk_level="high",
        ),
        lighting_quality=LightingQuality(
            level=LightingQualityLevel.GOOD,
            dark_fraction=0.01,
            clipped_fraction=0.0,
            gain_extremity=0.1,
            temporal_gain_variation=0.02,
        ),
        profile=CVDProfile.DEUTAN,
        severity=1.0,
        backend_name="mediapipe-selfie-torso/cpu + chromalens-candidate-v1",
        recolor_applied=True,
        view=view,
    )


def test_overlay_lines_label_original_and_assistive_colors_separately() -> None:
    lines = build_assistive_overlay_lines(_overlay_data())

    assert lines[0] == "VIEW: ASSISTIVE RESULT"
    assert lines[1].startswith("Original corrected: red/Do RGB=(220, 40, 40)")
    assert lines[2].startswith("Assistive display: RGB=(0, 120, 251)")
    assert "margin=0.421" in lines[1]
    assert "Mask confidence: unavailable" in lines[3]
    assert "Risk: high 0.693" in lines[3]
    assert "lighting: good" in lines[3]
    assert "Profile: deutan severity=1.00" in lines[4]
    assert lines[5] == "Frame: 17 | degraded: none"


def test_simulation_view_is_unambiguously_debug_only() -> None:
    data = _overlay_data(view=OverlayView.CVD_SIMULATION_DEBUG)
    lines = build_assistive_overlay_lines(data)

    assert lines[0] == "VIEW: CVD SIMULATION (DEBUG ONLY)"
    assert lines[0] != "VIEW: ASSISTIVE RESULT"
    assert lines[2].startswith("Assistive target (separate):")
    frame = np.zeros((200, 640, 3), dtype=np.uint8)
    mask = np.zeros((200, 640), dtype=np.bool_)
    assert render_cvd_simulation_debug_overlay(frame, mask, data).shape == frame.shape
    with pytest.raises(ValueError, match="explicit CVD simulation debug renderer"):
        render_assistive_overlay(frame, mask, data)


def test_renderer_uses_background_independent_opaque_high_contrast_tag() -> None:
    light = np.full((360, 800, 3), 245, dtype=np.uint8)
    dark = np.full((360, 800, 3), 10, dtype=np.uint8)
    mask = np.zeros((360, 800), dtype=np.bool_)
    mask[220:330, 280:520] = True

    rendered_light = render_assistive_overlay(light, mask, _overlay_data())
    rendered_dark = render_assistive_overlay(dark, mask, _overlay_data())
    # This crop is strictly inside the opaque tag for the declared content;
    # pixels beyond the computed tag width intentionally remain background.
    tag_light = rendered_light[12:156, 12:450]
    tag_dark = rendered_dark[12:156, 12:450]

    assert np.array_equal(tag_light, tag_dark)
    assert np.count_nonzero(np.all(tag_light == 0, axis=2)) > 1000
    assert np.count_nonzero(np.all(tag_light >= 200, axis=2)) > 100


def test_renderer_draws_exact_black_and_white_contour_without_mutating_input() -> None:
    frame = np.full((240, 640, 3), 127, dtype=np.uint8)
    before = frame.copy()
    mask = np.zeros((240, 640), dtype=np.bool_)
    mask[180:220, 250:390] = True

    rendered = render_assistive_overlay(frame, mask, _overlay_data())
    boundary_band = rendered[174:226, 244:396]

    assert np.array_equal(frame, before)
    assert not np.shares_memory(rendered, frame)
    assert np.any(np.all(boundary_band == (0, 0, 0), axis=2))
    assert np.any(np.all(boundary_band == (255, 255, 255), axis=2))


def test_renderer_rejects_non_boolean_or_misaligned_mask() -> None:
    frame = np.zeros((100, 200, 3), dtype=np.uint8)

    with pytest.raises(ValueError, match="garment_mask"):
        render_assistive_overlay(
            frame,
            np.ones((100, 200), dtype=np.uint8),
            _overlay_data(),
        )


@pytest.mark.parametrize(
    ("kwargs", "error"),
    [
        ({"frame_id": -1}, "frame_id"),
        ({"color_margin": 1.1}, "color_margin"),
        ({"severity": float("nan")}, "severity"),
        ({"backend_name": " "}, "backend_name"),
    ],
)
def test_overlay_data_validates_public_fields(
    kwargs: dict[str, object],
    error: str,
) -> None:
    values = {
        "frame_id": 1,
        "original_color_name": "red",
        "original_corrected_rgb": (220, 40, 40),
        "assistive_display_rgb": (0, 120, 251),
        "color_margin": 0.4,
        "risk": _overlay_data().risk,
        "lighting_quality": _overlay_data().lighting_quality,
        "profile": CVDProfile.DEUTAN,
        "severity": 1.0,
        "backend_name": "backend/cpu",
        "recolor_applied": True,
    }
    values.update(kwargs)
    with pytest.raises((TypeError, ValueError), match=error):
        AssistiveOverlayData(**values)


def test_overlay_style_requires_black_outline_to_be_thicker() -> None:
    with pytest.raises(ValueError, match="black outline"):
        AssistiveOverlayStyle(
            outline_black_thickness_px=2,
            outline_white_thickness_px=2,
        )
