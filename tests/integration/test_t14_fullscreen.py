from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

import cv2
import numpy as np

from chromalens.app import run_pipeline_session
from chromalens.camera import open_video
from chromalens.contracts import FramePacket, GarmentRegion
from chromalens.pipeline import ChromaLensPipeline
from chromalens.segmentation.base import Segmenter


class CountingSegmenter(Segmenter):
    """Deterministic backend proving display transitions reuse one pipeline."""

    def __init__(self) -> None:
        self.calls = 0
        self.closed = False
        self.shapes: list[tuple[int, int]] = []

    @property
    def backend_name(self) -> str:
        return "t14-counting-mask"

    @property
    def device_info(self) -> str:
        return "t14-counting-mask/cpu"

    def segment(self, packet: FramePacket) -> tuple[GarmentRegion, ...]:
        self.calls += 1
        height, width = packet.original_bgr.shape[:2]
        self.shapes.append((height, width))
        mask = np.zeros((height, width), dtype=np.bool_)
        mask[height // 4 : 3 * height // 4, width // 4 : 3 * width // 4] = True
        return (
            GarmentRegion(
                track_id=1,
                class_name="upper-clothes",
                mask=mask,
                mask_confidence=0.9,
            ),
        )

    def close(self) -> None:
        self.closed = True


def _write_video(path: Path) -> None:
    writer = cv2.VideoWriter(
        str(path), cv2.VideoWriter_fourcc(*"MJPG"), 12.0, (240, 160)
    )
    assert writer.isOpened()
    try:
        for index in range(4):
            frame = np.full((160, 240, 3), 60 + index * 10, dtype=np.uint8)
            frame[40:120, 60:180] = (25, 50, 210)
            writer.write(frame)
    finally:
        writer.release()


def test_f_esc_q_transition_keeps_one_pipeline_and_processing_resolution(
    tmp_path: Path,
) -> None:
    video_path = tmp_path / "t14-controls.avi"
    _write_video(video_path)
    source = open_video(video_path)
    segmenter = CountingSegmenter()
    pipeline = ChromaLensPipeline(segmenter, stream_id=source.name)
    keys = iter((ord("f"), 27, ord("q")))

    with (
        patch("chromalens.app.cv2.waitKey", side_effect=lambda _delay: next(keys)),
        patch("chromalens.display.cv2.imshow") as imshow,
        patch("chromalens.display.cv2.namedWindow") as named_window,
        patch("chromalens.display.cv2.resizeWindow") as resize_window,
        patch("chromalens.display.cv2.setWindowProperty") as set_property,
        patch(
            "chromalens.display.cv2.getWindowImageRect",
            return_value=(0, 0, 1366, 768),
        ),
        patch("chromalens.display.cv2.getWindowProperty", return_value=1.0),
        patch("chromalens.display.cv2.destroyWindow") as destroy_window,
    ):
        result = run_pipeline_session(
            source,
            pipeline,
            display=True,
            fullscreen_size=(1366, 768),
        )

    assert result.stop_reason == "user_exit"
    assert result.frames_processed == 3
    assert result.resolution == (240, 160)
    assert segmenter.calls == 3
    assert segmenter.closed
    assert imshow.call_count == 3
    assert imshow.call_args_list[1].args[1].shape == (768, 1366, 3)
    assert named_window.call_count == 1
    assert set_property.call_count == 2
    assert resize_window.call_count == 2
    destroy_window.assert_called_once()


def test_fullscreen_keeps_detailed_display_source_and_bounds_analysis(
    tmp_path: Path,
) -> None:
    video_path = tmp_path / "t14-dual-resolution.avi"
    writer = cv2.VideoWriter(
        str(video_path), cv2.VideoWriter_fourcc(*"MJPG"), 12.0, (1280, 720)
    )
    assert writer.isOpened()
    try:
        writer.write(np.full((720, 1280, 3), (40, 90, 180), dtype=np.uint8))
    finally:
        writer.release()

    source = open_video(video_path)
    segmenter = CountingSegmenter()
    pipeline = ChromaLensPipeline(segmenter, stream_id=source.name)
    with (
        patch("chromalens.app.cv2.waitKey", return_value=ord("q")),
        patch("chromalens.display.cv2.imshow") as imshow,
        patch("chromalens.display.cv2.namedWindow"),
        patch("chromalens.display.cv2.resizeWindow"),
        patch("chromalens.display.cv2.setWindowProperty"),
        patch("chromalens.display.cv2.getWindowProperty", return_value=1.0),
        patch("chromalens.display.cv2.destroyWindow"),
    ):
        result = run_pipeline_session(
            source,
            pipeline,
            display=True,
            fullscreen=True,
            fullscreen_size=(1920, 1080),
            analysis_size=(480, 360),
        )

    assert result.frames_processed == 1
    assert segmenter.shapes == [(270, 480)]
    assert imshow.call_args.args[1].shape == (1080, 1920, 3)
