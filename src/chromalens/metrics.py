"""Bounded T08 runtime metrics with a Windows working-set probe."""

from __future__ import annotations

from collections import deque
import ctypes
from ctypes import wintypes
from dataclasses import dataclass
import os
from pathlib import Path
from time import monotonic_ns
from typing import Callable

import numpy as np


@dataclass(frozen=True, slots=True)
class RuntimeMetricsConfig:
    """Bound storage and control how often process memory is sampled."""

    max_samples: int = 10_000
    memory_sample_interval_frames: int = 10

    def __post_init__(self) -> None:
        if self.max_samples <= 0:
            raise ValueError("max_samples must be positive")
        if self.memory_sample_interval_frames <= 0:
            raise ValueError("memory_sample_interval_frames must be positive")


@dataclass(frozen=True, slots=True)
class RuntimeMetricsSnapshot:
    """Measured session summary; unavailable values remain ``None``."""

    total_frames: int
    elapsed_seconds: float
    processed_fps: float | None
    source_read_to_render_p50_ms: float | None
    source_read_to_render_p95_ms: float | None
    source_read_to_display_submit_p50_ms: float | None
    source_read_to_display_submit_p95_ms: float | None
    frame_processing_to_render_p50_ms: float | None
    frame_processing_to_render_p95_ms: float | None
    rss_start_mib: float | None
    rss_end_mib: float | None
    rss_peak_mib: float | None
    rss_delta_mib: float | None
    rss_slope_mib_per_minute: float | None
    rss_steady_state_delta_mib: float | None
    rss_steady_state_slope_mib_per_minute: float | None
    source_read_to_render_slope_ms_per_minute: float | None
    latency_continuous_growth_flag: bool | None
    rss_continuous_growth_flag: bool | None
    retained_source_read_to_render_samples: int
    retained_source_read_to_display_submit_samples: int
    retained_memory_samples: int
    dropped_capture_frames: int
    degraded_frames: int


