"""Hardware-independent wiring checks for T15 stage instrumentation."""

from __future__ import annotations

import json
from pathlib import Path

import cv2
import numpy as np

from chromalens.app import _write_stage_metrics_json, run_pipeline_session
from chromalens.camera import open_video
from chromalens.contracts import FramePacket, GarmentRegion
from chromalens.metrics import StageTimingName, StageTimingTracker
from chromalens.pipeline import ChromaLensPipeline
from chromalens.segmentation.base import Segmenter


class InstrumentedMaskSegmenter(Segmenter):
    @property
    def backend_name(self) -> str:
        return "instrumented-mask"

    @property
    def device_info(self) -> str:
        return "instrumented-mask/cpu"

    def segment(self, packet: FramePacket) -> tuple[GarmentRegion, ...]:
        height, width = packet.original_bgr.shape[:2]
        mask = np.zeros((height, width), dtype=np.bool_)
        mask[height // 4 : 3 * height // 4, width // 5 : 4 * width // 5] = True
        return (
            GarmentRegion(
                track_id=1,
                class_name="upper-clothes",
                mask=mask,
                mask_confidence=0.9,
            ),
        )


def _write_fixture(path: Path) -> None:
    writer = cv2.VideoWriter(
        str(path),
        cv2.VideoWriter_fourcc(*"MJPG"),
        12.0,
        (96, 64),
    )
    assert writer.isOpened()
    try:
        frame = np.full((64, 96, 3), 160, dtype=np.uint8)
        frame[16:48, 20:48] = (30, 30, 210)
        frame[16:48, 48:76] = (20, 130, 130)
        for _ in range(3):
            writer.write(frame)
    finally:
        writer.release()


def test_full_pipeline_exports_all_frozen_stages_without_pixels(tmp_path: Path) -> None:
    video_path = tmp_path / "instrumentation.avi"
    output_path = tmp_path / "stage-timing.json"
    _write_fixture(video_path)
    tracker = StageTimingTracker()
    source = open_video(video_path)
    pipeline = ChromaLensPipeline(
        InstrumentedMaskSegmenter(),
        stream_id=source.name,
        stage_timing=tracker,
    )

    result = run_pipeline_session(source, pipeline, display=False)
    _write_stage_metrics_json(
        output_path,
        result,
        display=False,
        warmup_seconds=0.0,
    )

    stages = {item.stage: item for item in result.stage_timings}
    assert set(stages) == set(StageTimingName)
    assert stages[StageTimingName.SEGMENTATION_INFERENCE].count == 3
    assert stages[StageTimingName.OPTICAL_FLOW].skipped_count == 3
    assert stages[StageTimingName.WHITE_BALANCE].count == 3
    assert stages[StageTimingName.COLOR_EXTRACTION].count == 3
    assert stages[StageTimingName.PRESENTATION].count == 3
    assert stages[StageTimingName.DISPLAY_SUBMIT].count == 0
    assert stages[StageTimingName.DISPLAY_SUBMIT].skipped_count == 3
    assert all(item.retained_samples <= 10_000 for item in stages.values())

    payload = json.loads(output_path.read_text(encoding="utf-8"))
    assert payload["format"] == "chromalens-t15-stage-timing-1.0"
    assert payload["privacy"] == {
        "frames_saved": 0,
        "frames_uploaded": 0,
        "contains_frame_pixels": False,
    }
    assert [item["stage"] for item in payload["stages"]] == [
        stage.value for stage in StageTimingName
    ]
    assert "sensor_to_photon_ms" not in output_path.read_text(encoding="utf-8") or (
        payload["latency_semantics"]["sensor_to_photon_ms"] == "NOT_MEASURED"
    )
