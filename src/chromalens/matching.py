"""Deterministic CIELCH guidance derived from original corrected colors.

This module consumes only T04 :class:`~chromalens.contracts.ColorCluster`
values.  It deliberately has no parameter for T06 assistive display colors.
The project-authored rules are explainable guidance, not confidence estimates
or claims of objective fashion truth.
"""

from __future__ import annotations

import csv
import math
from dataclasses import dataclass
from enum import Enum
from pathlib import Path

from chromalens.color_naming import (
    BASIC_COLOR_NAMES,
    LabColor,
    RGBColor,
    cielab_to_rgb_color,
    name_cielab_color,
    rgb_color_to_cielab,
    vietnamese_color_label,
)
from chromalens.config import CVDProfile
from chromalens.contracts import ColorCluster
from chromalens.cvd_simulation import MachadoSimulator, validate_severity
from chromalens.risk_detection import ciede2000

CIELCHColor = tuple[float, float, float]

GUIDANCE_NOTICE_VI = (
    "Đây là gợi ý tham khảo, không phải quy tắc thời trang khách quan."
)
MISSING_COLOR_EXPLANATION_VI = (
    "Chưa có màu trang phục gốc đã hiệu chỉnh để tạo gợi ý an toàn."
)
UNKNOWN_COLOR_EXPLANATION_VI = (
    "Màu trang phục gốc chưa thuộc 11 nhóm màu được hỗ trợ; "
    "không tạo gợi ý hoặc độ tin cậy giả."
)

SUGGESTION_COLUMNS: tuple[str, ...] = (
    "rule_id",
    "source_kind",
    "harmony",
    "priority",
    "min_source_lightness",
    "max_source_lightness",
    "hue_offset_degrees",
    "lightness_strategy",
    "chroma_scale",
    "reason_vi",
    "provenance",
)

_DEFAULT_RULES_PATH = (
    Path(__file__).resolve().parents[2] / "assets" / "suggestions.csv"
)


class MatchingRulesError(ValueError):
    """Raised when the committed rule table is missing or invalid."""


class SourceKind(str, Enum):
    """Coarse CIELCH source class used to select applicable rules."""

    NEUTRAL = "neutral"
    CHROMATIC = "chromatic"


class HarmonyType(str, Enum):
    """Human-readable relationship represented by one suggestion."""

    NEUTRAL = "neutral"
    ANALOGOUS = "analogous"
    COMPLEMENTARY = "complementary"
    TONE = "tone"


class LightnessStrategy(str, Enum):
    """Small set of validated lightness transformations in the rule table."""

    NEUTRAL_CONTRAST = "neutral-contrast"
    PRESERVE = "preserve"
    CONTRAST_TONE = "contrast-tone"


class MatchingStatus(str, Enum):
    """Outcome state that never masquerades as a confidence score."""

    READY = "ready"
    MISSING_COLOR = "missing-color"
    UNKNOWN_COLOR = "unknown-color"


@dataclass(frozen=True, slots=True)
class MatchingRule:
    """One validated, attributed row from ``assets/suggestions.csv``."""

    rule_id: str
    source_kind: SourceKind
    harmony: HarmonyType
    priority: int
    min_source_lightness: float
    max_source_lightness: float
    hue_offset_degrees: float
    lightness_strategy: LightnessStrategy
    chroma_scale: float
    reason_vi: str
    provenance: str

    def __post_init__(self) -> None:
        if not self.rule_id or any(
            character not in "abcdefghijklmnopqrstuvwxyz0123456789-"
            for character in self.rule_id
        ):
            raise MatchingRulesError(
                "rule_id must be a non-empty lowercase ASCII slug"
            )
        if not 0 <= self.priority <= 1000:
            raise MatchingRulesError("priority must be an integer within [0, 1000]")
        numeric_values = (
            self.min_source_lightness,
            self.max_source_lightness,
            self.hue_offset_degrees,
            self.chroma_scale,
        )
        if not all(math.isfinite(value) for value in numeric_values):
            raise MatchingRulesError("rule numeric values must be finite")
        if not (
            0.0
            <= self.min_source_lightness
            <= self.max_source_lightness
            <= 100.0
        ):
            raise MatchingRulesError(
                "source lightness bounds must satisfy 0 <= min <= max <= 100"
            )
        if not -360.0 < self.hue_offset_degrees < 360.0:
            raise MatchingRulesError("hue_offset_degrees must be within (-360, 360)")
        if not 0.0 <= self.chroma_scale <= 2.0:
            raise MatchingRulesError("chroma_scale must be within [0, 2]")
        if not self.reason_vi.strip():
            raise MatchingRulesError("reason_vi must not be empty")
        if not self.provenance.strip():
            raise MatchingRulesError("provenance must not be empty")
        _validate_rule_relationship(self)


