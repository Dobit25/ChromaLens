"""Hardware-independent validation of the frozen T12-T17 Gate 0 contract."""

from __future__ import annotations

import csv
import json
from pathlib import Path
import re

from scripts import post_mvp_result_validation as validator


ROOT = Path(__file__).resolve().parents[2]
VERSION = "2.0.0"
BASIC_FAMILIES = {
    "black", "blue", "brown", "grey", "green", "orange", "pink",
    "purple", "red", "white", "yellow",
}
EXTENDED_LABELS = {
    "black", "light_blue", "blue", "navy", "teal", "beige", "brown",
    "dark_brown", "light_grey", "grey", "charcoal", "mint", "green",
    "dark_green", "olive", "peach", "orange", "light_pink", "pink",
    "lavender", "purple", "dark_purple", "coral", "red", "dark_red",
    "white", "cream", "light_yellow", "yellow",
}


def _json(path: str) -> dict[str, object]:
    return json.loads((ROOT / path).read_text(encoding="utf-8"))


def _cases() -> list[dict[str, str]]:
    with (ROOT / "evaluation/fixtures/post-mvp-cases.csv").open(
        encoding="utf-8", newline=""
    ) as handle:
        return list(csv.DictReader(handle))


def test_protocol_schema_registry_and_ownership_are_frozen_at_v2() -> None:
    protocol = (ROOT / "evaluation/protocol-v2.md").read_text(encoding="utf-8")
    ownership = (ROOT / "evaluation/OWNERSHIP-v2.md").read_text(encoding="utf-8")
    schema = _json("evaluation/schema/post-mvp-result.schema.json")
    registry = _json("evaluation/schema/post-mvp-metric-registry.json")

    assert "Status: `FROZEN`" in protocol
    assert "Protocol version: `2.0.0`" in protocol
    assert "Protocol version: `2.0.0`" in ownership
    assert schema["properties"]["protocol_version"]["const"] == VERSION
    assert schema["properties"]["schema_version"]["const"] == VERSION
    assert registry["protocol_version"] == VERSION
    assert registry["registry_version"] == VERSION
    assert "evaluation/protocol.md" in protocol
    assert "frozen T09 `evaluation/protocol.md` version" in protocol


def test_metric_registry_exactly_matches_schema_and_fixture_requirements() -> None:
    schema = _json("evaluation/schema/post-mvp-result.schema.json")
    registry = _json("evaluation/schema/post-mvp-metric-registry.json")
    registered = [item["name"] for item in registry["metrics"]]
    schema_names = schema["$defs"]["metric"]["properties"]["name"]["enum"]

    assert len(registered) == len(set(registered))
    assert set(registered) == set(schema_names)
    for row in _cases():
        assert set(row["required_metrics"].split(";")) <= set(registered)

    for metric in registry["metrics"]:
        assert metric["unit"]
        assert metric["formula"]
        assert metric["allowed_aggregations"]
        assert metric["thresholds"]


def test_fixture_registry_locks_all_176_unique_cases() -> None:
    rows = _cases()
    case_ids = [row["case_id"] for row in rows]
    assert len(rows) == 176
    assert len(case_ids) == len(set(case_ids))
    assert all(re.fullmatch(r"PM-[A-Z0-9-]+", case_id) for case_id in case_ids)

    contracts = [row for row in rows if row["category"] == "color_digital_contract"]
    labels = {row["fixture_id"].removeprefix("extended-") for row in contracts}
    assert labels == EXTENDED_LABELS
    assert len(BASIC_FAMILIES) == 11

    physical = [row for row in rows if row["category"] == "color_physical_lighting"]
    assert len(physical) == 90
    assert {row["lighting"] for row in physical} == {"neutral", "warm", "low"}
    assert len({row["fixture_id"] for row in physical}) == 30
    assert all(row["gate_asset_status"] == "TO_BE_ACQUIRED" for row in physical)

    standalone = [row for row in rows if row["category"] == "standalone_garment"]
    assert len(standalone) == 20
    assert {row["garment_type"] for row in standalone} == {
        "top", "trousers", "skirt", "dress", "coat",
    }
    assert {row["background"] for row in standalone} == {"simple", "complex"}


