"""Base OpenCV preview renderer and lightweight frame telemetry."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from time import monotonic_ns
from typing import TYPE_CHECKING
import unicodedata

import cv2
import numpy as np

from chromalens.color_naming import RGBColor, vietnamese_color_label
from chromalens.config import CVDProfile
from chromalens.contracts import (
    BinaryMask,
    ColorFrame,
    FramePacket,
    LightingQuality,
    RiskAssessment,
)

if TYPE_CHECKING:
    from chromalens.pipeline import PipelineFrameResult


@dataclass(frozen=True, slots=True)
class PreviewStyle:
    """Configurable diagnostic-overlay appearance."""

    margin_px: int = 12
    line_height_px: int = 24
    font_scale: float = 0.55
    text_thickness_px: int = 1
    panel_opacity: float = 0.62
    foreground_bgr: tuple[int, int, int] = (255, 255, 255)
    panel_bgr: tuple[int, int, int] = (0, 0, 0)

    def __post_init__(self) -> None:
        if self.margin_px < 0:
            raise ValueError("margin_px must be non-negative")
        if self.line_height_px <= 0:
            raise ValueError("line_height_px must be positive")
        if self.font_scale <= 0.0:
            raise ValueError("font_scale must be positive")
        if self.text_thickness_px <= 0:
            raise ValueError("text_thickness_px must be positive")
        if not 0.0 <= self.panel_opacity <= 1.0:
            raise ValueError("panel_opacity must be within [0, 1]")


@dataclass(frozen=True, slots=True)
class PreviewTelemetry:
    """Basic display measurements, separate from later AI confidences."""

    processed_fps: float | None
    frame_age_at_overlay_ms: float


class OverlayView(str, Enum):
    """Explicitly distinguish the assistive result from debug simulation."""

    ASSISTIVE = "assistive"
    CVD_SIMULATION_DEBUG = "cvd-simulation-debug"


class PipelineView(str, Enum):
    """Selectable T08 views; simulation remains a separate T06 debug API."""

    ASSISTIVE = "assistive"
    ORIGINAL = "original"
    MASK = "mask"
    RISK = "risk"
    DIAGNOSTIC = "diagnostic"


@dataclass(frozen=True, slots=True)
class PipelineDisplayState:
    """Current user controls and live-capture status rendered on every view."""

    profile: CVDProfile
    severity: float
    recolor_enabled: bool
    view: PipelineView
    dropped_capture_frames: int = 0

    def __post_init__(self) -> None:
        if not isinstance(self.profile, CVDProfile):
            raise TypeError("profile must be a CVDProfile selected by the user")
        if not np.isfinite(self.severity) or not 0.0 <= self.severity <= 1.0:
            raise ValueError("severity must be finite within [0, 1]")
        if not isinstance(self.recolor_enabled, bool):
            raise TypeError("recolor_enabled must be boolean")
        if not isinstance(self.view, PipelineView):
            raise TypeError("view must be a PipelineView")
        if self.dropped_capture_frames < 0:
            raise ValueError("dropped_capture_frames must be non-negative")


@dataclass(frozen=True, slots=True)
class AssistiveOverlayData:
    """Typed score/tag content; measured and display colors stay separate."""

    frame_id: int
    original_color_name: str
    original_corrected_rgb: RGBColor
    assistive_display_rgb: RGBColor
    color_margin: float | None
    risk: RiskAssessment
    lighting_quality: LightingQuality | None
    profile: CVDProfile
    severity: float
    backend_name: str
    recolor_applied: bool
    mask_confidence: float | None = None
    degraded_reason: str | None = None
    view: OverlayView = OverlayView.ASSISTIVE

    def __post_init__(self) -> None:
        if self.frame_id < 0:
            raise ValueError("frame_id must be non-negative")
        if not self.original_color_name.strip():
            raise ValueError("original_color_name must not be empty")
        _validate_rgb_tuple(self.original_corrected_rgb, "original_corrected_rgb")
        _validate_rgb_tuple(self.assistive_display_rgb, "assistive_display_rgb")
        if self.color_margin is not None and (
            not np.isfinite(self.color_margin)
            or not 0.0 <= self.color_margin <= 1.0
        ):
            raise ValueError("color_margin must be finite within [0, 1]")
        if not isinstance(self.profile, CVDProfile):
            raise TypeError("profile must be a CVDProfile selected by the user")
        if not np.isfinite(self.severity) or not 0.0 <= self.severity <= 1.0:
            raise ValueError("severity must be finite within [0, 1]")
        if not self.backend_name.strip():
            raise ValueError("backend_name must not be empty")
        if self.mask_confidence is not None and (
            not np.isfinite(self.mask_confidence)
            or not 0.0 <= self.mask_confidence <= 1.0
        ):
            raise ValueError("mask_confidence must be finite within [0, 1]")
        if self.degraded_reason is not None and not self.degraded_reason.strip():
            raise ValueError("degraded_reason must not be blank")
        if not isinstance(self.view, OverlayView):
            raise TypeError("view must be an OverlayView")


@dataclass(frozen=True, slots=True)
class AssistiveOverlayStyle:
    """High-contrast tag and double-outline appearance."""

    margin_px: int = 10
    padding_px: int = 8
    line_height_px: int = 22
    font_scale: float = 0.48
    text_thickness_px: int = 1
    tag_background_bgr: tuple[int, int, int] = (0, 0, 0)
    tag_foreground_bgr: tuple[int, int, int] = (255, 255, 255)
    tag_border_bgr: tuple[int, int, int] = (255, 255, 255)
    tag_border_thickness_px: int = 2
    outline_black_thickness_px: int = 6
    outline_white_thickness_px: int = 2

    def __post_init__(self) -> None:
        for field_name in ("margin_px", "padding_px"):
            if getattr(self, field_name) < 0:
                raise ValueError(f"{field_name} must be non-negative")
        for field_name in (
            "line_height_px",
            "text_thickness_px",
            "tag_border_thickness_px",
            "outline_black_thickness_px",
            "outline_white_thickness_px",
        ):
            if getattr(self, field_name) <= 0:
                raise ValueError(f"{field_name} must be positive")
        if self.outline_black_thickness_px <= self.outline_white_thickness_px:
            raise ValueError("black outline must be thicker than white outline")
        if not np.isfinite(self.font_scale) or self.font_scale <= 0.0:
            raise ValueError("font_scale must be positive and finite")
        for field_name in (
            "tag_background_bgr",
            "tag_foreground_bgr",
            "tag_border_bgr",
        ):
            _validate_rgb_tuple(getattr(self, field_name), field_name)


@dataclass(slots=True)
class PreviewMetricsTracker:
    """Track an exponential moving average of rendered-frame throughput."""

    fps_ema_alpha: float = 0.2
    _last_observed_ns: int | None = None
    _fps_ema: float | None = None

    def __post_init__(self) -> None:
        if not 0.0 < self.fps_ema_alpha <= 1.0:
            raise ValueError("fps_ema_alpha must be within (0, 1]")

    def observe(
        self,
        packet: FramePacket,
        *,
        observed_ns: int | None = None,
    ) -> PreviewTelemetry:
        """Measure processing latency and update FPS at a monotonic instant."""

        now_ns = monotonic_ns() if observed_ns is None else observed_ns
        if now_ns < packet.timestamp_ns:
            raise ValueError("observed_ns must not precede packet.timestamp_ns")

        if self._last_observed_ns is not None and now_ns > self._last_observed_ns:
            instantaneous_fps = 1_000_000_000.0 / (now_ns - self._last_observed_ns)
            if self._fps_ema is None:
                self._fps_ema = instantaneous_fps
            else:
                alpha = self.fps_ema_alpha
                self._fps_ema = alpha * instantaneous_fps + (1.0 - alpha) * self._fps_ema
        self._last_observed_ns = now_ns

        return PreviewTelemetry(
            processed_fps=self._fps_ema,
            frame_age_at_overlay_ms=(now_ns - packet.timestamp_ns) / 1_000_000.0,
        )


def render_preview(
    packet: FramePacket,
    *,
    source_name: str,
    telemetry: PreviewTelemetry,
    style: PreviewStyle | None = None,
) -> ColorFrame:
    """Render T01 diagnostics onto a copy of the original BGR frame."""

    if not source_name.strip():
        raise ValueError("source_name must not be empty")
    active_style = PreviewStyle() if style is None else style
    rendered = packet.original_bgr.copy()
    height, width = rendered.shape[:2]
    fps_text = (
        "warming up" if telemetry.processed_fps is None else f"{telemetry.processed_fps:.1f}"
    )
    lines = (
        f"Source: {source_name}",
        f"Resolution: {width}x{height} | Frame: {packet.frame_id}",
        f"Processed FPS: {fps_text} | Frame age at overlay: "
        f"{telemetry.frame_age_at_overlay_ms:.1f} ms",
        "Press q or Esc to quit",
    )

    panel_height = min(
        height,
        active_style.margin_px * 2 + active_style.line_height_px * len(lines),
    )
    if panel_height > 0 and width > 0:
        overlay = rendered.copy()
        cv2.rectangle(
            overlay,
            (0, 0),
            (width, panel_height),
            active_style.panel_bgr,
            thickness=-1,
        )
        cv2.addWeighted(
            overlay,
            active_style.panel_opacity,
            rendered,
            1.0 - active_style.panel_opacity,
            0.0,
            dst=rendered,
        )

    for line_index, line in enumerate(lines):
        baseline_y = active_style.margin_px + active_style.line_height_px * (line_index + 1)
        if baseline_y >= height:
            break
        cv2.putText(
            rendered,
            line,
            (active_style.margin_px, baseline_y),
            cv2.FONT_HERSHEY_SIMPLEX,
            active_style.font_scale,
            active_style.foreground_bgr,
            active_style.text_thickness_px,
            lineType=cv2.LINE_AA,
        )
    return rendered


def build_assistive_overlay_lines(data: AssistiveOverlayData) -> tuple[str, ...]:
    """Build inspectable ASCII lines for OpenCV's Hershey font renderer."""

    view_line = (
        "VIEW: ASSISTIVE RESULT"
        if data.view is OverlayView.ASSISTIVE
        else "VIEW: CVD SIMULATION (DEBUG ONLY)"
    )
    vietnamese_label = _ascii_for_opencv(
        vietnamese_color_label(data.original_color_name)
    )
    margin = "unavailable" if data.color_margin is None else f"{data.color_margin:.3f}"
    lighting = (
        "unavailable"
        if data.lighting_quality is None
        else data.lighting_quality.level.value
    )
    mask_confidence = (
        "unavailable"
        if data.mask_confidence is None
        else f"{data.mask_confidence:.3f} heuristic"
    )
    degraded = (
        "none"
        if data.degraded_reason is None
        else _ascii_for_opencv(data.degraded_reason)
    )
    display_prefix = (
        "Assistive display"
        if data.view is OverlayView.ASSISTIVE
        else "Assistive target (separate)"
    )
    return (
        view_line,
        (
            f"Original corrected: {data.original_color_name}/{vietnamese_label} "
            f"RGB={data.original_corrected_rgb} | margin={margin}"
        ),
        (
            f"{display_prefix}: RGB={data.assistive_display_rgb} | "
            f"applied={'yes' if data.recolor_applied else 'no'}"
        ),
        (
            f"Mask confidence: {mask_confidence} | Risk: "
            f"{data.risk.risk_level} {data.risk.risk_score:.3f} | "
            f"lighting: {lighting}"
        ),
        (
            f"Profile: {data.profile.value} severity={data.severity:.2f} | "
            f"backend: {data.backend_name}"
        ),
        f"Frame: {data.frame_id} | degraded: {degraded}",
    )


