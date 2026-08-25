"""Two-mode OpenCV presentation shell with an unobscured camera viewport."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from functools import lru_cache
from pathlib import Path

import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont

from chromalens.color_naming import RGBColor
from chromalens.config import CVDProfile
from chromalens.contracts import ColorFrame


class PresentationMode(str, Enum):
    """User-facing product shell or evidence-focused diagnostic shell."""

    PRODUCT = "product"
    DIAGNOSTIC = "diagnostic"


class PresentationTheme(str, Enum):
    """User-selected high-contrast presentation palette."""

    DARK = "dark"
    LIGHT = "light"


@dataclass(frozen=True, slots=True)
class PresentationStyle:
    """Validated layout and accessible color hierarchy for the app shell."""

    outer_padding_px: int = 18
    content_gap_px: int = 16
    header_height_px: int = 66
    footer_height_px: int = 66
    minimum_panel_width_px: int = 300
    maximum_panel_width_px: int = 380
    minimum_content_height_px: int = 480
    color_margin_medium: float = 0.15
    color_margin_high: float = 0.35
    background_bgr: tuple[int, int, int] = (20, 16, 11)
    surface_bgr: tuple[int, int, int] = (34, 28, 21)
    card_bgr: tuple[int, int, int] = (236, 232, 228)
    primary_card_bgr: tuple[int, int, int] = (250, 247, 245)
    border_bgr: tuple[int, int, int] = (217, 210, 202)
    primary_bgr: tuple[int, int, int] = (255, 231, 94)
    violet_bgr: tuple[int, int, int] = (255, 124, 139)
    success_bgr: tuple[int, int, int] = (164, 229, 82)
    warning_bgr: tuple[int, int, int] = (87, 200, 255)
    text_bgr: tuple[int, int, int] = (28, 22, 16)
    muted_text_bgr: tuple[int, int, int] = (107, 96, 83)
    chrome_text_bgr: tuple[int, int, int] = (250, 247, 245)
    chrome_muted_text_bgr: tuple[int, int, int] = (175, 164, 154)

    def __post_init__(self) -> None:
        for field_name in (
            "outer_padding_px",
            "content_gap_px",
            "header_height_px",
            "footer_height_px",
            "minimum_panel_width_px",
            "maximum_panel_width_px",
            "minimum_content_height_px",
        ):
            if getattr(self, field_name) <= 0:
                raise ValueError(f"{field_name} must be positive")
        if self.minimum_panel_width_px > self.maximum_panel_width_px:
            raise ValueError("minimum panel width must not exceed maximum")
        if not 0.0 <= self.color_margin_medium < self.color_margin_high <= 1.0:
            raise ValueError("color margin thresholds must satisfy 0 <= medium < high <= 1")


def style_for_theme(theme: PresentationTheme) -> PresentationStyle:
    """Return the frozen palette for a user-selected light or dark shell."""

    if not isinstance(theme, PresentationTheme):
        raise TypeError("theme must be a PresentationTheme")
    if theme is PresentationTheme.DARK:
        return PresentationStyle()
    return PresentationStyle(
        background_bgr=(248, 246, 244),
        surface_bgr=(255, 255, 255),
        card_bgr=(68, 58, 48),
        primary_card_bgr=(61, 50, 37),
        border_bgr=(109, 96, 82),
        primary_bgr=(158, 127, 0),
        violet_bgr=(164, 80, 103),
        success_bgr=(90, 135, 0),
        warning_bgr=(0, 106, 180),
        text_bgr=(250, 247, 245),
        muted_text_bgr=(204, 194, 184),
        chrome_text_bgr=(28, 22, 16),
        chrome_muted_text_bgr=(118, 107, 95),
    )


@dataclass(frozen=True, slots=True)
class PresentationLayout:
    """Exact canvas rectangles; coordinates use exclusive right/bottom edges."""

    canvas_width: int
    canvas_height: int
    header_rect: tuple[int, int, int, int]
    camera_rect: tuple[int, int, int, int]
    panel_rect: tuple[int, int, int, int]
    footer_rect: tuple[int, int, int, int]


@dataclass(frozen=True, slots=True)
class PresentationData:
    """Presentation-only view model derived from one current pipeline result."""

    source_name: str
    profile: CVDProfile
    severity: float
    recolor_enabled: bool
    view_name: str
    original_color_label: str | None
    original_color_rgb: RGBColor | None
    color_margin: float | None
    risk_level: str | None
    lighting_level: str | None
    matching_label: str | None
    matching_harmony: str | None
    action_message: str
    diagnostic_lines: tuple[str, ...]

    def __post_init__(self) -> None:
        if not self.source_name.strip() or not self.view_name.strip():
            raise ValueError("source_name and view_name must not be empty")
        if not isinstance(self.profile, CVDProfile):
            raise TypeError("profile must be a CVDProfile")
        if not np.isfinite(self.severity) or not 0.0 <= self.severity <= 1.0:
            raise ValueError("severity must be finite within [0, 1]")
        if self.color_margin is not None and (
            not np.isfinite(self.color_margin) or not 0.0 <= self.color_margin <= 1.0
        ):
            raise ValueError("color_margin must be finite within [0, 1]")
        if not self.action_message.strip():
            raise ValueError("action_message must not be empty")


@dataclass(frozen=True, slots=True)
class ProductCardRegions:
    """Non-overlapping card-local rectangles reserved for each text role."""

    title: tuple[int, int, int, int]
    value: tuple[int, int, int, int]
    detail: tuple[int, int, int, int]
    swatch: tuple[int, int, int, int] | None


def layout_for_camera(
    width: int,
    height: int,
    *,
    style: PresentationStyle | None = None,
) -> PresentationLayout:
    """Return a layout that preserves the camera frame at its exact size."""

    if width <= 0 or height <= 0:
        raise ValueError("camera dimensions must be positive")
    active = style or PresentationStyle()
    panel_width = int(
        np.clip(
            round(width * 0.52),
            active.minimum_panel_width_px,
            active.maximum_panel_width_px,
        )
    )
    content_height = max(height, active.minimum_content_height_px)
    canvas_width = (
        active.outer_padding_px * 2
        + width
        + active.content_gap_px
        + panel_width
    )
    canvas_height = (
        active.header_height_px
        + active.outer_padding_px * 2
        + content_height
        + active.footer_height_px
    )
    camera_x0 = active.outer_padding_px
    camera_y0 = active.header_height_px + active.outer_padding_px
    panel_x0 = camera_x0 + width + active.content_gap_px
    footer_y0 = canvas_height - active.footer_height_px
    return PresentationLayout(
        canvas_width=canvas_width,
        canvas_height=canvas_height,
        header_rect=(0, 0, canvas_width, active.header_height_px),
        camera_rect=(camera_x0, camera_y0, camera_x0 + width, camera_y0 + height),
        panel_rect=(
            panel_x0,
            camera_y0,
            panel_x0 + panel_width,
            camera_y0 + content_height,
        ),
        footer_rect=(0, footer_y0, canvas_width, canvas_height),
    )


def compose_presentation(
    camera_bgr: ColorFrame,
    data: PresentationData,
    *,
    mode: PresentationMode = PresentationMode.PRODUCT,
    theme: PresentationTheme = PresentationTheme.DARK,
    camera_cover_enabled: bool = False,
    style: PresentationStyle | None = None,
) -> ColorFrame:
    """Paste an unchanged camera view and draw all UI outside its rectangle."""

    _validate_frame(camera_bgr)
    if not isinstance(mode, PresentationMode):
        raise TypeError("mode must be a PresentationMode")
    if not isinstance(theme, PresentationTheme):
        raise TypeError("theme must be a PresentationTheme")
    if not isinstance(camera_cover_enabled, bool):
        raise TypeError("camera_cover_enabled must be boolean")
    active = style or style_for_theme(theme)
    height, width = camera_bgr.shape[:2]
    layout = layout_for_camera(width, height, style=active)
    canvas = np.full(
        (layout.canvas_height, layout.canvas_width, 3),
        active.background_bgr,
        dtype=np.uint8,
    )
    _fill_rect(canvas, layout.header_rect, active.surface_bgr)
    _fill_rect(canvas, layout.panel_rect, active.surface_bgr)
    _fill_rect(canvas, layout.footer_rect, active.surface_bgr)

    x0, y0, x1, y1 = layout.camera_rect
    canvas[y0:y1, x0:x1] = camera_bgr
    camera_border = (
        active.primary_bgr if mode is PresentationMode.PRODUCT else active.border_bgr
    )
    cv2.rectangle(
        canvas,
        (x0 - 3, y0 - 3),
        (x1 + 2, y1 + 2),
        camera_border,
        2,
    )

    pil_image = Image.fromarray(cv2.cvtColor(canvas, cv2.COLOR_BGR2RGB))
    draw = ImageDraw.Draw(pil_image)
    if camera_cover_enabled:
        _draw_camera_cover(draw, layout, theme)
    _draw_header(draw, layout, data, mode, active)
    if mode is PresentationMode.PRODUCT:
        _draw_product_panel(draw, layout, data, active)
    else:
        _draw_diagnostic_panel(draw, layout, data, active)
    _draw_footer(
        draw,
        layout,
        data,
        mode,
        camera_cover_enabled,
        active,
    )
    return cv2.cvtColor(np.asarray(pil_image), cv2.COLOR_RGB2BGR).copy()


def _draw_camera_cover(
    draw: ImageDraw.ImageDraw,
    layout: PresentationLayout,
    theme: PresentationTheme,
) -> None:
    """Hide only displayed camera pixels behind a centered ChromaLens mark."""

    x0, y0, x1, y1 = layout.camera_rect
    if theme is PresentationTheme.DARK:
        cover_rgb = (245, 247, 250)
        text_rgb = (16, 22, 28)
        icon_rgb = (0, 127, 158)
    else:
        cover_rgb = (11, 16, 20)
        text_rgb = (245, 247, 250)
        icon_rgb = (94, 231, 255)
    draw.rectangle((x0, y0, x1 - 1, y1 - 1), fill=cover_rgb)

    width = x1 - x0
    height = y1 - y0
    font_size = int(np.clip(round(width * 0.06), 24, 42))
    font = _font(font_size, bold=True)
    title = "ChromaLens AI"
    icon_radius = max(8, round(font_size * 0.32))
    gap = max(10, round(font_size * 0.32))
    total_width = icon_radius * 2 + gap + int(font.getlength(title))
    icon_x = x0 + max(12, (width - total_width) // 2 + icon_radius)
    center_y = y0 + height // 2
    draw.polygon(
        (
            (icon_x, center_y - icon_radius),
            (icon_x + icon_radius, center_y),
            (icon_x, center_y + icon_radius),
            (icon_x - icon_radius, center_y),
        ),
        fill=icon_rgb,
    )
    draw.text(
        (icon_x + icon_radius + gap, center_y),
        title,
        font=font,
        fill=text_rgb,
        anchor="lm",
    )


def build_product_copy(
    data: PresentationData,
    *,
    style: PresentationStyle | None = None,
) -> dict[str, str]:
    """Return inspectable Vietnamese product labels without technical values."""

    active = style or PresentationStyle()
    if data.original_color_label is None:
        color = "Đang phân tích…"
        confidence = "Chưa xác định"
    else:
        color = data.original_color_label
        if data.color_margin is None:
            confidence = "Chưa xác định"
        elif data.color_margin >= active.color_margin_high:
            confidence = "Độ chắc chắn: Cao"
        elif data.color_margin >= active.color_margin_medium:
            confidence = "Độ chắc chắn: Vừa"
        else:
            confidence = "Độ chắc chắn: Thấp"

    risk = {
        "low": "Không phát hiện xung đột đáng kể",
        "medium": "Có thể khó phân biệt",
        "high": "Khó phân biệt màu",
    }.get(data.risk_level, "Chưa đủ màu để so sánh")
    lighting = {
        "good": "Ánh sáng tốt",
        "medium": "Nên tăng thêm ánh sáng",
        "poor": "Ánh sáng chưa đủ",
    }.get(data.lighting_level, "Đang kiểm tra ánh sáng")
    guidance = (
        "Chưa có gợi ý phù hợp"
        if data.matching_label is None
        else f"Phối với {data.matching_label}"
    )
    if data.matching_harmony:
        harmony = {
            "neutral": "trung tính",
            "analogous": "tương đồng",
            "complementary": "bổ sung",
            "tone": "cùng tông",
        }.get(data.matching_harmony, data.matching_harmony)
        guidance = f"{guidance} · {harmony}"
    return {
        "color": color,
        "confidence": confidence,
        "risk": risk,
        "lighting": lighting,
        "guidance": guidance,
        "action": data.action_message,
    }


def _draw_header(
    draw: ImageDraw.ImageDraw,
    layout: PresentationLayout,
    data: PresentationData,
    mode: PresentationMode,
    style: PresentationStyle,
) -> None:
    _, _, x1, _ = layout.header_rect
    logo_x = style.outer_padding_px + 8
    logo_y = 26
    draw.polygon(
        (
            (logo_x, logo_y - 8),
            (logo_x + 8, logo_y),
            (logo_x, logo_y + 8),
            (logo_x - 8, logo_y),
        ),
        fill=_rgb(style.primary_bgr),
    )
    _text(
        draw,
        (style.outer_padding_px + 28, 13),
        "ChromaLens AI",
        27,
        style.chrome_text_bgr,
        bold=True,
    )
    if mode is PresentationMode.PRODUCT:
        profile_label = f"Hồ sơ: {data.profile.value.title()}"
        profile_width = int(_font(15, bold=True).getlength(profile_label)) + 28
        profile_rect = (x1 - style.outer_padding_px - profile_width, 13, x1 - style.outer_padding_px, 52)
        draw.rounded_rectangle(
            profile_rect,
            radius=12,
            fill=_rgb(style.card_bgr),
        )
        _text(
            draw,
            (profile_rect[0] + 14, 23),
            profile_label,
            15,
            style.text_bgr,
            bold=True,
        )
        product_right = profile_rect[0] - 24
        _right_text(
            draw,
            (product_right, 23),
            "SẢN PHẨM",
            14,
            style.chrome_text_bgr,
        )
        draw.line(
            (product_right - 72, 48, product_right, 48),
            fill=_rgb(style.primary_bgr),
            width=3,
        )
    else:
        right = f"KỸ THUẬT   ·   Hồ sơ: {data.profile.value.title()}"
        _right_text(
            draw,
            (x1 - style.outer_padding_px, 20),
            right,
            17,
            style.chrome_muted_text_bgr,
        )


def _draw_product_panel(
    draw: ImageDraw.ImageDraw,
    layout: PresentationLayout,
    data: PresentationData,
    style: PresentationStyle,
) -> None:
    copy = build_product_copy(data, style=style)
    risk_indicator = {
        "low": style.success_bgr,
        "medium": style.warning_bgr,
        "high": style.warning_bgr,
    }.get(data.risk_level, style.muted_text_bgr)
    lighting_indicator = {
        "good": style.success_bgr,
        "medium": style.warning_bgr,
        "poor": style.warning_bgr,
    }.get(data.lighting_level, style.muted_text_bgr)
    cards = (
        (
            "MÀU TRANG PHỤC",
            copy["color"],
            copy["confidence"],
            data.original_color_rgb,
            style.primary_bgr,
            True,
        ),
        (
            "KHẢ NĂNG PHÂN BIỆT",
            copy["risk"],
            "Đánh giá theo cặp màu",
            None,
            risk_indicator,
            False,
        ),
        (
            "ÁNH SÁNG",
            copy["lighting"],
            "Giúp nhận diện màu ổn định hơn",
            None,
            lighting_indicator,
            False,
        ),
        (
            "GỢI Ý PHỐI",
            copy["guidance"],
            "Gợi ý tham khảo",
            None,
            style.violet_bgr,
            False,
        ),
    )
    for rect, (title, value, detail, swatch, indicator, is_primary) in zip(
        _product_card_rectangles(layout), cards, strict=True
    ):
        _draw_product_card(
            draw,
            rect,
            title=title,
            value=value,
            detail=detail,
            swatch=swatch,
            indicator_bgr=indicator,
            is_primary=is_primary,
            style=style,
        )


def _draw_product_card(
    draw: ImageDraw.ImageDraw,
    rect: tuple[int, int, int, int],
    *,
    title: str,
    value: str,
    detail: str,
    swatch: RGBColor | None,
    indicator_bgr: tuple[int, int, int],
    is_primary: bool,
    style: PresentationStyle,
) -> None:
    """Draw one card with disjoint, line-limited title/value/detail regions."""

    x0, y0, x1, y1 = rect
    width = x1 - x0
    height = y1 - y0
    draw.rounded_rectangle(
        (x0, y0, x1 - 1, y1 - 1),
        radius=13,
        fill=_rgb(style.primary_card_bgr if is_primary else style.card_bgr),
        outline=_rgb(style.primary_bgr) if is_primary else None,
        width=2 if is_primary else 1,
    )

    regions = _product_card_regions(width, height, has_swatch=swatch is not None)
    indicator_x = x0 + 21
    indicator_y = y0 + 15
    draw.ellipse(
        (indicator_x - 5, indicator_y - 5, indicator_x + 5, indicator_y + 5),
        fill=_rgb(indicator_bgr),
    )

    _single_line_in_region(
        draw,
        _offset_rect(regions.title, x0, y0),
        title,
        13,
        style.muted_text_bgr,
        bold=True,
    )
    _bounded_text_in_region(
        draw,
        _offset_rect(regions.value, x0, y0),
        value,
        22 if is_primary else 20,
        style.text_bgr,
        maximum_lines=2,
        bold=True,
    )
    _single_line_in_region(
        draw,
        _offset_rect(regions.detail, x0, y0),
        detail,
        13,
        style.muted_text_bgr,
    )
    if swatch is not None and regions.swatch is not None:
        if regions.swatch[3] > regions.swatch[1]:
            draw.rounded_rectangle(
                _offset_rect(regions.swatch, x0, y0),
                radius=8,
                fill=tuple(int(channel) for channel in swatch),
                outline=(245, 245, 245),
                width=2,
            )


def _product_card_rectangles(
    layout: PresentationLayout,
) -> tuple[tuple[int, int, int, int], ...]:
    """Return four separated card rectangles within the product panel."""

    x0, y0, x1, y1 = layout.panel_rect
    gap = 10
    padding = 14
    usable_height = y1 - y0 - 2 * padding - 3 * gap
    heights = [
        round(usable_height * 0.28),
        round(usable_height * 0.28),
        round(usable_height * 0.22),
    ]
    heights.append(usable_height - sum(heights))
    rectangles: list[tuple[int, int, int, int]] = []
    cursor_y = y0 + padding
    for card_height in heights:
        rectangles.append(
            (x0 + padding, cursor_y, x1 - padding, cursor_y + card_height)
        )
        cursor_y += card_height + gap
    return tuple(rectangles)


def _product_card_regions(
    width: int, height: int, *, has_swatch: bool
) -> ProductCardRegions:
    """Reserve disjoint title/value/detail areas inside one clipped card."""

    horizontal_padding = 14
    title = (36, 7, width - horizontal_padding, 24)
    detail = (
        horizontal_padding,
        height - 24,
        width - horizontal_padding,
        height - 7,
    )
    value_left = horizontal_padding + (56 if has_swatch else 0)
    value = (value_left, title[3] + 4, width - horizontal_padding, detail[1] - 4)
    swatch = None
    if has_swatch:
        swatch = (
            horizontal_padding,
            value[1],
            horizontal_padding + 44,
            min(value[3], value[1] + 44),
        )
    return ProductCardRegions(title=title, value=value, detail=detail, swatch=swatch)


def _offset_rect(
    rect: tuple[int, int, int, int], x_offset: int, y_offset: int
) -> tuple[int, int, int, int]:
    x0, y0, x1, y1 = rect
    return (x0 + x_offset, y0 + y_offset, x1 + x_offset, y1 + y_offset)


def _draw_diagnostic_panel(
    draw: ImageDraw.ImageDraw,
    layout: PresentationLayout,
    data: PresentationData,
    style: PresentationStyle,
) -> None:
    x0, y0, x1, y1 = layout.panel_rect
    pad = 16
    _text(draw, (x0 + pad, y0 + 14), "THÔNG TIN KỸ THUẬT", 15, style.primary_bgr, bold=True)
    cursor_y = y0 + 45
    maximum_width = x1 - x0 - 2 * pad
    for line in data.diagnostic_lines:
        wrapped = _wrap_text(line, maximum_width, 13)
        for part in wrapped[:2]:
            if cursor_y + 19 >= y1 - pad:
                return
            _text(draw, (x0 + pad, cursor_y), part, 13, style.chrome_text_bgr)
            cursor_y += 19
        cursor_y += 5


def _draw_footer(
    draw: ImageDraw.ImageDraw,
    layout: PresentationLayout,
    data: PresentationData,
    mode: PresentationMode,
    camera_cover_enabled: bool,
    style: PresentationStyle,
) -> None:
    _, y0, x1, _ = layout.footer_rect
    support = "BẬT" if data.recolor_enabled else "TẮT"
    if mode is PresentationMode.PRODUCT:
        detected = data.original_color_label is not None
        statuses = (
            (
                "HIỂN THỊ ĐÃ CHE"
                if camera_cover_enabled
                else "CAMERA HOẠT ĐỘNG",
                style.primary_bgr
                if camera_cover_enabled
                else style.success_bgr,
            ),
            (
                "AI SẴN SÀNG" if detected else "ĐANG PHÂN TÍCH",
                style.success_bgr if detected else style.warning_bgr,
            ),
            (
                "ĐÃ NHẬN DIỆN" if detected else "CHỜ TRANG PHỤC",
                style.primary_bgr if detected else style.warning_bgr,
            ),
            (
                f"HỖ TRỢ {support}",
                style.success_bgr
                if data.recolor_enabled
                else style.chrome_muted_text_bgr,
            ),
        )
        available_width = x1 - 2 * style.outer_padding_px
        status_widths = (
            round(available_width * 0.27),
            round(available_width * 0.22),
            round(available_width * 0.25),
        )
        status_widths += (available_width - sum(status_widths),)
        status_x = style.outer_padding_px
        for (label, color), status_width in zip(
            statuses, status_widths, strict=True
        ):
            _draw_status_item(
                draw,
                x=status_x,
                y=y0 + 9,
                width=status_width,
                label=label,
                indicator_bgr=color,
                style=style,
            )
            status_x += status_width
        midpoint = round(x1 * 0.58)
        _single_line_in_region(
            draw,
            (style.outer_padding_px, y0 + 36, midpoint - 8, y0 + 60),
            data.action_message,
            14,
            style.primary_bgr,
            bold=True,
        )
        _single_line_in_region(
            draw,
            (midpoint, y0 + 38, x1 - style.outer_padding_px, y0 + 60),
            "C: Che camera  ·  T: Nền  ·  U: Kỹ thuật  ·  P: Hồ sơ  ·  Q: Thoát",
            12,
            style.chrome_muted_text_bgr,
        )
        return
    else:
        cover = "on" if camera_cover_enabled else "off"
        left = (
            f"Nguồn: {data.source_name} | Hỗ trợ={support} | "
            f"view={data.view_name} | cover={cover}"
        )
        keys = "C cover | T theme | U product/diagnostic | P profile | [/] severity | R recolor | V/1-5 view | Q quit"
        _text(
            draw,
            (style.outer_padding_px, y0 + 10),
            left,
            14,
            style.chrome_text_bgr,
        )
        _text(
            draw,
            (style.outer_padding_px, y0 + 37),
            keys,
            12,
            style.chrome_muted_text_bgr,
        )
        return


def _draw_status_item(
    draw: ImageDraw.ImageDraw,
    *,
    x: int,
    y: int,
    width: int,
    label: str,
    indicator_bgr: tuple[int, int, int],
    style: PresentationStyle,
) -> None:
    """Draw a text-backed status dot inside one footer allocation."""

    center_y = y + 8
    draw.ellipse(
        (x, center_y - 5, x + 10, center_y + 5),
        fill=_rgb(indicator_bgr),
    )
    _single_line_in_region(
        draw,
        (x + 18, y, x + width - 8, y + 22),
        label,
        12,
        style.chrome_text_bgr,
        bold=True,
    )


def _single_line_in_region(
    draw: ImageDraw.ImageDraw,
    region: tuple[int, int, int, int],
    value: str,
    size: int,
    color_bgr: tuple[int, int, int],
    *,
    bold: bool = False,
) -> None:
    """Draw at most one ellipsized line inside a reserved rectangle."""

    x0, y0, x1, y1 = region
    if x1 <= x0 or y1 - y0 < size:
        return
    fitted = _ellipsize(value, x1 - x0, size, bold=bold)
    _text(draw, (x0, y0), fitted, size, color_bgr, bold=bold)


def _bounded_text_in_region(
    draw: ImageDraw.ImageDraw,
    region: tuple[int, int, int, int],
    value: str,
    size: int,
    color_bgr: tuple[int, int, int],
    *,
    maximum_lines: int,
    bold: bool = False,
) -> None:
    """Wrap text using only the line capacity reserved by ``region``."""

    x0, y0, x1, y1 = region
    line_step = size + 5
    line_capacity = min(maximum_lines, max(0, (y1 - y0) // line_step))
    if x1 <= x0 or line_capacity == 0:
        return
    maximum_width = x1 - x0
    lines = _wrap_text(value, maximum_width, size, bold=bold)
    visible = lines[:line_capacity]
    if len(lines) > line_capacity:
        visible[-1] = _with_ellipsis(
            visible[-1], maximum_width, size, bold=bold
        )
    for index, line in enumerate(visible):
        _text(
            draw,
            (x0, y0 + index * line_step),
            line,
            size,
            color_bgr,
            bold=bold,
        )


def _wrap_text(value: str, maximum_width: int, size: int, *, bold: bool = False) -> list[str]:
    font = _font(size, bold=bold)
    words = value.split()
    if not words:
        return [""]
    lines: list[str] = []
    current = words[0]
    for word in words[1:]:
        candidate = f"{current} {word}"
        if font.getlength(candidate) <= maximum_width:
            current = candidate
        else:
            lines.append(_ellipsize(current, maximum_width, size, bold=bold))
            current = word
    lines.append(_ellipsize(current, maximum_width, size, bold=bold))
    return lines


def _ellipsize(value: str, maximum_width: int, size: int, *, bold: bool = False) -> str:
    font = _font(size, bold=bold)
    if font.getlength(value) <= maximum_width:
        return value
    suffix = "…"
    candidate = value
    while candidate and font.getlength(candidate.rstrip() + suffix) > maximum_width:
        candidate = candidate[:-1]
    return candidate.rstrip() + suffix


def _with_ellipsis(
    value: str, maximum_width: int, size: int, *, bold: bool = False
) -> str:
    """Append a visible truncation marker while respecting the same width."""

    suffix = "…"
    candidate = value.rstrip(" …")
    font = _font(size, bold=bold)
    while candidate and font.getlength(candidate + suffix) > maximum_width:
        candidate = candidate[:-1].rstrip()
    return candidate + suffix


def _text(
    draw: ImageDraw.ImageDraw,
    position: tuple[int, int],
    value: str,
    size: int,
    color_bgr: tuple[int, int, int],
    *,
    bold: bool = False,
) -> None:
    draw.text(position, value, font=_font(size, bold=bold), fill=_rgb(color_bgr))


def _right_text(
    draw: ImageDraw.ImageDraw,
    anchor: tuple[int, int],
    value: str,
    size: int,
    color_bgr: tuple[int, int, int],
) -> None:
    font = _font(size)
    draw.text(anchor, value, font=font, fill=_rgb(color_bgr), anchor="ra")


@lru_cache(maxsize=32)
def _font(size: int, *, bold: bool = False) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    for path in _font_candidates(bold):
        if path.is_file():
            return ImageFont.truetype(str(path), size=size)
    return ImageFont.load_default(size=size)


def _font_candidates(bold: bool) -> tuple[Path, ...]:
    filename = "segoeuib.ttf" if bold else "segoeui.ttf"
    return (
        Path("C:/Windows/Fonts") / filename,
        Path("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf" if bold else "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"),
        Path("/System/Library/Fonts/Supplemental/Arial Bold.ttf" if bold else "/System/Library/Fonts/Supplemental/Arial.ttf"),
    )


def _fill_rect(
    frame: ColorFrame,
    rect: tuple[int, int, int, int],
    color_bgr: tuple[int, int, int],
) -> None:
    x0, y0, x1, y1 = rect
    frame[y0:y1, x0:x1] = color_bgr


def _rgb(color_bgr: tuple[int, int, int]) -> tuple[int, int, int]:
    return (color_bgr[2], color_bgr[1], color_bgr[0])


def _validate_frame(frame: ColorFrame) -> None:
    if frame.dtype != np.uint8 or frame.ndim != 3 or frame.shape[2] != 3:
        raise ValueError("camera_bgr must be a uint8 H x W x 3 BGR frame")
    if frame.shape[0] == 0 or frame.shape[1] == 0:
        raise ValueError("camera_bgr dimensions must be non-empty")
