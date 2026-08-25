from __future__ import annotations

import numpy as np
import pytest

from chromalens.config import CVDProfile
from chromalens.presentation import (
    PresentationData,
    PresentationMode,
    PresentationStyle,
    PresentationTheme,
    build_product_copy,
    compose_presentation,
    layout_for_camera,
    style_for_theme,
    _product_card_rectangles,
    _product_card_regions,
)


def _data(**overrides: object) -> PresentationData:
    values: dict[str, object] = {
        "source_name": "webcam:0",
        "profile": CVDProfile.DEUTAN,
        "severity": 1.0,
        "recolor_enabled": True,
        "view_name": "assistive",
        "original_color_label": "Xám",
        "original_color_rgb": (163, 168, 173),
        "color_margin": 0.294,
        "risk_level": "medium",
        "lighting_level": "good",
        "matching_label": "Trắng",
        "matching_harmony": "neutral",
        "action_message": "Đã tăng khả năng phân biệt màu.",
        "diagnostic_lines": (
            "RGB=(163, 168, 173) | margin=0.294 | risk=medium 0.250",
            "backend=schp-atr/openvino/CPU | pipeline FPS=10.8",
            "SCHP FPS=1.5 | mask=propagated | keyframe=41 age=968ms",
            "sensor_to_photon_ms=NOT_MEASURED",
        ),
    }
    values.update(overrides)
    return PresentationData(**values)


@pytest.mark.parametrize("resolution", [(320, 240), (640, 360), (640, 480)])
@pytest.mark.parametrize("mode", list(PresentationMode))
@pytest.mark.parametrize("theme", list(PresentationTheme))
def test_presentation_never_overwrites_camera_viewport(
    resolution: tuple[int, int],
    mode: PresentationMode,
    theme: PresentationTheme,
) -> None:
    width, height = resolution
    rng = np.random.default_rng(width + height)
    camera = rng.integers(0, 256, size=(height, width, 3), dtype=np.uint8)

    rendered = compose_presentation(camera, _data(), mode=mode, theme=theme)
    layout = layout_for_camera(width, height)
    x0, y0, x1, y1 = layout.camera_rect

    assert rendered.shape == (layout.canvas_height, layout.canvas_width, 3)
    assert np.array_equal(rendered[y0:y1, x0:x1], camera)
    assert not np.shares_memory(rendered, camera)


def test_layout_preserves_aspect_ratio_by_using_exact_camera_dimensions() -> None:
    layout = layout_for_camera(640, 360)
    x0, y0, x1, y1 = layout.camera_rect
    panel_x0, panel_y0, panel_x1, panel_y1 = layout.panel_rect

    assert (x1 - x0, y1 - y0) == (640, 360)
    assert panel_x0 > x1
    assert panel_y0 == y0
    assert layout.footer_rect[1] >= max(y1, panel_y1)


def test_product_copy_is_unicode_actionable_and_hides_technical_values() -> None:
    copy = build_product_copy(_data())
    combined = " ".join(copy.values())

    assert copy["color"] == "Xám"
    assert copy["risk"] == "Có thể khó phân biệt"
    assert copy["lighting"] == "Ánh sáng tốt"
    assert copy["guidance"] == "Phối với Trắng · trung tính"
    assert "Độ chắc chắn: Vừa" == copy["confidence"]
    for forbidden in (
        "RGB=",
        "margin=",
        "backend",
        "FPS",
        "keyframe",
        "0.250",
        "frame",
    ):
        assert forbidden not in combined


@pytest.mark.parametrize(
    ("risk_level", "expected"),
    [
        ("low", "Không phát hiện xung đột đáng kể"),
        ("medium", "Có thể khó phân biệt"),
        ("high", "Khó phân biệt màu"),
        (None, "Chưa đủ màu để so sánh"),
    ],
)
def test_product_risk_status_always_has_text(
    risk_level: str | None,
    expected: str,
) -> None:
    assert build_product_copy(_data(risk_level=risk_level))["risk"] == expected


