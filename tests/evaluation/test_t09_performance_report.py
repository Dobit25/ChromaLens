"""Hardware-independent tests for the T09 performance evidence consolidator."""

from __future__ import annotations

from importlib.util import module_from_spec, spec_from_file_location
import json
from pathlib import Path
import sys

import pytest


ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "scripts/t09_benchmark_report.py"
SPEC = spec_from_file_location("t09_benchmark_report", SCRIPT)
assert SPEC is not None and SPEC.loader is not None
reporter = module_from_spec(SPEC)
sys.modules[SPEC.name] = reporter
SPEC.loader.exec_module(reporter)


def test_happy_path_orders_cases_renders_report_and_has_stable_manifest(
    tmp_path: Path,
) -> None:
    artifact_dir, video_path, paths = _fixture_set(tmp_path, reverse_creation=True)

    first = reporter.load_and_validate(artifact_dir, video_path)
    second = reporter.load_and_validate(artifact_dir, video_path)
    content = reporter.render_report(first)
    output = tmp_path / "curated/report.md"
    reporter.write_report_atomic(first, output)

    assert [item.case_id for item in first.artifacts] == list(reporter.CASE_ORDER)
    assert output.read_text(encoding="utf-8") == content
    assert [item.sha256 for item in first.artifacts] == [item.sha256 for item in second.artifacts]
    assert first.video_sha256 == second.video_sha256 == reporter.sha256_file(video_path)
    assert "Responsible-AI evidence remains `PENDING`" in content
    assert "No demo-floor or project-target PASS claim" in content
    assert "NOT_MEASURED / NOT_MEASURED" in content
    assert content.index("PERF-WEBCAM-GUI-120") < content.index("PERF-VIDEO-HEADLESS-120")
    assert all(path.is_file() for path in paths)


def test_missing_case_fails_closed(tmp_path: Path) -> None:
    artifact_dir, video_path, paths = _fixture_set(tmp_path)
    paths[-1].unlink()

    with pytest.raises(reporter.EvidenceValidationError, match="expected exactly"):
        reporter.load_and_validate(artifact_dir, video_path)


def test_duplicate_case_fails_closed(tmp_path: Path) -> None:
    artifact_dir, video_path, paths = _fixture_set(tmp_path)
    duplicate = _artifact("PERF-WEBCAM-GUI-120")
    _write(paths[-1], duplicate)

    with pytest.raises(reporter.EvidenceValidationError, match="duplicate"):
        reporter.load_and_validate(artifact_dir, video_path)


@pytest.mark.parametrize("result_status", ["PARTIAL", "INVALID"])
def test_non_complete_result_fails_closed(tmp_path: Path, result_status: str) -> None:
    artifact_dir, video_path, paths = _fixture_set(tmp_path)
    payload = _read(paths[0])
    payload["result_status"] = result_status
    _write(paths[0], payload)

    with pytest.raises(reporter.EvidenceValidationError, match="result_status"):
        reporter.load_and_validate(artifact_dir, video_path)


@pytest.mark.parametrize(
    ("mutation", "message"),
    [
        (lambda payload: payload["cases"][0].update(fixture_id="wrong"), "fixture_id"),
        (lambda payload: payload["environment"]["source_resolution"].update(width=1), "source_resolution"),
        (lambda payload: payload["environment"].update(display_mode="headless"), "display_mode"),
        (lambda payload: payload["environment"].update(warmup_seconds=14.0), "warmup_seconds"),
        (lambda payload: payload["environment"].update(measurement_seconds=119.0), "measurement_seconds"),
    ],
)
def test_wrong_fixture_resolution_mode_or_duration_fails_closed(
    tmp_path: Path,
    mutation: object,
    message: str,
) -> None:
    artifact_dir, video_path, paths = _fixture_set(tmp_path)
    payload = _read(paths[0])
    mutation(payload)
    _write(paths[0], payload)

    with pytest.raises(reporter.EvidenceValidationError, match=message):
        reporter.load_and_validate(artifact_dir, video_path)


