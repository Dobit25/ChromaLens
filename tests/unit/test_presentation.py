from __future__ import annotations

import numpy as np
import pytest
from PIL import Image

from chromalens.config import CVDProfile
from chromalens.presentation import (
    _CAMERA_BEZEL_LOGICAL_PX,
    _camera_shell_rect,
    _antialiased_rounded_patch,
    _draw_aa_rounded_rectangle,
    _antialiased_product_icon,
    _card_elevation_px,
    _highlight_rgb,
    PresentationData,
    PresentationMode,
    PresentationStyle,
    PresentationTheme,
    ProductPresentationState,
    ProductIcon,
    build_product_copy,
    compose_presentation,
    layout_for_camera,
    product_presentation_state,
    responsive_layout_for_display,
    style_for_theme,
    _product_card_rectangles,
    _product_card_regions,
    _product_sidebar_rect,
)


def test_rounded_rectangle_accepts_even_narrow_geometry() -> None:
    """Small responsive accents must not produce inverted native fill boxes."""

    image = Image.new("RGB", (24, 96), (0, 0, 0))

    _draw_aa_rounded_rectangle(
        image,
        (4, 3, 9, 92),
        radius=3,
        fill=(0, 126, 178),
        outline=(94, 231, 255),
        width=1,
    )

    assert image.getbbox() is not None


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
def test_presentation_clips_only_camera_corners_and_rim(
    resolution: tuple[int, int],
    mode: PresentationMode,
    theme: PresentationTheme,
) -> None:
    width, height = resolution
    rng = np.random.default_rng(width + height)
    camera = rng.integers(0, 256, size=(height, width, 3), dtype=np.uint8)
    snapshot = camera.copy()

    rendered = compose_presentation(camera, _data(), mode=mode, theme=theme)
    layout = layout_for_camera(width, height)
    x0, y0, x1, y1 = layout.camera_rect

    assert rendered.shape == (layout.canvas_height, layout.canvas_width, 3)
    content = rendered[y0:y1, x0:x1]
    radius = 18
    rim = 2
    antialias_extent = radius + rim + 1
    allowed = np.zeros((height, width), dtype=np.bool_)
    allowed[:rim, :] = True
    allowed[-rim:, :] = True
    allowed[:, :rim] = True
    allowed[:, -rim:] = True
    allowed[:antialias_extent, :antialias_extent] = True
    allowed[:antialias_extent, -antialias_extent:] = True
    allowed[-antialias_extent:, :antialias_extent] = True
    allowed[-antialias_extent:, -antialias_extent:] = True
    changed = np.any(content != camera, axis=2)

    assert np.array_equal(camera, snapshot)
    assert np.array_equal(
        content[radius:-radius, radius:-radius],
        camera[radius:-radius, radius:-radius],
    )
    assert np.any(changed)
    assert not np.any(changed & ~allowed)
    assert not np.array_equal(content[0, 0], camera[0, 0])
    assert not np.shares_memory(rendered, camera)


def test_layout_preserves_aspect_ratio_by_using_exact_camera_dimensions() -> None:
    layout = layout_for_camera(640, 360)
    x0, y0, x1, y1 = layout.camera_rect
    panel_x0, panel_y0, panel_x1, panel_y1 = layout.panel_rect

    assert (x1 - x0, y1 - y0) == (640, 360)
    assert panel_x0 > x1
    assert panel_y0 == y0
    assert layout.footer_rect[1] >= max(y1, panel_y1)


def test_camera_outer_shell_uses_the_frozen_wider_frame() -> None:
    camera = np.full((240, 320, 3), 127, dtype=np.uint8)
    style = PresentationStyle()
    rendered = compose_presentation(camera, _data(), style=style)
    layout = layout_for_camera(320, 240, style=style)
    x0, y0, _, y1 = layout.camera_rect
    middle_y = (y0 + y1) // 2

    assert _CAMERA_BEZEL_LOGICAL_PX == 7
    assert np.all(
        rendered[middle_y, x0 - _CAMERA_BEZEL_LOGICAL_PX + 1 : x0]
        == np.asarray(style.camera_shell_bgr, dtype=np.uint8)
    )
    assert np.array_equal(
        rendered[middle_y, x0 - _CAMERA_BEZEL_LOGICAL_PX - 1],
        np.asarray(style.background_bgr, dtype=np.uint8),
    )


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
    ("overrides", "expected"),
    [
        ({"camera_input_issue": "blocked_or_black"}, ProductPresentationState.CAMERA_BLOCKED),
        (
            {"original_color_label": None, "original_color_rgb": None},
            ProductPresentationState.WAITING_FOR_GARMENT,
        ),
        (
            {
                "original_color_label": None,
                "original_color_rgb": None,
                "garment_detected": True,
            },
            ProductPresentationState.ANALYZING,
        ),
        ({}, ProductPresentationState.RESULT_READY),
    ],
)
def test_product_state_machine_has_one_deterministic_state(
    overrides: dict[str, object], expected: ProductPresentationState
) -> None:
    assert product_presentation_state(_data(**overrides)) is expected


