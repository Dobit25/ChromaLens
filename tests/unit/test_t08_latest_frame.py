"""Hardware-independent capacity-one live-capture tests for T08."""

from __future__ import annotations

from threading import Event
from time import sleep

import numpy as np
import pytest

from chromalens.camera import FrameSource, LatestFrameReader, LatestFrameTimeout
from chromalens.contracts import FramePacket


class ControlledLiveSource(FrameSource):
    def __init__(self) -> None:
        self.release = Event()
        self.closed = False
        self.reads = 0

    @property
    def name(self) -> str:
        return "test:live"

    @property
    def is_live(self) -> bool:
        return True

    @property
    def resolution(self) -> tuple[int, int]:
        return (4, 4)

    @property
    def nominal_fps(self) -> None:
        return None

    def read(self) -> FramePacket | None:
        self.release.wait(timeout=1.0)
        if self.closed:
            return None
        if self.reads >= 5:
            return None
        frame_id = self.reads
        self.reads += 1
        return FramePacket(
            frame_id=frame_id,
            timestamp_ns=frame_id,
            original_bgr=np.zeros((4, 4, 3), dtype=np.uint8),
        )

    def close(self) -> None:
        self.closed = True
        self.release.set()


def test_latest_frame_reader_overwrites_capacity_one_mailbox() -> None:
    source = ControlledLiveSource()
    reader = LatestFrameReader(source).start()
    source.release.set()
    for _ in range(100):
        if reader.finished:
            break
        sleep(0.005)

    packet = reader.read_latest()
    reader.close()

    assert packet is not None and packet.frame_id == 4
    assert reader.dropped_frames == 4
    assert source.closed
    assert not reader.worker_alive


def test_latest_frame_reader_times_out_boundedly() -> None:
    source = ControlledLiveSource()
    reader = LatestFrameReader(source).start()
    try:
        with pytest.raises(LatestFrameTimeout, match="No frame arrived"):
            reader.read_latest(timeout_seconds=0.01)
    finally:
        reader.close()
