from __future__ import annotations

from scripts import t09_benchmark_report as report


def metrics_named(name: str) -> list[dict[str, object]]:
    return [item for item in report.observation_metrics() if item["name"] == name]


def test_development_observations_preserve_frozen_latency_boundaries() -> None:
    metrics = report.observation_metrics()
    render = [item for item in metrics if item["name"] == "source_read_to_render_ms"]
    display = [item for item in metrics if item["name"] == "source_read_to_display_submit_ms"]
    sensor = [item for item in metrics if item["name"] == "sensor_to_photon_ms"]

    assert len(render) == 8
    assert len(display) == 8
    assert len(sensor) == 10
    assert all(item["status"] == "NOT_MEASURED" for item in sensor)
    assert all(item["threshold_result"] == "NOT_EVALUATED" for item in metrics_named("processed_fps"))
    assert all(item["dimensions"]["evidence_class"] == "development_host_observation" for item in render)


def test_report_covers_exact_12_frozen_cases_with_honest_partial_statuses() -> None:
    cases = report.build_cases()
    frozen = report.load_cases(report.WORKSTREAM)
    statuses = {item["case_id"]: item["status"] for item in cases}

    assert len(cases) == 12
    assert {item["case_id"] for item in cases} == {row["case_id"] for row in frozen}
    assert statuses["PERF-SENSOR-EXTERNAL"] == "NOT_RUN"
    assert statuses["RAI-ARTIFACT-INTEGRITY"] == "PARTIAL"
    assert statuses["RAI-LICENSE"] == "PARTIAL"
    assert statuses["RAI-USER-VALIDATION"] == "NOT_RUN"


def test_manifest_is_complete_but_does_not_require_ignored_bytes_in_tests() -> None:
    assert len(report.RAW_MANIFESTS) == 7
    assert {item[0] for item in report.RAW_MANIFESTS} == {
        "perf-webcam-gui-raw",
        "perf-webcam-headless-raw",
        "perf-video-gui-raw",
        "perf-video-headless-raw",
        "generated-video-input",
        "manual-roi-raw",
        "responsible-ai-audit-raw",
    }
    assert all(len(item[3]) == 64 and item[4] > 0 for item in report.RAW_MANIFESTS)


def test_manual_roi_privacy_bias_license_and_failures_remain_explicit() -> None:
    text = report.render_report()

    assert "3.016 s" in text
    assert "not automatically locate garments" in text
    assert "neither saved nor uploaded" in text
    assert "not demographic validation" in text
    assert "GAPS_RECORDED" in text
    assert "sensor_to_photon_ms" in text and "NOT_MEASURED" in text
    assert len(report.failure_cases()) >= 3
