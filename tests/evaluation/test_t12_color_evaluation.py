"""T12 evaluator tests generate fresh evidence without external assets."""

from __future__ import annotations

import csv
import json
from pathlib import Path

from scripts import t12_color_evaluation
from scripts.t09_result_validation import _validate_schema

ROOT = Path(__file__).resolve().parents[2]


def test_evaluator_generates_schema_valid_complete_registry_coverage(
    tmp_path: Path,
    monkeypatch,
) -> None:
    monkeypatch.setattr(t12_color_evaluation, "ROOT", tmp_path)
    result_path = t12_color_evaluation.generate(
        tmp_path / "results",
        git_commit="a" * 40,
    )
    payload = json.loads(result_path.read_text(encoding="utf-8"))
    schema = json.loads(
        (ROOT / "evaluation/schema/post-mvp-result-v2.1.schema.json").read_text(
            encoding="utf-8"
        )
    )
    _validate_schema(payload, schema, schema, "$", strict_formats=True)

    assert len(payload["cases"]) == 203
    assert sum(case["status"] == "COMPLETE" for case in payload["cases"]) == 53
    assert sum(case["status"] == "NOT_RUN" for case in payload["cases"]) == 150
    assert payload["result_status"] == "PARTIAL"
    assert all(
        artifact["sha256"] and artifact["bytes"] > 0
        for artifact in payload["artifacts"]
    )

    with (tmp_path / "results/observations.csv").open(
        encoding="utf-8", newline=""
    ) as handle:
        observations = list(csv.DictReader(handle))
    assert len(observations) == 203
    assert sum(row["status"] == "NOT_RUN" for row in observations) == 150
