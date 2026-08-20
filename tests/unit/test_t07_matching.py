from __future__ import annotations

from pathlib import Path

import numpy as np
import pytest

from chromalens.color_naming import rgb_color_to_cielab
from chromalens.config import CVDProfile
from chromalens.contracts import ColorCluster
from chromalens.matching import (
    GUIDANCE_NOTICE_VI,
    HarmonyType,
    MatchingConfig,
    MatchingRulesError,
    MatchingStatus,
    RuleBasedMatcher,
    SourceKind,
    cielab_to_cielch,
    cielch_to_cielab,
    load_matching_rules,
)


def _cluster(
    rgb: tuple[int, int, int],
    name: str,
) -> ColorCluster:
    return ColorCluster(
        lab=rgb_color_to_cielab(rgb),
        rgb=rgb,
        ratio=1.0,
        submask=np.ones((3, 4), dtype=np.bool_),
        original_name=name,
        name_scores={name: 1.0},
        color_margin=0.75,
    )


def _circular_hue_difference(first: float, second: float) -> float:
    return abs((first - second + 180.0) % 360.0 - 180.0)


def test_cielab_cielch_round_trip_and_neutral_hue_are_deterministic() -> None:
    source = (62.0, -31.0, 44.0)
    lch = cielab_to_cielch(source)

    assert lch[0] == pytest.approx(62.0)
    assert lch[1] == pytest.approx(np.hypot(-31.0, 44.0))
    assert 0.0 <= lch[2] < 360.0
    assert cielch_to_cielab(lch) == pytest.approx(source, abs=1e-12)
    assert cielab_to_cielch((50.0, 0.0, 0.0)) == (50.0, 0.0, 0.0)


@pytest.mark.parametrize(
    "invalid",
    [
        (-1.0, 2.0, 30.0),
        (50.0, -2.0, 30.0),
        (50.0, 2.0, 360.0),
        (50.0, 2.0, float("nan")),
    ],
)
def test_cielch_rejects_invalid_values(invalid: tuple[float, float, float]) -> None:
    with pytest.raises(ValueError):
        cielch_to_cielab(invalid)


def test_committed_rule_table_has_required_schema_provenance_and_coverage() -> None:
    rules = load_matching_rules()

    assert len(rules) == 5
    assert len({rule.rule_id for rule in rules}) == len(rules)
    assert all(rule.reason_vi and rule.provenance for rule in rules)
    assert {(rule.source_kind, rule.harmony) for rule in rules} == {
        (SourceKind.NEUTRAL, HarmonyType.NEUTRAL),
        (SourceKind.CHROMATIC, HarmonyType.NEUTRAL),
        (SourceKind.CHROMATIC, HarmonyType.ANALOGOUS),
        (SourceKind.CHROMATIC, HarmonyType.COMPLEMENTARY),
        (SourceKind.CHROMATIC, HarmonyType.TONE),
    }


def test_rule_loader_rejects_wrong_headers(tmp_path: Path) -> None:
    invalid = tmp_path / "suggestions.csv"
    invalid.write_text("rule_id,source_kind\na,neutral\n", encoding="utf-8")

    with pytest.raises(MatchingRulesError, match="headers must exactly equal"):
        load_matching_rules(invalid)


def test_rule_loader_rejects_duplicate_ids(tmp_path: Path) -> None:
    source = Path("assets/suggestions.csv").read_text(encoding="utf-8")
    lines = source.splitlines()
    invalid = tmp_path / "suggestions.csv"
    invalid.write_text("\n".join([*lines, lines[1]]) + "\n", encoding="utf-8")

    with pytest.raises(MatchingRulesError, match="must be unique"):
        load_matching_rules(invalid)


def test_rule_loader_rejects_invalid_relationship(tmp_path: Path) -> None:
    source = Path("assets/suggestions.csv").read_text(encoding="utf-8")
    invalid = tmp_path / "suggestions.csv"
    invalid.write_text(
        source.replace(
            "chromatic-analogous,chromatic,analogous,300,0,100,30,",
            "chromatic-analogous,chromatic,analogous,300,0,100,0,",
        ),
        encoding="utf-8",
    )

    with pytest.raises(MatchingRulesError, match="analogous rules require"):
        load_matching_rules(invalid)


def test_neutral_example_returns_only_contrast_guidance() -> None:
    cluster = _cluster((128, 128, 128), "grey")
    result = RuleBasedMatcher().suggest_from_original_cluster(cluster)

    assert result.status is MatchingStatus.READY
    assert result.source_original_lab == cluster.lab
    assert result.source_original_rgb == cluster.rgb
    assert result.guidance_notice_vi == GUIDANCE_NOTICE_VI
    assert "không phải quy tắc thời trang khách quan" in result.guidance_notice_vi
    assert len(result.suggestions) == 1
    suggestion = result.suggestions[0]
    assert suggestion.harmony is HarmonyType.NEUTRAL
    assert suggestion.target_rgb == (0, 0, 0)
    assert suggestion.source_original_lab == cluster.lab
    assert suggestion.source_original_rgb == cluster.rgb
    assert not hasattr(suggestion, "confidence")