def render_assistive_overlay(
    frame_bgr: ColorFrame,
    garment_mask: BinaryMask,
    data: AssistiveOverlayData,
    *,
    style: AssistiveOverlayStyle | None = None,
) -> ColorFrame:
    """Draw an explicitly assistive T06 result on a copied BGR frame."""

    if data.view is not OverlayView.ASSISTIVE:
        raise ValueError(
            "render_assistive_overlay requires view=ASSISTIVE; use the explicit "
            "CVD simulation debug renderer for simulated pixels"
        )
    return _render_labeled_overlay(frame_bgr, garment_mask, data, style=style)


def render_cvd_simulation_debug_overlay(
    frame_bgr: ColorFrame,
    garment_mask: BinaryMask,
    data: AssistiveOverlayData,
    *,
    style: AssistiveOverlayStyle | None = None,
) -> ColorFrame:
    """Draw a CVD simulation with a mandatory ``DEBUG ONLY`` view contract."""

    if data.view is not OverlayView.CVD_SIMULATION_DEBUG:
        raise ValueError(
            "CVD simulation debug renderer requires view=CVD_SIMULATION_DEBUG"
        )
    return _render_labeled_overlay(frame_bgr, garment_mask, data, style=style)


def _render_labeled_overlay(
    frame_bgr: ColorFrame,
    garment_mask: BinaryMask,
    data: AssistiveOverlayData,
    *,
    style: AssistiveOverlayStyle | None = None,
) -> ColorFrame:
    """Render the validated view label, outline, and score tag."""

    _validate_render_frame(frame_bgr)
    if (
        garment_mask.dtype != np.bool_
        or garment_mask.ndim != 2
        or garment_mask.shape != frame_bgr.shape[:2]
    ):
        raise ValueError("garment_mask must be an aligned boolean H x W mask")
    active_style = style or AssistiveOverlayStyle()
    rendered = frame_bgr.copy()
    contours, _ = cv2.findContours(
        garment_mask.astype(np.uint8),
        cv2.RETR_EXTERNAL,
        cv2.CHAIN_APPROX_SIMPLE,
    )
    if contours:
        cv2.drawContours(
            rendered,
            contours,
            contourIdx=-1,
            color=(0, 0, 0),
            thickness=active_style.outline_black_thickness_px,
            lineType=cv2.LINE_8,
        )
        cv2.drawContours(
            rendered,
            contours,
            contourIdx=-1,
            color=(255, 255, 255),
            thickness=active_style.outline_white_thickness_px,
            lineType=cv2.LINE_8,
        )

    lines = build_assistive_overlay_lines(data)
    height, width = rendered.shape[:2]
    x0 = min(active_style.margin_px, max(0, width - 1))
    y0 = min(active_style.margin_px, max(0, height - 1))
    available_width = max(1, width - x0 - active_style.margin_px)
    fitted_lines = tuple(
        _fit_text_to_width(line, available_width - 2 * active_style.padding_px, active_style)
        for line in lines
    )
    text_widths = (
        cv2.getTextSize(
            line,
            cv2.FONT_HERSHEY_SIMPLEX,
            active_style.font_scale,
            active_style.text_thickness_px,
        )[0][0]
        for line in fitted_lines
    )
    panel_width = min(
        available_width,
        max(text_widths, default=0) + 2 * active_style.padding_px,
    )
    panel_height = min(
        max(1, height - y0),
        2 * active_style.padding_px + active_style.line_height_px * len(lines),
    )
    x1 = min(width - 1, x0 + max(1, panel_width))
    y1 = min(height - 1, y0 + max(1, panel_height))
    cv2.rectangle(
        rendered,
        (x0, y0),
        (x1, y1),
        active_style.tag_background_bgr,
        thickness=-1,
    )
    cv2.rectangle(
        rendered,
        (x0, y0),
        (x1, y1),
        active_style.tag_border_bgr,
        thickness=active_style.tag_border_thickness_px,
    )
    for index, line in enumerate(fitted_lines):
        baseline_y = (
            y0
            + active_style.padding_px
            + active_style.line_height_px * (index + 1)
        )
        if baseline_y >= y1:
            break
        cv2.putText(
            rendered,
            line,
            (x0 + active_style.padding_px, baseline_y),
            cv2.FONT_HERSHEY_SIMPLEX,
            active_style.font_scale,
            active_style.tag_foreground_bgr,
            active_style.text_thickness_px,
            lineType=cv2.LINE_AA,
        )
    return rendered


