"""OpenCV webcam and local-video sources for the live pipeline."""

from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path
from time import monotonic_ns

import cv2
import numpy as np

from chromalens.contracts import FramePacket


class FrameSourceError(RuntimeError):
    """Base class for actionable frame-source failures."""


class FrameSourceOpenError(FrameSourceError):
    """Raised when a webcam or video cannot be opened."""


class FrameSourceReadError(FrameSourceError):
    """Raised when a live source stops returning valid frames."""


class FrameSourceClosedError(FrameSourceError):
    """Raised when code reads from a source after it has been closed."""


class FrameSource(ABC):
    """Common sequential interface for live and finite frame sources.

    ``read`` returns ``None`` only for the normal end of a finite source. Live
    source failures raise ``FrameSourceReadError`` so callers cannot mistake a
    disconnected camera for a successful end-of-stream.
    """

    @property
    @abstractmethod
    def name(self) -> str:
        """Human-readable source name safe for the preview overlay."""

    @property
    @abstractmethod
    def is_live(self) -> bool:
        """Whether the source is expected to continue until user exit."""

    @property
    @abstractmethod
    def resolution(self) -> tuple[int, int] | None:
        """Most recently observed ``(width, height)``, if known."""

    @property
    @abstractmethod
    def nominal_fps(self) -> float | None:
        """Source-reported FPS when it is finite and trustworthy enough to pace."""

    @abstractmethod
    def read(self) -> FramePacket | None:
        """Read the next packet or return ``None`` at finite-source EOF."""

    @abstractmethod
    def close(self) -> None:
        """Release the underlying capture handle; repeated calls are safe."""

    def __enter__(self) -> "FrameSource":
        return self

    def __exit__(self, *_exc_info: object) -> None:
        self.close()


class OpenCVFrameSource(FrameSource):
    """Sequential ``cv2.VideoCapture`` adapter with no application queue."""

    def __init__(
        self,
        capture: cv2.VideoCapture,
        *,
        name: str,
        is_live: bool,
    ) -> None:
        self._capture = capture
        self._name = name
        self._is_live = is_live
        self._closed = False
        self._frame_id = 0
        self._resolution = _capture_resolution(capture)
        self._nominal_fps = _capture_fps(capture) if not is_live else None

    @property
    def name(self) -> str:
        return self._name

    @property
    def is_live(self) -> bool:
        return self._is_live

    @property
    def resolution(self) -> tuple[int, int] | None:
        return self._resolution

    @property
    def nominal_fps(self) -> float | None:
        return self._nominal_fps

    def read(self) -> FramePacket | None:
        if self._closed:
            raise FrameSourceClosedError(
                f"Source '{self.name}' is closed; open a new source before reading."
            )

        ok, frame = self._capture.read()
        if not ok or frame is None:
            if self.is_live:
                raise FrameSourceReadError(
                    f"Webcam '{self.name}' stopped returning frames. "
                    "Check the camera connection and close other camera applications."
                )
            return None

        if frame.dtype != np.uint8 or frame.ndim != 3 or frame.shape[2] != 3:
            raise FrameSourceReadError(
                f"Source '{self.name}' returned an unsupported frame; "
                "expected uint8 BGR with shape H x W x 3."
            )

        height, width = frame.shape[:2]
        self._resolution = (width, height)
        packet = FramePacket(
            frame_id=self._frame_id,
            timestamp_ns=monotonic_ns(),
            original_bgr=frame,
        )
        self._frame_id += 1
        return packet

    def close(self) -> None:
        if not self._closed:
            self._capture.release()
            self._closed = True


def open_webcam(
    index: int = 0,
    *,
    width: int | None = None,
    height: int | None = None,
) -> FrameSource:
    """Open a webcam and request an optional positive capture resolution."""

    if index < 0:
        raise ValueError("camera index must be non-negative")
    _validate_optional_dimension(width, "width")
    _validate_optional_dimension(height, "height")

    capture = cv2.VideoCapture(index)
    if not capture.isOpened():
        capture.release()
        raise FrameSourceOpenError(
            f"Cannot open webcam index {index}. Check camera permission, "
            "the selected --camera-index, and whether another application is using it."
        )

    if width is not None:
        capture.set(cv2.CAP_PROP_FRAME_WIDTH, float(width))
    if height is not None:
        capture.set(cv2.CAP_PROP_FRAME_HEIGHT, float(height))
    capture.set(cv2.CAP_PROP_BUFFERSIZE, 1.0)
    return OpenCVFrameSource(capture, name=f"webcam:{index}", is_live=True)


def open_video(path: str | Path) -> FrameSource:
    """Open a local video file without accessing any webcam device."""

    video_path = Path(path).expanduser()
    if not video_path.is_file():
        raise FrameSourceOpenError(
            f"Cannot open video '{video_path}': file does not exist or is not a file. "
            "Check the --video path and file permissions."
        )

    resolved_path = video_path.resolve()
    capture = cv2.VideoCapture(str(resolved_path))
    if not capture.isOpened():
        capture.release()
        raise FrameSourceOpenError(
            f"Cannot decode video '{resolved_path}'. Check that OpenCV supports "
            "the container/codec and that the file is not corrupt."
        )

    return OpenCVFrameSource(
        capture,
        name=f"video:{resolved_path.name}",
        is_live=False,
    )


def _capture_resolution(capture: cv2.VideoCapture) -> tuple[int, int] | None:
    width = int(capture.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(capture.get(cv2.CAP_PROP_FRAME_HEIGHT))
    if width <= 0 or height <= 0:
        return None
    return width, height


def _capture_fps(capture: cv2.VideoCapture) -> float | None:
    fps = float(capture.get(cv2.CAP_PROP_FPS))
    if not np.isfinite(fps) or fps <= 0.0:
        return None
    return fps


def _validate_optional_dimension(value: int | None, name: str) -> None:
    if value is not None and value <= 0:
        raise ValueError(f"{name} must be positive when provided")
