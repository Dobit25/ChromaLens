from __future__ import annotations

from unittest.mock import call, patch

import cv2
import numpy as np
import pytest

from chromalens.config import CVDProfile
from chromalens.display import (
    OpenCVDisplayController,
    fit_presentation_to_display,
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
        "T14 test", fullscreen_size=(1366, 768)
    )

    with (
        patch("chromalens.display.cv2.imshow") as imshow,
        patch("chromalens.display.cv2.namedWindow") as named_window,
        patch("chromalens.display.cv2.setWindowProperty") as set_property,
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
    destroy_window.assert_called_once_with("T14 test")


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