def render_pipeline_view(
    result: "PipelineFrameResult",
    *,
    source_name: str,
    telemetry: PreviewTelemetry,
    display_state: PipelineDisplayState,
) -> ColorFrame:
    """Render one T08 view using only analysis for the displayed frame ID."""

    if not source_name.strip():
        raise ValueError("source_name must not be empty")
    if result.analysis_frame_id != result.packet.frame_id:
        raise ValueError("stale analysis must not be rendered as the current frame")

    if display_state.view is PipelineView.ASSISTIVE:
        rendered = _render_pipeline_assistive(result, display_state)
    else:
        rendered = _pipeline_base_view(result, display_state.view)
        if result.primary_region is not None:
            _draw_double_outline(rendered, result.primary_region.mask)
        _draw_pipeline_status_panel(
            rendered,
            _pipeline_status_lines(result, display_state),
        )

    _draw_pipeline_footer(
        rendered,
        source_name=source_name,
        telemetry=telemetry,
        display_state=display_state,
    )
    return rendered


def _render_pipeline_assistive(
    result: "PipelineFrameResult",
    display_state: PipelineDisplayState,
) -> ColorFrame:
    region = result.primary_region
    cluster = result.primary_cluster
    risk = result.risk
    if region is None or cluster is None or risk is None:
        rendered = result.assistive_bgr
        if region is not None:
            _draw_double_outline(rendered, region.mask)
        _draw_pipeline_status_panel(
            rendered,
            _pipeline_status_lines(result, display_state),
        )
        return rendered

    recolor_debug = result.recolor.debug if result.recolor is not None else None
    overlay_data = AssistiveOverlayData(
        frame_id=result.packet.frame_id,
        original_color_name=cluster.original_name,
        original_corrected_rgb=cluster.rgb,
        assistive_display_rgb=(
            recolor_debug.assistive_display_rgb
            if recolor_debug is not None
            else cluster.rgb
        ),
        color_margin=cluster.color_margin,
        risk=risk,
        lighting_quality=result.packet.lighting_quality,
        profile=display_state.profile,
        severity=display_state.severity,
        backend_name=result.backend_name,
        recolor_applied=(
            bool(recolor_debug.applied)
            if recolor_debug is not None and display_state.recolor_enabled
            else False
        ),
        mask_confidence=region.mask_confidence,
        degraded_reason=(
            result.degraded_reasons[0] if result.degraded_reasons else None
        ),
    )
    return render_assistive_overlay(
        result.assistive_bgr,
        region.mask,
        overlay_data,
    )


