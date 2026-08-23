from __future__ import annotations

from pathlib import Path

from scripts import t09_benchmark_report as report


def raw_evidence() -> tuple[report.RawEvidence, ...]:
    return tuple(
        report.RawEvidence(case_id, Path(f"{case_id}.json"), {})
        for case_id in report.PERFORMANCE_CASE_IDS
    )


def test_report_covers_exact_twelve_cases_with_optional_boundaries() -> None:
    cases = report.build_cases(raw_evidence())
    frozen = report.load_cases(report.WORKSTREAM)
    statuses = {item["case_id"]: item["status"] for item in cases}

    assert len(cases) == 12
    assert {item["case_id"] for item in cases} == {
        row["case_id"] for row in frozen
    }
    assert all(statuses[case_id] == "COMPLETE" for case_id in report.PERFORMANCE_CASE_IDS)
    assert statuses["PERF-SENSOR-EXTERNAL"] == "NOT_RUN"
    assert statuses["BASELINE-MANUAL-ROI"] == "NOT_RUN"
    assert statuses["RAI-ARTIFACT-INTEGRITY"] == "COMPLETE"
    assert statuses["RAI-LICENSE"] == "COMPLETE"
    assert statuses["RAI-USER-VALIDATION"] == "NOT_RUN"


def test_unrecoverable_manual_timing_and_sensor_latency_are_not_fabricated() -> None:
    metrics = report.responsible_ai_metrics()
    manual = next(
        item
        for item in metrics
        if item["name"] == "manual_baseline_completion_seconds"
    )
    sensor = [item for item in metrics if item["name"] == "sensor_to_photon_ms"]

    assert manual["status"] == "NOT_MEASURED" and manual["value"] is None
    assert "not reconstructed" in manual["reason"]
    assert len(sensor) == 2
    assert all(item["status"] == "NOT_MEASURED" for item in sensor)
    assert all("external" in item["method"].lower() for item in sensor)


def test_active_raw_manifest_has_only_fresh_reproducible_artifacts() -> None:
    assert set(report.RAW_ARTIFACT_IDS) == set(report.PERFORMANCE_CASE_IDS)
    assert set(report.RAW_ARTIFACT_IDS.values()) == {
        "perf-webcam-gui-raw",
        "perf-webcam-headless-raw",
        "perf-video-gui-raw",
        "perf-video-headless-raw",
    }
    assert "manual-roi-raw" not in report.RAW_ARTIFACT_IDS.values()
    assert "responsible-ai-audit-raw" not in report.RAW_ARTIFACT_IDS.values()


def test_license_inventory_records_active_and_deferred_components() -> None:
    inventory = report.license_inventory()
    components = {row[0]: row for row in inventory}

    assert components["ChromaLens project"][2].startswith("Apache-2.0")
    assert "mediapipe" in components
    assert "daltonlens" in components
    assert "opencv-contrib-python" in components
    assert components["SCHP-ATR"][1] == "DEFERRED"
    assert "T10" in components["SCHP-ATR"][2]