@dataclass(frozen=True, slots=True)
class MatchingConfig:
    """Configurable matching heuristics awaiting T09 user evaluation."""

    neutral_chroma_threshold: float = 15.0
    neutral_contrast_boundary: float = 50.0
    tone_lightness_delta: float = 25.0
    minimum_target_lightness: float = 10.0
    maximum_target_lightness: float = 90.0
    cvd_minimum_delta_e: float = 20.0
    max_suggestions: int = 4

    def __post_init__(self) -> None:
        numeric_fields = (
            "neutral_chroma_threshold",
            "neutral_contrast_boundary",
            "tone_lightness_delta",
            "minimum_target_lightness",
            "maximum_target_lightness",
            "cvd_minimum_delta_e",
        )
        if not all(math.isfinite(getattr(self, name)) for name in numeric_fields):
            raise ValueError("matching thresholds must be finite")
        if self.neutral_chroma_threshold < 0.0:
            raise ValueError("neutral_chroma_threshold must be non-negative")
        if not 0.0 <= self.neutral_contrast_boundary <= 100.0:
            raise ValueError("neutral_contrast_boundary must be within [0, 100]")
        if self.tone_lightness_delta <= 0.0:
            raise ValueError("tone_lightness_delta must be positive")
        if not (
            0.0
            <= self.minimum_target_lightness
            < self.maximum_target_lightness
            <= 100.0
        ):
            raise ValueError(
                "target lightness bounds must satisfy 0 <= min < max <= 100"
            )
        if self.cvd_minimum_delta_e < 0.0:
            raise ValueError("cvd_minimum_delta_e must be non-negative")
        if not isinstance(self.max_suggestions, int) or isinstance(
            self.max_suggestions, bool
        ):
            raise ValueError("max_suggestions must be a positive integer")
        if self.max_suggestions <= 0:
            raise ValueError("max_suggestions must be a positive integer")


@dataclass(frozen=True, slots=True)
class CVDSeparationCheck:
    """Optional source-target separation diagnostic, not a safety guarantee."""

    profile: CVDProfile
    severity: float
    delta_e_original: float
    delta_e_cvd: float
    minimum_delta_e: float
    meets_minimum: bool

    def __post_init__(self) -> None:
        if not isinstance(self.profile, CVDProfile):
            raise TypeError("profile must be a CVDProfile selected by the user")
        validate_severity(self.severity)
        for field_name in (
            "delta_e_original",
            "delta_e_cvd",
            "minimum_delta_e",
        ):
            value = getattr(self, field_name)
            if not math.isfinite(value) or value < 0.0:
                raise ValueError(f"{field_name} must be finite and non-negative")


@dataclass(frozen=True, slots=True)
class MatchingSuggestion:
    """One deterministic guidance item derived from an original T04 cluster."""

    rule_id: str
    harmony: HarmonyType
    priority: int
    source_original_name: str
    source_original_lab: LabColor
    source_original_rgb: RGBColor
    target_name: str
    target_label_vi: str
    target_lab: LabColor
    target_lch: CIELCHColor
    target_rgb: RGBColor
    explanation_vi: str
    rule_provenance: str
    cvd_separation: CVDSeparationCheck | None = None


