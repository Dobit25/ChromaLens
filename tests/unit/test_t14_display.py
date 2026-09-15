from __future__ import annotations

from unittest.mock import call, MagicMock, patch

import cv2
import numpy as np
import pytest

from chromalens.config import CVDProfile
from chromalens.display import (
    configure_process_dpi_awareness,
    OpenCVDisplayController,
    fit_presentation_to_display,
    recommended_windowed_size,
)
from chromalens.presentation import (
    PresentationData,
    PresentationMode,
    PresentationTheme,
    compose_presentation,
    layout_for_camera,
)


def _data() -> PresentationData:
    return PresentationData(
        source_name="synthetic:t14",
        profile=CVDProfile.DEUTAN,
        severity=1.0,
        recolor_enabled=True,
        view_name="assistive",
        original_color_label="Xám",
        original_color_rgb=(163, 168, 173),
        color_margin=0.294,
        risk_level="medium",
        lighting_level="good",
        matching_label="Trắng",
        matching_harmony="neutral",
        action_message="Đã tăng khả năng phân biệt màu.",
        diagnostic_lines=(
            "RGB=(163, 168, 173) | margin=0.294 | risk=medium 0.250",
            "backend=schp-atr/openvino/CPU | pipeline FPS=10.8",
            "SCHP FPS=1.5 | mask=propagated | keyframe=41 age=968ms",
            "sensor_to_photon_ms=NOT_MEASURED",
        ),
    )


@pytest.mark.parametrize(
    ("target_size", "mode", "theme"),
    [
        ((1366, 768), PresentationMode.PRODUCT, PresentationTheme.DARK),
        ((1366, 768), PresentationMode.DIAGNOSTIC, PresentationTheme.LIGHT),
        ((1920, 1080), PresentationMode.PRODUCT, PresentationTheme.LIGHT),
        ((1920, 1080), PresentationMode.DIAGNOSTIC, PresentationTheme.DARK),
    ],
)
def test_frozen_fullscreen_cases_preserve_viewport_and_processing_pixels(
    target_size: tuple[int, int],
    mode: PresentationMode,
    theme: PresentationTheme,
) -> None:
    camera = np.random.default_rng(14).integers(
        0, 256, size=(360, 640, 3), dtype=np.uint8
    )
    camera_before = camera.copy()
    presentation = compose_presentation(camera, _data(), mode=mode, theme=theme)
    presentation_before = presentation.copy()
    layout = layout_for_camera(640, 360)

    fitted = fit_presentation_to_display(presentation, target_size)
    mapped_camera = fitted.map_rect(layout.camera_rect)

    assert fitted.frame_bgr.shape == (target_size[1], target_size[0], 3)
    assert fitted.aspect_ratio_error(layout.camera_rect) <= 0.005
    assert np.array_equal(camera, camera_before)
    assert np.array_equal(presentation, presentation_before)
    assert camera.shape[:2] == (360, 640)
    assert not np.shares_memory(fitted.frame_bgr, presentation)
    assert 0 <= mapped_camera[0] < mapped_camera[2] <= target_size[0]
    assert 0 <= mapped_camera[1] < mapped_camera[3] <= target_size[1]


def test_aspect_fit_uses_letterbox_or_pillarbox_without_stretching() -> None:
    presentation = np.full((600, 1000, 3), 127, dtype=np.uint8)

    fitted = fit_presentation_to_display(presentation, (1366, 768))
    x0, y0, x1, y1 = fitted.content_rect

    assert fitted.scale_x == pytest.approx(fitted.scale_y, abs=0.001)
    assert x0 > 0 or y0 > 0 or x1 < 1366 or y1 < 768
    assert np.all(fitted.frame_bgr[:y0] == 0) if y0 else True
    assert np.all(fitted.frame_bgr[:, :x0] == 0) if x0 else True


