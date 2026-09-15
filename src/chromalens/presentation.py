"""Two-mode OpenCV presentation shell with an unobscured camera viewport."""

from __future__ import annotations

from dataclasses import dataclass, replace
from enum import Enum
from functools import lru_cache
from pathlib import Path

import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont

from chromalens.color_naming import RGBColor
from chromalens.config import CVDProfile
from chromalens.contracts import ColorFrame


_CAMERA_BEZEL_LOGICAL_PX = 7
_MIN_ALIGNED_PRODUCT_STACK_LOGICAL_PX = 440


class PresentationMode(str, Enum):
    """User-facing product shell or evidence-focused diagnostic shell."""

    PRODUCT = "product"
    DIAGNOSTIC = "diagnostic"


class PresentationTheme(str, Enum):
    """User-selected high-contrast presentation palette."""

    DARK = "dark"
    LIGHT = "light"


class ProductPresentationState(str, Enum):
    """One coherent user-facing state derived from existing pipeline facts."""

    CAMERA_BLOCKED = "camera_blocked"
    WAITING_FOR_GARMENT = "waiting_for_garment"
    ANALYZING = "analyzing"
    RESULT_READY = "result_ready"


class ProductIcon(str, Enum):
    """Shape-coded Product icons; color is never their only distinction."""

    GARMENT = "garment"
    PROCESSING = "processing"
    READY = "ready"
    WARNING = "warning"
    RISK = "risk"
    LIGHTING = "lighting"
    MATCHING = "matching"
    PROFILE = "profile"


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
    tray_bgr: tuple[int, int, int] = (29, 24, 18)
    camera_shell_bgr: tuple[int, int, int] = (54, 46, 36)
    camera_rim_bgr: tuple[int, int, int] = (135, 120, 105)
    camera_shadow_bgr: tuple[int, int, int] = (15, 12, 8)
    divider_bgr: tuple[int, int, int] = (61, 52, 43)
    control_bgr: tuple[int, int, int] = (224, 220, 216)
    control_border_bgr: tuple[int, int, int] = (198, 191, 183)
    card_bgr: tuple[int, int, int] = (224, 220, 216)
    primary_card_bgr: tuple[int, int, int] = (250, 247, 245)
    border_bgr: tuple[int, int, int] = (198, 191, 183)
    primary_bgr: tuple[int, int, int] = (255, 231, 94)
    violet_bgr: tuple[int, int, int] = (255, 124, 139)
    success_bgr: tuple[int, int, int] = (164, 229, 82)
    warning_bgr: tuple[int, int, int] = (87, 200, 255)
    card_info_bgr: tuple[int, int, int] = (178, 126, 0)
    card_recommendation_bgr: tuple[int, int, int] = (160, 70, 110)
    card_success_bgr: tuple[int, int, int] = (90, 135, 0)
    card_warning_bgr: tuple[int, int, int] = (0, 90, 170)
    text_bgr: tuple[int, int, int] = (28, 22, 16)
    muted_text_bgr: tuple[int, int, int] = (92, 82, 70)
    chrome_text_bgr: tuple[int, int, int] = (250, 247, 245)
    chrome_muted_text_bgr: tuple[int, int, int] = (175, 164, 154)
    ui_scale: float = 1.0

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
        if not np.isfinite(self.ui_scale) or self.ui_scale <= 0.0:
            raise ValueError("ui_scale must be finite and positive")

    def scaled(self, factor: float) -> "PresentationStyle":
        """Scale geometry for native-resolution drawing, never bitmap UI zoom."""

        if not np.isfinite(factor) or factor <= 0.0:
            raise ValueError("style scale factor must be finite and positive")
        integer_fields = (
            "outer_padding_px",
            "content_gap_px",
            "header_height_px",
            "footer_height_px",
            "minimum_panel_width_px",
            "maximum_panel_width_px",
            "minimum_content_height_px",
        )
        values = {
            name: max(1, round(getattr(self, name) * factor))
            for name in integer_fields
        }
        return replace(self, **values, ui_scale=self.ui_scale * factor)