def _pipeline_base_view(
    result: "PipelineFrameResult",
    view: PipelineView,
) -> ColorFrame:
    if view is PipelineView.ORIGINAL:
        return result.packet.original_bgr.copy()
    if view is PipelineView.MASK:
        rendered = result.packet.original_bgr.copy()
        overlay = rendered.copy()
        for region in result.regions:
            overlay[region.mask] = (0, 220, 0)
        cv2.addWeighted(overlay, 0.42, rendered, 0.58, 0.0, dst=rendered)
        return rendered
    if view is PipelineView.RISK:
        rendered = result.packet.original_bgr.copy()
        if np.any(result.risk_mask):
            overlay = rendered.copy()
            overlay[result.risk_mask] = (0, 80, 255)
            cv2.addWeighted(overlay, 0.52, rendered, 0.48, 0.0, dst=rendered)
        return rendered
    if view is PipelineView.DIAGNOSTIC:
        if result.packet.corrected_rgb is None:
            rendered = result.packet.original_bgr.copy()
        else:
            rendered = cv2.cvtColor(
                result.packet.corrected_rgb,
                cv2.COLOR_RGB2BGR,
            )
        overlay = rendered.copy()
        for cluster in result.clusters:
            overlay[cluster.submask] = cluster.rgb[::-1]
        cv2.addWeighted(overlay, 0.32, rendered, 0.68, 0.0, dst=rendered)
        return rendered
    raise ValueError(f"unsupported non-assistive pipeline view: {view!r}")