def test_blocked_camera_never_reports_a_lighting_measurement() -> None:
    copy = build_product_copy(_data(camera_input_issue="blocked_or_black"))

    assert copy["lighting"] == "Chưa thể đo ánh sáng"
    assert "công tắc" in copy["action"] and "camera" in copy["action"]
    assert "Nên tăng" not in " ".join(copy.values())


def test_waiting_state_uses_causal_copy_and_a_temporary_camera_guide() -> None:
    camera = np.full((360, 640, 3), 96, dtype=np.uint8)
    snapshot = camera.copy()
    waiting = _data(original_color_label=None, original_color_rgb=None)
    rendered = compose_presentation(camera, waiting, mode=PresentationMode.PRODUCT)
    layout = layout_for_camera(640, 360)
    x0, y0, x1, y1 = layout.camera_rect

    copy = build_product_copy(waiting)
    assert copy["color"] == "Đang chờ trang phục"
    assert "Đang chờ" in copy["risk"]
    assert "sau khi" in copy["guidance"]
    assert not np.array_equal(rendered[y0:y1, x0:x1], camera)
    assert np.array_equal(camera, snapshot)


@pytest.mark.parametrize("target", [(1366, 768), (1920, 1080)])
def test_responsive_desktop_layout_bounds_sidebar_in_final_pixels(
    target: tuple[int, int],
) -> None:
    _, layout = responsive_layout_for_display((1280, 720), target)
    camera_x0, camera_y0, camera_x1, camera_y1 = layout.camera_rect
    panel_x0, panel_y0, panel_x1, panel_y1 = layout.panel_rect

    assert 300 <= panel_x1 - panel_x0 <= 430
    assert layout.canvas_width <= target[0]
    assert layout.canvas_height == target[1]
    assert panel_x0 > camera_x1
    assert panel_y0 == camera_y0
    assert abs(((camera_x1 - camera_x0) / (camera_y1 - camera_y0)) / (16 / 9) - 1) <= 0.005


@pytest.mark.parametrize("target", [(1366, 768), (1920, 1080)])
@pytest.mark.parametrize("theme", list(PresentationTheme))
def test_product_sidebar_and_cards_share_outer_camera_vertical_bounds(
    target: tuple[int, int],
    theme: PresentationTheme,
) -> None:
    style, layout = responsive_layout_for_display(
        (1280, 720), target, style=style_for_theme(theme)
    )
    camera_shell = _camera_shell_rect(layout, style)
    sidebar = _product_sidebar_rect(layout, style)
    cards = _product_card_rectangles(layout, style)

    assert sidebar[1] == camera_shell[1]
    assert sidebar[3] == camera_shell[3]
    assert cards[0][1] == camera_shell[1]
    assert cards[-1][3] == camera_shell[3]
    assert cards[0][3] - cards[0][1] > cards[-1][3] - cards[-1][1]
    assert [lower[1] - upper[3] for upper, lower in zip(cards, cards[1:])] == [
        max(10, round(10 * style.ui_scale))
    ] * 3


@pytest.mark.parametrize("resolution", [(320, 240), (640, 360)])
def test_short_source_canvas_keeps_readable_product_panel_fallback(
    resolution: tuple[int, int],
) -> None:
    width, height = resolution
    style = PresentationStyle()
    layout = layout_for_camera(width, height, style=style)
    cards = _product_card_rectangles(layout, style)

    assert _product_sidebar_rect(layout, style) == layout.panel_rect
    assert cards[0][1] > layout.panel_rect[1]
    assert cards[-1][3] < layout.panel_rect[3]
    assert min(y1 - y0 for _, y0, _, y1 in cards) >= 98


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
        assert (y1 - y0) - regions.detail[3] >= 12
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
    expected_gap_color = np.asarray(PresentationStyle().tray_bgr, dtype=np.uint8)
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


def test_theme_tokens_preserve_component_depth_and_readability_parity() -> None:
    dark = style_for_theme(PresentationTheme.DARK)
    light = style_for_theme(PresentationTheme.LIGHT)
    geometry = (
        "outer_padding_px",
        "content_gap_px",
        "header_height_px",
        "footer_height_px",
        "minimum_panel_width_px",
        "maximum_panel_width_px",
    )

    assert tuple(getattr(dark, name) for name in geometry) == tuple(
        getattr(light, name) for name in geometry
    )
    shell_contrasts: list[float] = []
    for style in (dark, light):
        shell_contrasts.append(
            _contrast_ratio(style.camera_shell_bgr, style.background_bgr)
        )
        assert 1.0 < _contrast_ratio(style.tray_bgr, style.background_bgr) <= 1.10
        assert _contrast_ratio(style.camera_shell_bgr, style.background_bgr) >= 1.30
        assert _contrast_ratio(style.camera_rim_bgr, style.camera_shell_bgr) >= 2.50
        assert _contrast_ratio(style.divider_bgr, style.surface_bgr) >= 1.15
        assert _contrast_ratio(style.card_bgr, style.muted_text_bgr) >= 4.50
        assert _contrast_ratio(style.primary_card_bgr, style.muted_text_bgr) >= 4.50
        assert _contrast_ratio(style.control_bgr, style.text_bgr) >= 7.00
        assert _contrast_ratio(style.primary_card_bgr, style.card_bgr) >= 1.20
        for surface, accent in (
            (style.primary_card_bgr, style.card_info_bgr),
            (style.card_bgr, style.card_recommendation_bgr),
            (style.card_bgr, style.card_success_bgr),
            (style.card_bgr, style.card_warning_bgr),
        ):
            assert _contrast_ratio(surface, accent) >= 3.00
    assert abs(shell_contrasts[0] - shell_contrasts[1]) <= 0.10


