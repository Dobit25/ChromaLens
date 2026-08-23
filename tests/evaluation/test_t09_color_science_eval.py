from __future__ import annotations

from pathlib import Path

from chromalens.color_naming import BASIC_COLOR_NAMES
from scripts import t09_color_science_eval as evaluator


def test_frozen_contract_is_11_of_11_and_case_ids_are_exact() -> None:
    rows = evaluator.evaluate_contract(evaluator.load_controlled_colors())

    assert len(rows) == 11
    assert all(row["correct"] for row in rows)
    assert {row["case_id"] for row in rows} == {
        f"COL-CONTRACT-{color.upper()}" for color in BASIC_COLOR_NAMES
    }


def test_synthetic_lighting_logic_and_confusion_matrix_are_retained() -> None:
    rows = evaluator.evaluate_synthetic_lighting(evaluator.load_controlled_colors())
    confusion = evaluator.build_confusion_rows(rows)
    stability = evaluator.stability_by_color(rows)

    assert len(rows) == 33
    assert sum(bool(row["correct"]) for row in rows) == 27
    assert len(confusion) == 121
    assert sum(int(row["count"]) for row in confusion) == 33
    assert sum(stability.values()) / len(stability) == 6 / 11
    assert all(row["evidence_class"] == "SUPPLEMENTAL_SYNTHETIC_NOT_PHYSICAL" for row in rows)


def test_exact_33_physical_rows_remain_visible_not_run() -> None:
    contract = evaluator.evaluate_contract(evaluator.load_controlled_colors())
    matrix = evaluator.build_case_matrix(contract)
    physical = [row for row in matrix if row["category"] == "color_lighting"]
    frozen = evaluator.load_cases(evaluator.WORKSTREAM)

    assert len(matrix) == 44
    assert len(physical) == 33
    assert {row["case_id"] for row in physical} == {
        row["case_id"] for row in frozen if row["category"] == "color_lighting"
    }
    assert all(row["status"] == "NOT_RUN" for row in physical)
    assert all("synthetic" in row["reason"] for row in physical)


def test_owner_acceptance_does_not_relabel_physical_cases_as_measured() -> None:
    source = Path(evaluator.__file__).read_text(encoding="utf-8")

    assert '"result_status": "COMPLETE"' in source
    assert "OWNER_ACCEPTED_NOT_RUN_WITHOUT_PHYSICAL_ACCURACY_CLAIM" in source
    assert '"status": "ACCEPTED_LIMITATION"' in source


def test_multicolor_containment_and_all_cvd_profiles_pass() -> None:
    multicolor = evaluator.evaluate_multicolor()
    risk_rows = evaluator.evaluate_risk()

    assert multicolor["cluster_count"] == 2
    assert multicolor["observed_names"] == ["red", "blue"]
    assert multicolor["outside_mask_pixels"] == [0, 0]
    assert evaluator.risk_order_results(risk_rows) == {
        "protan": True,
        "deutan": True,
        "tritan": True,
    }
    assert all(
        {"delta_e_original", "delta_e_cvd", "risk_score"} <= set(row)
        for row in risk_rows
    )


def test_color_environment_is_collected_not_hard_coded() -> None:
    source = Path(evaluator.__file__).read_text(encoding="utf-8")

    assert "collect_environment(" in source
    assert "83DV" not in source
    assert "13th Gen Intel Core i5-13450HX" not in source