def test_mixed_git_sha_and_missing_metric_fail_closed(tmp_path: Path) -> None:
    artifact_dir, video_path, paths = _fixture_set(tmp_path)
    mixed = _read(paths[1])
    mixed["git_commit"] = "b" * 40
    _write(paths[1], mixed)
    with pytest.raises(reporter.EvidenceValidationError, match="mixed Git SHA"):
        reporter.load_and_validate(artifact_dir, video_path)

    _write(paths[1], _artifact("PERF-WEBCAM-HEADLESS-120"))
    missing = _read(paths[2])
    missing["metrics"] = [
        metric for metric in missing["metrics"]
        if (metric["name"], metric["aggregation"])
        != ("rss_mib", "peak")
    ]
    _write(paths[2], missing)
    with pytest.raises(reporter.EvidenceValidationError, match="missing required metric"):
        reporter.load_and_validate(artifact_dir, video_path)


def test_not_measured_semantics_are_preserved_and_invalid_claims_fail(
    tmp_path: Path,
) -> None:
    artifact_dir, video_path, paths = _fixture_set(tmp_path)
    evidence = reporter.load_and_validate(artifact_dir, video_path)
    headless = next(item for item in evidence.artifacts if item.case_id.endswith("HEADLESS-120"))
    assert headless.metrics[("source_read_to_display_submit_ms", "p50")]["status"] == "NOT_MEASURED"
    assert headless.metrics[("sensor_to_photon_ms", "p95")]["value"] is None

    payload = _read(paths[1])
    display = next(
        metric for metric in payload["metrics"]
        if (metric["name"], metric["aggregation"])
        == ("source_read_to_display_submit_ms", "p50")
    )
    display.update(status="MEASURED", value=12.0)
    _write(paths[1], payload)
    with pytest.raises(reporter.EvidenceValidationError, match="headless display-submit"):
        reporter.load_and_validate(artifact_dir, video_path)


def test_validation_failure_does_not_replace_existing_report(tmp_path: Path) -> None:
    artifact_dir, video_path, paths = _fixture_set(tmp_path)
    output = tmp_path / "curated/report.md"
    output.parent.mkdir()
    output.write_text("existing report\n", encoding="utf-8")
    payload = _read(paths[0])
    payload["result_status"] = "PARTIAL"
    _write(paths[0], payload)

    with pytest.raises(reporter.EvidenceValidationError):
        evidence = reporter.load_and_validate(artifact_dir, video_path)
        reporter.write_report_atomic(evidence, output)
    assert output.read_text(encoding="utf-8") == "existing report\n"


@pytest.mark.parametrize(
    ("metric_key", "message"),
    [
        (("source_read_to_render_slope_ms_per_minute", "whole_session"), "missing required metric"),
        (("dropped_capture_frame_count", "count"), "missing required metric"),
    ],
)
def test_missing_slope_or_webcam_drop_count_fails_closed(
    tmp_path: Path, metric_key: tuple[str, str], message: str
) -> None:
    artifact_dir, video_path, paths = _fixture_set(tmp_path)
    payload = _read(paths[0])
    payload["metrics"] = [
        item for item in payload["metrics"]
        if (item["name"], item["aggregation"]) != metric_key
    ]
    _write(paths[0], payload)

    with pytest.raises(reporter.EvidenceValidationError, match=message):
        reporter.load_and_validate(artifact_dir, video_path)


def test_video_does_not_require_dropped_capture_count(tmp_path: Path) -> None:
    artifact_dir, video_path, paths = _fixture_set(tmp_path)
    video_payload = _read(paths[2])
    assert all(item["name"] != "dropped_capture_frame_count" for item in video_payload["metrics"])
    evidence = reporter.load_and_validate(artifact_dir, video_path)
    video_artifact = next(item for item in evidence.artifacts if item.case_id == "PERF-VIDEO-GUI-120")
    assert "dropped_capture_frame_count" not in {name for name, _ in video_artifact.metrics}
    assert "NOT_APPLICABLE" in reporter.render_report(evidence)


@pytest.mark.parametrize(
    ("mutation", "message"),
    [
        (lambda payload: _metric_for(payload, "processed_fps", "single").update(unit="ms"), "invalid unit"),
        (lambda payload: _metric_for(payload, "processed_fps", "single").update(case_ids=["OTHER"]), "case_ids"),
        (lambda payload: _metric_for(payload, "processed_fps", "single").update(value=float("nan")), "finite numeric"),
        (lambda payload: _metric_for(payload, "processed_fps", "single").update(value=True), "finite numeric"),
        (lambda payload: _metric_for(payload, "rss_mib", "peak").update(value=float("inf")), "finite numeric"),
        (lambda payload: _metric_for(payload, "degraded_frame_rate", "single").update(value=1.1), "within"),
    ],
)
def test_metric_unit_case_ids_numeric_and_range_contract(
    tmp_path: Path, mutation: object, message: str
) -> None:
    artifact_dir, video_path, paths = _fixture_set(tmp_path)
    payload = _read(paths[0])
    mutation(payload)
    _write(paths[0], payload)

    with pytest.raises(reporter.EvidenceValidationError, match=message):
        reporter.load_and_validate(artifact_dir, video_path)


