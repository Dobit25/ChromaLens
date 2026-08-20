"""Deterministic T08 tests for bounded temporal state and metrics."""

from __future__ import annotations

import numpy as np
import pytest

from chromalens.contracts import GarmentRegion
from chromalens.metrics import (
    RuntimeMetricsConfig,
    RuntimeMetricsTracker,
    current_process_rss_bytes,
)
from chromalens.tracking import MaskSmoothingConfig, TemporalMaskSmoother


def _region(mask: np.ndarray, *, track_id: int | None = 1) -> GarmentRegion:
    return GarmentRegion(
        track_id=track_id,
        class_name="upper-clothes",
        mask=mask.astype(np.bool_),
        mask_confidence=0.8,
    )


def test_mask_smoothing_never_resurrects_pixels_outside_current_mask() -> None:
    smoother = TemporalMaskSmoother(
        MaskSmoothingConfig(current_frame_weight=0.6, threshold=0.5)
    )
    first_mask = np.zeros((8, 8), dtype=np.bool_)
    first_mask[1:7, 1:7] = True
    current_mask = np.zeros((8, 8), dtype=np.bool_)
    current_mask[3:7, 3:7] = True

    first = smoother.smooth((_region(first_mask),), stream_id="test", frame_shape=(8, 8))
    second = smoother.smooth(
        (_region(current_mask),), stream_id="test", frame_shape=(8, 8)
    )

    assert np.array_equal(first[0].mask, first_mask)
    assert np.all(second[0].mask <= current_mask)
    assert not np.any(second[0].mask & ~current_mask)


def test_empty_current_segmentation_clears_state_and_stays_empty() -> None:
    smoother = TemporalMaskSmoother()
    mask = np.ones((4, 4), dtype=np.bool_)
    smoother.smooth((_region(mask),), stream_id="test", frame_shape=(4, 4))

    assert smoother.smooth((), stream_id="test", frame_shape=(4, 4)) == ()
    assert smoother.state_count == 0


def test_mask_state_is_capacity_bounded() -> None:
    smoother = TemporalMaskSmoother(MaskSmoothingConfig(max_state_entries=2))
    mask = np.ones((4, 4), dtype=np.bool_)
    regions = tuple(_region(mask, track_id=index) for index in range(4))

    smoother.smooth(regions, stream_id="test", frame_shape=(4, 4))

    assert smoother.state_count == 2


def test_runtime_metrics_keep_bounded_samples_and_report_measured_values() -> None:
    clock_values = iter([0])
    rss_values = iter([100, 101, 102, 103, 104, 105])
    tracker = RuntimeMetricsTracker(
        RuntimeMetricsConfig(max_samples=3, memory_sample_interval_frames=1),
        clock_ns=lambda: next(clock_values),
        rss_provider=lambda: next(rss_values) * 1024 * 1024,
    )
    for index in range(4):
        tracker.observe(
            capture_to_render_ms=float(index + 1),
            processing_ms=float(index) + 0.5,
            observed_ns=(index + 1) * 1_000_000_000,
        )

    snapshot = tracker.snapshot(
        dropped_capture_frames=7,
        degraded_frames=2,
        observed_ns=5_000_000_000,
    )

    assert snapshot.total_frames == 4
    assert snapshot.processed_fps == pytest.approx(0.8)
    assert snapshot.retained_latency_samples == 3
    assert snapshot.retained_memory_samples == 3
    assert snapshot.capture_to_render_p50_ms == pytest.approx(3.0)
    assert snapshot.rss_delta_mib == pytest.approx(2.0)
    assert snapshot.rss_slope_mib_per_minute == pytest.approx(60.0)
    assert snapshot.rss_steady_state_delta_mib == pytest.approx(1.0)
    assert snapshot.rss_steady_state_slope_mib_per_minute == pytest.approx(60.0)
    assert snapshot.capture_to_render_slope_ms_per_minute == pytest.approx(60.0)
    assert snapshot.dropped_capture_frames == 7
    assert snapshot.degraded_frames == 2


def test_runtime_rss_probe_returns_a_positive_value_on_supported_host() -> None:
    rss_bytes = current_process_rss_bytes()

    assert rss_bytes is not None
    assert rss_bytes > 0