def _pipeline_status_lines(
    result: "PipelineFrameResult",
    display_state: PipelineDisplayState,
) -> tuple[str, ...]:
    cluster = result.primary_cluster
    region = result.primary_region
    risk = result.risk
    color_text = (
        "Original corrected: unavailable | margin=unavailable"
        if cluster is None
        else (
            f"Original corrected: {cluster.original_name}/"
            f"{_ascii_for_opencv(vietnamese_color_label(cluster.original_name))} "
            f"RGB={cluster.rgb} | margin="
            f"{'unavailable' if cluster.color_margin is None else f'{cluster.color_margin:.3f}'}"
        )
    )
    mask_confidence = (
        "unavailable"
        if region is None or region.mask_confidence is None
        else f"{region.mask_confidence:.3f} heuristic"
    )
    risk_text = (
        "unavailable"
        if risk is None
        else f"{risk.risk_level} {risk.risk_score:.3f}"
    )
    lighting = (
        "unavailable"
        if result.packet.lighting_quality is None
        else result.packet.lighting_quality.level.value
    )
    degraded = (
        "none"
        if not result.degraded_reasons
        else _ascii_for_opencv(result.degraded_reasons[0])
    )
    guidance = "unavailable"
    if result.matching is not None and result.matching.suggestions:
        first = result.matching.suggestions[0]
        guidance = (
            f"{first.target_name} ({first.harmony.value}); guidance only, not objective"
        )
    return (
        f"VIEW: {display_state.view.value.upper()} | "
        f"Analysis: current frame {result.analysis_frame_id}",
        color_text,
        f"Mask confidence: {mask_confidence} | CVD risk: {risk_text}",
        (
            f"Lighting: {lighting} | profile={display_state.profile.value} "
            f"severity={display_state.severity:.2f}"
        ),
        f"Backend: {result.backend_name}",
        f"Degraded: {degraded}",
        f"Match guidance: {guidance}",
    )


