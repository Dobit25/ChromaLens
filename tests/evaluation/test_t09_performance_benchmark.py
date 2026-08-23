from __future__ import annotations

from pathlib import Path

import cv2
import numpy as np

from chromalens.metrics import RuntimeMetricsSnapshot
from scripts import t09_benchmark_performance as benchmark


def snapshot(*, display_samples: int) -> RuntimeMetricsSnapshot:
    return RuntimeMetricsSnapshot(
        total_frames=1200,
        elapsed_seconds=120.0,
        processed_fps=10.0,
        source_read_to_render_p50_ms=80.0,
        source_read_to_render_p95_ms=140.0,
        source_read_to_display_submit_p50_ms=82.0 if display_samples else None,
        source_read_to_display_submit_p95_ms=143.0 if display_samples else None,
        frame_processing_to_render_p50_ms=70.0,
        frame_processing_to_render_p95_ms=130.0,
        rss_start_mib=100.0,
        rss_end_mib=102.0,
        rss_peak_mib=110.0,
        rss_delta_mib=2.0,
        rss_slope_mib_per_minute=1.0,
        rss_steady_state_delta_mib=0.5,
        rss_steady_state_slope_mib_per_minute=0.2,
        source_read_to_render_slope_ms_per_minute=-1.0,
        latency_continuous_growth_flag=False,
        rss_continuous_growth_flag=False,
        retained_source_read_to_render_samples=1200,
        retained_source_read_to_display_submit_samples=display_samples,
        retained_memory_samples=121,
        dropped_capture_frames=5,
        degraded_frames=12,
    )


def by_name(metrics: list[dict[str, object]], name: str, aggregation: str) -> dict[str, object]:
    return next(
        item
        for item in metrics
        if item["name"] == name and item["aggregation"] == aggregation
    )


def test_benchmark_cases_are_exactly_the_four_frozen_runs() -> None:
    assert set(benchmark.CASES) == {
        "PERF-WEBCAM-GUI-120",
        "PERF-WEBCAM-HEADLESS-120",
        "PERF-VIDEO-GUI-120",
        "PERF-VIDEO-HEADLESS-120",
    }


def test_gui_and_headless_latency_semantics_are_separate() -> None:
    gui = benchmark.snapshot_metrics(
        benchmark.CASES["PERF-WEBCAM-GUI-120"],
        snapshot(display_samples=1200),
        declared_demo_hardware=False,
    )
    headless = benchmark.snapshot_metrics(
        benchmark.CASES["PERF-WEBCAM-HEADLESS-120"],
        snapshot(display_samples=0),
        declared_demo_hardware=False,
    )

    assert by_name(gui, "source_read_to_render_ms", "p50")["value"] == 80.0
    assert by_name(gui, "source_read_to_display_submit_ms", "p50")["value"] == 82.0
    assert by_name(headless, "source_read_to_display_submit_ms", "p50")["status"] == "NOT_MEASURED"
    assert "headless" in str(by_name(headless, "source_read_to_display_submit_ms", "p50")["reason"]).lower()


def test_sensor_to_photon_is_never_inferred_from_software_timestamps() -> None:
    metrics = benchmark.snapshot_metrics(
        benchmark.CASES["PERF-VIDEO-GUI-120"],
        snapshot(display_samples=1200),
        declared_demo_hardware=False,
    )
    sensor = [item for item in metrics if item["name"] == "sensor_to_photon_ms"]

    assert len(sensor) == 2
    assert all(item["status"] == "NOT_MEASURED" for item in sensor)
    assert all(item["value"] is None for item in sensor)
    assert all("external" in str(item["method"]).lower() for item in sensor)


def test_looping_video_rewinds_without_opening_a_webcam(tmp_path: Path) -> None:
    path = tmp_path / "two-frames.avi"
    writer = cv2.VideoWriter(
        str(path), cv2.VideoWriter_fourcc(*"MJPG"), 10.0, (32, 24)
    )
    assert writer.isOpened()
    writer.write(np.full((24, 32, 3), 20, dtype=np.uint8))
    writer.write(np.full((24, 32, 3), 220, dtype=np.uint8))
    writer.release()

    source = benchmark.LoopingVideoSource(path)
    packets = [source.read(), source.read(), source.read()]
    source.close()

    assert all(packet is not None for packet in packets)
    assert [packet.frame_id for packet in packets if packet is not None] == [0, 1, 2]
    assert source.resolution == (32, 24)