@dataclass(frozen=True, slots=True)
class MatchingResult:
    """Safe matching outcome with explicit source and no confidence field."""

    status: MatchingStatus
    source_original_name: str | None
    source_original_lab: LabColor | None
    source_original_rgb: RGBColor | None
    suggestions: tuple[MatchingSuggestion, ...]
    explanation_vi: str
    guidance_notice_vi: str = GUIDANCE_NOTICE_VI

    def __post_init__(self) -> None:
        if not self.explanation_vi.strip() or not self.guidance_notice_vi.strip():
            raise ValueError("matching explanations must not be empty")
        if self.status is MatchingStatus.READY:
            if (
                self.source_original_name is None
                or self.source_original_lab is None
                or self.source_original_rgb is None
                or not self.suggestions
            ):
                raise ValueError("ready matching results require source data and suggestions")
        elif self.suggestions:
            raise ValueError("non-ready matching results must not contain suggestions")


class RuleBasedMatcher:
    """Apply the committed guidance table to one original corrected cluster."""

    def __init__(
        self,
        config: MatchingConfig | None = None,
        *,
        rules_path: Path | str | None = None,
        simulator: MachadoSimulator | None = None,
    ) -> None:
        self.config = config or MatchingConfig()
        self.rules_path = Path(rules_path) if rules_path is not None else _DEFAULT_RULES_PATH
        self.rules = load_matching_rules(self.rules_path)
        self.simulator = simulator or MachadoSimulator()

    def suggest_from_original_cluster(
        self,
        cluster: ColorCluster | None,
        *,
        profile: CVDProfile | None = None,
        severity: float | None = None,
    ) -> MatchingResult:
        """Return guidance from T04's original corrected Lab/RGB values only.

        ``profile`` and ``severity`` are optional as a pair.  When supplied,
        each suggestion includes an informational CVD-separation diagnostic.
        The diagnostic is a heuristic and is never reported as confidence.
        """

        validated_severity = _validate_optional_cvd_context(profile, severity)
        if cluster is None:
            return MatchingResult(
                status=MatchingStatus.MISSING_COLOR,
                source_original_name=None,
                source_original_lab=None,
                source_original_rgb=None,
                suggestions=(),
                explanation_vi=MISSING_COLOR_EXPLANATION_VI,
            )
        if not isinstance(cluster, ColorCluster):
            raise TypeError(
                "cluster must be a T04 ColorCluster containing original corrected color"
            )

        source_name = cluster.original_name.strip().lower()
        source_lab = _validated_lab(cluster.lab)
        source_lch = cielab_to_cielch(source_lab)
        if source_name not in BASIC_COLOR_NAMES:
            return MatchingResult(
                status=MatchingStatus.UNKNOWN_COLOR,
                source_original_name=cluster.original_name,
                source_original_lab=source_lab,
                source_original_rgb=cluster.rgb,
                suggestions=(),
                explanation_vi=UNKNOWN_COLOR_EXPLANATION_VI,
            )

        source_kind = (
            SourceKind.NEUTRAL
            if source_lch[1] <= self.config.neutral_chroma_threshold
            else SourceKind.CHROMATIC
        )
        applicable = sorted(
            (
                rule
                for rule in self.rules
                if rule.source_kind is source_kind
                and rule.min_source_lightness
                <= source_lch[0]
                <= rule.max_source_lightness
            ),
            key=lambda rule: (-rule.priority, rule.rule_id),
        )
        suggestions = tuple(
            self._apply_rule(
                rule,
                cluster=cluster,
                source_name=source_name,
                source_lab=source_lab,
                source_lch=source_lch,
                profile=profile,
                severity=validated_severity,
            )
            for rule in applicable[: self.config.max_suggestions]
        )
        if not suggestions:
            return MatchingResult(
                status=MatchingStatus.UNKNOWN_COLOR,
                source_original_name=source_name,
                source_original_lab=source_lab,
                source_original_rgb=cluster.rgb,
                suggestions=(),
                explanation_vi=(
                    "Không có quy tắc phù hợp với màu gốc hiện tại; "
                    "không tạo gợi ý hoặc độ tin cậy giả."
                ),
            )

        return MatchingResult(
            status=MatchingStatus.READY,
            source_original_name=source_name,
            source_original_lab=source_lab,
            source_original_rgb=cluster.rgb,
            suggestions=suggestions,
            explanation_vi=(
                f"Đã tạo {len(suggestions)} gợi ý từ màu gốc đã hiệu chỉnh "
                f"{vietnamese_color_label(source_name)} ({source_name})."
            ),
        )

    def _apply_rule(
        self,
        rule: MatchingRule,
        *,
        cluster: ColorCluster,
        source_name: str,
        source_lab: LabColor,
        source_lch: CIELCHColor,
        profile: CVDProfile | None,
        severity: float | None,
    ) -> MatchingSuggestion:
        requested_lab = _target_lab_for_rule(rule, source_lch, self.config)
        target_rgb = cielab_to_rgb_color(requested_lab)
        # Recompute Lab after sRGB gamut clipping/8-bit quantization so all
        # reported target values describe the color that can actually display.
        target_lab = rgb_color_to_cielab(target_rgb)
        target_lch = cielab_to_cielch(target_lab)
        target_name_result = name_cielab_color(target_lab)
        cvd_separation = None
        if profile is not None and severity is not None:
            cvd_separation = self._check_cvd_separation(
                cluster.rgb,
                target_rgb,
                profile=profile,
                severity=severity,
            )
        return MatchingSuggestion(
            rule_id=rule.rule_id,
            harmony=rule.harmony,
            priority=rule.priority,
            source_original_name=source_name,
            source_original_lab=source_lab,
            source_original_rgb=cluster.rgb,
            target_name=target_name_result.name,
            target_label_vi=target_name_result.label_vi,
            target_lab=target_lab,
            target_lch=target_lch,
            target_rgb=target_rgb,
            explanation_vi=(
                f"{rule.reason_vi} Gợi ý hiển thị: "
                f"{target_name_result.label_vi} ({target_name_result.name})."
            ),
            rule_provenance=rule.provenance,
            cvd_separation=cvd_separation,
        )

    def _check_cvd_separation(
        self,
        source_rgb: RGBColor,
        target_rgb: RGBColor,
        *,
        profile: CVDProfile,
        severity: float,
    ) -> CVDSeparationCheck:
        source_lab = rgb_color_to_cielab(source_rgb)
        target_lab = rgb_color_to_cielab(target_rgb)
        simulated_source = self.simulator.simulate_color(
            source_rgb,
            profile=profile,
            severity=severity,
        )
        simulated_target = self.simulator.simulate_color(
            target_rgb,
            profile=profile,
            severity=severity,
        )
        delta_e_original = ciede2000(source_lab, target_lab)
        delta_e_cvd = ciede2000(
            rgb_color_to_cielab(simulated_source),
            rgb_color_to_cielab(simulated_target),
        )
        return CVDSeparationCheck(
            profile=profile,
            severity=severity,
            delta_e_original=delta_e_original,
            delta_e_cvd=delta_e_cvd,
            minimum_delta_e=self.config.cvd_minimum_delta_e,
            meets_minimum=delta_e_cvd >= self.config.cvd_minimum_delta_e,
        )


