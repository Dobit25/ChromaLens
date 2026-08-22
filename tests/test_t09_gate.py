"""Hardware-independent contract tests for the frozen T09 Gate 0."""

from __future__ import annotations

import csv
from dataclasses import fields
import inspect
import json
from pathlib import Path
import re

from chromalens.metrics import RuntimeMetricsSnapshot, RuntimeMetricsTracker


ROOT = Path(__file__).resolve().parents[1]
PROTOCOL_VERSION = "1.0.0"
BASIC_COLORS = {
    "black",
    "blue",
    "brown",
    "grey",
    "green",
    "orange",
    "pink",
    "purple",
    "red",
    "white",
    "yellow",
}
LIGHTING = {"daylight", "neutral_indoor", "warm_low"}
WORKSTREAMS = {
    "end_to_end",
    "segmentation",
    "color_science",
    "performance_responsible_ai",
}


def _json(relative_path: str) -> dict[str, object]:
    return json.loads((ROOT / relative_path).read_text(encoding="utf-8"))


def _cases() -> list[dict[str, str]]:
    with (ROOT / "evaluation/fixtures/test_cases.csv").open(
        newline="", encoding="utf-8"
    ) as handle:
        return list(csv.DictReader(handle))


def test_schema_and_metric_registry_are_versioned_and_exactly_aligned() -> None:
    schema = _json("evaluation/schema/t09-result.schema.json")
    registry = _json("evaluation/schema/metric_registry.json")

    assert schema["$schema"] == "https://json-schema.org/draft/2020-12/schema"
    assert schema["properties"]["protocol_version"]["const"] == PROTOCOL_VERSION
    assert schema["properties"]["schema_version"]["const"] == PROTOCOL_VERSION
    assert registry["protocol_version"] == PROTOCOL_VERSION
    assert registry["registry_version"] == PROTOCOL_VERSION

    registered = {metric["name"] for metric in registry["metrics"]}
    schema_names = set(schema["$defs"]["metric"]["properties"]["name"]["enum"])
    assert registered == schema_names
    assert len(registered) == len(registry["metrics"])

    def walk(value: object) -> None:
        if isinstance(value, dict):
            if "pattern" in value:
                re.compile(value["pattern"])
            if "$ref" in value and value["$ref"].startswith("#/$defs/"):
                assert value["$ref"].removeprefix("#/$defs/") in schema["$defs"]
            for nested in value.values():
                walk(nested)
        elif isinstance(value, list):
            for nested in value:
                walk(nested)

    walk(schema)


def test_latency_registry_locks_units_formulae_and_claim_boundaries() -> None:
    registry = _json("evaluation/schema/metric_registry.json")
    metrics = {metric["name"]: metric for metric in registry["metrics"]}

    render = metrics["source_read_to_render_ms"]
    display = metrics["source_read_to_display_submit_ms"]
    sensor = metrics["sensor_to_photon_ms"]

    assert render["unit"] == display["unit"] == sensor["unit"] == "ms"
    assert "render_complete_monotonic_ns" in render["formula"]
    assert "post_cv2_imshow_monotonic_ns" in display["formula"]
    assert "external synchronized" in sensor["formula"]
    assert {item["id"] for item in display["thresholds"]} == {
        "demo_floor_p50",
        "project_target_p50",
    }

    protocol = (ROOT / "evaluation/protocol.md").read_text(encoding="utf-8")
    normalized_protocol = " ".join(protocol.split())
    for exact_name in (
        "source_read_to_render_ms",
        "source_read_to_display_submit_ms",
        "sensor_to_photon_ms",
        "capture-return-to-render-complete latency",
        "NOT_MEASURED",
    ):
        assert exact_name in protocol
    assert "camera exposure-to-display latency" in normalized_protocol
    assert "screen physically emits light" in normalized_protocol