class RuntimeMetricsTracker:
    """Collect latency and RSS in fixed-capacity deques."""

    def __init__(
        self,
        config: RuntimeMetricsConfig | None = None,
        *,
        clock_ns: Callable[[], int] = monotonic_ns,
        rss_provider: Callable[[], int | None] | None = None,
    ) -> None:
        self.config = config or RuntimeMetricsConfig()
        self._clock_ns = clock_ns
        self._rss_provider = rss_provider or current_process_rss_bytes
        self._started_ns = self._clock_ns()
        self._last_observed_ns = self._started_ns
        self._total_frames = 0
        self._source_read_to_render_ms: deque[tuple[float, float]] = deque(
            maxlen=self.config.max_samples
        )
        self._source_read_to_display_submit_ms: deque[tuple[float, float]] = deque(
            maxlen=self.config.max_samples
        )
        self._frame_processing_to_render_ms: deque[tuple[float, float]] = deque(
            maxlen=self.config.max_samples
        )
        self._memory_samples: deque[tuple[float, float]] = deque(
            maxlen=self.config.max_samples
        )
        self._record_memory(self._started_ns)

    def observe(
        self,
        *,
        source_read_to_render_ms: float,
        frame_processing_to_render_ms: float,
        source_read_to_display_submit_ms: float | None = None,
        observed_ns: int | None = None,
    ) -> None:
        """Record one frame using the frozen T09 software-latency semantics.

        ``source_read_to_render_ms`` starts at the timestamp created after the
        source ``read()`` returned and ends after rendering completes.
        ``source_read_to_display_submit_ms`` is optional because headless runs
        do not call ``cv2.imshow``; when present it ends immediately after that
        call returns. Neither measurement is sensor-to-photon latency.
        """

        now_ns = self._clock_ns() if observed_ns is None else observed_ns
        if now_ns < self._last_observed_ns:
            raise ValueError("observed_ns must be monotonic")
        for field_name, value in (
            ("source_read_to_render_ms", source_read_to_render_ms),
            ("frame_processing_to_render_ms", frame_processing_to_render_ms),
        ):
            if not np.isfinite(value) or value < 0.0:
                raise ValueError(f"{field_name} must be finite and non-negative")
        if source_read_to_display_submit_ms is not None:
            if (
                not np.isfinite(source_read_to_display_submit_ms)
                or source_read_to_display_submit_ms < source_read_to_render_ms
            ):
                raise ValueError(
                    "source_read_to_display_submit_ms must be finite and no "
                    "smaller than source_read_to_render_ms"
                )
        self._last_observed_ns = now_ns
        self._total_frames += 1
        elapsed_seconds = (now_ns - self._started_ns) / 1_000_000_000.0
        self._source_read_to_render_ms.append(
            (elapsed_seconds, float(source_read_to_render_ms))
        )
        if source_read_to_display_submit_ms is not None:
            self._source_read_to_display_submit_ms.append(
                (elapsed_seconds, float(source_read_to_display_submit_ms))
            )
        self._frame_processing_to_render_ms.append(
            (elapsed_seconds, float(frame_processing_to_render_ms))
        )
        if self._total_frames % self.config.memory_sample_interval_frames == 0:
            self._record_memory(now_ns)

    def snapshot(
        self,
        *,
        dropped_capture_frames: int = 0,
        degraded_frames: int = 0,
        observed_ns: int | None = None,
    ) -> RuntimeMetricsSnapshot:
        """Return a non-mutating summary of the bounded measurements."""

        now_ns = self._clock_ns() if observed_ns is None else observed_ns
        if now_ns < self._last_observed_ns:
            raise ValueError("observed_ns must be monotonic")
        if dropped_capture_frames < 0 or degraded_frames < 0:
            raise ValueError("frame counts must be non-negative")
        self._record_memory(now_ns)
        elapsed_seconds = max(0.0, (now_ns - self._started_ns) / 1_000_000_000.0)
        memory_values = [sample[1] for sample in self._memory_samples]
        rss_start = memory_values[0] if memory_values else None
        rss_end = memory_values[-1] if memory_values else None
        rss_peak = max(memory_values) if memory_values else None
        steady_memory = _second_half(self._memory_samples)
        steady_values = [sample[1] for sample in steady_memory]
        return RuntimeMetricsSnapshot(
            total_frames=self._total_frames,
            elapsed_seconds=elapsed_seconds,
            processed_fps=(
                self._total_frames / elapsed_seconds
                if self._total_frames and elapsed_seconds > 0.0
                else None
            ),
            source_read_to_render_p50_ms=_timed_percentile(
                self._source_read_to_render_ms, 50.0
            ),
            source_read_to_render_p95_ms=_timed_percentile(
                self._source_read_to_render_ms, 95.0
            ),
            source_read_to_display_submit_p50_ms=_timed_percentile(
                self._source_read_to_display_submit_ms, 50.0
            ),
            source_read_to_display_submit_p95_ms=_timed_percentile(
                self._source_read_to_display_submit_ms, 95.0
            ),
            frame_processing_to_render_p50_ms=_timed_percentile(
                self._frame_processing_to_render_ms, 50.0
            ),
            frame_processing_to_render_p95_ms=_timed_percentile(
                self._frame_processing_to_render_ms, 95.0
            ),
            rss_start_mib=rss_start,
            rss_end_mib=rss_end,
            rss_peak_mib=rss_peak,
            rss_delta_mib=(
                None if rss_start is None or rss_end is None else rss_end - rss_start
            ),
            rss_slope_mib_per_minute=_memory_slope(self._memory_samples),
            rss_steady_state_delta_mib=(
                None
                if len(steady_values) < 2
                else steady_values[-1] - steady_values[0]
            ),
            rss_steady_state_slope_mib_per_minute=_memory_slope(steady_memory),
            source_read_to_render_slope_ms_per_minute=_timed_slope(
                self._source_read_to_render_ms
            ),
            latency_continuous_growth_flag=_four_window_growth_flag(
                self._source_read_to_render_ms,
                elapsed_seconds=elapsed_seconds,
                absolute_increase=20.0,
                relative_increase=0.10,
            ),
            rss_continuous_growth_flag=_four_window_growth_flag(
                self._memory_samples,
                elapsed_seconds=elapsed_seconds,
                absolute_increase=8.0,
                relative_increase=0.05,
            ),
            retained_source_read_to_render_samples=len(
                self._source_read_to_render_ms
            ),
            retained_source_read_to_display_submit_samples=len(
                self._source_read_to_display_submit_ms
            ),
            retained_memory_samples=len(self._memory_samples),
            dropped_capture_frames=dropped_capture_frames,
            degraded_frames=degraded_frames,
        )

    def _record_memory(self, observed_ns: int) -> None:
        rss_bytes = self._rss_provider()
        if rss_bytes is None or rss_bytes < 0:
            return
        elapsed_seconds = (observed_ns - self._started_ns) / 1_000_000_000.0
        self._memory_samples.append((elapsed_seconds, rss_bytes / (1024.0**2)))