def load_matching_rules(path: Path | str = _DEFAULT_RULES_PATH) -> tuple[MatchingRule, ...]:
    """Load and strictly validate the project-authored matching rule table."""

    rules_path = Path(path)
    try:
        with rules_path.open("r", encoding="utf-8-sig", newline="") as handle:
            reader = csv.DictReader(handle)
            if tuple(reader.fieldnames or ()) != SUGGESTION_COLUMNS:
                raise MatchingRulesError(
                    "suggestions.csv headers must exactly equal: "
                    + ",".join(SUGGESTION_COLUMNS)
                )
            rules = tuple(
                _parse_rule_row(row, line_number=reader.line_num)
                for row in reader
            )
    except OSError as exc:
        raise MatchingRulesError(
            f"unable to read matching rules at {rules_path}"
        ) from exc
    if not rules:
        raise MatchingRulesError("suggestions.csv must contain at least one rule")
    rule_ids = [rule.rule_id for rule in rules]
    if len(rule_ids) != len(set(rule_ids)):
        raise MatchingRulesError("suggestions.csv rule_id values must be unique")
    _validate_rule_coverage(rules)
    return rules


def cielab_to_cielch(lab: LabColor) -> CIELCHColor:
    """Convert conventional CIELAB to ``(L*, C*, h°)`` with hue in [0, 360)."""

    lightness, a_star, b_star = _validated_lab(lab)
    chroma = math.hypot(a_star, b_star)
    hue = 0.0 if chroma <= 1e-12 else math.degrees(math.atan2(b_star, a_star)) % 360.0
    return (lightness, chroma, hue)


