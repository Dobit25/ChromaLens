"""CIEDE2000 relational CVD-risk assessment for original color clusters."""

from __future__ import annotations

import math
from dataclasses import dataclass
from enum import Enum
from itertools import combinations
from typing import Sequence

import numpy as np

from chromalens.color_naming import LabColor, RGBColor, rgb_color_to_cielab
from chromalens.config import CVDProfile
from chromalens.contracts import ColorCluster, RiskAssessment
from chromalens.cvd_simulation import MachadoSimulator, validate_severity


class RiskLevel(str, Enum):
    """Display-only levels derived from a transparent heuristic score."""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


@dataclass(frozen=True, slots=True)
class RelationalRiskConfig:
    """Validated, user-evaluation-dependent relational-risk thresholds.

    ``minimum_original_delta_e`` prevents a CVD-created-risk claim when the
    source colors were already very similar. ``cvd_confusion_delta_e`` defines
    the simulated-distance range over which closeness contributes to risk.
    All values are heuristics for T09 validation, not universal perceptual or
    medical thresholds.
    """

    minimum_original_delta_e: float = 5.0
    cvd_confusion_delta_e: float = 20.0
    medium_score_threshold: float = 0.25
    high_score_threshold: float = 0.60

    def __post_init__(self) -> None:
        for field_name in (
            "minimum_original_delta_e",
            "cvd_confusion_delta_e",
            "medium_score_threshold",
            "high_score_threshold",
        ):
            value = getattr(self, field_name)
            if not np.isfinite(value):
                raise ValueError(f"{field_name} must be finite")
        if self.minimum_original_delta_e < 0.0:
            raise ValueError("minimum_original_delta_e must be non-negative")
        if self.cvd_confusion_delta_e <= 0.0:
            raise ValueError("cvd_confusion_delta_e must be positive")
        if not 0.0 < self.medium_score_threshold < self.high_score_threshold <= 1.0:
            raise ValueError(
                "risk score thresholds must satisfy 0 < medium < high <= 1"
            )


class RelationalRiskDetector:
    """Compare original colors before and after one selected CVD simulation."""

    def __init__(
        self,
        config: RelationalRiskConfig | None = None,
        *,
        simulator: MachadoSimulator | None = None,
    ) -> None:
        self.config = config or RelationalRiskConfig()
        self.simulator = simulator or MachadoSimulator()

    def assess_pair(
        self,
        source_rgb: RGBColor,
        comparison_rgb: RGBColor,
        *,
        source_id: str,
        comparison_id: str,
        profile: CVDProfile,
        severity: float,
    ) -> RiskAssessment:
        """Assess one pair of original corrected sRGB colors."""

        if not source_id.strip() or not comparison_id.strip():
            raise ValueError("risk comparison identifiers must not be empty")
        validated_severity = validate_severity(severity)
        source_lab = rgb_color_to_cielab(source_rgb)
        comparison_lab = rgb_color_to_cielab(comparison_rgb)
        simulated_source_rgb = self.simulator.simulate_color(
            source_rgb,
            profile=profile,
            severity=validated_severity,
        )
        simulated_comparison_rgb = self.simulator.simulate_color(
            comparison_rgb,
            profile=profile,
            severity=validated_severity,
        )
        simulated_source_lab = rgb_color_to_cielab(simulated_source_rgb)
        simulated_comparison_lab = rgb_color_to_cielab(simulated_comparison_rgb)

        delta_e_original = ciede2000(source_lab, comparison_lab)
        delta_e_cvd = ciede2000(simulated_source_lab, simulated_comparison_lab)
        risk_score = relational_risk_score(
            delta_e_original,
            delta_e_cvd,
            config=self.config,
        )
        return RiskAssessment(
            source_id=source_id,
            comparison_id=comparison_id,
            delta_e_original=delta_e_original,
            delta_e_cvd=delta_e_cvd,
            risk_score=risk_score,
            risk_level=risk_level_for_score(risk_score, config=self.config).value,
        )

    def assess_cluster_pairs(
        self,
        clusters: Sequence[ColorCluster],
        *,
        garment_id: str,
        profile: CVDProfile,
        severity: float,
    ) -> tuple[RiskAssessment, ...]:
        """Assess every unordered retained-color pair inside one garment."""

        if not garment_id.strip():
            raise ValueError("garment_id must not be empty")
        validated_severity = validate_severity(severity)
        assessments: list[RiskAssessment] = []
        for source_index, comparison_index in combinations(range(len(clusters)), 2):
            source = clusters[source_index]
            comparison = clusters[comparison_index]
            assessments.append(
                self.assess_pair(
                    source.rgb,
                    comparison.rgb,
                    source_id=(
                        f"{garment_id}:cluster:{source_index}:{source.original_name}"
                    ),
                    comparison_id=(
                        f"{garment_id}:cluster:{comparison_index}:"
                        f"{comparison.original_name}"
                    ),
                    profile=profile,
                    severity=validated_severity,
                )
            )
        return tuple(assessments)


