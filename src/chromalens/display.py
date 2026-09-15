"""Resolution-independent OpenCV display boundary for ChromaLens.

This module scales only the final presentation canvas.  It never receives a
camera source, model input, mask, or analytical result, so fullscreen state
cannot implicitly change processing resolution or restart inference.
"""

from __future__ import annotations

import ctypes
import sys
from dataclasses import dataclass
from functools import lru_cache

import cv2
import numpy as np

from chromalens.contracts import ColorFrame


Rect = tuple[int, int, int, int]


@dataclass(frozen=True, slots=True)
class DpiAwarenessStatus:
    """Result of the one-time Windows process DPI-awareness request."""

    enabled: bool
    mode: str
    error_code: int | None = None


@lru_cache(maxsize=1)
def configure_process_dpi_awareness() -> DpiAwarenessStatus:
    """Enable physical-pixel rendering before OpenCV creates a GUI window.

    Windows bitmap-scales DPI-unaware processes. At 125% display scaling that
    makes a nominal 1536x864 canvas fill a 1920x1080 panel and visibly softens
    text and one-pixel curves. Per-Monitor V2 keeps layout/display dimensions
    in physical pixels. The fallbacks support older Windows releases without
    changing behaviour on non-Windows platforms.
    """

    if sys.platform != "win32":
        return DpiAwarenessStatus(enabled=False, mode="not-applicable")

    error_code: int | None = None
    try:
        user32 = ctypes.WinDLL("user32", use_last_error=True)
        set_context = user32.SetProcessDpiAwarenessContext
        set_context.argtypes = [ctypes.c_void_p]
        set_context.restype = ctypes.c_int
        ctypes.set_last_error(0)
        if bool(set_context(ctypes.c_void_p(-4))):
            return DpiAwarenessStatus(enabled=True, mode="per-monitor-v2")
        error_code = int(ctypes.get_last_error()) or None
    except (AttributeError, OSError, TypeError, ValueError):
        pass

    existing = _query_windows_process_dpi_awareness()
    if existing is not None:
        if existing > 0:
            return DpiAwarenessStatus(
                enabled=True,
                mode=(
                    "already-configured-per-monitor"
                    if existing == 2
                    else "already-configured-system"
                ),
                error_code=error_code,
            )
        # ERROR_ACCESS_DENIED means awareness was fixed by a manifest or an
        # earlier API call. Retrying older APIs cannot change that decision.
        if error_code == 5:
            return DpiAwarenessStatus(
                enabled=False,
                mode="already-configured-unaware",
                error_code=error_code,
            )

    try:
        shcore = ctypes.WinDLL("shcore", use_last_error=True)
        set_awareness = shcore.SetProcessDpiAwareness
        set_awareness.argtypes = [ctypes.c_int]
        set_awareness.restype = ctypes.c_long
        result = int(set_awareness(2))
        if result == 0:
            return DpiAwarenessStatus(enabled=True, mode="per-monitor-v1")
        error_code = result
    except (AttributeError, OSError, TypeError, ValueError):
        pass

    try:
        user32 = ctypes.WinDLL("user32", use_last_error=True)
        legacy = user32.SetProcessDPIAware
        legacy.argtypes = []
        legacy.restype = ctypes.c_int
        ctypes.set_last_error(0)
        if bool(legacy()):
            return DpiAwarenessStatus(enabled=True, mode="system")
        error_code = int(ctypes.get_last_error()) or error_code
    except (AttributeError, OSError, TypeError, ValueError):
        pass
    return DpiAwarenessStatus(
        enabled=False,
        mode="unavailable",
        error_code=error_code,
    )


def _query_windows_process_dpi_awareness() -> int | None:
    """Return PROCESS_DPI_AWARENESS (0..2), when Windows exposes it."""

    try:
        shcore = ctypes.WinDLL("shcore", use_last_error=True)
        get_awareness = shcore.GetProcessDpiAwareness
        get_awareness.argtypes = [ctypes.c_void_p, ctypes.POINTER(ctypes.c_int)]
        get_awareness.restype = ctypes.c_long
        awareness = ctypes.c_int()
        if int(get_awareness(None, ctypes.byref(awareness))) == 0:
            return int(awareness.value)
    except (AttributeError, OSError, TypeError, ValueError):
        pass
    return None


