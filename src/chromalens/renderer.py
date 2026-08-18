"""Base OpenCV preview renderer and lightweight frame telemetry."""

from __future__ import annotations

from dataclasses import dataclass
from time import monotonic_ns

import cv2

from chromalens.contracts import ColorFrame, FramePacket


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
    pipeline_latency_ms: float


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
            pipeline_latency_ms=(now_ns - packet.timestamp_ns) / 1_000_000.0,
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
        f"Processed FPS: {fps_text} | Pipeline latency: {telemetry.pipeline_latency_ms:.1f} ms",
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
