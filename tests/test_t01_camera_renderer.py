"""Hardware-independent tests for T01 capture, rendering, and CLI behavior."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

import cv2
import numpy as np
import pytest

from chromalens.app import main, run_preview
from chromalens.camera import (
    FrameSource,
    FrameSourceOpenError,
    open_video,
    open_webcam,
)
from chromalens.contracts import FramePacket
from chromalens.renderer import PreviewMetricsTracker, render_preview


def _write_test_video(path: Path, *, frame_count: int = 4) -> None:
    writer = cv2.VideoWriter(
        str(path),
        cv2.VideoWriter_fourcc(*"MJPG"),
        12.0,
        (64, 48),
    )
    assert writer.isOpened(), "OpenCV MJPG writer is required for the T01 smoke test"
    try:
        for frame_index in range(frame_count):
            frame = np.full((48, 64, 3), frame_index * 30, dtype=np.uint8)
            writer.write(frame)
    finally:
        writer.release()


def test_video_source_emits_aligned_monotonic_packets_and_clean_eof(
    tmp_path: Path,
) -> None:
    video_path = tmp_path / "sample.avi"
    _write_test_video(video_path, frame_count=3)

    source = open_video(video_path)
    packets: list[FramePacket] = []
    try:
        while (packet := source.read()) is not None:
            packets.append(packet)
        assert source.read() is None
    finally:
        source.close()

    assert [packet.frame_id for packet in packets] == [0, 1, 2]
    assert all(packet.original_bgr.shape == (48, 64, 3) for packet in packets)
    assert all(packet.original_bgr.dtype == np.uint8 for packet in packets)
    assert [packet.timestamp_ns for packet in packets] == sorted(
        packet.timestamp_ns for packet in packets
    )
    assert source.resolution == (64, 48)
    assert source.nominal_fps == pytest.approx(12.0)


def test_renderer_overlays_a_copy_and_preserves_original_frame() -> None:
    original = np.full((120, 360, 3), 127, dtype=np.uint8)
    before = original.copy()
    packet = FramePacket(frame_id=7, timestamp_ns=1_000, original_bgr=original)
    tracker = PreviewMetricsTracker()
    telemetry = tracker.observe(packet, observed_ns=2_001_000)

    rendered = render_preview(
        packet,
        source_name="video:sample.avi",
        telemetry=telemetry,
    )

    assert np.array_equal(packet.original_bgr, before)
    assert not np.shares_memory(rendered, packet.original_bgr)
    assert not np.array_equal(rendered, packet.original_bgr)
    assert telemetry.frame_age_at_overlay_ms == pytest.approx(2.0)
    assert telemetry.processed_fps is None


def test_video_cli_runs_to_eof_without_opening_webcam(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    video_path = tmp_path / "camera-free.avi"
    _write_test_video(video_path, frame_count=4)

    with patch("chromalens.app.open_webcam") as webcam_factory:
        exit_code = main(
            ["--video", str(video_path), "--preview-only", "--no-display"]
        )

    assert exit_code == 0
    webcam_factory.assert_not_called()
    output = capsys.readouterr().out
    assert "frames=4" in output
    assert "reason=end_of_video" in output


def test_missing_video_reports_actionable_error(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    missing_path = tmp_path / "missing.avi"

    exit_code = main(["--video", str(missing_path), "--no-display"])

    captured = capsys.readouterr()
    assert exit_code == 2
    assert str(missing_path) in captured.err
    assert "file does not exist" in captured.err
    assert "Check the --video path" in captured.err


def test_webcam_open_failure_releases_handle_and_is_actionable() -> None:
    class ClosedCapture:
        def __init__(self) -> None:
            self.released = False

        def isOpened(self) -> bool:
            return False

        def release(self) -> None:
            self.released = True

    capture = ClosedCapture()
    with patch("chromalens.camera.cv2.VideoCapture", return_value=capture):
        with pytest.raises(FrameSourceOpenError, match="camera permission"):
            open_webcam(3)

    assert capture.released


def test_preview_loop_processes_sequentially_without_prefetch_queue() -> None:
    events: list[str] = []

    class SequentialSource(FrameSource):
        def __init__(self) -> None:
            self.next_frame_id = 0
            self.closed = False

        @property
        def name(self) -> str:
            return "test:sequential"

        @property
        def is_live(self) -> bool:
            return True

        @property
        def resolution(self) -> tuple[int, int]:
            return (32, 24)

        @property
        def nominal_fps(self) -> None:
            return None

        def read(self) -> FramePacket:
            frame_id = self.next_frame_id
            events.append(f"read:{frame_id}")
            self.next_frame_id += 1
            return FramePacket(
                frame_id=frame_id,
                timestamp_ns=frame_id + 1,
                original_bgr=np.zeros((24, 32, 3), dtype=np.uint8),
            )

        def close(self) -> None:
            self.closed = True
            events.append("close")

    def recording_renderer(
        packet: FramePacket,
        *,
        source_name: str,
        telemetry: object,
    ) -> np.ndarray:
        assert source_name == "test:sequential"
        assert telemetry is not None
        events.append(f"render:{packet.frame_id}")
        return packet.original_bgr.copy()

    source = SequentialSource()
    result = run_preview(
        source,
        display=False,
        max_frames=3,
        render_frame=recording_renderer,
    )

    assert result.frames_processed == 3
    assert result.stop_reason == "frame_limit"
    assert source.closed
    assert events == [
        "read:0",
        "render:0",
        "read:1",
        "render:1",
        "read:2",
        "render:2",
        "close",
    ]


def test_preview_q_exit_releases_source_and_window() -> None:
    class OneFrameSource(FrameSource):
        def __init__(self) -> None:
            self.closed = False

        @property
        def name(self) -> str:
            return "test:q-exit"

        @property
        def is_live(self) -> bool:
            return True

        @property
        def resolution(self) -> tuple[int, int]:
            return (64, 48)

        @property
        def nominal_fps(self) -> None:
            return None

        def read(self) -> FramePacket:
            return FramePacket(
                frame_id=0,
                timestamp_ns=1,
                original_bgr=np.zeros((48, 64, 3), dtype=np.uint8),
            )

        def close(self) -> None:
            self.closed = True

    source = OneFrameSource()
    with (
        patch("chromalens.app.cv2.imshow") as imshow,
        patch("chromalens.app.cv2.waitKey", return_value=ord("q")),
        patch("chromalens.app.cv2.destroyWindow") as destroy_window,
    ):
        result = run_preview(source, display=True)

    assert result.stop_reason == "user_exit"
    assert result.frames_processed == 1
    assert source.closed
    imshow.assert_called_once()
    destroy_window.assert_called_once()