def test_runtime_instrumentation_exposes_only_frozen_software_latency_names() -> None:
    observe_parameters = inspect.signature(RuntimeMetricsTracker.observe).parameters
    snapshot_fields = {field.name for field in fields(RuntimeMetricsSnapshot)}

    assert "source_read_to_render_ms" in observe_parameters
    assert "source_read_to_display_submit_ms" in observe_parameters
    assert "frame_processing_to_render_ms" in observe_parameters
    assert "capture_to_render_ms" not in observe_parameters
    assert "source_read_to_render_p50_ms" in snapshot_fields
    assert "source_read_to_display_submit_p50_ms" in snapshot_fields
    assert "capture_to_render_p50_ms" not in snapshot_fields
    assert "sensor_to_photon_ms" not in snapshot_fields

    renderer_source = (ROOT / "src/chromalens/renderer.py").read_text(
        encoding="utf-8"
    )
    assert "pipeline_latency_ms" not in renderer_source
    assert "pre-render age" in renderer_source


def test_frozen_case_registry_has_required_matrix_and_known_owners() -> None:
    rows = _cases()
    case_ids = [row["case_id"] for row in rows]
    assert rows
    assert len(case_ids) == len(set(case_ids))
    assert {row["workstream"] for row in rows} == WORKSTREAMS
    assert all(row["owner"] == row["workstream"] for row in rows)

    physical = [row for row in rows if row["category"] == "color_lighting"]
    physical_matrix = {
        (row["fixture_id"].removeprefix("physical-basic11-"), row["lighting"])
        for row in physical
    }
    assert len(physical) == 33
    assert physical_matrix == {
        (color, lighting) for color in BASIC_COLORS for lighting in LIGHTING
    }

    contract = [row for row in rows if row["category"] == "color_contract"]
    assert {row["fixture_id"].removeprefix("basic11-") for row in contract} == BASIC_COLORS
    assert all(row["gate_asset_status"] == "AVAILABLE_TRACKED" for row in contract)

    segmentation = [row for row in rows if row["workstream"] == "segmentation"]
    assert len(segmentation) >= 20
    assert sum("segmentation_iou" in row["required_metrics"] for row in segmentation) >= 3

    for profile in ("protan", "deutan", "tritan"):
        profile_rows = [
            row
            for row in rows
            if row["category"] == "cvd_risk" and row["cvd_profile"] == profile
        ]
        assert len(profile_rows) == 2
        assert any(row["case_id"].endswith("CONFUSING") for row in profile_rows)
        assert any(row["case_id"].endswith("CONTROL") for row in profile_rows)


def test_every_case_metric_is_registered_and_gate_status_is_explicit() -> None:
    registry = _json("evaluation/schema/metric_registry.json")
    metric_names = {metric["name"] for metric in registry["metrics"]}
    allowed_statuses = {
        "AVAILABLE_TRACKED",
        "GENERATED_AT_RUN",
        "TO_BE_ACQUIRED",
        "INLINE_SYNTHETIC",
    }

    for row in _cases():
        assert row["gate_asset_status"] in allowed_statuses
        assert row["expected_observation"]
        assert row["provenance_class"]
        assert row["consent_requirement"]
        assert row["license_requirement"]
        assert set(row["required_metrics"].split(";")) <= metric_names


def test_artifact_and_ownership_policy_separates_curated_text_from_raw_media() -> None:
    ignore = (ROOT / ".gitignore").read_text(encoding="utf-8")
    results_policy = (ROOT / "evaluation/results/README.md").read_text(
        encoding="utf-8"
    )
    ownership = (ROOT / "evaluation/OWNERSHIP.md").read_text(encoding="utf-8")

    assert "artifacts/" in ignore
    assert "evaluation/results/**" in ignore
    for extension in ("csv", "json", "md"):
        assert f"!evaluation/results/curated/**/*.{extension}" in ignore
    assert "SHA-256" in results_policy
    assert "provenance" in results_policy
    assert "consent" in results_policy
    assert "git add -f" in results_policy
    for workstream in WORKSTREAMS:
        assert f"evaluation/results/curated/{workstream}/**" in ownership


def test_protocol_freeze_does_not_pretend_missing_assets_or_demo_hardware_exist() -> None:
    protocol = (ROOT / "evaluation/protocol.md").read_text(encoding="utf-8")
    normalized_protocol = " ".join(protocol.split())

    assert "Status: `FROZEN`" in protocol
    assert "development machine only" in protocol
    assert "not declared competition demo hardware" in protocol
    assert "TO_BE_ACQUIRED" in protocol
    assert "does not claim that T09 evaluation is complete" in normalized_protocol
    assert "15 seconds of warm-up" in protocol
    assert "120 continuous seconds" in protocol
