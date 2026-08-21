"""Hardware-independent contracts for Trinh's T09 performance runner."""

from __future__ import annotations

from dataclasses import replace
from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path
import sys
from types import SimpleNamespace

import pytest

from chromalens.metrics import RuntimeMetricsSnapshot


ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "scripts/t09_benchmark_performance.py"
SPEC = spec_from_file_location("t09_benchmark_performance", SCRIPT)
assert SPEC is not None and SPEC.loader is not None
benchmark = module_from_spec(SPEC)
sys.modules[SPEC.name] = benchmark
SPEC.loader.exec_module(benchmark)


def _snapshot(
    *, display_samples: int = 4, elapsed_seconds: float = 2.0
) -> RuntimeMetricsSnapshot:
    return RuntimeMetricsSnapshot(
        total_frames=4,
        elapsed_seconds=elapsed_seconds,
        processed_fps=2.0,
        source_read_to_render_p50_ms=12.0,
        source_read_to_render_p95_ms=18.0,
        source_read_to_display_submit_p50_ms=14.0,
        source_read_to_display_submit_p95_ms=22.0,
        frame_processing_to_render_p50_ms=7.0,
        frame_processing_to_render_p95_ms=9.0,
        rss_start_mib=100.0,
        rss_end_mib=103.0,
        rss_peak_mib=104.0,
        rss_delta_mib=3.0,
        rss_slope_mib_per_minute=1.5,
        rss_steady_state_delta_mib=0.4,
        rss_steady_state_slope_mib_per_minute=0.2,
        source_read_to_render_slope_ms_per_minute=0.3,
        latency_continuous_growth_flag=False,
        rss_continuous_growth_flag=False,
        retained_source_read_to_render_samples=4,
        retained_source_read_to_display_submit_samples=display_samples,
        retained_memory_samples=3,
        dropped_capture_frames=2,
        degraded_frames=1,
    )


def _metric(records: list[dict[str, object]], name: str, aggregation: str) -> dict[str, object]:
    return next(item for item in records if item["name"] == name and item["aggregation"] == aggregation)


def test_snapshot_mapping_reports_all_required_webcam_metrics() -> None:
    case = benchmark.CASES["PERF-WEBCAM-GUI-120"]
    records = benchmark.snapshot_to_schema_metrics(case, _snapshot(), False)

    names = {item["name"] for item in records}
    assert {
        "processed_fps", "source_read_to_render_ms",
        "source_read_to_render_slope_ms_per_minute",
        "source_read_to_display_submit_ms", "sensor_to_photon_ms",
        "frame_processing_to_render_ms", "rss_mib", "rss_delta_mib",
        "rss_slope_mib_per_minute", "latency_continuous_growth_flag",
        "rss_continuous_growth_flag", "processed_frame_count",
        "dropped_capture_frame_count", "degraded_frame_rate",
        "retained_source_read_to_render_sample_count",
        "retained_source_read_to_display_submit_sample_count",
    } <= names
    assert _metric(records, "processed_fps", "single")["value"] == 2.0
    assert _metric(records, "rss_mib", "peak")["value"] == 104.0
    assert _metric(records, "degraded_frame_rate", "single")["value"] == 0.25
    assert _metric(records, "dropped_capture_frame_count", "count")["value"] == 2


def test_cases_use_the_exact_frozen_fixture_ids() -> None:
    assert {
        case_id: case.fixture_id for case_id, case in benchmark.CASES.items()
    } == {
        "PERF-WEBCAM-GUI-120": "webcam-gui-640x480",
        "PERF-WEBCAM-HEADLESS-120": "webcam-headless-640x480",
        "PERF-VIDEO-GUI-120": "generated-video-gui-360x240",
        "PERF-VIDEO-HEADLESS-120": "generated-video-headless-360x240",
    }


