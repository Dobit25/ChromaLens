"""OpenCV webcam and local-video sources for the live pipeline."""

from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path
from threading import Condition, Event, Thread
from time import monotonic, monotonic_ns

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


class LatestFrameTimeout(TimeoutError):
    """Raised when no live frame arrives within a bounded consumer wait."""


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


class LatestFrameReader:
    """Read a live source on one daemon thread and retain only its newest frame.

    The mailbox has an exact capacity of one. A producer overwrite increments
    ``dropped_frames`` instead of allowing camera latency or memory to grow.
    Finite video deliberately does not use this class in T08.
    """

    def __init__(self, source: FrameSource, *, close_timeout_seconds: float = 2.0) -> None:
        if not source.is_live:
            raise ValueError("LatestFrameReader requires a live FrameSource")
        if close_timeout_seconds <= 0.0:
            raise ValueError("close_timeout_seconds must be positive")
        self.source = source
        self.close_timeout_seconds = close_timeout_seconds
        self._condition = Condition()
        self._stop_event = Event()
        self._latest: FramePacket | None = None
        self._error: Exception | None = None
        self._finished = False
        self._started = False
        self._closed = False
        self._dropped_frames = 0
        self._thread = Thread(
            target=self._capture_loop,
            name=f"chromalens-capture:{source.name}",
            daemon=True,
        )

    @property
    def dropped_frames(self) -> int:
        """Return producer overwrites observed by the capacity-one mailbox."""

        with self._condition:
            return self._dropped_frames

    @property
    def finished(self) -> bool:
        """Whether the producer stopped because of EOF, error, or close."""

        with self._condition:
            return self._finished

    @property
    def worker_alive(self) -> bool:
        """Expose worker lifecycle for deterministic shutdown evidence."""

        return self._thread.is_alive()

    def start(self) -> "LatestFrameReader":
        """Start the sole capture worker exactly once."""

        with self._condition:
            if self._closed:
                raise FrameSourceClosedError("latest-frame reader is closed")
            if self._started:
                raise RuntimeError("latest-frame reader has already started")
            self._started = True
        self._thread.start()
        return self

    def read_latest(self, *, timeout_seconds: float = 0.25) -> FramePacket | None:
        """Take the newest packet, wait boundedly, or return ``None`` at finish."""

        if timeout_seconds <= 0.0:
            raise ValueError("timeout_seconds must be positive")
        deadline = monotonic() + timeout_seconds
        with self._condition:
            if not self._started:
                raise RuntimeError("latest-frame reader must be started before reading")
            while self._latest is None and self._error is None and not self._finished:
                remaining = deadline - monotonic()
                if remaining <= 0.0:
                    raise LatestFrameTimeout(
                        f"No frame arrived from '{self.source.name}' within "
                        f"{timeout_seconds:.2f}s."
                    )
                self._condition.wait(timeout=remaining)
            if self._latest is not None:
                packet = self._latest
                self._latest = None
                return packet
            if self._error is not None:
                error = self._error
                self._error = None
                if isinstance(error, FrameSourceError):
                    raise error
                raise FrameSourceReadError(
                    f"Live capture worker failed for '{self.source.name}': "
                    f"{error.__class__.__name__}: {error}"
                ) from error
            return None

    def close(self) -> None:
        """Stop capture, release the source, and join for a bounded interval."""

        with self._condition:
            if self._closed:
                return
            self._closed = True
            self._stop_event.set()
            self._condition.notify_all()
        self.source.close()
        if self._started and self._thread.is_alive():
            self._thread.join(timeout=self.close_timeout_seconds)
        with self._condition:
            self._finished = True
            self._latest = None
            self._condition.notify_all()

    def __enter__(self) -> "LatestFrameReader":
        return self.start()

    def __exit__(self, *_exc_info: object) -> None:
        self.close()

    def _capture_loop(self) -> None:
        try:
            while not self._stop_event.is_set():
                packet = self.source.read()
                if packet is None:
                    break
                with self._condition:
                    if self._latest is not None:
                        self._dropped_frames += 1
                    self._latest = packet
                    self._condition.notify_all()
        except Exception as exc:  # backend boundary reported to the main thread
            if not self._stop_event.is_set():
                with self._condition:
                    self._error = exc
                    self._condition.notify_all()
        finally:
            with self._condition:
                self._finished = True
                self._condition.notify_all()


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
