"""Debug overlay utilities for garment segmentation visualisation.

These functions render mask overlays onto copies of source frames.
They never mutate the original frame and are suitable for development
debugging and the T02 evidence artifacts.
"""

from __future__ import annotations

import logging

import cv2
import numpy as np
from numpy.typing import NDArray

from chromalens.contracts import BinaryMask, ColorFrame, GarmentRegion

_logger = logging.getLogger(__name__)

# Per-class BGR overlay colours (B, G, R)
_CLASS_COLORS: dict[str, tuple[int, int, int]] = {
    "upper-clothes": (0, 220, 0),      # vivid green
    "pants":         (220, 60, 0),     # vivid blue-orange
    "skirt":         (180, 105, 255),  # pink-purple
    "dress":         (255, 180, 80),   # lavender-blue
}
_FALLBACK_COLOR: tuple[int, int, int] = (0, 220, 220)  # yellow


def draw_mask_overlay(
    bgr_frame: ColorFrame,
    regions: tuple[GarmentRegion, ...],
    *,
    alpha: float = 0.40,
    backend_info: str = "",
    font_scale: float = 0.55,
    font_thickness: int = 1,
) -> ColorFrame:
    """Render segmentation masks onto a copy of the source frame.

    Each garment region is drawn with a semi-transparent colour fill.
    A text panel in the top-left corner lists the backend identifier,
    each detected class name, and its confidence (if available).

    Args:
        bgr_frame: Source frame in BGR uint8 format. Not mutated.
        regions: Tuple of :class:`~chromalens.contracts.GarmentRegion` objects
            aligned with ``bgr_frame``.
        alpha: Opacity of the colour overlay (0 = transparent, 1 = opaque).
        backend_info: Short string displayed in the top-left panel
            (e.g. ``"mediapipe/cpu"``).
        font_scale: OpenCV font scale for overlay text.
        font_thickness: OpenCV font thickness for overlay text.

    Returns:
        A new BGR uint8 frame with overlays applied. The original
        ``bgr_frame`` array is never modified.

    Raises:
        ValueError: If ``alpha`` is not in ``[0, 1]``.
    """
    if not 0.0 <= alpha <= 1.0:
        raise ValueError(f"alpha must be in [0, 1]; got {alpha}")

    # Work on a copy — never mutate the original.
    canvas: ColorFrame = bgr_frame.copy()
    overlay = canvas.copy()

    for region in regions:
        color = _CLASS_COLORS.get(region.class_name, _FALLBACK_COLOR)
        overlay[region.mask] = color

    # Blend overlay onto canvas.
    cv2.addWeighted(overlay, alpha, canvas, 1.0 - alpha, 0, canvas)

    # Draw contour outlines for clarity.
    for region in regions:
        color = _CLASS_COLORS.get(region.class_name, _FALLBACK_COLOR)
        uint8_mask = region.mask.astype(np.uint8) * 255
        contours, _ = cv2.findContours(
            uint8_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE
        )
        cv2.drawContours(canvas, contours, -1, color, thickness=2)

    # Text panel — top-left corner.
    lines: list[str] = []
    if backend_info:
        lines.append(f"backend: {backend_info}")
    if not regions:
        lines.append("no garment detected")
    for region in regions:
        conf_str = (
            f"{region.mask_confidence:.2f}"
            if region.mask_confidence is not None
            else "n/a"
        )
        lines.append(f"{region.class_name}  conf={conf_str}")

    _draw_text_panel(canvas, lines, font_scale=font_scale, thickness=font_thickness)

    _logger.debug(
        "draw_mask_overlay: %d region(s) drawn on frame %s",
        len(regions),
        bgr_frame.shape[:2],
    )
    return canvas


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _draw_text_panel(
    canvas: ColorFrame,
    lines: list[str],
    *,
    x: int = 8,
    y_start: int = 20,
    line_height: int = 20,
    font_scale: float = 0.55,
    thickness: int = 1,
) -> None:
    """Draw a semi-transparent black panel with white text lines.

    Modifies ``canvas`` in-place (caller already holds a copy).

    Args:
        canvas: BGR uint8 frame to draw onto.
        lines: Text lines to display, top to bottom.
        x: Left margin in pixels.
        y_start: Vertical position of the first line baseline.
        line_height: Vertical spacing between lines in pixels.
        font_scale: OpenCV font scale.
        thickness: OpenCV font thickness.
    """
    font = cv2.FONT_HERSHEY_SIMPLEX
    pad = 4

    # Measure panel dimensions.
    max_w = 0
    for line in lines:
        (tw, _), _ = cv2.getTextSize(line, font, font_scale, thickness)
        max_w = max(max_w, tw)
    panel_h = line_height * len(lines) + pad * 2
    panel_w = max_w + pad * 4

    # Draw translucent dark rectangle.
    panel = canvas[y_start - line_height: y_start + panel_h, x: x + panel_w]
    if panel.size > 0:
        dark = np.zeros_like(panel)
        cv2.addWeighted(dark, 0.55, panel, 0.45, 0, panel)
        canvas[y_start - line_height: y_start + panel_h, x: x + panel_w] = panel

    # Draw text.
    for i, line in enumerate(lines):
        y = y_start + i * line_height
        # Black shadow for readability on any background.
        cv2.putText(canvas, line, (x + 1, y + 1), font, font_scale, (0, 0, 0), thickness + 1)
        cv2.putText(canvas, line, (x, y), font, font_scale, (255, 255, 255), thickness)
