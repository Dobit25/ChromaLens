from __future__ import annotations

import cv2
import numpy as np
import pytest

from chromalens.color_naming import rgb_color_to_cielab
from chromalens.config import CVDProfile
from chromalens.contracts import ColorCluster, RiskAssessment
from chromalens.recolor import (
    RecolorConfig,
    SelectiveRecolorer,
    apply_lightness_preserving_chroma_shift,
    inward_feather_alpha,
)
from chromalens.risk_detection import RelationalRiskDetector


def _scene() -> tuple[
    np.ndarray,
    np.ndarray,
    np.ndarray,
    np.ndarray,
    ColorCluster,
    RiskAssessment,
    tuple[int, int, int],
]:
    height, width = 48, 64
    original_rgb = (220, 40, 40)
    comparison_rgb = (120, 120, 30)
    source_bgr = np.full((height, width, 3), 128, dtype=np.uint8)
    garment_mask = np.zeros((height, width), dtype=np.bool_)
    garment_mask[4:44, 4:60] = True
    cluster_mask = np.zeros_like(garment_mask)
    cluster_mask[7:41, 7:37] = True
    risk_mask = np.zeros_like(garment_mask)
    risk_mask[11:37, 11:50] = True
    source_bgr[cluster_mask] = original_rgb[::-1]
    cluster = ColorCluster(
        lab=rgb_color_to_cielab(original_rgb),
        rgb=original_rgb,
        ratio=0.5,
        submask=cluster_mask,
        original_name="red",
        name_scores={"red": 1.0},
        color_margin=0.75,
    )
    risk = RelationalRiskDetector().assess_pair(
        original_rgb,
        comparison_rgb,
        source_id="garment:cluster:red",
        comparison_id="garment:cluster:olive",
        profile=CVDProfile.DEUTAN,
        severity=1.0,
    )
    return (
        source_bgr,
        garment_mask,
        cluster_mask,
        risk_mask,
        cluster,
        risk,
        comparison_rgb,
    )


def _run_recolor(
    recolorer: SelectiveRecolorer | None = None,
    *,
    profile: CVDProfile = CVDProfile.DEUTAN,
    severity: float = 1.0,
    risk_override: RiskAssessment | None = None,
    state_key: str = "stream:garment:red",
):
    source, garment, _, risk_mask, cluster, risk, comparison = _scene()
    active = recolorer or SelectiveRecolorer()
    result = active.recolor(
        source,
        garment_mask=garment,
        cluster=cluster,
        risk_mask=risk_mask,
        comparison_rgb=comparison,
        risk=risk_override or risk,
        profile=profile,
        severity=severity,
        state_key=state_key,
    )
    return source, garment, cluster, risk_mask, comparison, result


def test_recolor_uses_exact_three_mask_intersection_and_preserves_everything_outside() -> None:
    source, garment, cluster, risk_mask, _, result = _run_recolor()
    source_snapshot = source.copy()
    expected_mask = garment & cluster.submask & risk_mask
    changed = np.any(result.assistive_bgr != source, axis=2)

    assert result.debug.applied
    assert np.array_equal(result.recolor_mask, expected_mask)
    assert np.count_nonzero(changed & expected_mask) > 0
    assert np.count_nonzero(changed & ~expected_mask) == 0
    assert np.array_equal(source, source_snapshot)
    assert not np.shares_memory(result.assistive_bgr, source)


def test_inward_feather_is_zero_outside_and_stronger_in_the_interior() -> None:
    mask = np.zeros((15, 15), dtype=np.bool_)
    mask[2:13, 2:13] = True

    alpha = inward_feather_alpha(mask, radius_px=4.0)

    assert alpha.dtype == np.float32
    assert np.all(alpha[~mask] == 0.0)
    assert 0.0 < float(alpha[2, 7]) < float(alpha[7, 7])
    assert alpha[7, 7] == pytest.approx(1.0)


def test_zero_radius_returns_a_hard_float_alpha_mask() -> None:
    mask = np.asarray([[False, True], [True, False]], dtype=np.bool_)

    alpha = inward_feather_alpha(mask, radius_px=0.0)

    assert alpha.dtype == np.float32
    assert np.array_equal(alpha, mask.astype(np.float32))


def test_recolor_preserves_representative_lightness_with_small_roundtrip_error() -> None:
    source, _, _, _, _, result = _run_recolor()
    interior = result.alpha_mask == 1.0
    source_lab = cv2.cvtColor(source.astype(np.float32) / 255.0, cv2.COLOR_BGR2LAB)
    result_lab = cv2.cvtColor(
        result.assistive_bgr.astype(np.float32) / 255.0,
        cv2.COLOR_BGR2LAB,
    )

    assert np.any(interior)
    assert float(np.max(np.abs(result_lab[..., 0][interior] - source_lab[..., 0][interior]))) < 1.0


def test_debug_data_separates_original_corrected_and_assistive_display_colors() -> None:
    _, _, cluster, _, comparison, result = _run_recolor()

    assert result.debug.original_corrected_rgb == cluster.rgb
    assert result.debug.assistive_display_rgb != cluster.rgb
    assert result.debug.comparison_original_rgb == comparison
    assert result.debug.original_color_name == "red"
    assert result.debug.decision_reason == "candidate_applied"
    assert result.debug.assistive_simulated_delta_e > result.debug.original_simulated_delta_e