def style_for_theme(theme: PresentationTheme) -> PresentationStyle:
    """Return the frozen palette for a user-selected light or dark shell."""

    if not isinstance(theme, PresentationTheme):
        raise TypeError("theme must be a PresentationTheme")
    if theme is PresentationTheme.DARK:
        return PresentationStyle()
    return PresentationStyle(
        background_bgr=(248, 246, 244),
        surface_bgr=(255, 255, 255),
        tray_bgr=(246, 243, 240),
        camera_shell_bgr=(220, 215, 208),
        camera_rim_bgr=(133, 121, 108),
        camera_shadow_bgr=(223, 219, 214),
        divider_bgr=(218, 213, 207),
        control_bgr=(68, 58, 48),
        control_border_bgr=(104, 91, 76),
        card_bgr=(82, 72, 61),
        primary_card_bgr=(58, 47, 34),
        border_bgr=(109, 96, 82),
        primary_bgr=(158, 127, 0),
        violet_bgr=(164, 80, 103),
        success_bgr=(90, 135, 0),
        warning_bgr=(0, 106, 180),
        card_info_bgr=(255, 231, 94),
        card_recommendation_bgr=(255, 150, 165),
        card_success_bgr=(164, 229, 82),
        card_warning_bgr=(87, 200, 255),
        text_bgr=(250, 247, 245),
        muted_text_bgr=(220, 212, 204),
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
    camera_input_issue: str | None = None
    garment_detected: bool = False

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
        if not isinstance(self.garment_detected, bool):
            raise TypeError("garment_detected must be boolean")
        if self.camera_input_issue not in {None, "blocked_or_black"}:
            raise ValueError("camera_input_issue is not a supported presentation state")


def product_presentation_state(data: PresentationData) -> ProductPresentationState:
    """Derive one Product state without changing analytical pipeline behavior."""

    if data.camera_input_issue == "blocked_or_black":
        return ProductPresentationState.CAMERA_BLOCKED
    if data.original_color_label is not None:
        return ProductPresentationState.RESULT_READY
    if data.garment_detected:
        return ProductPresentationState.ANALYZING
    return ProductPresentationState.WAITING_FOR_GARMENT


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


def responsive_layout_for_display(
    camera_size: tuple[int, int],
    target_size: tuple[int, int],
    *,
    style: PresentationStyle | None = None,
) -> tuple[PresentationStyle, PresentationLayout]:
    """Return final-pixel UI geometry with a bounded desktop sidebar."""

    source_width, source_height = camera_size
    target_width, target_height = target_size
    if min(source_width, source_height, target_width, target_height) <= 0:
        raise ValueError("camera and target dimensions must be positive")
    base = style or PresentationStyle()
    ui_scale = float(np.clip(target_height / 768.0, 0.85, 1.20))
    outer_padding = max(10, round(20 * ui_scale))
    content_gap = max(10, round(20 * ui_scale))
    header_height = max(54, round(72 * ui_scale))
    footer_height = max(58, round(76 * ui_scale))
    available_height = (
        target_height - header_height - footer_height - 2 * outer_padding
    )
    if available_height <= 0:
        raise ValueError("target display is too short for the presentation shell")

    desired_panel_width = int(np.clip(round(target_width * 0.24), 300, 430))
    maximum_panel_width = target_width - 2 * outer_padding - content_gap - 1
    if maximum_panel_width <= 0:
        raise ValueError("target display is too narrow for the presentation shell")
    panel_width = min(desired_panel_width, maximum_panel_width)
    available_camera_width = (
        target_width - 2 * outer_padding - content_gap - panel_width
    )
    source_aspect = source_width / source_height
    camera_width = min(
        available_camera_width,
        max(1, round(available_height * source_aspect)),
    )
    camera_height = min(
        available_height,
        max(1, round(camera_width / source_aspect)),
    )
    responsive_style = replace(
        base,
        outer_padding_px=outer_padding,
        content_gap_px=content_gap,
        header_height_px=header_height,
        footer_height_px=footer_height,
        minimum_panel_width_px=panel_width,
        maximum_panel_width_px=panel_width,
        minimum_content_height_px=available_height,
        ui_scale=base.ui_scale * ui_scale,
    )
    return (
        responsive_style,
        layout_for_camera(camera_width, camera_height, style=responsive_style),
    )


def compose_presentation(
    camera_bgr: ColorFrame,
    data: PresentationData,
    *,
    mode: PresentationMode = PresentationMode.PRODUCT,
    theme: PresentationTheme = PresentationTheme.DARK,
    camera_cover_enabled: bool = False,
    style: PresentationStyle | None = None,
    target_size: tuple[int, int] | None = None,
) -> ColorFrame:
    """Draw a camera-first shell, natively at the display size when requested."""

    _validate_frame(camera_bgr)
    if not isinstance(mode, PresentationMode):
        raise TypeError("mode must be a PresentationMode")
    if not isinstance(theme, PresentationTheme):
        raise TypeError("theme must be a PresentationTheme")
    if not isinstance(camera_cover_enabled, bool):
        raise TypeError("camera_cover_enabled must be boolean")
    active = style or style_for_theme(theme)
    if target_size is not None:
        target_width, target_height = target_size
        source_height, source_width = camera_bgr.shape[:2]
        active, native_layout = responsive_layout_for_display(
            (source_width, source_height),
            target_size,
            style=active,
        )
        x0, y0, x1, y1 = native_layout.camera_rect
        camera_width = x1 - x0
        camera_height = y1 - y0
        interpolation = (
            cv2.INTER_AREA
            if camera_width < source_width or camera_height < source_height
            else cv2.INTER_LANCZOS4
        )
        camera_bgr = cv2.resize(
            camera_bgr,
            (camera_width, camera_height),
            interpolation=interpolation,
        )
        native = _compose_presentation_canvas(
            camera_bgr,
            data,
            mode=mode,
            theme=theme,
            camera_cover_enabled=camera_cover_enabled,
            style=active,
        )
        if native.shape[:2] == (target_height, target_width):
            return native
        output = np.full(
            (target_height, target_width, 3),
            active.background_bgr,
            dtype=np.uint8,
        )
        y0 = (target_height - native.shape[0]) // 2
        x0 = (target_width - native.shape[1]) // 2
        output[y0 : y0 + native.shape[0], x0 : x0 + native.shape[1]] = native
        return output
    return _compose_presentation_canvas(
        camera_bgr,
        data,
        mode=mode,
        theme=theme,
        camera_cover_enabled=camera_cover_enabled,
        style=active,
    )


def _compose_presentation_canvas(
    camera_bgr: ColorFrame,
    data: PresentationData,
    *,
    mode: PresentationMode,
    theme: PresentationTheme,
    camera_cover_enabled: bool,
    style: PresentationStyle,
) -> ColorFrame:
    """Compose at final pixel density so text and rounded shapes stay crisp."""

    active = style
    height, width = camera_bgr.shape[:2]
    layout = layout_for_camera(width, height, style=active)
    pil_image = Image.new(
        "RGB",
        (layout.canvas_width, layout.canvas_height),
        _rgb(active.background_bgr),
    )
    draw = ImageDraw.Draw(pil_image)
    background_rgb = _rgb(active.background_bgr)
    surface_rgb = _rgb(active.surface_bgr)
    panel_tray_rgb = _rgb(active.tray_bgr)
    for rect in (layout.header_rect, layout.footer_rect):
        rx0, ry0, rx1, ry1 = rect
        draw.rectangle(
            (rx0, ry0, rx1 - 1, ry1 - 1),
            fill=surface_rgb,
        )
    panel_x0, panel_y0, panel_x1, panel_y1 = (
        _product_sidebar_rect(layout, active)
        if mode is PresentationMode.PRODUCT
        else layout.panel_rect
    )
    draw.rectangle(
        (panel_x0, panel_y0, panel_x1 - 1, panel_y1 - 1),
        fill=panel_tray_rgb,
    )
    separator_rgb = _rgb(active.divider_bgr)
    surface_highlight_rgb = _highlight_rgb(surface_rgb, 0.08)
    draw.line(
        (0, 0, layout.canvas_width - 1, 0),
        fill=surface_highlight_rgb,
        width=max(1, _sp(active, 1)),
    )
    draw.line(
        (0, layout.header_rect[3] - 1, layout.canvas_width - 1, layout.header_rect[3] - 1),
        fill=separator_rgb,
        width=max(1, _sp(active, 1)),
    )
    draw.line(
        (0, layout.footer_rect[1], layout.canvas_width - 1, layout.footer_rect[1]),
        fill=separator_rgb,
        width=max(1, _sp(active, 1)),
    )
    draw.line(
        (
            0,
            layout.footer_rect[1] + max(1, _sp(active, 1)),
            layout.canvas_width - 1,
            layout.footer_rect[1] + max(1, _sp(active, 1)),
        ),
        fill=surface_highlight_rgb,
        width=max(1, _sp(active, 1)),
    )

    x0, y0, x1, y1 = layout.camera_rect
    content_radius = _sp(active, 18)
    bezel_width = _sp(active, _CAMERA_BEZEL_LOGICAL_PX)
    shadow_depth = _sp(active, 3)
    bezel_rgb = _rgb(active.camera_shell_bgr)
    bezel_highlight_rgb = _highlight_rgb(bezel_rgb, 0.08)
    shadow_rgb = _rgb(active.camera_shadow_bgr)
    outer_rect = (
        x0 - bezel_width,
        y0 - bezel_width,
        x1 + bezel_width - 1,
        y1 + bezel_width - 1,
    )
    _draw_aa_rounded_rectangle(
        pil_image,
        (
            outer_rect[0] + shadow_depth,
            outer_rect[1] + shadow_depth,
            outer_rect[2] + shadow_depth,
            outer_rect[3] + shadow_depth,
        ),
        radius=content_radius + bezel_width,
        fill=shadow_rgb,
    )
    _draw_aa_rounded_rectangle(
        pil_image,
        outer_rect,
        radius=content_radius + bezel_width,
        fill=bezel_rgb,
    )
    chrome_inset = content_radius + bezel_width
    edge_width = max(1, _sp(active, 1))
    draw.line(
        (
            outer_rect[0] + chrome_inset,
            outer_rect[1],
            outer_rect[2] - chrome_inset,
            outer_rect[1],
        ),
        fill=bezel_highlight_rgb,
        width=edge_width,
    )
    draw.line(
        (
            outer_rect[0],
            outer_rect[1] + chrome_inset,
            outer_rect[0],
            outer_rect[3] - chrome_inset,
        ),
        fill=bezel_highlight_rgb,
        width=edge_width,
    )
    camera_rgb = Image.fromarray(cv2.cvtColor(camera_bgr, cv2.COLOR_BGR2RGB))
    pil_image.paste(camera_rgb, (x0, y0))
    _clip_rounded_content_corners(
        pil_image,
        layout.camera_rect,
        radius=content_radius,
        outside_rgb=bezel_rgb,
    )
    draw = ImageDraw.Draw(pil_image)
    if camera_cover_enabled:
        _draw_camera_cover(draw, layout, theme, active)
        _clip_rounded_content_corners(
            pil_image,
            layout.camera_rect,
            radius=content_radius,
            outside_rgb=bezel_rgb,
        )
    elif (
        mode is PresentationMode.PRODUCT
        and product_presentation_state(data)
        is ProductPresentationState.WAITING_FOR_GARMENT
    ):
        _draw_waiting_guide(pil_image, draw, layout, active)
    # Draw the inset rim last so camera/cover pixels cannot square its corners.
    _draw_aa_rounded_rectangle(
        pil_image,
        (x0, y0, x1 - 1, y1 - 1),
        radius=content_radius,
        outline=_rgb(active.camera_rim_bgr),
        width=max(1, _sp(active, 1)),
    )
    _draw_header(pil_image, draw, layout, data, mode, active)
    if mode is PresentationMode.PRODUCT:
        _draw_product_panel(pil_image, draw, layout, data, active)
    else:
        _draw_diagnostic_panel(draw, layout, data, active)
    _draw_footer(
        pil_image,
        draw,
        layout,
        data,
        mode,
        camera_cover_enabled,
        active,
    )
    # cvtColor already allocates a new contiguous BGR array; a second copy
    # would add full-canvas bandwidth without strengthening ownership.
    return cv2.cvtColor(np.asarray(pil_image), cv2.COLOR_RGB2BGR)


def _draw_camera_cover(
    draw: ImageDraw.ImageDraw,
    layout: PresentationLayout,
    theme: PresentationTheme,
    style: PresentationStyle,
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
    font_size = int(
        np.clip(
            round(width * 0.06),
            _sp(style, 24),
            _sp(style, 42),
        )
    )
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
    subtitle = "Hình ảnh đang được ẩn  ·  Nhấn C để hiển thị"
    subtitle_size = max(_sp(style, 12), round(font_size * 0.42))
    subtitle_font = _font(subtitle_size)
    subtitle_width = int(subtitle_font.getlength(subtitle))
    if subtitle_width > width - _sp(style, 24):
        subtitle = _ellipsize(
            subtitle,
            width - _sp(style, 24),
            subtitle_size,
        )
    draw.text(
        (x0 + width // 2, center_y + font_size),
        subtitle,
        font=subtitle_font,
        fill=text_rgb,
        anchor="mm",
    )


def _draw_waiting_guide(
    image: Image.Image,
    draw: ImageDraw.ImageDraw,
    layout: PresentationLayout,
    style: PresentationStyle,
) -> None:
    """Draw a restrained garment-area guide that disappears after detection."""

    x0, y0, x1, y1 = layout.camera_rect
    width = x1 - x0
    height = y1 - y0
    inset = _sp(style, 12)
    guide_width = min(
        max(1, width - 2 * inset),
        max(_sp(style, 120), round(width * 0.52)),
    )
    guide_height = min(
        max(1, height - 2 * inset),
        max(_sp(style, 150), round(height * 0.72)),
    )
    gx0 = x0 + (width - guide_width) // 2
    gy0 = y0 + (height - guide_height) // 2
    gx1 = gx0 + guide_width
    gy1 = gy0 + guide_height
    corner = min(_sp(style, 34), max(_sp(style, 16), guide_width // 8))
    stroke = _sp(style, 2)
    color = _rgb(style.primary_bgr)
    for points in (
        (gx0 + corner, gy0, gx0, gy0, gx0, gy0 + corner),
        (gx1 - corner, gy0, gx1, gy0, gx1, gy0 + corner),
        (gx0, gy1 - corner, gx0, gy1, gx0 + corner, gy1),
        (gx1, gy1 - corner, gx1, gy1, gx1 - corner, gy1),
    ):
        draw.line(points, fill=color, width=stroke, joint="curve")

    label = "ĐẶT TRANG PHỤC TRONG KHUNG"
    label_size = _sp(style, 12)
    label = _ellipsize(label, max(1, width - _sp(style, 48)), label_size, bold=True)
    label_font = _font(label_size, bold=True)
    label_width = int(label_font.getlength(label))
    pad_x = _sp(style, 12)
    pad_y = _sp(style, 6)
    label_rect = (
        x0 + (width - label_width) // 2 - pad_x,
        y0 + _sp(style, 14),
        x0 + (width + label_width) // 2 + pad_x,
        y0 + _sp(style, 14) + label_size + 2 * pad_y,
    )
    _draw_aa_rounded_rectangle(
        image,
        label_rect,
        radius=_sp(style, 10),
        fill=_rgb(style.surface_bgr),
        outline=color,
        width=max(1, _sp(style, 1)),
    )
    draw.text(
        (
            (label_rect[0] + label_rect[2]) // 2,
            (label_rect[1] + label_rect[3]) // 2,
        ),
        label,
        font=label_font,
        fill=_rgb(style.chrome_text_bgr),
        anchor="mm",
    )


def build_product_copy(
    data: PresentationData,
    *,
    style: PresentationStyle | None = None,
) -> dict[str, str]:
    """Return inspectable Vietnamese product labels without technical values."""

    active = style or PresentationStyle()
    state = product_presentation_state(data)
    if state is ProductPresentationState.CAMERA_BLOCKED:
        return {
            "color": "Không nhận được hình ảnh",
            "confidence": "Kiểm tra công tắc camera",
            "risk": "Chưa thể đánh giá màu",
            "lighting": "Chưa thể đo ánh sáng",
            "guidance": "Sẵn sàng khi camera hoạt động",
            "action": "Mở công tắc bảo mật camera để tiếp tục.",
        }
    if state is ProductPresentationState.WAITING_FOR_GARMENT:
        return {
            "color": "Đang chờ trang phục",
            "confidence": "Đặt trang phục trong khung",
            "risk": "Đang chờ màu trang phục",
            "lighting": _lighting_copy(data.lighting_level),
            "guidance": "Có sau khi nhận diện màu",
            "action": "Đưa trang phục vào vùng hướng dẫn.",
        }
    if state is ProductPresentationState.ANALYZING:
        return {
            "color": "Đang phân tích màu…",
            "confidence": "Vui lòng giữ trang phục ổn định",
            "risk": "Đang chờ kết quả màu",
            "lighting": _lighting_copy(data.lighting_level),
            "guidance": "Đang chờ kết quả màu",
            "action": "Giữ trang phục trong khung thêm một chút.",
        }

    assert data.original_color_label is not None
    color = data.original_color_label
    if data.color_margin is None:
        confidence = "Độ chắc chắn: Chưa xác định"
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
    lighting = _lighting_copy(data.lighting_level)
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


def _lighting_copy(lighting_level: str | None) -> str:
    return {
        "good": "Ánh sáng tốt",
        "medium": "Nên tăng thêm ánh sáng",
        "poor": "Ánh sáng chưa đủ",
    }.get(lighting_level, "Đang kiểm tra ánh sáng")


def _draw_header(
    image: Image.Image,
    draw: ImageDraw.ImageDraw,
    layout: PresentationLayout,
    data: PresentationData,
    mode: PresentationMode,
    style: PresentationStyle,
) -> None:
    _, _, x1, _ = layout.header_rect
    logo_x = style.outer_padding_px + _sp(style, 8)
    logo_y = _sp(style, 26)
    logo_radius = _sp(style, 8)
    draw.polygon(
        (
            (logo_x, logo_y - logo_radius),
            (logo_x + logo_radius, logo_y),
            (logo_x, logo_y + logo_radius),
            (logo_x - logo_radius, logo_y),
        ),
        fill=_rgb(style.primary_bgr),
    )
    _text(
        draw,
        (style.outer_padding_px + _sp(style, 28), _sp(style, 13)),
        "ChromaLens AI",
        _sp(style, 27),
        style.chrome_text_bgr,
        bold=True,
    )
    if mode is PresentationMode.PRODUCT:
        profile_label = data.profile.value.title()
        profile_font_size = _sp(style, 14)
        profile_width = (
            int(_font(profile_font_size, bold=True).getlength(profile_label))
            + _sp(style, 48)
        )
        profile_rect = (
            x1 - style.outer_padding_px - profile_width,
            _sp(style, 13),
            x1 - style.outer_padding_px,
            _sp(style, 49),
        )
        shadow_depth = _sp(style, 2)
        pill_surface_rgb = _rgb(style.control_bgr)
        _draw_aa_rounded_rectangle(
            image,
            (
                profile_rect[0],
                profile_rect[1] + shadow_depth,
                profile_rect[2],
                profile_rect[3] + shadow_depth,
            ),
            radius=_sp(style, 12),
            fill=_shade_rgb(pill_surface_rgb, 0.14),
        )
        _draw_aa_rounded_rectangle(
            image,
            profile_rect,
            radius=_sp(style, 12),
            fill=pill_surface_rgb,
            outline=_rgb(style.control_border_bgr),
            width=max(1, _sp(style, 1)),
        )
        pill_highlight_y = profile_rect[1] + max(1, _sp(style, 1))
        draw.line(
            (
                profile_rect[0] + _sp(style, 12),
                pill_highlight_y,
                profile_rect[2] - _sp(style, 12),
                pill_highlight_y,
            ),
            fill=_highlight_rgb(pill_surface_rgb, 0.14),
            width=max(1, _sp(style, 1)),
        )
        _draw_product_icon(
            image,
            center=(profile_rect[0] + _sp(style, 17), (profile_rect[1] + profile_rect[3]) // 2),
            icon=ProductIcon.PROFILE,
            color_bgr=style.text_bgr,
            style=style,
        )
        _text(
            draw,
            (profile_rect[0] + _sp(style, 31), _sp(style, 21)),
            profile_label,
            profile_font_size,
            style.text_bgr,
            bold=True,
        )
        product_right = profile_rect[0] - _sp(style, 20)
        _right_text(
            draw,
            (product_right, _sp(style, 24)),
            "HỒ SƠ NGƯỜI DÙNG",
            _sp(style, 13),
            style.chrome_text_bgr,
            bold=True,
        )
    else:
        right = f"[U] KỸ THUẬT   ·   [P] {data.profile.value.title()}"
        _right_text(
            draw,
            (x1 - style.outer_padding_px, _sp(style, 20)),
            right,
            _sp(style, 17),
            style.chrome_muted_text_bgr,
        )


def _draw_product_panel(
    image: Image.Image,
    draw: ImageDraw.ImageDraw,
    layout: PresentationLayout,
    data: PresentationData,
    style: PresentationStyle,
) -> None:
    copy = build_product_copy(data, style=style)
    state = product_presentation_state(data)
    risk_indicator = {
        "low": style.card_success_bgr,
        "medium": style.card_warning_bgr,
        "high": style.card_warning_bgr,
    }.get(data.risk_level, style.muted_text_bgr)
    lighting_indicator = {
        "good": style.card_success_bgr,
        "medium": style.card_warning_bgr,
        "poor": style.card_warning_bgr,
    }.get(data.lighting_level, style.muted_text_bgr)
    color_icon = {
        ProductPresentationState.CAMERA_BLOCKED: ProductIcon.WARNING,
        ProductPresentationState.WAITING_FOR_GARMENT: ProductIcon.GARMENT,
        ProductPresentationState.ANALYZING: ProductIcon.PROCESSING,
        ProductPresentationState.RESULT_READY: ProductIcon.READY,
    }[state]
    color_indicator = (
        style.card_warning_bgr
        if state is ProductPresentationState.CAMERA_BLOCKED
        else style.card_info_bgr
    )
    color_card = (
        "MÀU TRANG PHỤC",
        copy["color"],
        copy["confidence"],
        data.original_color_rgb,
        color_indicator,
        color_icon,
        "primary",
    )
    risk_card = (
        "KHẢ NĂNG PHÂN BIỆT MÀU",
        copy["risk"],
        "Đánh giá theo cặp màu"
        if state is ProductPresentationState.RESULT_READY
        else "",
        None,
        risk_indicator,
        ProductIcon.RISK,
        "inactive" if state is not ProductPresentationState.RESULT_READY else "normal",
    )
    lighting_needs_action = data.lighting_level in {"medium", "poor"} and state not in {
        ProductPresentationState.CAMERA_BLOCKED,
    }
    lighting_card = (
        "ÁNH SÁNG",
        copy["lighting"],
        "Điều chỉnh để màu ổn định hơn",
        None,
        style.card_warning_bgr if lighting_needs_action else lighting_indicator,
        ProductIcon.WARNING if lighting_needs_action else ProductIcon.LIGHTING,
        (
            "warning"
            if lighting_needs_action
            else (
                "inactive"
                if state is ProductPresentationState.CAMERA_BLOCKED
                else "normal"
            )
        ),
    )
    matching_card = (
        "GỢI Ý PHỐI MÀU",
        copy["guidance"],
        "Gợi ý tham khảo"
        if state is ProductPresentationState.RESULT_READY
        else "",
        None,
        style.card_recommendation_bgr,
        ProductIcon.MATCHING,
        "inactive" if state is not ProductPresentationState.RESULT_READY else "normal",
    )
    cards = (
        (color_card, lighting_card, risk_card, matching_card)
        if lighting_needs_action
        else (color_card, risk_card, matching_card, lighting_card)
    )
    for rect, (title, value, detail, swatch, indicator, icon, emphasis) in zip(
        _product_card_rectangles(layout, style), cards, strict=True
    ):
        _draw_product_card(
            image,
            draw,
            rect,
            title=title,
            value=value,
            detail=detail,
            swatch=swatch,
            indicator_bgr=indicator,
            icon=icon,
            emphasis=emphasis,
            style=style,
        )


def _draw_product_card(
    image: Image.Image,
    draw: ImageDraw.ImageDraw,
    rect: tuple[int, int, int, int],
    *,
    title: str,
    value: str,
    detail: str,
    swatch: RGBColor | None,
    indicator_bgr: tuple[int, int, int],
    icon: ProductIcon,
    emphasis: str,
    style: PresentationStyle,
) -> None:
    """Draw one card with disjoint, line-limited title/value/detail regions."""

    x0, y0, x1, y1 = rect
    width = x1 - x0
    height = y1 - y0
    if emphasis not in {"primary", "warning", "normal", "inactive"}:
        raise ValueError("unsupported Product card emphasis")
    is_primary = emphasis == "primary"
    radius = _sp(style, 18)
    shadow_depth = _card_elevation_px(emphasis, style)
    card_surface_rgb = _rgb(
        style.primary_card_bgr if is_primary else style.card_bgr
    )
    if shadow_depth > 0:
        _draw_aa_rounded_rectangle(
            image,
            (x0, y0, x1 - 1, y1 - 1),
            radius=radius,
            fill=_shade_rgb(
                card_surface_rgb,
                0.14 if is_primary else 0.10,
            ),
        )
    surface_y1 = y1 - shadow_depth
    card_outline = indicator_bgr if emphasis in {"primary", "warning"} else None
    _draw_aa_rounded_rectangle(
        image,
        (x0, y0, x1 - 1, surface_y1 - 1),
        radius=radius,
        fill=card_surface_rgb,
        outline=None if card_outline is None else _rgb(card_outline),
        width=_sp(style, 2) if emphasis in {"primary", "warning"} else 1,
    )
    highlight_y = y0 + max(1, _sp(style, 1))
    draw.line(
        (
            x0 + radius,
            highlight_y,
            x1 - radius - 1,
            highlight_y,
        ),
        fill=_highlight_rgb(card_surface_rgb, 0.08 if is_primary else 0.05),
        width=max(1, _sp(style, 1)),
    )
    if is_primary:
        _draw_aa_rounded_rectangle(
            image,
            (
                x0 + _sp(style, 7),
                y0 + _sp(style, 12),
                x0 + _sp(style, 11),
                surface_y1 - _sp(style, 12),
            ),
            radius=_sp(style, 2),
            fill=_rgb(indicator_bgr),
        )

    regions = _product_card_regions(
        width,
        surface_y1 - y0,
        has_swatch=swatch is not None,
        scale=style.ui_scale,
    )
    indicator_x = x0 + _sp(style, 24)
    indicator_y = y0 + _sp(style, 15)
    _draw_product_icon(
        image,
        center=(indicator_x, indicator_y),
        icon=icon,
        color_bgr=indicator_bgr,
        style=style,
    )

    _single_line_in_region(
        draw,
        _offset_rect(regions.title, x0, y0),
        title,
        _sp(style, 13),
        style.muted_text_bgr,
        bold=True,
    )
    _bounded_text_in_region(
        draw,
        _offset_rect(regions.value, x0, y0),
        value,
        _sp(style, 22 if is_primary else (17 if emphasis == "inactive" else 20)),
        style.muted_text_bgr if emphasis == "inactive" else style.text_bgr,
        maximum_lines=2,
        bold=emphasis != "inactive",
    )
    _single_line_in_region(
        draw,
        _offset_rect(regions.detail, x0, y0),
        detail,
        _sp(style, 13),
        style.muted_text_bgr,
    )
    if swatch is not None and regions.swatch is not None:
        if regions.swatch[3] > regions.swatch[1]:
            _draw_aa_rounded_rectangle(
                image,
                _offset_rect(regions.swatch, x0, y0),
                radius=_sp(style, 8),
                fill=tuple(int(channel) for channel in swatch),
                outline=(245, 245, 245),
                width=_sp(style, 2),
            )


def _draw_product_icon(
    image: Image.Image,
    *,
    center: tuple[int, int],
    icon: ProductIcon,
    color_bgr: tuple[int, int, int],
    style: PresentationStyle,
) -> None:
    """Draw a compact status glyph whose silhouette remains meaningful in mono."""

    cx, cy = center
    radius = _sp(style, 6)
    stroke = max(1, _sp(style, 2))
    color = _rgb(color_bgr)
    patch = _antialiased_product_icon(icon, radius, stroke, color)
    image.paste(
        patch,
        (cx - patch.width // 2, cy - patch.height // 2),
        patch,
    )


@lru_cache(maxsize=96)
def _antialiased_product_icon(
    icon: ProductIcon,
    radius: int,
    stroke: int,
    color: tuple[int, int, int],
) -> Image.Image:
    """Rasterize one small shape-coded icon at 4x and cache the result."""

    supersample = 4
    padding = max(3, stroke + 1)
    size = 2 * (radius + padding) + 1
    high_size = size * supersample
    patch = Image.new("RGBA", (high_size, high_size), (0, 0, 0, 0))
    icon_draw = ImageDraw.Draw(patch)
    cx = cy = high_size // 2
    _paint_product_icon(
        icon_draw,
        center=(cx, cy),
        icon=icon,
        radius=radius * supersample,
        stroke=stroke * supersample,
        color=color + (255,),
    )
    return patch.resize((size, size), Image.Resampling.LANCZOS)


def _paint_product_icon(
    draw: ImageDraw.ImageDraw,
    *,
    center: tuple[int, int],
    icon: ProductIcon,
    radius: int,
    stroke: int,
    color: tuple[int, int, int, int],
) -> None:
    """Paint icon geometry onto an RGBA surface at the requested density."""

    cx, cy = center
    if icon is ProductIcon.GARMENT:
        draw.polygon(
            (
                (cx - radius, cy - radius // 2),
                (cx - radius // 2, cy - radius),
                (cx - radius // 4, cy - radius // 2),
                (cx + radius // 4, cy - radius // 2),
                (cx + radius // 2, cy - radius),
                (cx + radius, cy - radius // 2),
                (cx + radius // 2, cy + radius // 4),
                (cx + radius // 2, cy + radius),
                (cx - radius // 2, cy + radius),
                (cx - radius // 2, cy + radius // 4),
            ),
            fill=color,
        )
    elif icon is ProductIcon.PROCESSING:
        draw.arc(
            (cx - radius, cy - radius, cx + radius, cy + radius),
            start=25,
            end=300,
            fill=color,
            width=stroke,
        )
        draw.ellipse(
            (cx + radius - stroke, cy - stroke, cx + radius + stroke, cy + stroke),
            fill=color,
        )
    elif icon is ProductIcon.READY:
        draw.ellipse(
            (cx - radius, cy - radius, cx + radius, cy + radius),
            outline=color,
            width=stroke,
        )
        draw.line(
            (
                cx - radius // 2,
                cy,
                cx - radius // 6,
                cy + radius // 2,
                cx + radius * 3 // 4,
                cy - radius // 2,
            ),
            fill=color,
            width=stroke,
            joint="curve",
        )
    elif icon is ProductIcon.WARNING:
        draw.polygon(
            (
                (cx, cy - radius),
                (cx + radius, cy + radius),
                (cx - radius, cy + radius),
            ),
            outline=color,
            width=stroke,
        )
        draw.line((cx, cy - radius // 2, cx, cy + radius // 3), fill=color, width=stroke)
        dot_radius = max(1, stroke // 2)
        draw.ellipse(
            (
                cx - dot_radius,
                cy + radius // 2,
                cx + dot_radius,
                cy + radius // 2 + 2 * dot_radius,
            ),
            fill=color,
        )
    elif icon is ProductIcon.RISK:
        draw.polygon(
            (
                (cx, cy - radius),
                (cx + radius, cy - radius // 2),
                (cx + radius * 2 // 3, cy + radius // 2),
                (cx, cy + radius),
                (cx - radius * 2 // 3, cy + radius // 2),
                (cx - radius, cy - radius // 2),
            ),
            outline=color,
            width=stroke,
        )
    elif icon is ProductIcon.LIGHTING:
        bulb_radius = max(2, radius // 2)
        draw.ellipse(
            (cx - bulb_radius, cy - radius, cx + bulb_radius, cy),
            outline=color,
            width=stroke,
        )
        baseline_offset = max(1, stroke)
        draw.line(
            (cx - bulb_radius, cy + baseline_offset, cx + bulb_radius, cy + baseline_offset),
            fill=color,
            width=stroke,
        )
        draw.line(
            (cx - radius, cy - radius // 2, cx - radius - stroke, cy - radius // 2),
            fill=color,
            width=stroke,
        )
        draw.line(
            (cx + radius, cy - radius // 2, cx + radius + stroke, cy - radius // 2),
            fill=color,
            width=stroke,
        )
    elif icon is ProductIcon.MATCHING:
        draw.polygon(
            (
                (cx, cy - radius),
                (cx + radius, cy),
                (cx, cy + radius),
                (cx - radius, cy),
            ),
            outline=color,
            width=stroke,
        )
        draw.ellipse(
            (cx - stroke, cy - stroke, cx + stroke, cy + stroke),
            fill=color,
        )
    elif icon is ProductIcon.PROFILE:
        head_radius = max(stroke, radius // 3)
        draw.ellipse(
            (
                cx - head_radius,
                cy - radius,
                cx + head_radius,
                cy - radius + 2 * head_radius,
            ),
            fill=color,
        )
        draw.arc(
            (cx - radius, cy - radius // 3, cx + radius, cy + radius),
            start=190,
            end=350,
            fill=color,
            width=stroke,
        )


def _camera_shell_rect(
    layout: PresentationLayout,
    style: PresentationStyle,
) -> tuple[int, int, int, int]:
    """Return the outer camera component boundary using exclusive edges."""

    x0, y0, x1, y1 = layout.camera_rect
    bezel_width = _sp(style, _CAMERA_BEZEL_LOGICAL_PX)
    return (
        x0 - bezel_width,
        y0 - bezel_width,
        x1 + bezel_width,
        y1 + bezel_width,
    )


def _product_sidebar_rect(
    layout: PresentationLayout,
    style: PresentationStyle,
) -> tuple[int, int, int, int]:
    """Return Product bounds shared with the camera shell when space permits.

    Source-sized legacy canvases can be too short for four readable cards.
    They retain the existing content-height panel instead of compressing text.
    """

    panel_x0, panel_y0, panel_x1, panel_y1 = layout.panel_rect
    _, shell_y0, _, shell_y1 = _camera_shell_rect(layout, style)
    minimum_height = _sp(style, _MIN_ALIGNED_PRODUCT_STACK_LOGICAL_PX)
    if shell_y1 - shell_y0 < minimum_height:
        return layout.panel_rect
    return (panel_x0, shell_y0, panel_x1, shell_y1)


def _product_card_rectangles(
    layout: PresentationLayout,
    style: PresentationStyle | None = None,
) -> tuple[tuple[int, int, int, int], ...]:
    """Allocate four cards from one Product-sidebar geometry contract."""

    active = style or PresentationStyle()
    sidebar_rect = _product_sidebar_rect(layout, active)
    x0, y0, x1, y1 = sidebar_rect
    aligned_to_camera = sidebar_rect != layout.panel_rect
    scale = max(1.0, active.ui_scale)
    gap = max(10, round(10 * scale))
    horizontal_padding = max(14, round(14 * scale))
    vertical_padding = 0 if aligned_to_camera else horizontal_padding
    usable_height = y1 - y0 - 2 * vertical_padding - 3 * gap
    heights = [
        round(usable_height * 0.27),
        round(usable_height * 0.25),
        round(usable_height * 0.24),
    ]
    heights.append(usable_height - sum(heights))
    rectangles: list[tuple[int, int, int, int]] = []
    cursor_y = y0 + vertical_padding
    for card_height in heights:
        rectangles.append(
            (
                x0 + horizontal_padding,
                cursor_y,
                x1 - horizontal_padding,
                cursor_y + card_height,
            )
        )
        cursor_y += card_height + gap
    return tuple(rectangles)


def _product_card_regions(
    width: int, height: int, *, has_swatch: bool, scale: float = 1.0
) -> ProductCardRegions:
    """Reserve disjoint title/value/detail areas inside one clipped card."""

    horizontal_padding = max(1, round(14 * scale))
    title = (
        round(36 * scale),
        round(7 * scale),
        width - horizontal_padding,
        round(24 * scale),
    )
    detail = (
        horizontal_padding,
        height - round(29 * scale),
        width - horizontal_padding,
        height - round(12 * scale),
    )
    value_left = horizontal_padding + (round(56 * scale) if has_swatch else 0)
    value = (
        value_left,
        title[3] + round(4 * scale),
        width - horizontal_padding,
        detail[1] - round(4 * scale),
    )
    swatch = None
    if has_swatch:
        swatch = (
            horizontal_padding,
            value[1],
            horizontal_padding + round(44 * scale),
            min(value[3], value[1] + round(44 * scale)),
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
    pad = _sp(style, 16)
    title_size = _sp(style, 15)
    body_size = _sp(style, 13)
    line_step = _sp(style, 19)
    _text(
        draw,
        (x0 + pad, y0 + _sp(style, 14)),
        "THÔNG TIN KỸ THUẬT",
        title_size,
        style.primary_bgr,
        bold=True,
    )
    cursor_y = y0 + _sp(style, 45)
    maximum_width = x1 - x0 - 2 * pad
    for line in data.diagnostic_lines:
        wrapped = _wrap_text(line, maximum_width, body_size)
        for part in wrapped[:2]:
            if cursor_y + line_step >= y1 - pad:
                return
            _text(draw, (x0 + pad, cursor_y), part, body_size, style.chrome_text_bgr)
            cursor_y += line_step
        cursor_y += _sp(style, 5)


def _draw_footer(
    image: Image.Image,
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
        state = product_presentation_state(data)
        if camera_cover_enabled:
            state_label = "Hình ảnh đang được ẩn"
            state_icon = ProductIcon.GARMENT
            state_color = style.primary_bgr
        else:
            state_label, state_icon, state_color = {
                ProductPresentationState.CAMERA_BLOCKED: (
                    "Không nhận được hình camera",
                    ProductIcon.WARNING,
                    style.warning_bgr,
                ),
                ProductPresentationState.WAITING_FOR_GARMENT: (
                    "Đang chờ trang phục",
                    ProductIcon.GARMENT,
                    style.primary_bgr,
                ),
                ProductPresentationState.ANALYZING: (
                    "Đang phân tích màu",
                    ProductIcon.PROCESSING,
                    style.primary_bgr,
                ),
                ProductPresentationState.RESULT_READY: (
                    "Kết quả đã sẵn sàng",
                    ProductIcon.READY,
                    style.success_bgr,
                ),
            }[state]
        icon_x = style.outer_padding_px + _sp(style, 8)
        icon_y = y0 + _sp(style, 17)
        _draw_product_icon(
            image,
            center=(icon_x, icon_y),
            icon=state_icon,
            color_bgr=state_color,
            style=style,
        )
        _single_line_in_region(
            draw,
            (
                icon_x + _sp(style, 16),
                y0 + _sp(style, 8),
                round(x1 * 0.58),
                y0 + _sp(style, 31),
            ),
            state_label,
            _sp(style, 14),
            style.chrome_text_bgr,
            bold=True,
        )
        midpoint = round(x1 * 0.62)
        _single_line_in_region(
            draw,
            (
                style.outer_padding_px,
                y0 + _sp(style, 36),
                midpoint - _sp(style, 8),
                y0 + _sp(style, 60),
            ),
        (
            "Nhấn C để hiển thị lại hình camera."
            if camera_cover_enabled
            else build_product_copy(data, style=style)["action"]
        ),
            _sp(style, 14),
            style.primary_bgr,
        )
        _single_line_in_region(
            draw,
            (
                midpoint,
                y0 + _sp(style, 38),
                x1 - style.outer_padding_px,
                y0 + _sp(style, 60),
            ),
            f"[R] Hỗ trợ màu: {support}   [F] Toàn màn hình   [P] Hồ sơ   [Q] Thoát",
            _sp(style, 12),
            style.chrome_muted_text_bgr,
        )
        return
    else:
        cover = "on" if camera_cover_enabled else "off"
        left = (
            f"Nguồn: {data.source_name} | Hỗ trợ={support} | "
            f"view={data.view_name} | cover={cover}"
        )
        keys = (
            "F fullscreen | Esc windowed | Q quit | C cover | T theme | "
            "U product/diagnostic | P profile | [/] severity | R recolor | V/1-5 view"
        )
        _single_line_in_region(
            draw,
            (
                style.outer_padding_px,
                y0 + _sp(style, 7),
                x1 - style.outer_padding_px,
                y0 + _sp(style, 31),
            ),
            left,
            _sp(style, 14),
            style.chrome_text_bgr,
        )
        _single_line_in_region(
            draw,
            (
                style.outer_padding_px,
                y0 + _sp(style, 34),
                x1 - style.outer_padding_px,
                y0 + _sp(style, 60),
            ),
            keys,
            _sp(style, 12),
            style.chrome_muted_text_bgr,
        )
        return
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
    *,
    bold: bool = False,
) -> None:
    font = _font(size, bold=bold)
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


def _rgb(color_bgr: tuple[int, int, int]) -> tuple[int, int, int]:
    return (color_bgr[2], color_bgr[1], color_bgr[0])


def _highlight_rgb(
    color_rgb: tuple[int, int, int], amount: float
) -> tuple[int, int, int]:
    """Lift an RGB surface toward white for a restrained material highlight."""

    bounded = float(np.clip(amount, 0.0, 1.0))
    return tuple(round(channel + (255 - channel) * bounded) for channel in color_rgb)


def _shade_rgb(
    color_rgb: tuple[int, int, int], amount: float
) -> tuple[int, int, int]:
    """Darken an RGB surface by a bounded fraction for restrained elevation."""

    factor = 1.0 - float(np.clip(amount, 0.0, 1.0))
    return tuple(round(channel * factor) for channel in color_rgb)


def _card_elevation_px(emphasis: str, style: PresentationStyle) -> int:
    """Return the explicit Product elevation tier in final display pixels."""

    depths = {
        "primary": 2,
        "warning": 1,
        "normal": 1,
        "inactive": 0,
    }
    try:
        depth = depths[emphasis]
    except KeyError as exc:
        raise ValueError("unsupported Product card emphasis") from exc
    return 0 if depth == 0 else _sp(style, depth)


def _clip_rounded_content_corners(
    image: Image.Image,
    rect: tuple[int, int, int, int],
    *,
    radius: int,
    outside_rgb: tuple[int, int, int],
) -> None:
    """Clip a rectangular bitmap by compositing only four rounded cutouts."""

    x0, y0, x1, y1 = rect
    effective_radius = min(max(1, radius), (x1 - x0) // 2, (y1 - y0) // 2)
    corners = _rounded_corner_cutouts(effective_radius, outside_rgb)
    positions = (
        (x0, y0),
        (x1 - effective_radius, y0),
        (x0, y1 - effective_radius),
        (x1 - effective_radius, y1 - effective_radius),
    )
    for corner, position in zip(corners, positions, strict=True):
        image.paste(corner, position, corner)


@lru_cache(maxsize=32)
def _rounded_corner_cutouts(
    radius: int,
    outside_rgb: tuple[int, int, int],
) -> tuple[Image.Image, Image.Image, Image.Image, Image.Image]:
    """Return antialiased outer-corner overlays for one rounded content radius."""

    supersample = 4
    diameter = radius * 2
    high_diameter = diameter * supersample
    high_mask = Image.new("L", (high_diameter, high_diameter), 0)
    ImageDraw.Draw(high_mask).rounded_rectangle(
        (0, 0, high_diameter - 1, high_diameter - 1),
        radius=radius * supersample,
        fill=255,
    )
    content_mask = high_mask.resize((diameter, diameter), Image.Resampling.LANCZOS)
    outside_alpha = content_mask.point(lambda value: 255 - value)
    overlay = Image.new("RGBA", (diameter, diameter), outside_rgb + (0,))
    overlay.putalpha(outside_alpha)
    return (
        overlay.crop((0, 0, radius, radius)),
        overlay.crop((radius, 0, diameter, radius)),
        overlay.crop((0, radius, radius, diameter)),
        overlay.crop((radius, radius, diameter, diameter)),
    )


def _draw_aa_rounded_rectangle(
    image: Image.Image,
    box: tuple[int, int, int, int],
    *,
    radius: int,
    fill: tuple[int, int, int] | None = None,
    outline: tuple[int, int, int] | None = None,
    width: int = 1,
) -> None:
    """Composite supersampled corners with native, pixel-aligned interiors."""

    x0, y0, x1, y1 = box
    patch_width = x1 - x0 + 1
    patch_height = y1 - y0 + 1
    if patch_width <= 0 or patch_height <= 0:
        return
    effective_radius = min(max(0, radius), patch_width // 2, patch_height // 2)
    native_draw = ImageDraw.Draw(image)
    if fill is not None:
        if effective_radius == 0:
            native_draw.rectangle(box, fill=fill)
        else:
            native_draw.rectangle(
                (x0 + effective_radius, y0, x1 - effective_radius, y1),
                fill=fill,
            )
            native_draw.rectangle(
                (x0, y0 + effective_radius, x1, y1 - effective_radius),
                fill=fill,
            )
    if outline is not None:
        edge_width = min(max(1, width), patch_width, patch_height)
        native_draw.rectangle(
            (x0 + effective_radius, y0, x1 - effective_radius, y0 + edge_width - 1),
            fill=outline,
        )
        native_draw.rectangle(
            (x0 + effective_radius, y1 - edge_width + 1, x1 - effective_radius, y1),
            fill=outline,
        )
        native_draw.rectangle(
            (x0, y0 + effective_radius, x0 + edge_width - 1, y1 - effective_radius),
            fill=outline,
        )
        native_draw.rectangle(
            (x1 - edge_width + 1, y0 + effective_radius, x1, y1 - effective_radius),
            fill=outline,
        )
    if effective_radius == 0:
        return

    # Alpha-composite only the curved corner neighborhoods. The large opaque
    # interior and straight pixel-aligned edges above do not benefit from 4x
    # rasterization, and avoiding their per-frame blend keeps UI cost bounded.
    extent = min(
        effective_radius + max(2, width + 1),
        patch_width // 2,
        patch_height // 2,
    )
    corner_images = _antialiased_rounded_corners(
        patch_width,
        patch_height,
        effective_radius,
        fill,
        outline,
        max(1, width),
        extent,
    )
    destinations = (
        (x0, y0),
        (x1 - extent + 1, y0),
        (x0, y1 - extent + 1),
        (x1 - extent + 1, y1 - extent + 1),
    )
    for corner, destination in zip(corner_images, destinations, strict=True):
        image.paste(corner, destination, corner)


@lru_cache(maxsize=32)
def _antialiased_rounded_patch(
    width: int,
    height: int,
    radius: int,
    fill: tuple[int, int, int] | None,
    outline: tuple[int, int, int] | None,
    outline_width: int,
) -> Image.Image:
    """Render reusable UI chrome at 4x then downsample with Lanczos."""

    supersample = 4
    high_width = width * supersample
    high_height = height * supersample
    patch = Image.new("RGBA", (high_width, high_height), (0, 0, 0, 0))
    patch_draw = ImageDraw.Draw(patch)
    effective_radius = min(radius, width // 2, height // 2) * supersample
    patch_draw.rounded_rectangle(
        (0, 0, high_width - 1, high_height - 1),
        radius=effective_radius,
        fill=None if fill is None else fill + (255,),
        outline=None if outline is None else outline + (255,),
        width=outline_width * supersample,
    )
    return patch.resize((width, height), Image.Resampling.LANCZOS)


@lru_cache(maxsize=64)
def _antialiased_rounded_corners(
    width: int,
    height: int,
    radius: int,
    fill: tuple[int, int, int] | None,
    outline: tuple[int, int, int] | None,
    outline_width: int,
    extent: int,
) -> tuple[Image.Image, Image.Image, Image.Image, Image.Image]:
    """Crop reusable AA corner tiles once instead of once per rendered frame."""

    patch = _antialiased_rounded_patch(
        width,
        height,
        radius,
        fill,
        outline,
        outline_width,
    )
    return (
        patch.crop((0, 0, extent, extent)),
        patch.crop((width - extent, 0, width, extent)),
        patch.crop((0, height - extent, extent, height)),
        patch.crop((width - extent, height - extent, width, height)),
    )


def _sp(style: PresentationStyle, value: int) -> int:
    """Scale one logical UI unit to the native presentation density."""

    return max(1, round(value * style.ui_scale))


def _validate_frame(frame: ColorFrame) -> None:
    if frame.dtype != np.uint8 or frame.ndim != 3 or frame.shape[2] != 3:
        raise ValueError("camera_bgr must be a uint8 H x W x 3 BGR frame")
    if frame.shape[0] == 0 or frame.shape[1] == 0:
        raise ValueError("camera_bgr dimensions must be non-empty")