def relational_risk_score(
    delta_e_original: float,
    delta_e_cvd: float,
    *,
    config: RelationalRiskConfig | None = None,
) -> float:
    """Combine relative separation loss and post-simulation closeness.

    The score is ``relative_loss * simulated_closeness``. It reaches zero if
    simulation does not reduce Delta-E or if simulated Delta-E is at/above the
    configured confusion distance. This is an explainable ranking heuristic,
    not a calibrated probability of confusion.
    """

    active_config = config or RelationalRiskConfig()
    _validate_delta_e(delta_e_original, "delta_e_original")
    _validate_delta_e(delta_e_cvd, "delta_e_cvd")
    if (
        delta_e_original == 0.0
        or delta_e_original < active_config.minimum_original_delta_e
    ):
        return 0.0
    relative_loss = np.clip(
        (delta_e_original - delta_e_cvd) / delta_e_original,
        0.0,
        1.0,
    )
    simulated_closeness = np.clip(
        1.0 - (delta_e_cvd / active_config.cvd_confusion_delta_e),
        0.0,
        1.0,
    )
    return float(np.clip(relative_loss * simulated_closeness, 0.0, 1.0))


def risk_level_for_score(
    risk_score: float,
    *,
    config: RelationalRiskConfig | None = None,
) -> RiskLevel:
    """Map a validated heuristic score to a configured display level."""

    active_config = config or RelationalRiskConfig()
    if not np.isfinite(risk_score) or not 0.0 <= risk_score <= 1.0:
        raise ValueError("risk_score must be finite within [0, 1]")
    if risk_score >= active_config.high_score_threshold:
        return RiskLevel.HIGH
    if risk_score >= active_config.medium_score_threshold:
        return RiskLevel.MEDIUM
    return RiskLevel.LOW