def _draw_double_outline(frame: ColorFrame, mask: BinaryMask) -> None:
    contours, _ = cv2.findContours(
        mask.astype(np.uint8),
        cv2.RETR_EXTERNAL,
        cv2.CHAIN_APPROX_SIMPLE,
    )
    if not contours:
        return
    cv2.drawContours(frame, contours, -1, (0, 0, 0), 6, cv2.LINE_8)
    cv2.drawContours(frame, contours, -1, (255, 255, 255), 2, cv2.LINE_8)


def _draw_pipeline_status_panel(
    frame: ColorFrame,
    lines: tuple[str, ...],
) -> None:
    height, width = frame.shape[:2]
    margin = 8
    padding = 7
    line_height = 20
    font_scale = 0.43
    thickness = 1
    maximum_text_width = max(1, width - 2 * margin - 2 * padding)
    fitted = tuple(
        _fit_generic_text(line, maximum_text_width, font_scale, thickness)
        for line in lines
    )
    panel_height = min(
        height,
        2 * padding + line_height * len(fitted),
    )
    overlay = frame.copy()
    cv2.rectangle(
        overlay,
        (margin, margin),
        (max(margin, width - margin - 1), min(height - 1, margin + panel_height)),
        (0, 0, 0),
        -1,
    )
    cv2.addWeighted(overlay, 0.86, frame, 0.14, 0.0, dst=frame)
    for index, line in enumerate(fitted):
        baseline_y = margin + padding + line_height * (index + 1)
        if baseline_y >= height:
            break
        cv2.putText(
            frame,
            line,
            (margin + padding, baseline_y),
            cv2.FONT_HERSHEY_SIMPLEX,
            font_scale,
            (255, 255, 255),
            thickness,
            cv2.LINE_AA,
        )