def test_every_product_icon_has_visible_cached_antialiased_pixels() -> None:
    for icon in ProductIcon:
        first = _antialiased_product_icon(icon, 6, 2, (30, 90, 180))
        second = _antialiased_product_icon(icon, 6, 2, (30, 90, 180))
        alpha = np.asarray(first)[:, :, 3]

        assert first is second
        assert np.any(alpha > 0)
        assert np.any((alpha > 0) & (alpha < 255))


def test_product_elevation_tiers_are_explicit_and_ordered() -> None:
    style = PresentationStyle().scaled(1.5)

    depths = [
        _card_elevation_px(emphasis, style)
        for emphasis in ("primary", "warning", "normal", "inactive")
    ]

    assert depths == [3, 2, 2, 0]
    with pytest.raises(ValueError, match="unsupported Product card emphasis"):
        _card_elevation_px("clickable", style)


def test_material_highlight_moves_each_channel_toward_white() -> None:
    surface = (30, 90, 180)

    highlighted = _highlight_rgb(surface, 0.2)

    assert all(source < lifted <= 255 for source, lifted in zip(surface, highlighted))
    assert _highlight_rgb(surface, 0.0) == surface
    assert _highlight_rgb(surface, 2.0) == (255, 255, 255)


@pytest.mark.parametrize(
    ("theme", "cover_bgr", "text_bgr"),
    [
        (PresentationTheme.DARK, (250, 247, 245), (28, 22, 16)),
        (PresentationTheme.LIGHT, (20, 16, 11), (250, 247, 245)),
    ],
)
def test_camera_cover_is_theme_inverted_and_hides_only_displayed_viewport(
    theme: PresentationTheme,
    cover_bgr: tuple[int, int, int],
    text_bgr: tuple[int, int, int],
) -> None:
    rng = np.random.default_rng(2026)
    camera = rng.integers(0, 256, size=(240, 320, 3), dtype=np.uint8)
    snapshot = camera.copy()

    rendered = compose_presentation(
        camera,
        _data(),
        theme=theme,
        camera_cover_enabled=True,
    )
    layout = layout_for_camera(320, 240)
    x0, y0, x1, y1 = layout.camera_rect
    covered = rendered[y0:y1, x0:x1]
    cover_color = np.asarray(cover_bgr, dtype=np.uint8)
    background_fraction = float(np.mean(np.all(covered == cover_color, axis=2)))

    assert np.array_equal(camera, snapshot)
    assert not np.array_equal(covered, camera)
    assert background_fraction > 0.90
    assert _contrast_ratio(cover_bgr, text_bgr) >= 7.0


def test_camera_and_privacy_cover_share_the_same_rounded_boundary() -> None:
    camera = np.full((240, 320, 3), (40, 90, 180), dtype=np.uint8)
    visible = compose_presentation(camera, _data(), camera_cover_enabled=False)
    covered = compose_presentation(camera, _data(), camera_cover_enabled=True)
    layout = layout_for_camera(320, 240)
    x0, y0, x1, y1 = layout.camera_rect
    visible_content = visible[y0:y1, x0:x1]
    covered_content = covered[y0:y1, x0:x1]

    for y, x in ((0, 0), (0, -1), (-1, 0), (-1, -1)):
        assert np.array_equal(visible_content[y, x], covered_content[y, x])
    assert not np.array_equal(
        visible_content[30:-30, 30:-30],
        covered_content[30:-30, 30:-30],
    )


def test_camera_cover_rejects_non_boolean_state() -> None:
    with pytest.raises(TypeError, match="camera_cover_enabled"):
        compose_presentation(
            np.zeros((120, 160, 3), dtype=np.uint8),
            _data(),
            camera_cover_enabled=1,
        )


def test_rounded_chrome_is_supersampled_and_cached() -> None:
    first = _antialiased_rounded_patch(
        180,
        90,
        18,
        (32, 40, 48),
        (94, 231, 255),
        2,
    )
    second = _antialiased_rounded_patch(
        180,
        90,
        18,
        (32, 40, 48),
        (94, 231, 255),
        2,
    )
    alpha = np.asarray(first)[:, :, 3]

    assert first is second
    assert np.any((alpha > 0) & (alpha < 255))