def test_fullscreen_performance_severity_and_release_cases_are_exact() -> None:
    rows = _cases()
    fullscreen = [row for row in rows if row["category"] == "fullscreen"]
    performance = [row for row in rows if row["category"] == "performance_acceptance"]
    severity = [row for row in rows if row["category"] == "severity_matrix"]
    gradients = [row for row in rows if row["category"] == "spatial_gradient"]
    release = [row for row in rows if row["category"] == "release_gate"]

    assert len(fullscreen) == 4
    assert {row["resolution"] for row in fullscreen} == {"1366x768", "1920x1080"}
    assert {row["display_mode"] for row in fullscreen} == {"product", "diagnostic"}
    assert len(performance) == 4
    assert all(row["case_id"].endswith("300") for row in performance)
    assert len(severity) == 15
    assert {row["cvd_profile"] for row in severity} == {"protan", "deutan", "tritan"}
    assert {row["severity"] for row in severity} == {"0.00", "0.25", "0.50", "0.75", "1.00"}
    assert len(gradients) == 3
    assert len(release) == 7


def test_latency_and_growth_semantics_are_unambiguous() -> None:
    protocol = (ROOT / "evaluation/protocol-v2.md").read_text(encoding="utf-8")
    normalized_protocol = " ".join(protocol.split())
    registry = _json("evaluation/schema/post-mvp-metric-registry.json")
    metrics = {item["name"]: item for item in registry["metrics"]}

    assert "immediately after `VideoCapture.read()` returns" in protocol
    assert "immediately after `cv2.imshow()` returns" in normalized_protocol
    assert "sensor_to_photon_ms" in protocol and "NOT_MEASURED" in protocol
    assert registry["measurement_window_seconds"] == 300
    assert registry["growth_windows"] == {"count": 6, "seconds_each": 50}
    assert metrics["processed_fps"]["thresholds"] == [
        {"id": "internal_target", "comparator": ">=", "value": 20.0}
    ]
    assert metrics["source_read_to_render_ms"]["thresholds"][0]["value"] == 120.0
    assert metrics["source_read_to_display_submit_ms"]["thresholds"][0]["value"] == 120.0


def test_artifact_policy_and_file_ownership_prevent_parallel_conflicts() -> None:
    ignore = (ROOT / ".gitignore").read_text(encoding="utf-8")
    policy = (ROOT / "evaluation/results/README.md").read_text(encoding="utf-8")
    ownership = (ROOT / "evaluation/OWNERSHIP-v2.md").read_text(encoding="utf-8")
    workflow = (ROOT / ".github/workflows/ci.yml").read_text(encoding="utf-8")

    assert "artifacts/" in ignore
    assert "evaluation/results/curated/post_mvp/" in policy
    for word in ("provenance", "consent", "license", "SHA-256", "git add -f"):
        assert word in policy
    for task in ("T12", "T13", "T14", "T15", "T16", "T17"):
        assert f"| {task} |" in ownership
    for shared in ("app.py", "pipeline.py", "config.py", "contracts.py"):
        assert shared in ownership
    assert "post_mvp/(gate0|t12|t13|t14|t15|t16|t17)" in workflow
    assert "artifacts/(t09|post_mvp)" in workflow


def test_gate0_result_is_portable_when_ignored_raw_artifact_is_absent() -> None:
    summary = validator.validate_result_file(
        ROOT / "evaluation/results/curated/post_mvp/gate0/result.json"
    )
    assert summary.case_count == 1
    assert summary.metric_count == 9
    assert (
        summary.verified_artifact_count
        + summary.unavailable_ignored_artifact_count
        == 1
    )


def test_clean_checkout_validation_does_not_depend_on_ignored_raw_bytes(tmp_path: Path) -> None:
    payload = _json("evaluation/results/curated/post_mvp/gate0/result.json")
    payload["artifacts"][0]["path"] = "artifacts/post_mvp/gate0/not-present-in-clean-checkout.json"
    payload["artifacts"][0]["availability"] = "UNAVAILABLE"
    candidate = tmp_path / "result.json"
    candidate.write_text(json.dumps(payload), encoding="utf-8")

    summary = validator.validate_result_file(candidate)
    assert summary.verified_artifact_count == 0
    assert summary.unavailable_ignored_artifact_count == 1
