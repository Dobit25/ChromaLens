from __future__ import annotations

from scripts.t09_color_science_eval import (
    _build_confusion_rows,
    _evaluate_lighting,
    _evaluate_multicolor,
    _evaluate_risk,
    _load_controlled_colors,
    _risk_order_results,
    _stability_by_color,
)


def test_synthetic_matrix_covers_11_families_and_three_lightings() -> None:
    rows = _evaluate_lighting(_load_controlled_colors())

    assert len(rows) == 33
    assert len({row["expected_name"] for row in rows}) == 11
    assert {row["lighting"] for row in rows} == {"daylight", "neutral_indoor", "warm_low"}
    assert all("predicted_name" in row and "corrected_rgb" in row for row in rows)


def test_confusion_table_retains_all_121_cells() -> None:
    table = _build_confusion_rows(_evaluate_lighting(_load_controlled_colors()))

    assert len(table) == 121
    assert sum(int(row["count"]) for row in table) == 33


def test_multicolor_is_reported_separately_and_mask_contained() -> None:
    result = _evaluate_multicolor()

    assert result["cluster_count"] == 2
    assert len(result["observed_names"]) == 2
    assert result["outside_mask_pixels"] == [0, 0]


def test_all_three_profiles_pass_frozen_risk_order_sanity() -> None:
    rows = _evaluate_risk()

    assert len(rows) == 6
    assert _risk_order_results(rows) == {"protan": True, "deutan": True, "tritan": True}
    assert all("delta_e_original" in row and "delta_e_cvd" in row and "risk_score" in row for row in rows)


def test_stability_metric_is_a_diagnostic_not_a_probability() -> None:
    stability = _stability_by_color(_evaluate_lighting(_load_controlled_colors()))

    assert len(stability) == 11
    assert all(isinstance(value, bool) for value in stability.values())