def test_low_risk_returns_an_explicit_unchanged_result() -> None:
    _, _, _, _, _, high_risk, _ = _scene()
    low_risk = RiskAssessment(
        source_id=high_risk.source_id,
        comparison_id=high_risk.comparison_id,
        delta_e_original=high_risk.delta_e_original,
        delta_e_cvd=high_risk.delta_e_cvd,
        risk_score=0.10,
        risk_level="low",
    )
    source, _, cluster, _, _, result = _run_recolor(risk_override=low_risk)

    assert not result.debug.applied
    assert result.debug.assistive_display_rgb == cluster.rgb
    assert result.debug.decision_reason == "risk_below_threshold"
    assert not np.any(result.alpha_mask)
    assert np.array_equal(result.assistive_bgr, source)


def test_zero_severity_never_fabricates_an_assistive_change() -> None:
    source, _, cluster, _, _, result = _run_recolor(severity=0.0)

    assert not result.debug.applied
    assert result.debug.assistive_display_rgb == cluster.rgb
    assert result.debug.decision_reason == "severity_zero"
    assert np.array_equal(result.assistive_bgr, source)


def test_empty_intersection_returns_an_explicit_unchanged_result() -> None:
    source, garment, _, _, cluster, risk, comparison = _scene()
    empty_risk_mask = np.zeros(garment.shape, dtype=np.bool_)

    result = SelectiveRecolorer().recolor(
        source,
        garment_mask=garment,
        cluster=cluster,
        risk_mask=empty_risk_mask,
        comparison_rgb=comparison,
        risk=risk,
        profile=CVDProfile.DEUTAN,
        severity=1.0,
        state_key="empty",
    )

    assert not result.debug.applied
    assert result.debug.decision_reason == "empty_mask_intersection"
    assert not np.any(result.recolor_mask)
    assert np.array_equal(result.assistive_bgr, source)


def test_candidate_selection_depends_on_selected_profile_not_a_universal_rule() -> None:
    _, _, _, _, _, protan = _run_recolor(profile=CVDProfile.PROTAN, state_key="p")
    _, _, _, _, _, deutan = _run_recolor(profile=CVDProfile.DEUTAN, state_key="d")

    assert protan.debug.applied and deutan.debug.applied
    assert protan.debug.assistive_display_rgb != deutan.debug.assistive_display_rgb


def test_static_short_run_has_one_color_and_zero_switches() -> None:
    recolorer = SelectiveRecolorer()
    results = [_run_recolor(recolorer)[-1] for _ in range(20)]

    assert len({result.debug.assistive_display_rgb for result in results}) == 1
    assert sum(result.debug.switched for result in results) == 0


def test_hysteresis_requires_consecutive_better_proposals_before_switch() -> None:
    recolorer = SelectiveRecolorer(
        RecolorConfig(
            switch_objective_margin=0.0,
            switch_confirmation_frames=3,
        )
    )
    first = _run_recolor(
        recolorer,
        profile=CVDProfile.DEUTAN,
        state_key="same",
    )[-1]
    challengers = [
        _run_recolor(
            recolorer,
            profile=CVDProfile.PROTAN,
            state_key="same",
        )[-1]
        for _ in range(3)
    ]

    assert challengers[0].debug.assistive_display_rgb == first.debug.assistive_display_rgb
    assert challengers[1].debug.assistive_display_rgb == first.debug.assistive_display_rgb
    assert not challengers[0].debug.switched
    assert not challengers[1].debug.switched
    assert challengers[2].debug.switched
    assert challengers[2].debug.assistive_display_rgb != first.debug.assistive_display_rgb


def test_temporal_state_is_lru_bounded() -> None:
    recolorer = SelectiveRecolorer(RecolorConfig(max_state_entries=3))

    for index in range(8):
        _run_recolor(recolorer, state_key=f"track:{index}")

    assert recolorer.state_count == 3


def test_lightness_shift_rejects_alpha_support_outside_mask() -> None:
    source = np.zeros((3, 3, 3), dtype=np.uint8)
    mask = np.zeros((3, 3), dtype=np.bool_)
    mask[1, 1] = True
    alpha = mask.astype(np.float32)
    alpha[0, 0] = 0.1

    with pytest.raises(ValueError, match="zero outside"):
        apply_lightness_preserving_chroma_shift(
            source,
            mask,
            alpha,
            original_lab=rgb_color_to_cielab((220, 40, 40)),
            display_rgb=(0, 120, 251),
        )


@pytest.mark.parametrize(
    ("kwargs", "message"),
    [
        ({"minimum_risk_score": 1.1}, "minimum_risk_score"),
        ({"feather_radius_px": -1.0}, "feather_radius_px"),
        ({"candidate_hue_offsets_degrees": ()}, "hue offsets"),
        ({"candidate_chroma_scales": (0.0,)}, "chroma scales"),
        ({"switch_confirmation_frames": 0}, "switch_confirmation_frames"),
        ({"max_state_entries": 0}, "max_state_entries"),
    ],
)
def test_recolor_config_rejects_invalid_values(
    kwargs: dict[str, object],
    message: str,
) -> None:
    with pytest.raises(ValueError, match=message):
        RecolorConfig(**kwargs)


def test_recolor_rejects_misaligned_risk_mask() -> None:
    source, garment, _, _, cluster, risk, comparison = _scene()

    with pytest.raises(ValueError, match="risk_mask"):
        SelectiveRecolorer().recolor(
            source,
            garment_mask=garment,
            cluster=cluster,
            risk_mask=np.ones((2, 2), dtype=np.bool_),
            comparison_rgb=comparison,
            risk=risk,
            profile=CVDProfile.DEUTAN,
            severity=1.0,
            state_key="bad-mask",
        )
