from __future__ import annotations

from pathlib import Path

from scripts.post_mvp_result_validation import validate_result_file


ROOT = Path(__file__).resolve().parents[2]
RESULT = ROOT / "evaluation/results/curated/post_mvp/t14/result.json"


def test_t14_result_matches_frozen_schema_without_requiring_ignored_artifacts() -> None:
    summary = validate_result_file(RESULT)

    assert summary.case_count == 4
    assert summary.metric_count == 4
    assert (
        summary.verified_artifact_count
        + summary.unavailable_ignored_artifact_count
        == 5
    )