def test_long_content_is_bounded_and_renders_in_both_modes() -> None:
    long_text = "Trang phục có mô tả rất dài " * 25
    data = _data(
        matching_label=long_text,
        action_message=long_text,
        diagnostic_lines=(long_text,) * 20,
    )
    frame = np.full((240, 320, 3), 127, dtype=np.uint8)

    for mode in PresentationMode:
        rendered = compose_presentation(frame, data, mode=mode)
        assert rendered.dtype == np.uint8
        assert rendered.size > frame.size


@pytest.mark.parametrize("resolution", [(320, 240), (640, 360), (640, 480)])
def test_product_card_text_regions_are_disjoint_and_clipped(
    resolution: tuple[int, int],
) -> None:
    width, height = resolution
    layout = layout_for_camera(width, height)
    cards = _product_card_rectangles(layout)

    assert len(cards) == 4
    for index, rect in enumerate(cards):
        x0, y0, x1, y1 = rect
        regions = _product_card_regions(
            x1 - x0, y1 - y0, has_swatch=index == 0
        )
        assert regions.title[3] < regions.value[1]
        assert regions.value[3] < regions.detail[1]
        for region in (regions.title, regions.value, regions.detail):
            assert 0 <= region[0] < region[2] <= x1 - x0
            assert 0 <= region[1] < region[3] <= y1 - y0

    long_text = "Ná»™i dung ráº¥t dÃ i cáº§n xuá»‘ng dÃ²ng " * 30
    rendered = compose_presentation(
        np.zeros((height, width, 3), dtype=np.uint8),
        _data(
            original_color_label=long_text,
            matching_label=long_text,
            diagnostic_lines=(long_text,),
        ),
        mode=PresentationMode.PRODUCT,
    )
    expected_gap_color = np.asarray(PresentationStyle().surface_bgr, dtype=np.uint8)
    for upper, lower in zip(cards, cards[1:]):
        gap = rendered[upper[3] : lower[1], upper[0] : upper[2]]
        assert gap.size > 0
        assert np.all(gap == expected_gap_color)


def test_style_validates_confidence_threshold_order() -> None:
    with pytest.raises(ValueError, match="color margin thresholds"):
        PresentationStyle(color_margin_medium=0.8, color_margin_high=0.2)


def _relative_luminance(color_bgr: tuple[int, int, int]) -> float:
    channels = [channel / 255.0 for channel in reversed(color_bgr)]
    linear = [
        channel / 12.92
        if channel <= 0.04045
        else ((channel + 0.055) / 1.055) ** 2.4
        for channel in channels
    ]
    return 0.2126 * linear[0] + 0.7152 * linear[1] + 0.0722 * linear[2]


def _contrast_ratio(
    first_bgr: tuple[int, int, int], second_bgr: tuple[int, int, int]
) -> float:
    first = _relative_luminance(first_bgr)
    second = _relative_luminance(second_bgr)
    lighter, darker = max(first, second), min(first, second)
    return (lighter + 0.05) / (darker + 0.05)


@pytest.mark.parametrize("theme", list(PresentationTheme))
def test_theme_palettes_invert_cards_with_strong_text_contrast(
    theme: PresentationTheme,
) -> None:
    style = style_for_theme(theme)

    assert _contrast_ratio(style.background_bgr, style.card_bgr) >= 7.0
    assert _contrast_ratio(style.card_bgr, style.text_bgr) >= 7.0
    assert _contrast_ratio(style.surface_bgr, style.chrome_text_bgr) >= 7.0
    if theme is PresentationTheme.DARK:
        assert _relative_luminance(style.card_bgr) > _relative_luminance(
            style.background_bgr
        )
    else:
        assert _relative_luminance(style.card_bgr) < _relative_luminance(
            style.background_bgr
        )