def cielch_to_cielab(lch: CIELCHColor) -> LabColor:
    """Convert conventional ``(L*, C*, h°)`` to CIELAB."""

    if len(lch) != 3:
        raise ValueError("lch must contain exactly three values")
    try:
        lightness, chroma, hue = (float(value) for value in lch)
    except (TypeError, ValueError) as exc:
        raise ValueError("lch must contain exactly three finite values") from exc
    if not all(math.isfinite(value) for value in (lightness, chroma, hue)):
        raise ValueError("lch must contain exactly three finite values")
    if not 0.0 <= lightness <= 100.0:
        raise ValueError("CIELCH L* must be within [0, 100]")
    if chroma < 0.0:
        raise ValueError("CIELCH C* must be non-negative")
    if not 0.0 <= hue < 360.0:
        raise ValueError("CIELCH hue must be within [0, 360)")
    hue_radians = math.radians(hue)
    return (
        lightness,
        chroma * math.cos(hue_radians),
        chroma * math.sin(hue_radians),
    )


def _target_lab_for_rule(
    rule: MatchingRule,
    source_lch: CIELCHColor,
    config: MatchingConfig,
) -> LabColor:
    source_lightness, source_chroma, source_hue = source_lch
    if rule.lightness_strategy is LightnessStrategy.NEUTRAL_CONTRAST:
        neutral_rgb: RGBColor = (
            (255, 255, 255)
            if source_lightness < config.neutral_contrast_boundary
            else (0, 0, 0)
        )
        return rgb_color_to_cielab(neutral_rgb)
    if rule.lightness_strategy is LightnessStrategy.PRESERVE:
        target_lightness = source_lightness
    else:
        target_lightness = (
            min(
                config.maximum_target_lightness,
                source_lightness + config.tone_lightness_delta,
            )
            if source_lightness < config.neutral_contrast_boundary
            else max(
                config.minimum_target_lightness,
                source_lightness - config.tone_lightness_delta,
            )
        )
    return cielch_to_cielab(
        (
            target_lightness,
            source_chroma * rule.chroma_scale,
            (source_hue + rule.hue_offset_degrees) % 360.0,
        )
    )


def _parse_rule_row(row: dict[str, str], *, line_number: int) -> MatchingRule:
    try:
        return MatchingRule(
            rule_id=row["rule_id"].strip(),
            source_kind=SourceKind(row["source_kind"].strip()),
            harmony=HarmonyType(row["harmony"].strip()),
            priority=_parse_integer(row["priority"], "priority"),
            min_source_lightness=_parse_float(
                row["min_source_lightness"], "min_source_lightness"
            ),
            max_source_lightness=_parse_float(
                row["max_source_lightness"], "max_source_lightness"
            ),
            hue_offset_degrees=_parse_float(
                row["hue_offset_degrees"], "hue_offset_degrees"
            ),
            lightness_strategy=LightnessStrategy(
                row["lightness_strategy"].strip()
            ),
            chroma_scale=_parse_float(row["chroma_scale"], "chroma_scale"),
            reason_vi=row["reason_vi"].strip(),
            provenance=row["provenance"].strip(),
        )
    except (KeyError, TypeError, ValueError) as exc:
        if isinstance(exc, MatchingRulesError):
            detail = str(exc)
        else:
            detail = str(exc) or exc.__class__.__name__
        raise MatchingRulesError(
            f"invalid suggestions.csv row at line {line_number}: {detail}"
        ) from exc


