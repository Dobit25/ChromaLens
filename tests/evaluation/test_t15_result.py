"""Strict schema, registry, fixture, and checksum checks for T15 evidence."""

from pathlib import Path

from scripts.post_mvp_result_validation import validate_result_file


ROOT = Path(__file__).resolve().parents[2]
RESULT = ROOT / "evaluation/results/curated/post_mvp/t15/result.json"


def test_t15_partial_result_matches_frozen_contract() -> None:
    summary = validate_result_file(RESULT, require_ignored_artifacts=False)

    assert summary.case_count == 1
    assert summary.metric_count >= 20
