"""Hardware-independent tests for the T09 Responsible-AI audit artifact."""

from __future__ import annotations

from datetime import datetime, timezone
import importlib.util
import json
from pathlib import Path
import re
import sys

import pytest


ROOT = Path(__file__).resolve().parents[2]
SPEC = importlib.util.spec_from_file_location("t09_rai_audit", ROOT / "scripts" / "t09_responsible_ai_audit.py")
assert SPEC and SPEC.loader
audit = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = audit
SPEC.loader.exec_module(audit)

START = datetime(2026, 8, 23, 1, 0, tzinfo=timezone.utc)
END = datetime(2026, 8, 23, 1, 1, tzinfo=timezone.utc)
COMMIT = "c" * 40
ENVIRONMENT = {
    "host_role": "development", "declared_demo_hardware": False, "manufacturer": "Mock", "model": "Host",
    "operating_system": "Windows", "cpu": "Mock CPU", "physical_core_count": 4, "logical_processor_count": 8,
    "ram_gib": 16.0, "gpu": "Mock GPU", "npu": "not detected", "camera_or_source": "manual",
    "python_version": "3.10.20", "package_versions": {"chromalens-ai": "0.1", "numpy": "1", "opencv-contrib-python": "4", "mediapipe": "0", "daltonlens": "0"},
    "lock_sha256": "a" * 64, "backend_name": "manual", "backend_device": "human", "source_kind": "manual_baseline",
    "source_resolution": {"width": 1, "height": 1}, "render_resolution": {"width": 1, "height": 1}, "display_mode": "not_applicable", "warmup_seconds": 0, "measurement_seconds": 0,
}
SCHEMA = json.loads((ROOT / "evaluation/schema/t09-result.schema.json").read_text(encoding="utf-8"))
REGISTRY = json.loads((ROOT / "evaluation/schema/metric_registry.json").read_text(encoding="utf-8"))


def _schema_type_matches(value: object, type_name: str) -> bool:
    return {
        "object": isinstance(value, dict), "array": isinstance(value, list), "string": isinstance(value, str),
        "number": isinstance(value, (int, float)) and not isinstance(value, bool),
        "integer": isinstance(value, int) and not isinstance(value, bool), "boolean": isinstance(value, bool),
        "null": value is None,
    }[type_name]


def _schema_matches(value: object, schema: dict[str, object]) -> bool:
    try:
        _validate_schema(value, schema)
    except AssertionError:
        return False
    return True


def _validate_schema(value: object, schema: dict[str, object]) -> None:
    if "$ref" in schema:
        reference = str(schema["$ref"])
        assert reference.startswith("#/$defs/")
        _validate_schema(value, SCHEMA["$defs"][reference.removeprefix("#/$defs/")])
        return
    if "const" in schema:
        assert value == schema["const"]
    if "enum" in schema:
        assert value in schema["enum"]
    if "type" in schema:
        type_names = schema["type"] if isinstance(schema["type"], list) else [schema["type"]]
        assert any(_schema_type_matches(value, str(type_name)) for type_name in type_names)
    if isinstance(value, str):
        if "minLength" in schema: assert len(value) >= schema["minLength"]
        if "pattern" in schema: assert re.search(str(schema["pattern"]), value)
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        if "minimum" in schema: assert value >= schema["minimum"]
        if "exclusiveMinimum" in schema: assert value > schema["exclusiveMinimum"]
        if "maximum" in schema: assert value <= schema["maximum"]
    if isinstance(value, dict):
        for key in schema.get("required", []): assert key in value
        if schema.get("additionalProperties") is False:
            assert set(value) <= set(schema.get("properties", {}))
        for key, nested in schema.get("properties", {}).items():
            if key in value: _validate_schema(value[key], nested)
        additional = schema.get("additionalProperties")
        if isinstance(additional, dict):
            for key, item in value.items():
                if key not in schema.get("properties", {}): _validate_schema(item, additional)
    if isinstance(value, list):
        if "minItems" in schema: assert len(value) >= schema["minItems"]
        if schema.get("uniqueItems"): assert len({json.dumps(item, sort_keys=True) for item in value}) == len(value)
        if "items" in schema:
            for item in value: _validate_schema(item, schema["items"])
    for conditional in schema.get("allOf", []):
        branch = conditional.get("then") if _schema_matches(value, conditional["if"]) else conditional.get("else")
        if branch: _validate_schema(value, branch)


