from __future__ import annotations

from time import monotonic_ns

import numpy as np

from chromalens.camera import assess_camera_frame, prepare_analysis_packet
from chromalens.config import CVDProfile
from chromalens.contracts import FramePacket
from chromalens.display import fit_presentation_to_display
from chromalens.pipeline import ChromaLensPipeline, PipelineSettings
from chromalens.presentation import PresentationMode, PresentationTheme, compose_presentation
from chromalens.renderer import PipelineDisplayState, PipelineView, render_pipeline_camera_view
from chromalens.segmentation.base import Segmenter


class NoGarmentSegmenter(Segmenter):
    @property
    def backend_name(self) -> str:
        return "t14-no-garment"

    @property
    def device_info(self) -> str:
        return "t14-no-garment/cpu"

    def segment(self, packet: FramePacket):
        return ()


def _packet(frame: np.ndarray) -> FramePacket:
    return FramePacket(frame_id=17, timestamp_ns=monotonic_ns(), original_bgr=frame)


def test_uniform_black_camera_is_distinct_from_a_dark_detailed_scene() -> None:
    blocked = np.full((120, 160, 3), 16, dtype=np.uint8)
    detailed = blocked.copy()
    detailed[:, 80:] = 40

    assert assess_camera_frame(blocked).appears_blocked
    assert not assess_camera_frame(detailed).appears_blocked


def test_analysis_packet_preserves_identity_aspect_and_display_pixels() -> None:
    display = np.random.default_rng(14).integers(
        0, 256, size=(720, 1280, 3), dtype=np.uint8
    )
    display_before = display.copy()
    source = _packet(display)

    analysis = prepare_analysis_packet(
        source,
        maximum_width=480,
        maximum_height=360,
    )

    assert analysis.frame_id == source.frame_id
    assert analysis.timestamp_ns == source.timestamp_ns
    assert analysis.original_bgr.shape == (270, 480, 3)
    assert np.array_equal(source.original_bgr, display_before)
    assert not np.shares_memory(analysis.original_bgr, source.original_bgr)


def test_high_resolution_source_remains_the_original_product_view() -> None:
    display = np.random.default_rng(15).integers(
        0, 256, size=(720, 1280, 3), dtype=np.uint8
    )
    analysis_packet = prepare_analysis_packet(
        _packet(display),
        maximum_width=480,
        maximum_height=360,
    )
    result = ChromaLensPipeline(NoGarmentSegmenter(), stream_id="dual").process(
        analysis_packet,
        PipelineSettings(),
    )
    state = PipelineDisplayState(
        profile=CVDProfile.DEUTAN,
        severity=1.0,
        recolor_enabled=True,
        view=PipelineView.ORIGINAL,
    )

    rendered = render_pipeline_camera_view(
        result,
        display_state=state,
        display_source_bgr=display,
    )

    assert rendered.shape == display.shape
    assert np.array_equal(rendered, display)
    assert not np.shares_memory(rendered, display)


def test_product_shell_draws_natively_at_both_frozen_display_sizes() -> None:
    from chromalens.presentation import PresentationData

    camera = np.random.default_rng(16).integers(
        0, 256, size=(720, 1280, 3), dtype=np.uint8
    )
    data = PresentationData(
        source_name="synthetic:t14-native",
        profile=CVDProfile.DEUTAN,
        severity=1.0,
        recolor_enabled=True,
        view_name="original",
        original_color_label="Xám",
        original_color_rgb=(163, 168, 173),
        color_margin=0.294,
        risk_level="low",
        lighting_level="good",
        matching_label="Trắng",
        matching_harmony="neutral",
        action_message="Đưa trang phục vào giữa khung hình.",
        diagnostic_lines=(),
    )

    for target in ((1366, 768), (1920, 1080)):
        rendered = compose_presentation(
            camera,
            data,
            mode=PresentationMode.PRODUCT,
            theme=PresentationTheme.DARK,
            target_size=target,
        )
        assert rendered.shape == (target[1], target[0], 3)


def test_native_display_canvas_is_not_resampled_a_second_time() -> None:
    frame = np.random.default_rng(17).integers(
        0, 256, size=(768, 1366, 3), dtype=np.uint8
    )

    fitted = fit_presentation_to_display(frame, (1366, 768))

    assert fitted.frame_bgr is frame
    assert fitted.content_rect == (0, 0, 1366, 768)
    assert fitted.scale_x == fitted.scale_y == 1.0
