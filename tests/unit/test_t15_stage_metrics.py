"""Deterministic contracts for bounded T15 named-stage timing."""

from __future__ import annotations

from threading import Event
from time import monotonic, monotonic_ns

import numpy as np
import pytest

from chromalens.contracts import FramePacket, GarmentRegion
from chromalens.metrics import (
    StageTimingConfig,
    StageTimingName,
    StageTimingTracker,
)
from chromalens.segmentation.async_keyframes import AsyncKeyframeSegmenter
from chromalens.segmentation.base import Segmenter


class ManualClock:
    def __init__(self) -> None:
        self.now_ns = 0

    def __call__(self) -> int:
        return self.now_ns

    def advance_ms(self, value: float) -> None:
        self.now_ns += round(value * 1_000_000.0)


class ImmediateSegmenter(Segmenter):
    @property
    def backend_name(self) -> str:
        return "immediate"

    @property
    def device_info(self) -> str:
        return "immediate/cpu"

    def segment(self, packet: FramePacket) -> tuple[GarmentRegion, ...]:
        mask = np.zeros(packet.original_bgr.shape[:2], dtype=np.bool_)
        mask[8:24, 8:24] = True
        return (
            GarmentRegion(
                track_id=1,
                class_name="upper-clothes",
                mask=mask,
                mask_confidence=0.9,
            ),
        )


def _packet(frame_id: int) -> FramePacket:
    rng = np.random.default_rng(17)
    frame = rng.integers(0, 256, size=(32, 32, 3), dtype=np.uint8)
    return FramePacket(
        frame_id=frame_id,
        timestamp_ns=monotonic_ns(),
        original_bgr=frame,
    )


def test_stage_timing_is_bounded_and_reports_frozen_order() -> None:
    clock = ManualClock()
    tracker = StageTimingTracker(
        StageTimingConfig(max_samples_per_stage=2),
        clock_ns=clock,
    )

    for duration_ms in (1.0, 2.0, 3.0):
        with tracker.measure(StageTimingName.WHITE_BALANCE):
            clock.advance_ms(duration_ms)
    tracker.skip(StageTimingName.DISPLAY_SUBMIT)

    snapshots = tracker.snapshot()
    assert tuple(item.stage for item in snapshots) == tuple(StageTimingName)
    white_balance = snapshots[2]
    assert white_balance.stage is StageTimingName.WHITE_BALANCE
    assert white_balance.count == 3
    assert white_balance.retained_samples == 2
    assert white_balance.mean_ms == pytest.approx(2.0)
    assert white_balance.p50_ms == pytest.approx(2.5)
    assert white_balance.p95_ms == pytest.approx(2.95)
    assert white_balance.max_ms == pytest.approx(3.0)
    assert snapshots[-1].skipped_count == 1


def test_stage_timing_records_errors_without_swallowing_them() -> None:
    clock = ManualClock()
    tracker = StageTimingTracker(clock_ns=clock)

    with pytest.raises(RuntimeError, match="controlled"):
        with tracker.measure(StageTimingName.RISK):
            clock.advance_ms(4.0)
            raise RuntimeError("controlled")

    risk = tracker.snapshot()[4]
    assert risk.count == 1
    assert risk.error_count == 1
    assert risk.p50_ms == pytest.approx(4.0)


def test_reset_excludes_work_started_during_warmup() -> None:
    clock = ManualClock()
    tracker = StageTimingTracker(clock_ns=clock)
    measurement = tracker.measure(StageTimingName.SEGMENTATION_INFERENCE)
    measurement.__enter__()
    clock.advance_ms(5.0)
    tracker.reset()
    clock.advance_ms(7.0)
    measurement.__exit__(None, None, None)

    inference = tracker.snapshot()[0]
    assert inference.count == 0
    assert inference.retained_samples == 0


def test_invalid_stage_type_fails_fast() -> None:
    tracker = StageTimingTracker()

    with pytest.raises(TypeError, match="StageTimingName"):
        tracker.skip("risk")  # type: ignore[arg-type]


def test_async_adapter_times_worker_inference_and_main_thread_flow() -> None:
    tracker = StageTimingTracker()
    adapter = AsyncKeyframeSegmenter(ImmediateSegmenter(), stage_timing=tracker)
    try:
        assert adapter.segment(_packet(0)) == ()
        deadline = monotonic() + 2.0
        while tracker.snapshot()[0].count == 0 and monotonic() < deadline:
            Event().wait(0.005)
        assert tracker.snapshot()[0].count == 1

        regions = adapter.segment(_packet(1))
        assert regions
        snapshots = {item.stage: item for item in tracker.snapshot()}
        assert snapshots[StageTimingName.SEGMENTATION_INFERENCE].count >= 1
        assert snapshots[StageTimingName.OPTICAL_FLOW].count == 1
    finally:
        adapter.close()
