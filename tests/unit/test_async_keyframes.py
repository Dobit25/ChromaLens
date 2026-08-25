"""Deterministic tests for bounded SCHP keyframes and mask propagation."""

from __future__ import annotations

from threading import Event
from time import monotonic, monotonic_ns
from unittest.mock import patch

import cv2
import numpy as np
import pytest

from chromalens.app import _build_segmenter, build_parser
from chromalens.contracts import FramePacket, GarmentRegion
from chromalens.segmentation.async_keyframes import (
    AsyncKeyframeConfig,
    AsyncKeyframeSegmenter,
    estimate_backward_flow,
    warp_mask_with_backward_flow,
)
from chromalens.segmentation.base import SegmentationMaskSource, Segmenter


class ControlledSegmenter(Segmenter):
    def __init__(self, *, fail: bool = False, block: bool = False) -> None:
        self.fail = fail
        self.block = block
        self.started = Event()
        self.release = Event()
        self.finished = Event()
        self.calls: list[int] = []
        self.closed = False

    @property
    def backend_name(self) -> str:
        return "controlled-schp"

    @property
    def device_info(self) -> str:
        return "controlled-schp/cpu"

    def segment(self, packet: FramePacket) -> tuple[GarmentRegion, ...]:
        self.calls.append(packet.frame_id)
        self.started.set()
        if self.block:
            assert self.release.wait(timeout=2.0)
        try:
            if self.fail:
                raise RuntimeError("controlled backend failure")
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
        finally:
            self.finished.set()

    def close(self) -> None:
        self.closed = True


def _packet(frame_id: int, timestamp_ns: int | None = None) -> FramePacket:
    frame = np.zeros((32, 32, 3), dtype=np.uint8)
    frame[6:26, 6:26] = (80, 140, 220)
    return FramePacket(
        frame_id=frame_id,
        timestamp_ns=monotonic_ns() if timestamp_ns is None else timestamp_ns,
        original_bgr=frame,
    )


def _wait_for_completed(adapter: AsyncKeyframeSegmenter) -> None:
    deadline = monotonic() + 2.0
    while monotonic() < deadline:
        with adapter._condition:  # test-only inspection of the capacity-one mailbox
            if adapter._completed is not None:
                return
        Event().wait(0.005)
    raise AssertionError("asynchronous inference did not complete")


def test_backward_flow_warp_translates_mask_to_current_frame() -> None:
    mask = np.zeros((8, 10), dtype=np.bool_)
    mask[2:6, 2:5] = True
    target_to_source = np.zeros((8, 10, 2), dtype=np.float32)
    target_to_source[..., 0] = -2.0

    warped = warp_mask_with_backward_flow(mask, target_to_source)

    expected = np.zeros_like(mask)
    expected[2:6, 4:7] = True
    assert np.array_equal(warped, expected)


def test_quarter_scale_flow_tracks_a_textured_translation() -> None:
    rng = np.random.default_rng(17)
    source = rng.integers(0, 256, size=(96, 128, 3), dtype=np.uint8)
    transform = np.asarray(((1.0, 0.0, 4.0), (0.0, 1.0, 3.0)), dtype=np.float32)
    target = cv2.warpAffine(source, transform, (128, 96), borderValue=(0, 0, 0))
    source_mask = np.zeros((96, 128), dtype=np.bool_)
    source_mask[24:72, 32:88] = True
    expected = cv2.warpAffine(
        source_mask.astype(np.uint8),
        transform,
        (128, 96),
        flags=cv2.INTER_NEAREST,
    ).astype(np.bool_)

    flow = estimate_backward_flow(source, target, scale=0.25)
    actual = warp_mask_with_backward_flow(source_mask, flow)

    intersection = int(np.logical_and(actual, expected).sum())
    union = int(np.logical_or(actual, expected).sum())
    assert intersection / union >= 0.90


def test_worker_is_non_blocking_latest_only_and_reports_propagation() -> None:
    backend = ControlledSegmenter(block=True)
    adapter = AsyncKeyframeSegmenter(backend)
    try:
        started = monotonic()
        assert adapter.segment(_packet(0)) == ()
        assert monotonic() - started < 0.1
        assert adapter.frame_telemetry is not None
        assert adapter.frame_telemetry.mask_source is SegmentationMaskSource.WARMING_UP
        assert backend.started.wait(timeout=1.0)

        adapter.segment(_packet(1))
        adapter.segment(_packet(2))
        assert adapter.dropped_pending_frames >= 1
        backend.release.set()
        _wait_for_completed(adapter)

        regions = adapter.segment(_packet(3))
        assert regions
        assert regions[0].mask.shape == (32, 32)
        assert adapter.frame_telemetry is not None
        assert adapter.frame_telemetry.mask_source is SegmentationMaskSource.PROPAGATED
        assert adapter.frame_telemetry.keyframe_id in {0, 2}
    finally:
        backend.release.set()
        adapter.close()

    assert not adapter.worker_alive
    assert backend.closed
    assert 1 not in backend.calls


def test_mask_is_cleared_when_completed_keyframe_is_too_old() -> None:
    backend = ControlledSegmenter()
    adapter = AsyncKeyframeSegmenter(
        backend,
        AsyncKeyframeConfig(maximum_mask_age_ms=5.0),
    )
    try:
        adapter.segment(_packet(0, timestamp_ns=0))
        _wait_for_completed(adapter)

        assert adapter.segment(_packet(1, timestamp_ns=10_000_000)) == ()
        assert adapter.frame_telemetry is not None
        assert adapter.frame_telemetry.mask_source is SegmentationMaskSource.STALE
        assert adapter.frame_telemetry.mask_age_ms == pytest.approx(10.0)
    finally:
        adapter.close()


def test_backend_failure_is_exposed_without_a_fabricated_mask() -> None:
    backend = ControlledSegmenter(fail=True)
    adapter = AsyncKeyframeSegmenter(backend)
    try:
        adapter.segment(_packet(0))
        _wait_for_completed(adapter)

        assert adapter.segment(_packet(1)) == ()
        assert adapter.frame_telemetry is not None
        assert adapter.frame_telemetry.mask_source is SegmentationMaskSource.UNAVAILABLE
        assert "controlled backend failure" in (adapter.frame_telemetry.message or "")
    finally:
        adapter.close()


def test_cli_defaults_live_schp_to_async_and_keeps_sync_diagnostic() -> None:
    parser = build_parser()

    defaults = parser.parse_args(["--webcam"])
    assert defaults.schp_live_mode == "async"
    assert (defaults.width, defaults.height) == (480, 360)
    assert (
        parser.parse_args(["--webcam", "--schp-live-mode", "sync"]).schp_live_mode
        == "sync"
    )


def test_segmenter_factory_wraps_only_a_live_schp_source() -> None:
    parser = build_parser()
    live_backend = ControlledSegmenter()
    video_backend = ControlledSegmenter()
    args = parser.parse_args(["--webcam"])

    with patch(
        "chromalens.segmentation.schp_backend.SCHPSegmenter",
        return_value=live_backend,
    ):
        live = _build_segmenter(args, live_source=True)
    assert isinstance(live, AsyncKeyframeSegmenter)
    live.close()

    with patch(
        "chromalens.segmentation.schp_backend.SCHPSegmenter",
        return_value=video_backend,
    ):
        video = _build_segmenter(args, live_source=False)
    assert video is video_backend
    video.close()