@dataclass(frozen=True, slots=True)
class DisplayFit:
    """One presentation canvas fitted inside a display surface."""

    frame_bgr: ColorFrame
    source_size: tuple[int, int]
    target_size: tuple[int, int]
    content_rect: Rect
    scale_x: float
    scale_y: float

    def map_rect(self, rect: Rect) -> Rect:
        """Map a source-canvas rectangle into the fitted display surface."""

        x0, y0, x1, y1 = rect
        source_width, source_height = self.source_size
        if not (0 <= x0 < x1 <= source_width and 0 <= y0 < y1 <= source_height):
            raise ValueError("rect must be contained by the source canvas")
        content_x0, content_y0, _, _ = self.content_rect
        return (
            content_x0 + round(x0 * self.scale_x),
            content_y0 + round(y0 * self.scale_y),
            content_x0 + round(x1 * self.scale_x),
            content_y0 + round(y1 * self.scale_y),
        )

    def aspect_ratio_error(self, source_rect: Rect) -> float:
        """Return the frozen relative aspect-ratio error for a mapped viewport."""

        x0, y0, x1, y1 = source_rect
        mapped_x0, mapped_y0, mapped_x1, mapped_y1 = self.map_rect(source_rect)
        source_aspect = (x1 - x0) / (y1 - y0)
        displayed_aspect = (mapped_x1 - mapped_x0) / (mapped_y1 - mapped_y0)
        return abs(displayed_aspect / source_aspect - 1.0)


def fit_presentation_to_display(
    presentation_bgr: ColorFrame,
    target_size: tuple[int, int],
    *,
    background_bgr: tuple[int, int, int] = (0, 0, 0),
) -> DisplayFit:
    """Aspect-fit a completed presentation into a fixed display surface.

    A single uniform scale is applied to the complete presentation. Remaining
    pixels become letterbox/pillarbox bands. The input is never mutated.
    """

    _validate_frame(presentation_bgr)
    target_width, target_height = target_size
    if target_width <= 0 or target_height <= 0:
        raise ValueError("target display dimensions must be positive")
    if len(background_bgr) != 3 or any(
        not isinstance(channel, int) or not 0 <= channel <= 255
        for channel in background_bgr
    ):
        raise ValueError("background_bgr must contain three integer channels")

    source_height, source_width = presentation_bgr.shape[:2]
    if (source_width, source_height) == target_size:
        return DisplayFit(
            frame_bgr=presentation_bgr,
            source_size=(source_width, source_height),
            target_size=target_size,
            content_rect=(0, 0, source_width, source_height),
            scale_x=1.0,
            scale_y=1.0,
        )
    scale = min(target_width / source_width, target_height / source_height)
    fitted_width = min(target_width, max(1, round(source_width * scale)))
    fitted_height = min(target_height, max(1, round(source_height * scale)))
    interpolation = cv2.INTER_AREA if scale < 1.0 else cv2.INTER_LINEAR
    resized = cv2.resize(
        presentation_bgr,
        (fitted_width, fitted_height),
        interpolation=interpolation,
    )
    output = np.full(
        (target_height, target_width, 3),
        background_bgr,
        dtype=np.uint8,
    )
    x0 = (target_width - fitted_width) // 2
    y0 = (target_height - fitted_height) // 2
    x1 = x0 + fitted_width
    y1 = y0 + fitted_height
    output[y0:y1, x0:x1] = resized
    return DisplayFit(
        frame_bgr=output,
        source_size=(source_width, source_height),
        target_size=target_size,
        content_rect=(x0, y0, x1, y1),
        scale_x=fitted_width / source_width,
        scale_y=fitted_height / source_height,
    )


def primary_display_size() -> tuple[int, int] | None:
    """Return the physical primary desktop size when safely available."""

    if sys.platform != "win32":
        return None
    # This call is idempotent and cached. It must happen before querying
    # metrics, otherwise Windows may return DPI-virtualized logical pixels.
    configure_process_dpi_awareness()
    try:
        user32 = ctypes.windll.user32
        width = int(user32.GetSystemMetrics(0))
        height = int(user32.GetSystemMetrics(1))
    except (AttributeError, OSError, TypeError, ValueError):
        return None
    return (width, height) if width > 0 and height > 0 else None


def recommended_windowed_size() -> tuple[int, int] | None:
    """Return a bounded native client size that fits the primary display."""

    display_size = primary_display_size()
    if display_size is None:
        return None
    display_width, display_height = display_size
    return (
        min(1366, max(640, round(display_width * 0.85))),
        min(768, max(480, round(display_height * 0.82))),
    )