def test_headless_semantics_never_claim_gui_submission() -> None:
    case = benchmark.CASES["PERF-VIDEO-HEADLESS-120"]
    records = benchmark.snapshot_to_schema_metrics(case, _snapshot(display_samples=0), False)

    for aggregation in ("p50", "p95"):
        metric = _metric(records, "source_read_to_display_submit_ms", aggregation)
        assert metric["status"] == "NOT_MEASURED"
        assert metric["value"] is None
        assert "headless" in str(metric["reason"])
    retained = _metric(records, "retained_source_read_to_display_submit_sample_count", "count")
    assert retained["value"] == 0
    assert retained["threshold_result"] == "PASS"
    assert "dropped_capture_frame_count" not in {item["name"] for item in records}


def test_headless_display_samples_are_not_hidden_and_invalidate_result(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    payload = _payload(
        monkeypatch,
        case=benchmark.CASES["PERF-VIDEO-HEADLESS-120"],
        snapshot=_snapshot(display_samples=4, elapsed_seconds=120.0),
        resolution=(360, 240),
    )
    retained = _metric(
        payload["metrics"], "retained_source_read_to_display_submit_sample_count", "count"
    )
    assert retained["value"] == 4
    assert retained["threshold_result"] == "FAIL"
    assert payload["result_status"] == "INVALID"


def test_sensor_to_photon_is_always_not_measured_without_external_apparatus() -> None:
    records = benchmark.snapshot_to_schema_metrics(
        benchmark.CASES["PERF-WEBCAM-GUI-120"], _snapshot(), True
    )

    for aggregation in ("p50", "p95"):
        metric = _metric(records, "sensor_to_photon_ms", aggregation)
        assert metric["status"] == "NOT_MEASURED"
        assert metric["value"] is None
        assert "external" in str(metric["reason"])


def test_cli_accepts_only_frozen_cases_and_valid_source_pairing() -> None:
    parser = benchmark.build_parser()
    args = parser.parse_args(["--case", "PERF-WEBCAM-GUI-120"])
    assert benchmark.validate_args(args, parser).case_id == "PERF-WEBCAM-GUI-120"

    with pytest.raises(SystemExit):
        parser.parse_args(["--case", "PERF-NOT-A-CASE"])
    video_args = parser.parse_args(["--case", "PERF-VIDEO-GUI-120"])
    with pytest.raises(SystemExit):
        benchmark.validate_args(video_args, parser)
    webcam_args = parser.parse_args([
        "--case", "PERF-WEBCAM-GUI-120", "--video", "fixture.avi"
    ])
    with pytest.raises(SystemExit):
        benchmark.validate_args(webcam_args, parser)


def test_overridden_duration_is_marked_non_official_and_output_namespace_is_fixed() -> None:
    assert benchmark.is_official_duration(15.0, 120.0)
    assert not benchmark.is_official_duration(0.0, 0.1)
    benchmark._validate_output_dir(Path("artifacts/t09/performance_responsible_ai/smoke"))
    with pytest.raises(ValueError, match="artifacts/t09/performance_responsible_ai"):
        benchmark._validate_output_dir(Path("artifacts/t09/other"))


def test_payload_exposes_schema_version_and_override_disclaimer(monkeypatch: pytest.MonkeyPatch) -> None:
    payload = _payload(
        monkeypatch,
        case=benchmark.CASES["PERF-VIDEO-HEADLESS-120"],
        snapshot=_snapshot(display_samples=0),
        resolution=(360, 240),
        warmup_seconds=0.0,
        measurement_seconds=0.1,
    )
    assert payload["schema_version"] == "1.0.0"
    assert payload["result_status"] == "PARTIAL"
    assert "not an official benchmark" in payload["notes"]
    assert payload["environment"]["display_mode"] == "headless"


def test_truncated_retained_series_is_invalid_not_an_approximate_percentile(monkeypatch: pytest.MonkeyPatch) -> None:
    truncated = replace(
        _snapshot(elapsed_seconds=120.0),
        retained_source_read_to_render_samples=3,
    )
    payload = _payload(
        monkeypatch,
        case=benchmark.CASES["PERF-WEBCAM-GUI-120"],
        snapshot=truncated,
        resolution=(640, 480),
    )
    assert payload["result_status"] == "INVALID"


def test_early_stop_and_wrong_resolution_cannot_be_complete(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    snapshot = _snapshot(elapsed_seconds=120.0)
    early = _payload(
        monkeypatch,
        case=benchmark.CASES["PERF-WEBCAM-GUI-120"],
        snapshot=snapshot,
        resolution=(640, 480),
        stop_reason="user_exit",
    )
    wrong_resolution = _payload(
        monkeypatch,
        case=benchmark.CASES["PERF-WEBCAM-GUI-120"],
        snapshot=snapshot,
        resolution=(320, 240),
    )
    assert early["result_status"] == "PARTIAL"
    assert "stop reason" in early["cases"][0]["reason"]
    assert wrong_resolution["result_status"] == "PARTIAL"
    assert "320x240" in wrong_resolution["cases"][0]["reason"]


def test_only_a_complete_official_run_gets_complete_status(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    payload = _payload(
        monkeypatch,
        case=benchmark.CASES["PERF-WEBCAM-GUI-120"],
        snapshot=_snapshot(elapsed_seconds=120.0),
        resolution=(640, 480),
    )
    assert payload["result_status"] == "COMPLETE"
    assert payload["cases"][0]["fixture_id"] == "webcam-gui-640x480"
    assert "perf-webcam-gui-120" in payload["result_id"]


def test_display_p95_is_observation_only() -> None:
    records = benchmark.snapshot_to_schema_metrics(
        benchmark.CASES["PERF-WEBCAM-GUI-120"], _snapshot(), True
    )
    p50 = _metric(records, "source_read_to_display_submit_ms", "p50")
    p95 = _metric(records, "source_read_to_display_submit_ms", "p95")
    assert p50["threshold_id"] == "demo_floor_p50"
    assert p95["threshold_id"] is None
    assert p95["threshold_result"] == "NOT_EVALUATED"


@pytest.mark.parametrize("result", ["A" * 40, "a" * 39])
def test_git_commit_rejects_invalid_sha(monkeypatch: pytest.MonkeyPatch, result: str) -> None:
    monkeypatch.setattr(
        benchmark.subprocess,
        "run",
        lambda *_args, **_kwargs: SimpleNamespace(stdout=result + "\n"),
    )
    with pytest.raises(RuntimeError, match="invalid SHA"):
        benchmark._git_commit()


def test_git_commit_command_failure_is_explicit(monkeypatch: pytest.MonkeyPatch) -> None:
    def fail(*_args: object, **_kwargs: object) -> object:
        raise benchmark.subprocess.CalledProcessError(1, "git")

    monkeypatch.setattr(benchmark.subprocess, "run", fail)
    with pytest.raises(RuntimeError, match="could not determine"):
        benchmark._git_commit()


def _payload(
    monkeypatch: pytest.MonkeyPatch,
    *,
    case: benchmark.BenchmarkCase,
    snapshot: RuntimeMetricsSnapshot,
    resolution: tuple[int, int],
    warmup_seconds: float = 15.0,
    measurement_seconds: float = 120.0,
    stop_reason: str = "duration_limit",
) -> dict[str, object]:
    monkeypatch.setattr(benchmark, "collect_environment", lambda: {
        "manufacturer": "test", "model": "test", "operating_system": "test",
        "cpu": "test", "physical_core_count": 1, "logical_processor_count": 1,
        "ram_gib": 1.0, "gpu": "not detected", "npu": "not detected",
        "python_version": "3.10.20",
        "package_versions": {"a": "1", "b": "1", "c": "1", "d": "1"},
        "lock_sha256": "0" * 64,
    })
    monkeypatch.setattr(benchmark, "_git_commit", lambda: "a" * 40)
    return benchmark.build_result_payload(
        case=case, snapshot=snapshot, source_name="source", resolution=resolution,
        backend_name="test/cpu", warmup_seconds=warmup_seconds,
        measurement_seconds=measurement_seconds, profile="deutan", severity=0.8,
        operator="Trinh", host_role="development", declared_demo_hardware=False,
        command="test", started_at_utc="2026-08-21T00:00:00Z",
        ended_at_utc="2026-08-21T00:02:15Z", stop_reason=stop_reason,
    )