def test_display_controller_toggles_existing_window_without_recreation() -> None:
    frame = np.zeros((480, 800, 3), dtype=np.uint8)
    controller = OpenCVDisplayController(
        "T14 test", fullscreen_size=(1366, 768), windowed_size=(800, 480)
    )

    with (
        patch("chromalens.display.cv2.imshow") as imshow,
        patch("chromalens.display.cv2.namedWindow") as named_window,
        patch("chromalens.display.cv2.resizeWindow") as resize_window,
        patch("chromalens.display.cv2.setWindowProperty") as set_property,
        patch(
            "chromalens.display.cv2.getWindowImageRect",
            return_value=(0, 0, 800, 480),
        ),
        patch("chromalens.display.cv2.destroyWindow") as destroy_window,
    ):
        controller.submit(controller.prepare(frame))
        assert controller.toggle_fullscreen()
        controller.submit(controller.prepare(frame))
        controller.set_fullscreen(False)
        controller.close()

    assert imshow.call_count == 2
    named_window.assert_called_once_with("T14 test", cv2.WINDOW_NORMAL)
    assert set_property.call_args_list == [
        call("T14 test", cv2.WND_PROP_FULLSCREEN, cv2.WINDOW_FULLSCREEN),
        call("T14 test", cv2.WND_PROP_FULLSCREEN, cv2.WINDOW_NORMAL),
    ]
    assert resize_window.call_args_list == [
        call("T14 test", 800, 480),
        call("T14 test", 800, 480),
    ]
    destroy_window.assert_called_once_with("T14 test")


def test_windowed_controller_tracks_native_client_resize() -> None:
    frame = np.zeros((480, 800, 3), dtype=np.uint8)
    controller = OpenCVDisplayController(
        "T14 resize", windowed_size=(800, 480)
    )

    with (
        patch("chromalens.display.cv2.namedWindow"),
        patch("chromalens.display.cv2.resizeWindow"),
        patch("chromalens.display.cv2.imshow"),
        patch(
            "chromalens.display.cv2.getWindowImageRect",
            return_value=(40, 60, 1024, 600),
        ),
    ):
        first = controller.prepare(frame)
        controller.submit(first)
        observed_size = controller.presentation_size
        native = np.zeros((600, 1024, 3), dtype=np.uint8)
        second = controller.prepare(native)

    assert first.target_size == (800, 480)
    assert observed_size == (1024, 600)
    assert second.frame_bgr is native
    assert second.target_size == (1024, 600)


@pytest.mark.parametrize(
    ("display_size", "expected"),
    [
        ((1920, 1080), (1366, 768)),
        ((1366, 768), (1161, 630)),
    ],
)
def test_recommended_window_size_is_bounded_to_physical_display(
    display_size: tuple[int, int], expected: tuple[int, int]
) -> None:
    with patch("chromalens.display.primary_display_size", return_value=display_size):
        assert recommended_windowed_size() == expected


def test_dpi_configuration_is_a_no_op_off_windows() -> None:
    configure_process_dpi_awareness.cache_clear()
    try:
        with patch("chromalens.display.sys.platform", "linux"):
            status = configure_process_dpi_awareness()
        assert not status.enabled
        assert status.mode == "not-applicable"
        assert status.error_code is None
    finally:
        configure_process_dpi_awareness.cache_clear()


def test_windows_dpi_configuration_prefers_per_monitor_v2() -> None:
    user32 = MagicMock()
    user32.SetProcessDpiAwarenessContext.return_value = 1
    configure_process_dpi_awareness.cache_clear()
    try:
        with (
            patch("chromalens.display.sys.platform", "win32"),
            patch(
                "chromalens.display.ctypes.WinDLL",
                return_value=user32,
                create=True,
            ),
            patch("chromalens.display.ctypes.set_last_error", create=True),
        ):
            status = configure_process_dpi_awareness()
        assert status.enabled
        assert status.mode == "per-monitor-v2"
        assert status.error_code is None
        user32.SetProcessDpiAwarenessContext.assert_called_once()
    finally:
        configure_process_dpi_awareness.cache_clear()


def test_windows_dpi_configuration_reports_unavailable_without_os_apis() -> None:
    configure_process_dpi_awareness.cache_clear()
    try:
        with (
            patch("chromalens.display.sys.platform", "win32"),
            patch(
                "chromalens.display.ctypes.WinDLL",
                side_effect=OSError("Windows DPI API unavailable"),
                create=True,
            ),
        ):
            status = configure_process_dpi_awareness()
        assert not status.enabled
        assert status.mode == "unavailable"
    finally:
        configure_process_dpi_awareness.cache_clear()


@pytest.mark.parametrize(
    ("frame", "target_size", "message"),
    [
        (np.zeros((10, 10), dtype=np.uint8), (100, 100), "shape HxWx3"),
        (np.zeros((10, 10, 3), dtype=np.float32), (100, 100), "shape HxWx3"),
        (np.zeros((10, 10, 3), dtype=np.uint8), (0, 100), "positive"),
    ],
)
def test_display_fit_rejects_invalid_contracts(
    frame: np.ndarray, target_size: tuple[int, int], message: str
) -> None:
    with pytest.raises(ValueError, match=message):
        fit_presentation_to_display(frame, target_size)