def test_retained_counts_and_growth_threshold_result_fail_closed(tmp_path: Path) -> None:
    artifact_dir, video_path, paths = _fixture_set(tmp_path)
    payload = _read(paths[0])
    _metric_for(payload, "retained_source_read_to_render_sample_count", "count")["value"] = 1499
    _write(paths[0], payload)
    with pytest.raises(reporter.EvidenceValidationError, match="retained render"):
        reporter.load_and_validate(artifact_dir, video_path)

    _write(paths[0], _artifact("PERF-WEBCAM-GUI-120"))
    payload = _read(paths[0])
    _metric_for(payload, "rss_continuous_growth_flag", "single")["threshold_result"] = "PASS"
    _write(paths[0], payload)
    with pytest.raises(reporter.EvidenceValidationError, match="threshold_result must be FAIL"):
        reporter.load_and_validate(artifact_dir, video_path)


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("manufacturer", "other"),
        ("package_versions", {"numpy": "other"}),
        ("lock_sha256", "d" * 64),
        ("backend_name", "other/cpu"),
    ],
)
def test_mixed_hardware_provenance_fails_closed(
    tmp_path: Path, field: str, value: object
) -> None:
    artifact_dir, video_path, paths = _fixture_set(tmp_path)
    payload = _read(paths[1])
    payload["environment"][field] = value
    _write(paths[1], payload)

    with pytest.raises(reporter.EvidenceValidationError, match=f"environment.{field}"):
        reporter.load_and_validate(artifact_dir, video_path)


@pytest.mark.parametrize(
    ("mutation", "message"),
    [
        (lambda payload: payload.update(workstream="other"), "workstream"),
        (lambda payload: payload["configuration"].update(cvd_profile="protan"), "cvd_profile"),
        (lambda payload: payload["configuration"].update(severity=1.0), "severity"),
        (lambda payload: payload["environment"].update(source_kind="video"), "source_kind"),
    ],
)
def test_workstream_configuration_and_source_kind_fail_closed(
    tmp_path: Path, mutation: object, message: str
) -> None:
    artifact_dir, video_path, paths = _fixture_set(tmp_path)
    payload = _read(paths[0])
    mutation(payload)
    _write(paths[0], payload)

    with pytest.raises(reporter.EvidenceValidationError, match=message):
        reporter.load_and_validate(artifact_dir, video_path)


def test_development_demo_threshold_cannot_be_pass_or_fail(tmp_path: Path) -> None:
    artifact_dir, video_path, paths = _fixture_set(tmp_path)
    payload = _read(paths[0])
    fps = _metric_for(payload, "processed_fps", "single")
    fps.update(threshold_id="demo_floor", threshold_result="PASS")
    _write(paths[0], payload)

    with pytest.raises(reporter.EvidenceValidationError, match="demo threshold"):
        reporter.load_and_validate(artifact_dir, video_path)


def test_cli_output_path_is_limited_to_trinh_namespace() -> None:
    reporter._validate_cli_output(
        Path("evaluation/results/curated/performance_responsible_ai/report.md")
    )
    for forbidden in (
        Path("evaluation/results/curated/summary.md"),
        Path("evaluation/results/curated/segmentation/report.md"),
    ):
        with pytest.raises(reporter.EvidenceValidationError, match="--output"):
            reporter._validate_cli_output(forbidden)


def _fixture_set(
    tmp_path: Path, *, reverse_creation: bool = False
) -> tuple[Path, Path, list[Path]]:
    artifact_dir = tmp_path / "artifacts"
    artifact_dir.mkdir()
    video_path = artifact_dir / "inputs/generated-360x240.avi"
    video_path.parent.mkdir()
    video_path.write_bytes(b"synthetic-video-bytes")
    case_ids = list(reporter.CASE_ORDER)
    if reverse_creation:
        case_ids.reverse()
    paths: list[Path] = []
    for index, case_id in enumerate(case_ids):
        path = artifact_dir / f"t09-performance-{index}.json"
        _write(path, _artifact(case_id))
        paths.append(path)
    return artifact_dir, video_path, paths