def test_chromatic_example_returns_four_rules_in_stable_priority_order() -> None:
    cluster = _cluster((220, 40, 40), "red")
    matcher = RuleBasedMatcher()

    first = matcher.suggest_from_original_cluster(cluster)
    second = matcher.suggest_from_original_cluster(cluster)

    assert first == second
    assert [suggestion.harmony for suggestion in first.suggestions] == [
        HarmonyType.NEUTRAL,
        HarmonyType.ANALOGOUS,
        HarmonyType.COMPLEMENTARY,
        HarmonyType.TONE,
    ]
    source_lch = cielab_to_cielch(cluster.lab)
    by_harmony = {item.harmony: item for item in first.suggestions}
    analogous_hue_shift = _circular_hue_difference(
        by_harmony[HarmonyType.ANALOGOUS].target_lch[2],
        source_lch[2],
    )
    complementary_hue_shift = _circular_hue_difference(
        by_harmony[HarmonyType.COMPLEMENTARY].target_lch[2],
        source_lch[2],
    )
    tone = by_harmony[HarmonyType.TONE]

    complementary_rule = next(
        rule for rule in matcher.rules if rule.harmony is HarmonyType.COMPLEMENTARY
    )
    assert complementary_rule.hue_offset_degrees == 180.0

    # Display targets are measured after sRGB gamut clipping. The analogous
    # target remains nearby and the complementary target remains opposite,
    # while the validated rule above preserves the exact requested rotation.
    assert analogous_hue_shift == pytest.approx(30.0, abs=20.0)
    assert complementary_hue_shift >= 150.0
    assert _circular_hue_difference(tone.target_lch[2], source_lch[2]) < 15.0
    assert abs(tone.target_lch[0] - source_lch[0]) > 15.0
    assert all(item.source_original_lab == cluster.lab for item in first.suggestions)
    assert all(item.source_original_rgb == cluster.rgb for item in first.suggestions)


def test_optional_cvd_separation_is_explicit_and_not_confidence() -> None:
    cluster = _cluster((220, 40, 40), "red")
    result = RuleBasedMatcher().suggest_from_original_cluster(
        cluster,
        profile=CVDProfile.DEUTAN,
        severity=0.8,
    )

    assert all(item.cvd_separation is not None for item in result.suggestions)
    for suggestion in result.suggestions:
        check = suggestion.cvd_separation
        assert check is not None
        assert check.profile is CVDProfile.DEUTAN
        assert check.severity == pytest.approx(0.8)
        assert check.delta_e_original >= 0.0
        assert check.delta_e_cvd >= 0.0
        assert check.meets_minimum == (
            check.delta_e_cvd >= check.minimum_delta_e
        )
        assert not hasattr(check, "confidence")


@pytest.mark.parametrize(
    ("profile", "severity"),
    [(CVDProfile.PROTAN, None), (None, 1.0)],
)
def test_optional_cvd_context_must_be_complete(
    profile: CVDProfile | None,
    severity: float | None,
) -> None:
    with pytest.raises(ValueError, match="provided together"):
        RuleBasedMatcher().suggest_from_original_cluster(
            _cluster((220, 40, 40), "red"),
            profile=profile,
            severity=severity,
        )


def test_missing_and_unknown_colors_return_safe_empty_explanations() -> None:
    matcher = RuleBasedMatcher()

    missing = matcher.suggest_from_original_cluster(None)
    unknown = matcher.suggest_from_original_cluster(
        _cluster((12, 34, 56), "ultraviolet")
    )

    assert missing.status is MatchingStatus.MISSING_COLOR
    assert missing.suggestions == ()
    assert "Chưa có màu" in missing.explanation_vi
    assert unknown.status is MatchingStatus.UNKNOWN_COLOR
    assert unknown.suggestions == ()
    assert unknown.source_original_rgb == (12, 34, 56)
    assert "không tạo gợi ý hoặc độ tin cậy giả" in unknown.explanation_vi
    assert not hasattr(missing, "confidence")
    assert not hasattr(unknown, "confidence")


def test_matcher_rejects_non_t04_color_contract() -> None:
    with pytest.raises(TypeError, match="T04 ColorCluster"):
        RuleBasedMatcher().suggest_from_original_cluster(  # type: ignore[arg-type]
            (220, 40, 40)
        )


@pytest.mark.parametrize(
    "config",
    [
        MatchingConfig(max_suggestions=1),
        MatchingConfig(neutral_chroma_threshold=0.0),
    ],
)
def test_matching_config_valid_examples(config: MatchingConfig) -> None:
    assert isinstance(config, MatchingConfig)


def test_matching_config_rejects_invalid_bounds() -> None:
    with pytest.raises(ValueError, match="target lightness bounds"):
        MatchingConfig(minimum_target_lightness=90.0, maximum_target_lightness=20.0)
