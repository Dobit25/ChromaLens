"""Cross-validate the additive T12 protocol-2.1 contract."""

from __future__ import annotations

import csv
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def _json(relative: str) -> dict[str, object]:
    return json.loads((ROOT / relative).read_text(encoding="utf-8"))


def _csv(relative: str) -> list[dict[str, str]]:
    with (ROOT / relative).open(encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def test_v21_versions_and_case_matrix_are_frozen_consistently() -> None:
    schema = _json("evaluation/schema/post-mvp-result-v2.1.schema.json")
    metrics = _json("evaluation/schema/post-mvp-metric-registry-v2.1.json")
    cases = _csv("evaluation/fixtures/post-mvp-cases-v2.1.csv")
    t12 = [row for row in cases if row["task_id"] == "T12"]

    assert schema["properties"]["protocol_version"]["const"] == "2.1.0"
    assert metrics["protocol_version"] == metrics["registry_version"] == "2.1.0"
    assert len(cases) == len({row["case_id"] for row in cases}) == 257
    assert len(t12) == 203
    assert sum(row["category"] == "color_digital_contract" for row in t12) == 50
    assert sum(row["category"] == "color_uncertainty_contract" for row in t12) == 3
    assert sum(row["category"] == "color_physical_lighting" for row in t12) == 150


def test_every_palette_label_has_one_digital_and_three_physical_cases() -> None:
    palette = _csv("assets/color_names/extended_palette.csv")
    cases = _csv("evaluation/fixtures/post-mvp-cases-v2.1.csv")
    t12 = [row for row in cases if row["task_id"] == "T12"]

    for row in palette:
        key = row["level2_key"]
        assert sum(item["fixture_id"] == f"extended-{key}" for item in t12) == 1
        physical = [
            item
            for item in t12
            if item["category"] == "color_physical_lighting"
            and item["fixture_id"].endswith(f"-{key}")
        ]
        assert len(physical) == 3
        assert {item["lighting"] for item in physical} == {"neutral", "warm", "low"}
        assert all(item["gate_asset_status"] == "TO_BE_ACQUIRED" for item in physical)


def test_v20_contract_remains_historical_and_unchanged_in_scope() -> None:
    old_cases = _csv("evaluation/fixtures/post-mvp-cases.csv")
    old_schema = _json("evaluation/schema/post-mvp-result.schema.json")

    assert len(old_cases) == 176
    assert old_schema["properties"]["protocol_version"]["const"] == "2.0.0"
    assert sum(row["task_id"] == "T12" for row in old_cases) == 122
