from __future__ import annotations

import numpy as np
import pytest

from chromalens.color_naming import rgb_color_to_cielab
from chromalens.config import CVDProfile
from chromalens.contracts import ColorCluster
from chromalens.risk_detection import (
    RelationalRiskConfig,
    RelationalRiskDetector,
    RiskLevel,
    ciede2000,
    relational_risk_score,
    risk_level_for_score,
)


SHARMA_REFERENCE_PAIRS = (
    ((50.0000, 2.6772, -79.7751), (50.0000, 0.0000, -82.7485), 2.0425),
    ((50.0000, 3.1571, -77.2803), (50.0000, 0.0000, -82.7485), 2.8615),
    ((50.0000, 2.8361, -74.0200), (50.0000, 0.0000, -82.7485), 3.4412),
    ((50.0000, -1.3802, -84.2814), (50.0000, 0.0000, -82.7485), 1.0000),
    ((50.0000, -1.1848, -84.8006), (50.0000, 0.0000, -82.7485), 1.0000),
    ((50.0000, -0.9009, -85.5211), (50.0000, 0.0000, -82.7485), 1.0000),
    ((50.0000, 0.0000, 0.0000), (50.0000, -1.0000, 2.0000), 2.3669),
    ((50.0000, -1.0000, 2.0000), (50.0000, 0.0000, 0.0000), 2.3669),
    ((50.0000, 2.4900, -0.0010), (50.0000, -2.4900, 0.0009), 7.1792),
    ((50.0000, 2.4900, -0.0010), (50.0000, -2.4900, 0.0011), 7.2195),
)


@pytest.mark.parametrize("lab1,lab2,expected", SHARMA_REFERENCE_PAIRS)
def test_ciede2000_matches_published_supplemental_values(
    lab1: tuple[float, float, float],
    lab2: tuple[float, float, float],
    expected: float,
) -> None:
    assert ciede2000(lab1, lab2) == pytest.approx(expected, abs=5e-5)


def test_ciede2000_is_symmetric_and_zero_for_identity() -> None:
    first = rgb_color_to_cielab((220, 40, 40))
    second = rgb_color_to_cielab((120, 120, 30))

    assert ciede2000(first, first) == pytest.approx(0.0, abs=1e-12)
    assert ciede2000(first, second) == pytest.approx(
        ciede2000(second, first),
        abs=1e-12,
    )


def test_known_deutan_confusing_pair_scores_above_separated_control() -> None:
    detector = RelationalRiskDetector()

    confusing = detector.assess_pair(
        (220, 40, 40),
        (120, 120, 30),
        source_id="red",
        comparison_id="olive",
        profile=CVDProfile.DEUTAN,
        severity=1.0,
    )
    control = detector.assess_pair(
        (40, 90, 220),
        (235, 220, 40),
        source_id="blue",
        comparison_id="yellow",
        profile=CVDProfile.DEUTAN,
        severity=1.0,
    )

    assert confusing.delta_e_cvd < confusing.delta_e_original
    assert confusing.risk_score > control.risk_score
    assert confusing.risk_level == RiskLevel.HIGH.value
    assert control.risk_level == RiskLevel.LOW.value


def test_assessment_records_both_delta_e_values_score_and_level() -> None:
    result = RelationalRiskDetector().assess_pair(
        (220, 40, 40),
        (120, 120, 30),
        source_id="garment:cluster:0",
        comparison_id="garment:cluster:1",
        profile=CVDProfile.DEUTAN,
        severity=0.8,
    )

    assert result.source_id == "garment:cluster:0"
    assert result.comparison_id == "garment:cluster:1"
    assert result.delta_e_original > 0.0
    assert result.delta_e_cvd >= 0.0
    assert 0.0 <= result.risk_score <= 1.0
    assert result.risk_level in {level.value for level in RiskLevel}


