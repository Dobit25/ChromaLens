"""Camera-, network-, and model-independent integration tests for T08."""

from __future__ import annotations

from dataclasses import replace
from pathlib import Path
from time import monotonic_ns
from unittest.mock import patch

import cv2
import numpy as np
import pytest

from chromalens.app import RuntimeControls, build_parser, run_pipeline_session
from chromalens.camera import open_video
from chromalens.config import CVDProfile
from chromalens.contracts import FramePacket, GarmentRegion
from chromalens.pipeline import (
    ChromaLensPipeline,
    PipelineSettings,
    PipelineStage,
    StageStatus,
)
from chromalens.renderer import (
    PipelineDisplayState,
    PipelineView,
    PreviewMetricsTracker,
    render_pipeline_view,
)
from chromalens.segmentation.base import Segmenter


class MaskSegmenter(Segmenter):
    def __init__(self, *, empty_after: int | None = None) -> None:
        self.empty_after = empty_after
        self.calls = 0
        self.closed = False

    @property
    def backend_name(self) -> str:
        return "test-mask"

    @property
    def device_info(self) -> str:
        return "test-mask/cpu"

    def segment(self, packet: FramePacket) -> tuple[GarmentRegion, ...]:
        self.calls += 1
        if self.empty_after is not None and self.calls > self.empty_after:
            return ()
        height, width = packet.original_bgr.shape[:2]
        mask = np.zeros((height, width), dtype=np.bool_)
        mask[height // 4 : 3 * height // 4, width // 5 : 4 * width // 5] = True
        return (
            GarmentRegion(
                track_id=1,
                class_name="upper-clothes",
                mask=mask,
                mask_confidence=0.82,
            ),
        )

    def close(self) -> None:
        self.closed = True


class FailingSegmenter(MaskSegmenter):
    def segment(self, packet: FramePacket) -> tuple[GarmentRegion, ...]:
        raise RuntimeError("controlled segmentation failure")


def _packet(frame_id: int = 0) -> FramePacket:
    height, width = 160, 240
    frame = np.full((height, width, 3), 128, dtype=np.uint8)
    y0, y1 = height // 4, 3 * height // 4
    x0, x1 = width // 5, 4 * width // 5
    split = x0 + round((x1 - x0) * 0.62)
    frame[y0:y1, x0:split] = (30, 30, 210)  # RGB (210, 30, 30)
    frame[y0:y1, split:x1] = (20, 130, 130)  # RGB (130, 130, 20)
    return FramePacket(
        frame_id=frame_id,
        timestamp_ns=monotonic_ns(),
        original_bgr=frame,
    )


def _write_video(path: Path, *, frame_count: int = 3) -> None:
    writer = cv2.VideoWriter(
        str(path), cv2.VideoWriter_fourcc(*"MJPG"), 12.0, (240, 160)
    )
    assert writer.isOpened()
    try:
        for frame_id in range(frame_count):
            writer.write(_packet(frame_id).original_bgr)
    finally:
        writer.release()


def test_full_pipeline_preserves_original_and_keeps_recolor_inside_mask() -> None:
    packet = _packet()
    original_before = packet.original_bgr.copy()
    pipeline = ChromaLensPipeline(MaskSegmenter(), stream_id="test")

    result = pipeline.process(
        packet,
        PipelineSettings(profile=CVDProfile.DEUTAN, severity=1.0),
    )

    assert result.analysis_frame_id == packet.frame_id
    assert result.primary_region is not None
    assert len(result.clusters) == 2
    assert result.risk is not None and result.risk.risk_level in {"medium", "high"}
    assert result.recolor is not None and result.recolor.debug.applied
    assert np.any(result.risk_mask)
    assert np.array_equal(packet.original_bgr, original_before)
    outside = ~result.primary_region.mask
    assert np.array_equal(result.assistive_bgr[outside], original_before[outside])
    assert result.matching is not None
    assert result.matching.source_original_name == result.primary_cluster.original_name
    assert [report.stage for report in result.stage_reports] == list(PipelineStage)


def test_all_views_render_current_frame_on_copies() -> None:
    result = ChromaLensPipeline(MaskSegmenter(), stream_id="views").process(
        _packet(4), PipelineSettings()
    )
    telemetry = PreviewMetricsTracker().observe(
        result.packet, observed_ns=monotonic_ns()
    )

    for view in PipelineView:
        rendered = render_pipeline_view(
            result,
            source_name="test:views",
            telemetry=telemetry,
            display_state=PipelineDisplayState(
                profile=CVDProfile.DEUTAN,
                severity=1.0,
                recolor_enabled=True,
                view=view,
                dropped_capture_frames=2,
            ),
        )
        assert rendered.shape == result.packet.original_bgr.shape
        assert rendered.dtype == np.uint8
        assert not np.shares_memory(rendered, result.packet.original_bgr)


def test_default_assistive_view_receives_separate_mask_confidence() -> None:
    result = ChromaLensPipeline(MaskSegmenter(), stream_id="scores").process(
        _packet(), PipelineSettings()
    )
    telemetry = PreviewMetricsTracker().observe(
        result.packet, observed_ns=monotonic_ns()
    )
    state = PipelineDisplayState(
        profile=CVDProfile.DEUTAN,
        severity=1.0,
        recolor_enabled=True,
        view=PipelineView.ASSISTIVE,
    )

    with patch("chromalens.renderer.render_assistive_overlay") as renderer:
        renderer.return_value = result.assistive_bgr
        render_pipeline_view(
            result,
            source_name="test:scores",
            telemetry=telemetry,
            display_state=state,
        )

    overlay_data = renderer.call_args.args[2]
    assert overlay_data.mask_confidence == pytest.approx(0.82)
    assert overlay_data.degraded_reason is None


def test_disabled_recolor_is_explicit_and_leaves_analytical_result_original() -> None:
    result = ChromaLensPipeline(MaskSegmenter(), stream_id="disabled").process(
        _packet(), PipelineSettings(recolor_enabled=False)
    )

    recolor_report = next(
        report for report in result.stage_reports if report.stage is PipelineStage.RECOLOR
    )
    assert recolor_report.status is StageStatus.SKIPPED
    assert "disabled by user" in recolor_report.message
    assert result.recolor is None
    assert np.array_equal(result.assistive_bgr, result.packet.original_bgr)


def test_missing_current_mask_never_reuses_previous_analysis() -> None:
    pipeline = ChromaLensPipeline(
        MaskSegmenter(empty_after=1), stream_id="no-stale"
    )
    first = pipeline.process(_packet(0), PipelineSettings())
    second = pipeline.process(_packet(1), PipelineSettings())

    assert first.primary_region is not None
    assert second.analysis_frame_id == 1
    assert second.regions == ()
    assert second.primary_region is None
    assert second.clusters == ()
    assert second.risk is None
    assert second.recolor is None
    assert not np.any(second.risk_mask)
    assert second.degraded
    assert "prior masks cleared" in second.degraded_reasons[0]
    with pytest.raises(ValueError, match="stale analysis"):
        replace(second, analysis_frame_id=0)


def test_backend_failure_is_visible_on_the_current_frame() -> None:
    result = ChromaLensPipeline(FailingSegmenter(), stream_id="failure").process(
        _packet(), PipelineSettings()
    )

    segmentation = result.stage_reports[0]
    assert segmentation.stage is PipelineStage.SEGMENTATION
    assert segmentation.status is StageStatus.UNAVAILABLE
    assert "controlled segmentation failure" in segmentation.message
    assert result.primary_region is None
    assert result.degraded


def test_runtime_controls_are_reversible_and_create_snapshots() -> None:
    controls = RuntimeControls()

    assert controls.apply_key(ord("p"))
    assert controls.profile is CVDProfile.TRITAN
    assert controls.apply_key(ord("["))
    assert controls.severity == pytest.approx(0.9)
    assert controls.apply_key(ord("r"))
    assert not controls.settings.recolor_enabled
    assert controls.apply_key(ord("5"))
    assert controls.view is PipelineView.DIAGNOSTIC
    assert not controls.apply_key(ord("x"))


def test_cli_rejects_non_finite_duration_and_severity() -> None:
    parser = build_parser()

    with pytest.raises(SystemExit):
        parser.parse_args(["--webcam", "--duration-seconds", "nan"])
    with pytest.raises(SystemExit):
        parser.parse_args(["--webcam", "--severity", "nan"])


def test_local_video_runs_the_same_pipeline_to_clean_eof(tmp_path: Path) -> None:
    video_path = tmp_path / "t08.avi"
    _write_video(video_path, frame_count=3)
    source = open_video(video_path)
    segmenter = MaskSegmenter()
    pipeline = ChromaLensPipeline(segmenter, stream_id=source.name)

    session = run_pipeline_session(source, pipeline, display=False)

    assert session.frames_processed == 3
    assert session.stop_reason == "end_of_video"
    assert session.metrics.total_frames == 3
    assert session.metrics.retained_latency_samples == 3
    assert segmenter.calls == 3
    assert segmenter.closed