def ciede2000(
    lab1: LabColor,
    lab2: LabColor,
    *,
    k_l: float = 1.0,
    k_c: float = 1.0,
    k_h: float = 1.0,
) -> float:
    """Return CIEDE2000 Delta-E for conventional CIELAB tuples.

    The implementation follows Sharma, Wu, and Dalal (2005). Parametric
    factors default to the reference conditions used by their supplemental
    test data.
    """

    first = _validate_lab(lab1, "lab1")
    second = _validate_lab(lab2, "lab2")
    for field_name, value in (("k_l", k_l), ("k_c", k_c), ("k_h", k_h)):
        if not np.isfinite(value) or value <= 0.0:
            raise ValueError(f"{field_name} must be positive and finite")

    l1, a1, b1 = (float(value) for value in first)
    l2, a2, b2 = (float(value) for value in second)
    c1 = math.hypot(a1, b1)
    c2 = math.hypot(a2, b2)
    c_bar = (c1 + c2) / 2.0
    c_bar_seventh = c_bar**7
    g = 0.5 * (
        1.0 - math.sqrt(c_bar_seventh / (c_bar_seventh + 25.0**7))
    )

    a1_prime = (1.0 + g) * a1
    a2_prime = (1.0 + g) * a2
    c1_prime = math.hypot(a1_prime, b1)
    c2_prime = math.hypot(a2_prime, b2)
    h1_prime = _hue_degrees(b1, a1_prime)
    h2_prime = _hue_degrees(b2, a2_prime)

    delta_l_prime = l2 - l1
    delta_c_prime = c2_prime - c1_prime
    hue_difference = h2_prime - h1_prime
    if c1_prime * c2_prime == 0.0:
        delta_h_prime = 0.0
    elif abs(hue_difference) <= 180.0:
        delta_h_prime = hue_difference
    elif hue_difference > 180.0:
        delta_h_prime = hue_difference - 360.0
    else:
        delta_h_prime = hue_difference + 360.0
    delta_big_h_prime = (
        2.0
        * math.sqrt(c1_prime * c2_prime)
        * math.sin(math.radians(delta_h_prime / 2.0))
    )

    l_bar_prime = (l1 + l2) / 2.0
    c_bar_prime = (c1_prime + c2_prime) / 2.0
    if c1_prime * c2_prime == 0.0:
        h_bar_prime = h1_prime + h2_prime
    elif abs(h1_prime - h2_prime) <= 180.0:
        h_bar_prime = (h1_prime + h2_prime) / 2.0
    elif h1_prime + h2_prime < 360.0:
        h_bar_prime = (h1_prime + h2_prime + 360.0) / 2.0
    else:
        h_bar_prime = (h1_prime + h2_prime - 360.0) / 2.0

    t = (
        1.0
        - 0.17 * math.cos(math.radians(h_bar_prime - 30.0))
        + 0.24 * math.cos(math.radians(2.0 * h_bar_prime))
        + 0.32 * math.cos(math.radians(3.0 * h_bar_prime + 6.0))
        - 0.20 * math.cos(math.radians(4.0 * h_bar_prime - 63.0))
    )
    delta_theta = 30.0 * math.exp(-(((h_bar_prime - 275.0) / 25.0) ** 2))
    c_bar_prime_seventh = c_bar_prime**7
    r_c = 2.0 * math.sqrt(
        c_bar_prime_seventh / (c_bar_prime_seventh + 25.0**7)
    )
    l_offset_squared = (l_bar_prime - 50.0) ** 2
    s_l = 1.0 + (0.015 * l_offset_squared) / math.sqrt(
        20.0 + l_offset_squared
    )
    s_c = 1.0 + 0.045 * c_bar_prime
    s_h = 1.0 + 0.015 * c_bar_prime * t
    r_t = -math.sin(math.radians(2.0 * delta_theta)) * r_c

    lightness_term = delta_l_prime / (k_l * s_l)
    chroma_term = delta_c_prime / (k_c * s_c)
    hue_term = delta_big_h_prime / (k_h * s_h)
    squared_distance = (
        lightness_term**2
        + chroma_term**2
        + hue_term**2
        + r_t * chroma_term * hue_term
    )
    return math.sqrt(max(0.0, squared_distance))


def _hue_degrees(b: float, a_prime: float) -> float:
    if a_prime == 0.0 and b == 0.0:
        return 0.0
    return math.degrees(math.atan2(b, a_prime)) % 360.0


def _validate_lab(lab: LabColor, field_name: str) -> np.ndarray:
    array = np.asarray(lab, dtype=np.float64)
    if array.shape != (3,) or not np.all(np.isfinite(array)):
        raise ValueError(f"{field_name} must contain three finite values")
    if not 0.0 <= float(array[0]) <= 100.0:
        raise ValueError(f"{field_name} L* must be within [0, 100]")
    return array


def _validate_delta_e(value: float, field_name: str) -> None:
    if not np.isfinite(value) or value < 0.0:
        raise ValueError(f"{field_name} must be finite and non-negative")