def _metric_for(
    payload: dict[str, object], name: str, aggregation: str
) -> dict[str, object]:
    return next(
        item for item in payload["metrics"]
        if (item["name"], item["aggregation"]) == (name, aggregation)
    )


def _artifact(case_id: str) -> dict[str, object]:
    expectation = reporter.CASE_EXPECTATIONS[case_id]
    display_not_measured = expectation.display_mode == "headless"
    metrics = [
        _metric("processed_fps", "single", 12.5),
        _metric("source_read_to_render_ms", "p50", 10.0),
        _metric("source_read_to_render_ms", "p95", 20.0),
        _metric("source_read_to_render_slope_ms_per_minute", "whole_session", 1.0),
        _metric("source_read_to_display_submit_ms", "p50", None if display_not_measured else 12.0, status="NOT_MEASURED" if display_not_measured else "MEASURED"),
        _metric("source_read_to_display_submit_ms", "p95", None if display_not_measured else 24.0, status="NOT_MEASURED" if display_not_measured else "MEASURED"),
        _metric("sensor_to_photon_ms", "p50", None, status="NOT_MEASURED"),
        _metric("sensor_to_photon_ms", "p95", None, status="NOT_MEASURED"),
        _metric("frame_processing_to_render_ms", "p50", 7.0),
        _metric("frame_processing_to_render_ms", "p95", 15.0),
        _metric("processed_frame_count", "count", 1500),
        _metric("degraded_frame_rate", "single", 0.4),
        _metric("rss_mib", "start", 100.0),
        _metric("rss_mib", "end", 110.0),
        _metric("rss_mib", "peak", 115.0),
        _metric("rss_delta_mib", "whole_session", 10.0),
        _metric("rss_slope_mib_per_minute", "whole_session", 5.0),
        _metric("latency_continuous_growth_flag", "single", False, threshold_result="PASS"),
        _metric("rss_continuous_growth_flag", "single", True, threshold_result="FAIL"),
        _metric("retained_source_read_to_render_sample_count", "count", 1500),
        _metric("retained_source_read_to_display_submit_sample_count", "count", 0 if display_not_measured else 1500),
    ]
    if expectation.source_kind == "webcam":
        metrics.append(_metric("dropped_capture_frame_count", "count", 10))
    for metric in metrics:
        metric["unit"] = reporter.METRIC_UNITS[metric["name"]]
        metric["case_ids"] = [case_id]
    width, height = expectation.resolution
    return {
        "protocol_version": "1.0.0",
        "schema_version": "1.0.0",
        "metric_registry_version": "1.0.0",
        "workstream": "performance_responsible_ai",
        "result_status": "COMPLETE",
        "git_commit": "a" * 40,
        "created_at_utc": "2026-08-22T00:00:00Z",
        "cases": [{
            "case_id": case_id,
            "status": "COMPLETE",
            "fixture_id": expectation.fixture_id,
        }],
        "environment": {
            "manufacturer": "test", "model": "model", "cpu": "cpu",
            "physical_core_count": 1, "logical_processor_count": 2,
            "ram_gib": 1.0, "gpu": "gpu", "npu": "not detected",
            "operating_system": "test-os", "python_version": "3.10.20",
            "backend_name": "test/cpu", "backend_device": "cpu",
            "lock_sha256": "c" * 64,
            "package_versions": {"numpy": "1", "opencv": "1"},
            "camera_or_source": "source", "source_kind": expectation.source_kind,
            "display_mode": expectation.display_mode,
            "source_resolution": {"width": width, "height": height},
            "render_resolution": {"width": width, "height": height},
            "warmup_seconds": 15.0, "measurement_seconds": 120.0,
            "host_role": "development", "declared_demo_hardware": False,
        },
        "configuration": {"cvd_profile": "deutan", "severity": 0.8},
        "metrics": metrics,
    }


def _metric(
    name: str,
    aggregation: str,
    value: object,
    *,
    status: str = "MEASURED",
    threshold_result: str = "NOT_EVALUATED",
) -> dict[str, object]:
    return {
        "name": name,
        "aggregation": aggregation,
        "status": status,
        "value": value,
        "threshold_result": threshold_result,
    }


def _read(path: Path) -> dict[str, object]:
    return json.loads(path.read_text(encoding="utf-8"))


def _write(path: Path, payload: dict[str, object]) -> None:
    path.write_text(json.dumps(payload), encoding="utf-8")