def test_severity_zero_has_no_cvd_created_risk() -> None:
    result = RelationalRiskDetector().assess_pair(
        (220, 40, 40),
        (120, 120, 30),
        source_id="red",
        comparison_id="olive",
        profile=CVDProfile.PROTAN,
        severity=0.0,
    )

    assert result.delta_e_cvd == pytest.approx(result.delta_e_original, abs=1e-12)
    assert result.risk_score == 0.0
    assert result.risk_level == RiskLevel.LOW.value


def test_cluster_comparison_returns_each_unordered_pair_once() -> None:
    mask = np.ones((2, 2), dtype=np.bool_)
    colors = ((220, 40, 40), (120, 120, 30), (40, 90, 220))
    clusters = tuple(
        ColorCluster(
            lab=rgb_color_to_cielab(rgb),
            rgb=rgb,
            ratio=1.0 / 3.0,
            submask=mask.copy(),
            original_name=f"color-{index}",
            name_scores={"placeholder": 1.0},
            color_margin=1.0,
        )
        for index, rgb in enumerate(colors)
    )

    results = RelationalRiskDetector().assess_cluster_pairs(
        clusters,
        garment_id="upper-0",
        profile=CVDProfile.DEUTAN,
        severity=1.0,
    )

    assert len(results) == 3
    assert [(item.source_id, item.comparison_id) for item in results] == [
        ("upper-0:cluster:0:color-0", "upper-0:cluster:1:color-1"),
        ("upper-0:cluster:0:color-0", "upper-0:cluster:2:color-2"),
        ("upper-0:cluster:1:color-1", "upper-0:cluster:2:color-2"),
    ]


def test_zero_or_one_cluster_produces_no_fabricated_comparison() -> None:
    mask = np.ones((2, 2), dtype=np.bool_)
    cluster = ColorCluster(
        lab=rgb_color_to_cielab((220, 40, 40)),
        rgb=(220, 40, 40),
        ratio=1.0,
        submask=mask,
        original_name="red",
        name_scores={"red": 1.0},
        color_margin=1.0,
    )
    detector = RelationalRiskDetector()

    assert detector.assess_cluster_pairs(
        (),
        garment_id="upper-0",
        profile=CVDProfile.DEUTAN,
        severity=1.0,
    ) == ()
    assert detector.assess_cluster_pairs(
        (cluster,),
        garment_id="upper-0",
        profile=CVDProfile.DEUTAN,
        severity=1.0,
    ) == ()


def test_configurable_score_thresholds_control_level_mapping() -> None:
    config = RelationalRiskConfig(
        minimum_original_delta_e=5.0,
        cvd_confusion_delta_e=25.0,
        medium_score_threshold=0.20,
        high_score_threshold=0.50,
    )

    score = relational_risk_score(50.0, 5.0, config=config)

    assert score == pytest.approx(0.72)
    assert risk_level_for_score(score, config=config) is RiskLevel.HIGH
    assert risk_level_for_score(0.20, config=config) is RiskLevel.MEDIUM


def test_zero_original_distance_is_safe_when_floor_is_configured_to_zero() -> None:
    config = RelationalRiskConfig(minimum_original_delta_e=0.0)

    assert relational_risk_score(0.0, 0.0, config=config) == 0.0


@pytest.mark.parametrize(
    "kwargs",
    [
        {"minimum_original_delta_e": -1.0},
        {"cvd_confusion_delta_e": 0.0},
        {"medium_score_threshold": 0.60, "high_score_threshold": 0.50},
        {"medium_score_threshold": 0.0},
        {"high_score_threshold": 1.01},
        {"cvd_confusion_delta_e": float("nan")},
    ],
)
def test_invalid_risk_configuration_is_rejected(kwargs: dict[str, float]) -> None:
    with pytest.raises(ValueError):
        RelationalRiskConfig(**kwargs)


@pytest.mark.parametrize(
    "original,simulated",
    [(-1.0, 1.0), (1.0, -1.0), (float("nan"), 1.0), (1.0, float("inf"))],
)
def test_invalid_delta_e_inputs_are_rejected(
    original: float,
    simulated: float,
) -> None:
    with pytest.raises(ValueError):
        relational_risk_score(original, simulated)