def current_process_rss_bytes() -> int | None:
    """Return current resident/working-set bytes without an external package."""

    if os.name == "nt":
        return _windows_working_set_bytes()
    statm = Path("/proc/self/statm")
    if statm.is_file():
        try:
            resident_pages = int(statm.read_text(encoding="ascii").split()[1])
            return resident_pages * os.sysconf("SC_PAGE_SIZE")
        except (OSError, ValueError, IndexError):
            return None
    return None


def _windows_working_set_bytes() -> int | None:
    class ProcessMemoryCounters(ctypes.Structure):
        _fields_ = (
            ("cb", ctypes.c_ulong),
            ("PageFaultCount", ctypes.c_ulong),
            ("PeakWorkingSetSize", ctypes.c_size_t),
            ("WorkingSetSize", ctypes.c_size_t),
            ("QuotaPeakPagedPoolUsage", ctypes.c_size_t),
            ("QuotaPagedPoolUsage", ctypes.c_size_t),
            ("QuotaPeakNonPagedPoolUsage", ctypes.c_size_t),
            ("QuotaNonPagedPoolUsage", ctypes.c_size_t),
            ("PagefileUsage", ctypes.c_size_t),
            ("PeakPagefileUsage", ctypes.c_size_t),
        )

    counters = ProcessMemoryCounters()
    counters.cb = ctypes.sizeof(ProcessMemoryCounters)
    try:
        kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
        psapi = ctypes.WinDLL("psapi", use_last_error=True)
        kernel32.GetCurrentProcess.argtypes = []
        kernel32.GetCurrentProcess.restype = wintypes.HANDLE
        psapi.GetProcessMemoryInfo.argtypes = (
            wintypes.HANDLE,
            ctypes.POINTER(ProcessMemoryCounters),
            wintypes.DWORD,
        )
        psapi.GetProcessMemoryInfo.restype = wintypes.BOOL
        process = kernel32.GetCurrentProcess()
        ok = psapi.GetProcessMemoryInfo(
            process,
            ctypes.byref(counters),
            counters.cb,
        )
    except (AttributeError, OSError):
        return None
    return int(counters.WorkingSetSize) if ok else None


def _timed_percentile(
    samples: deque[tuple[float, float]], percentile: float
) -> float | None:
    if not samples:
        return None
    values = np.asarray([sample[1] for sample in samples], dtype=np.float64)
    return float(np.percentile(values, percentile))


def _memory_slope(samples: deque[tuple[float, float]]) -> float | None:
    return _timed_slope(samples)


def _timed_slope(samples: deque[tuple[float, float]]) -> float | None:
    if len(samples) < 2:
        return None
    seconds = np.asarray([sample[0] for sample in samples], dtype=np.float64)
    values = np.asarray([sample[1] for sample in samples], dtype=np.float64)
    centered_seconds = seconds - float(np.mean(seconds))
    denominator = float(np.sum(centered_seconds**2))
    if denominator <= 0.0:
        return 0.0
    slope_mib_per_second = float(
        np.sum(centered_seconds * (values - float(np.mean(values)))) / denominator
    )
    return slope_mib_per_second * 60.0


def _second_half(
    samples: deque[tuple[float, float]],
) -> deque[tuple[float, float]]:
    if len(samples) < 2:
        return deque()
    values = tuple(samples)
    return deque(values[len(values) // 2 :])


def _four_window_growth_flag(
    samples: deque[tuple[float, float]],
    *,
    elapsed_seconds: float,
    absolute_increase: float,
    relative_increase: float,
    window_seconds: float = 30.0,
) -> bool | None:
    """Apply the frozen T09 four-window continuous-growth diagnostic."""

    required_seconds = 4.0 * window_seconds
    if elapsed_seconds < required_seconds:
        return None
    medians: list[float] = []
    for index in range(4):
        start = index * window_seconds
        end = (index + 1) * window_seconds
        values = [
            value
            for elapsed, value in samples
            if elapsed >= start
            and (elapsed < end or (index == 3 and elapsed <= required_seconds))
        ]
        if not values:
            return None
        medians.append(float(np.median(np.asarray(values, dtype=np.float64))))
    strictly_increasing = all(
        current > previous for previous, current in zip(medians, medians[1:])
    )
    required_increase = max(
        absolute_increase,
        relative_increase * max(medians[0], np.finfo(np.float64).eps),
    )
    return strictly_increasing and medians[-1] - medians[0] > required_increase
