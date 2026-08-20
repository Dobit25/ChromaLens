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

    max_samples: int = 600
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
    capture_to_render_p50_ms: float | None
    capture_to_render_p95_ms: float | None
    processing_p50_ms: float | None
    processing_p95_ms: float | None
    rss_start_mib: float | None
    rss_end_mib: float | None
    rss_peak_mib: float | None
    rss_delta_mib: float | None
    rss_slope_mib_per_minute: float | None
    rss_steady_state_delta_mib: float | None
    rss_steady_state_slope_mib_per_minute: float | None
    capture_to_render_slope_ms_per_minute: float | None
    retained_latency_samples: int
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
        self._latencies_ms: deque[tuple[float, float]] = deque(
            maxlen=self.config.max_samples
        )
        self._processing_ms: deque[tuple[float, float]] = deque(
            maxlen=self.config.max_samples
        )
        self._memory_samples: deque[tuple[float, float]] = deque(
            maxlen=self.config.max_samples
        )
        self._record_memory(self._started_ns)

    def observe(
        self,
        *,
        capture_to_render_ms: float,
        processing_ms: float,
        observed_ns: int | None = None,
    ) -> None:
        """Record one processed frame and periodically sample current RSS."""

        now_ns = self._clock_ns() if observed_ns is None else observed_ns
        if now_ns < self._last_observed_ns:
            raise ValueError("observed_ns must be monotonic")
        for field_name, value in (
            ("capture_to_render_ms", capture_to_render_ms),
            ("processing_ms", processing_ms),
        ):
            if not np.isfinite(value) or value < 0.0:
                raise ValueError(f"{field_name} must be finite and non-negative")
        self._last_observed_ns = now_ns
        self._total_frames += 1
        elapsed_seconds = (now_ns - self._started_ns) / 1_000_000_000.0
        self._latencies_ms.append((elapsed_seconds, float(capture_to_render_ms)))
        self._processing_ms.append((elapsed_seconds, float(processing_ms)))
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
            capture_to_render_p50_ms=_timed_percentile(self._latencies_ms, 50.0),
            capture_to_render_p95_ms=_timed_percentile(self._latencies_ms, 95.0),
            processing_p50_ms=_timed_percentile(self._processing_ms, 50.0),
            processing_p95_ms=_timed_percentile(self._processing_ms, 95.0),
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
            capture_to_render_slope_ms_per_minute=_timed_slope(
                self._latencies_ms
            ),
            retained_latency_samples=len(self._latencies_ms),
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