@dataclass(slots=True)
class OpenCVDisplayController:
    """Own one OpenCV window and reversible fullscreen presentation state."""

    window_title: str
    fullscreen: bool = False
    fullscreen_size: tuple[int, int] | None = None
    windowed_size: tuple[int, int] | None = None
    _window_created: bool = False
    _window_configured: bool = False

    def __post_init__(self) -> None:
        if not self.window_title.strip():
            raise ValueError("window_title must not be empty")
        if self.fullscreen_size is not None:
            width, height = self.fullscreen_size
            if width <= 0 or height <= 0:
                raise ValueError("fullscreen_size dimensions must be positive")
        if self.windowed_size is not None:
            width, height = self.windowed_size
            if width <= 0 or height <= 0:
                raise ValueError("windowed_size dimensions must be positive")

    @property
    def window_created(self) -> bool:
        """Whether at least one frame has been submitted to this window."""

        return self._window_created

    @property
    def presentation_size(self) -> tuple[int, int] | None:
        """Current physical client size used for native presentation drawing."""

        if self.fullscreen:
            return self.fullscreen_size or primary_display_size()
        observed = self._window_client_size()
        if observed is not None:
            self.windowed_size = observed
        if self.windowed_size is None:
            self.windowed_size = recommended_windowed_size()
        return self.windowed_size

    def prepare(self, presentation_bgr: ColorFrame) -> DisplayFit:
        """Prepare a frame for the current window state without displaying it."""

        _validate_frame(presentation_bgr)
        source_height, source_width = presentation_bgr.shape[:2]
        target_size = self.presentation_size
        if target_size is None:
            return DisplayFit(
                frame_bgr=presentation_bgr,
                source_size=(source_width, source_height),
                target_size=(source_width, source_height),
                content_rect=(0, 0, source_width, source_height),
                scale_x=1.0,
                scale_y=1.0,
            )
        return fit_presentation_to_display(presentation_bgr, target_size)

    def submit(self, prepared: DisplayFit) -> None:
        """Submit one already prepared frame to OpenCV."""

        first_submission = not self._window_created
        self._ensure_window_configuration()
        if first_submission and not self.fullscreen:
            self.windowed_size = prepared.target_size
            cv2.resizeWindow(
                self.window_title,
                prepared.target_size[0],
                prepared.target_size[1],
            )
        cv2.imshow(self.window_title, prepared.frame_bgr)
        self._window_created = True

    def toggle_fullscreen(self) -> bool:
        """Toggle fullscreen in place and return the new state."""

        self.set_fullscreen(not self.fullscreen)
        return self.fullscreen

    def set_fullscreen(self, enabled: bool) -> None:
        """Request a reversible OpenCV fullscreen/windowed transition."""

        if not isinstance(enabled, bool):
            raise TypeError("enabled must be boolean")
        if enabled == self.fullscreen:
            return
        if enabled:
            observed = self._window_client_size()
            if observed is not None:
                self.windowed_size = observed
        self.fullscreen = enabled
        if self._window_created or self._window_configured:
            self._ensure_named_window()
            cv2.setWindowProperty(
                self.window_title,
                cv2.WND_PROP_FULLSCREEN,
                cv2.WINDOW_FULLSCREEN if enabled else cv2.WINDOW_NORMAL,
            )
            if not enabled:
                restore_size = self.windowed_size or recommended_windowed_size()
                if restore_size is not None:
                    self.windowed_size = restore_size
                    cv2.resizeWindow(
                        self.window_title,
                        restore_size[0],
                        restore_size[1],
                    )
            self._window_configured = True

    def is_visible(self) -> bool:
        """Return whether OpenCV reports that the window remains visible."""

        if not self._window_created:
            return True
        try:
            return cv2.getWindowProperty(
                self.window_title, cv2.WND_PROP_VISIBLE
            ) >= 1.0
        except cv2.error:
            return False

    def close(self) -> None:
        """Destroy only this controller's window, tolerating GUI teardown races."""

        if not self._window_created and not self._window_configured:
            return
        try:
            cv2.destroyWindow(self.window_title)
        except cv2.error:
            pass
        self._window_created = False
        self._window_configured = False

    def _ensure_window_configuration(self) -> None:
        if self._window_configured:
            return
        self._ensure_named_window()
        if self.fullscreen:
            cv2.setWindowProperty(
                self.window_title,
                cv2.WND_PROP_FULLSCREEN,
                cv2.WINDOW_FULLSCREEN,
            )
        self._window_configured = True

    def _ensure_named_window(self) -> None:
        if not self._window_configured:
            cv2.namedWindow(self.window_title, cv2.WINDOW_NORMAL)

    def _window_client_size(self) -> tuple[int, int] | None:
        """Read a positive HighGUI image area without trusting window chrome."""

        if not self._window_created or self.fullscreen:
            return None
        try:
            _, _, width, height = cv2.getWindowImageRect(self.window_title)
            width = int(width)
            height = int(height)
        except (cv2.error, TypeError, ValueError):
            return None
        return (width, height) if width > 0 and height > 0 else None


def _validate_frame(frame_bgr: ColorFrame) -> None:
    if not isinstance(frame_bgr, np.ndarray):
        raise TypeError("presentation_bgr must be a NumPy array")
    if frame_bgr.dtype != np.uint8 or frame_bgr.ndim != 3 or frame_bgr.shape[2] != 3:
        raise ValueError("presentation_bgr must be uint8 with shape HxWx3")
    if frame_bgr.shape[0] <= 0 or frame_bgr.shape[1] <= 0:
        raise ValueError("presentation_bgr dimensions must be positive")