def _draw_pipeline_footer(
    frame: ColorFrame,
    *,
    source_name: str,
    telemetry: PreviewTelemetry,
    display_state: PipelineDisplayState,
) -> None:
    height, width = frame.shape[:2]
    line_height = 19
    panel_height = min(height, 2 * line_height + 8)
    y0 = max(0, height - panel_height)
    cv2.rectangle(frame, (0, y0), (width - 1, height - 1), (0, 0, 0), -1)
    fps = (
        "warming"
        if telemetry.processed_fps is None
        else f"{telemetry.processed_fps:.1f}"
    )
    lines = (
        (
            f"{source_name} | FPS={fps} | pre-render age="
            f"{telemetry.frame_age_at_overlay_ms:.1f}ms "
            f"| dropped={display_state.dropped_capture_frames}"
        ),
        "Keys: p profile | [/] severity | r recolor | v/1-5 view | q/Esc quit",
    )
    for index, line in enumerate(lines):
        fitted = _fit_generic_text(line, max(1, width - 12), 0.42, 1)
        cv2.putText(
            frame,
            fitted,
            (6, y0 + 16 + index * line_height),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.42,
            (255, 255, 255),
            1,
            cv2.LINE_AA,
        )


def _fit_generic_text(
    value: str,
    maximum_width: int,
    font_scale: float,
    thickness: int,
) -> str:
    if maximum_width <= 0:
        return ""
    if cv2.getTextSize(
        value,
        cv2.FONT_HERSHEY_SIMPLEX,
        font_scale,
        thickness,
    )[0][0] <= maximum_width:
        return value
    suffix = "..."
    candidate = value
    while candidate:
        candidate = candidate[:-1]
        fitted = candidate.rstrip() + suffix
        if cv2.getTextSize(
            fitted,
            cv2.FONT_HERSHEY_SIMPLEX,
            font_scale,
            thickness,
        )[0][0] <= maximum_width:
            return fitted
    return ""


def _fit_text_to_width(
    value: str,
    maximum_width: int,
    style: AssistiveOverlayStyle,
) -> str:
    if maximum_width <= 0:
        return ""
    width = cv2.getTextSize(
        value,
        cv2.FONT_HERSHEY_SIMPLEX,
        style.font_scale,
        style.text_thickness_px,
    )[0][0]
    if width <= maximum_width:
        return value
    suffix = "..."
    candidate = value
    while candidate:
        candidate = candidate[:-1]
        fitted = candidate.rstrip() + suffix
        fitted_width = cv2.getTextSize(
            fitted,
            cv2.FONT_HERSHEY_SIMPLEX,
            style.font_scale,
            style.text_thickness_px,
        )[0][0]
        if fitted_width <= maximum_width:
            return fitted
    return ""


def _ascii_for_opencv(value: str) -> str:
    replaced = value.replace("Đ", "D").replace("đ", "d")
    return unicodedata.normalize("NFKD", replaced).encode("ascii", "ignore").decode()


def _validate_rgb_tuple(value: RGBColor, field_name: str) -> None:
    if len(value) != 3 or any(
        not isinstance(channel, (int, np.integer)) or not 0 <= int(channel) <= 255
        for channel in value
    ):
        raise ValueError(f"{field_name} must contain three integer channels in [0, 255]")


def _validate_render_frame(frame: ColorFrame) -> None:
    if frame.dtype != np.uint8 or frame.ndim != 3 or frame.shape[2] != 3:
        raise ValueError("frame_bgr must be a uint8 H x W x 3 BGR image")
    if frame.shape[0] == 0 or frame.shape[1] == 0:
        raise ValueError("frame_bgr dimensions must be non-empty")