def _parse_float(raw: str, field_name: str) -> float:
    try:
        value = float(raw)
    except (TypeError, ValueError) as exc:
        raise MatchingRulesError(f"{field_name} must be numeric") from exc
    if not math.isfinite(value):
        raise MatchingRulesError(f"{field_name} must be finite")
    return value


def _parse_integer(raw: str, field_name: str) -> int:
    try:
        value = int(raw)
    except (TypeError, ValueError) as exc:
        raise MatchingRulesError(f"{field_name} must be an integer") from exc
    if str(value) != raw.strip():
        raise MatchingRulesError(f"{field_name} must be an integer")
    return value


def _validate_rule_relationship(rule: MatchingRule) -> None:
    if rule.harmony is HarmonyType.NEUTRAL:
        if (
            rule.lightness_strategy is not LightnessStrategy.NEUTRAL_CONTRAST
            or rule.hue_offset_degrees != 0.0
            or rule.chroma_scale != 0.0
        ):
            raise MatchingRulesError(
                "neutral rules require neutral-contrast, zero hue offset, and zero chroma"
            )
    elif rule.harmony is HarmonyType.ANALOGOUS:
        if (
            rule.source_kind is not SourceKind.CHROMATIC
            or rule.lightness_strategy is not LightnessStrategy.PRESERVE
            or not 0.0 < abs(rule.hue_offset_degrees) <= 60.0
        ):
            raise MatchingRulesError(
                "analogous rules require a chromatic source and 0 < |hue offset| <= 60"
            )
    elif rule.harmony is HarmonyType.COMPLEMENTARY:
        if (
            rule.source_kind is not SourceKind.CHROMATIC
            or rule.lightness_strategy is not LightnessStrategy.PRESERVE
            or not 150.0 <= abs(rule.hue_offset_degrees) <= 210.0
        ):
            raise MatchingRulesError(
                "complementary rules require a chromatic source and 150 <= |hue offset| <= 210"
            )
    elif (
        rule.source_kind is not SourceKind.CHROMATIC
        or rule.lightness_strategy is not LightnessStrategy.CONTRAST_TONE
        or rule.hue_offset_degrees != 0.0
    ):
        raise MatchingRulesError(
            "tone rules require a chromatic source, contrast-tone, and zero hue offset"
        )


def _validate_rule_coverage(rules: tuple[MatchingRule, ...]) -> None:
    coverage = {(rule.source_kind, rule.harmony) for rule in rules}
    required = {
        (SourceKind.NEUTRAL, HarmonyType.NEUTRAL),
        (SourceKind.CHROMATIC, HarmonyType.NEUTRAL),
        (SourceKind.CHROMATIC, HarmonyType.ANALOGOUS),
        (SourceKind.CHROMATIC, HarmonyType.COMPLEMENTARY),
        (SourceKind.CHROMATIC, HarmonyType.TONE),
    }
    missing = required - coverage
    if missing:
        labels = ", ".join(
            f"{source.value}/{harmony.value}"
            for source, harmony in sorted(
                missing,
                key=lambda item: (item[0].value, item[1].value),
            )
        )
        raise MatchingRulesError(f"suggestions.csv is missing required coverage: {labels}")


def _validate_optional_cvd_context(
    profile: CVDProfile | None,
    severity: float | None,
) -> float | None:
    if (profile is None) != (severity is None):
        raise ValueError("profile and severity must be provided together")
    if profile is None:
        return None
    if not isinstance(profile, CVDProfile):
        raise TypeError("profile must be a CVDProfile selected by the user")
    return validate_severity(severity)


def _validated_lab(lab: LabColor) -> LabColor:
    if len(lab) != 3:
        raise ValueError("lab must contain exactly three values")
    try:
        values = tuple(float(value) for value in lab)
    except (TypeError, ValueError) as exc:
        raise ValueError("lab must contain exactly three finite values") from exc
    if not all(math.isfinite(value) for value in values):
        raise ValueError("lab must contain exactly three finite values")
    if not 0.0 <= values[0] <= 100.0:
        raise ValueError("Lab L* must be within [0, 100]")
    return (values[0], values[1], values[2])