def _manual() -> dict[str, object]:
    return {"result_status": "COMPLETE", "git_commit": audit.EXPECTED_MANUAL_COMMIT, "workstream": audit.WORKSTREAM,
            "schema_version": "1.0.0", "environment": ENVIRONMENT,
            "cases": [{"case_id": "BASELINE-MANUAL-ROI", "fixture_id": "manual-roi-public-fixtures", "status": "COMPLETE"}]}


def _payload(**overrides: object) -> dict[str, object]:
    args = {"manual": _manual(), "evidence": [{"path": "artifact.json", "sha256": "b" * 64, "byte_size": 1}],
            "unknown_media": [], "actual_media": sorted(audit.FIXTURE_SHA256),
            "fixture_records": audit.validate_fixture_provenance(sorted(audit.FIXTURE_SHA256)),
            "inventory": audit.license_inventory(package_versions=ENVIRONMENT["package_versions"], fixture_records=audit.validate_fixture_provenance(sorted(audit.FIXTURE_SHA256))), "commit": COMMIT, "started_at": START, "ended_at": END}
    args.update(overrides)
    return audit.build_payload(**args)


def test_seven_frozen_cases_and_sensor_boundary_are_exact() -> None:
    payload = _payload()
    assert [(case["case_id"], case["fixture_id"]) for case in payload["cases"]] == [
        (item.case_id, item.fixture_id) for item in audit.CASES
    ]
    sensor = [metric for metric in payload["metrics"] if metric["name"] == "sensor_to_photon_ms"]
    assert [(metric["aggregation"], metric["status"], metric["value"], metric["threshold_result"]) for metric in sensor] == [
        ("p50", "NOT_MEASURED", None, "NOT_EVALUATED"), ("p95", "NOT_MEASURED", None, "NOT_EVALUATED")
    ]


@pytest.mark.parametrize("field,value", [("result_status", "PARTIAL"), ("git_commit", "a" * 40)])
def test_manual_roi_contract_rejects_wrong_status_or_sha(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, field: str, value: object) -> None:
    path = tmp_path / audit.MANUAL_NAME
    payload = _manual(); payload[field] = value
    path.write_text(json.dumps(payload), encoding="utf-8")
    monkeypatch.setattr(audit, "EXPECTED_MANUAL_SHA256", audit.sha256_file(path))
    with pytest.raises(audit.AuditError):
        audit.validate_manual_artifact(path, expected_dir=tmp_path)


def test_manual_roi_contract_rejects_wrong_case_or_path(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    path = tmp_path / audit.MANUAL_NAME
    payload = _manual(); payload["cases"][0]["case_id"] = "WRONG"
    path.write_text(json.dumps(payload), encoding="utf-8")
    monkeypatch.setattr(audit, "EXPECTED_MANUAL_SHA256", audit.sha256_file(path))
    with pytest.raises(audit.AuditError): audit.validate_manual_artifact(path, expected_dir=tmp_path)
    with pytest.raises(audit.AuditError): audit.validate_manual_artifact(path, expected_dir=ROOT)


def test_manual_roi_timing_tamper_is_rejected_by_locked_sha(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    path = tmp_path / audit.MANUAL_NAME
    path.write_text(json.dumps(_manual()), encoding="utf-8")
    monkeypatch.setattr(audit, "EXPECTED_MANUAL_SHA256", audit.sha256_file(path))
    value = json.loads(path.read_text(encoding="utf-8")); value["created_at_utc"] = "2026-08-23T00:00:00Z"
    path.write_text(json.dumps(value), encoding="utf-8")
    with pytest.raises(audit.AuditError, match="SHA-256"):
        audit.validate_manual_artifact(path, expected_dir=tmp_path)


def test_manifest_fails_closed_for_missing_or_mismatched_bytes(tmp_path: Path) -> None:
    evidence = tmp_path / "evidence.json"; evidence.write_bytes(b"good")
    with pytest.raises(audit.AuditError, match="missing"):
        audit.validate_evidence_manifest([evidence], {})
    with pytest.raises(audit.AuditError, match="mismatch"):
        audit.validate_evidence_manifest([evidence], {evidence.resolve().as_posix().replace("/", "\\"): "0" * 64})


def test_duplicate_or_smoke_performance_artifact_is_rejected(tmp_path: Path) -> None:
    def write(name: str, case: str, warmup: int = 15) -> None:
        (tmp_path / name).write_text(json.dumps({"result_status": "COMPLETE", "environment": {"warmup_seconds": warmup, "measurement_seconds": 120}, "cases": [{"case_id": case}]}), encoding="utf-8")
    for index, case in enumerate(audit.PERFORMANCE_CASES): write(f"t09-performance-{index}.json", case)
    write("t09-performance-duplicate.json", audit.PERFORMANCE_CASES[0])
    with pytest.raises(audit.AuditError, match="expected exactly 4"):
        audit.load_performance_artifacts(tmp_path)
    (tmp_path / "t09-performance-duplicate.json").unlink()
    write("t09-performance-0.json", audit.PERFORMANCE_CASES[0], warmup=0)
    with pytest.raises(audit.AuditError, match="smoke"):
        audit.load_performance_artifacts(tmp_path)


def test_privacy_allowlist_counts_unknown_and_exempts_documented_public_fixture() -> None:
    media, unknown = audit.tracked_media(["tests/samples/t02/astronaut.png", "unknown/private.jpg", "src/code.py"])
    assert media == ["tests/samples/t02/astronaut.png", "unknown/private.jpg"]
    assert unknown == ["unknown/private.jpg"]
    payload = _payload(unknown_media=unknown, actual_media=sorted(audit.FIXTURE_SHA256) + unknown)
    privacy = next(metric for metric in payload["metrics"] if metric["case_ids"] == ["RAI-PRIVACY"])
    assert privacy["value"] == 1 and privacy["threshold_result"] == "FAIL"


def test_license_gaps_limitations_and_user_validation_remain_honest() -> None:
    payload = _payload(); notes = payload["notes"]
    assert "NOT_MEASURED" in notes
    assert len(payload["limitations"]) >= 3
    assert payload["responsible_ai"]["user_validation_status"] == "NOT_MEASURED"
    assert payload["responsible_ai"]["medical_diagnosis_claim"] is False


def test_payload_validates_against_frozen_schema_and_metric_registry() -> None:
    payload = _payload()
    _validate_schema(payload, SCHEMA)
    datetime.fromisoformat(payload["created_at_utc"].replace("Z", "+00:00"))
    registered = {item["name"]: item for item in REGISTRY["metrics"]}
    for metric in payload["metrics"]:
        definition = registered[metric["name"]]
        assert metric["unit"] == definition["unit"]
        assert metric["aggregation"] in definition["allowed_aggregations"]
        assert metric["threshold_id"] in {item["id"] for item in definition["thresholds"]}


def test_project_license_requires_apache_content_not_merely_an_evidence_file(tmp_path: Path) -> None:
    (tmp_path / "LICENSE").write_text("This is not a license declaration.", encoding="utf-8")
    project = next(item for item in audit.license_inventory(package_versions={}, root=tmp_path) if item["component_id"] == "chromalens-project")
    assert project["status"] == "GAP"


def test_runtime_package_with_missing_license_metadata_is_a_gap(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(audit, "installed_package_license", lambda _distribution: None)
    package = next(item for item in audit.license_inventory(package_versions={"numpy": "1.2.3"}) if item["component_id"] == "runtime-package-numpy")
    assert package["declared_version"] == "1.2.3"
    assert package["status"] == "GAP"


def test_five_validated_fixtures_are_license_inventory_components() -> None:
    fixtures = audit.validate_fixture_provenance(sorted(audit.FIXTURE_SHA256))
    inventory = audit.license_inventory(package_versions=ENVIRONMENT["package_versions"], fixture_records=fixtures)
    components = [item for item in inventory if item["category"] == "public_fixture"]
    assert len(components) == 5
    assert {item["fixture_sha256"] for item in components} == set(audit.FIXTURE_SHA256.values())
    assert all(item["status"] == "VERIFIED" and item["source_record"] and item["rights_statement"] for item in components)


def test_license_gap_is_derived_from_inventory_and_records_compliance_status() -> None:
    inventory = audit.license_inventory(package_versions=ENVIRONMENT["package_versions"], fixture_records=audit.validate_fixture_provenance(sorted(audit.FIXTURE_SHA256)))
    inventory[0] = {**inventory[0], "status": "GAP", "gap_reason": "test gap"}
    findings = json.loads(_payload(inventory=inventory)["notes"].removeprefix("responsible_ai_audit_findings="))
    assert findings["license_gaps"] == [item["component_id"] for item in inventory if item["status"] == "GAP"]
    assert findings["compliance_status"] == "GAPS_RECORDED"


def test_untracked_audit_script_or_test_blocks_official_audit(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(audit, "git_tracked_paths", lambda _paths: {"scripts/t09_responsible_ai_audit.py"})
    with pytest.raises(audit.AuditError, match="source and validation test"):
        audit.require_required_audit_files_tracked()


def test_untracked_provenance_readme_is_rejected() -> None:
    with pytest.raises(audit.AuditError, match="provenance README"):
        audit.validate_fixture_provenance(sorted(audit.FIXTURE_SHA256), tracked_files=set())


def test_wrong_python_git_and_timestamp_order_fail_closed(monkeypatch: pytest.MonkeyPatch) -> None:
    with pytest.raises(audit.AuditError): audit.validate_python_version("3.11.0")
    monkeypatch.setattr(audit.subprocess, "run", lambda *args, **kwargs: type("P", (), {"stdout": "BAD", "returncode": 0})())
    with pytest.raises(audit.AuditError): audit.git_commit()
    with pytest.raises(audit.AuditError): _payload(started_at=END, ended_at=START)


@pytest.mark.parametrize("result_id", ["../escape", "..\\escape", "t09-bad-20260823t010100z", "C:\\escape"])
def test_output_confinement_no_overwrite_and_atomic_cleanup(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, result_id: str) -> None:
    monkeypatch.setattr(audit, "ARTIFACT_DIR", tmp_path / "allowed")
    payload = _payload(); payload["result_id"] = result_id
    with pytest.raises(audit.AuditError): audit.write_atomic(payload, audit.ARTIFACT_DIR)
    assert not list(tmp_path.rglob("*.json")) and not list(tmp_path.rglob("*.tmp"))
    payload["result_id"] = "t09-responsible-ai-audit-token-20260823t010100z"
    output = audit.write_atomic(payload, audit.ARTIFACT_DIR)
    with pytest.raises(audit.AuditError): audit.write_atomic(payload, audit.ARTIFACT_DIR)
    output.unlink()
    monkeypatch.setattr(audit.json, "dump", lambda *_args, **_kwargs: (_ for _ in ()).throw(TypeError("bad json")))
    with pytest.raises(audit.AuditError): audit.write_atomic(payload, audit.ARTIFACT_DIR)
    assert not list(tmp_path.rglob("*.tmp"))


def test_payload_is_schema_shaped_and_media_free() -> None:
    payload = _payload()
    required = {"protocol_version", "schema_version", "metric_registry_version", "result_id", "workstream", "result_status", "git_commit", "created_at_utc", "operator", "environment", "cases", "configuration", "metrics", "artifacts", "commands", "failure_cases", "limitations", "responsible_ai"}
    assert required <= set(payload)
    assert payload["protocol_version"] == payload["schema_version"] == "1.0.0"
    assert payload["artifacts"] == []
    assert "base64" not in repr(payload).lower() and "private consent" not in repr(payload).lower()
