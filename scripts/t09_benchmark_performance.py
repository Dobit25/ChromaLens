"""Run one frozen T09 performance case and write a schema-1.0.0 JSON artifact.

This runner intentionally records software latency only.  It never turns
OpenCV timestamps into a sensor-to-photon claim and it writes no frames,
video, or per-frame trace.  The normal procedure is 15 seconds warm-up plus
120 measured seconds; any CLI duration override is marked as a smoke result.
"""

from __future__ import annotations

import argparse
from dataclasses import dataclass
from datetime import datetime, timezone
import hashlib
import importlib.metadata
import json
import os
from pathlib import Path
import platform
import re
import subprocess
import sys
from time import monotonic_ns
from typing import Any, Sequence

from chromalens import __version__
from chromalens.app import RuntimeControls, run_pipeline_session
from chromalens.camera import FrameSource, open_video, open_webcam
from chromalens.config import CVDProfile
from chromalens.contracts import FramePacket
from chromalens.metrics import RuntimeMetricsSnapshot
from chromalens.pipeline import ChromaLensPipeline
from chromalens.renderer import PipelineView
from chromalens.segmentation.mediapipe_backend import MediaPipeSegmenter


DEFAULT_OUTPUT_DIR = Path("artifacts/t09/performance_responsible_ai")
DEFAULT_WARMUP_SECONDS = 15.0
DEFAULT_MEASUREMENT_SECONDS = 120.0
LOCK_FILE = Path("requirements/segment-mediapipe-py310-win64.lock")
WORKSTREAM = "performance_responsible_ai"


@dataclass(frozen=True, slots=True)
class BenchmarkCase:
    case_id: str
    fixture_id: str
    source_kind: str
    display_mode: str
    requested_resolution: tuple[int, int]


CASES = {
    "PERF-WEBCAM-GUI-120": BenchmarkCase(
        "PERF-WEBCAM-GUI-120", "webcam-gui-640x480", "webcam", "gui", (640, 480)
    ),
    "PERF-WEBCAM-HEADLESS-120": BenchmarkCase(
        "PERF-WEBCAM-HEADLESS-120", "webcam-headless-640x480", "webcam", "headless", (640, 480)
    ),
    "PERF-VIDEO-GUI-120": BenchmarkCase(
        "PERF-VIDEO-GUI-120", "generated-video-gui-360x240", "video", "gui", (360, 240)
    ),
    "PERF-VIDEO-HEADLESS-120": BenchmarkCase(
        "PERF-VIDEO-HEADLESS-120", "generated-video-headless-360x240", "video", "headless", (360, 240)
    ),
}


class LoopingVideoSource(FrameSource):
    """Reopen a finite local video at EOF without retaining any frames."""

    def __init__(self, path: Path) -> None:
        self._path = path
        self._source = open_video(path)
        self._frame_id = 0
        self._closed = False

    @property
    def name(self) -> str:
        return self._source.name

    @property
    def is_live(self) -> bool:
        return False

    @property
    def resolution(self) -> tuple[int, int] | None:
        return self._source.resolution

    @property
    def nominal_fps(self) -> float | None:
        return self._source.nominal_fps

    def read(self) -> FramePacket | None:
        if self._closed:
            raise RuntimeError("looping video source is closed")
        packet = self._source.read()
        if packet is None:
            self._source.close()
            self._source = open_video(self._path)
            packet = self._source.read()
        if packet is None:
            raise RuntimeError(f"video '{self._path}' contains no decodable frames")
        looped = FramePacket(
            frame_id=self._frame_id,
            timestamp_ns=monotonic_ns(),
            original_bgr=packet.original_bgr,
        )
        self._frame_id += 1
        return looped

    def close(self) -> None:
        if not self._closed:
            self._source.close()
            self._closed = True


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--case", required=True, choices=tuple(CASES))
    parser.add_argument("--video", type=Path, help="local generated comparison video")
    parser.add_argument("--camera-index", type=_non_negative_int, default=0)
    parser.add_argument("--warmup-seconds", type=_non_negative_float, default=DEFAULT_WARMUP_SECONDS)
    parser.add_argument(
        "--measurement-seconds",
        "--duration-seconds",
        dest="measurement_seconds",
        type=_positive_float,
        default=DEFAULT_MEASUREMENT_SECONDS,
    )
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--operator", default="Trinh")
    parser.add_argument("--host-role", choices=("development", "demo"), default="development")
    parser.add_argument("--declared-demo-hardware", action="store_true")
    parser.add_argument("--profile", choices=tuple(item.value for item in CVDProfile), default="deutan")
    parser.add_argument("--severity", type=_severity, default=0.8)
    parser.add_argument("--window-title", default="ChromaLens AI - T09 Benchmark")
    return parser


def validate_args(args: argparse.Namespace, parser: argparse.ArgumentParser) -> BenchmarkCase:
    case = CASES[args.case]
    if case.source_kind == "video" and args.video is None:
        parser.error("--video is required for a PERF-VIDEO-* case")
    if case.source_kind == "webcam" and args.video is not None:
        parser.error("--video is valid only for a PERF-VIDEO-* case")
    if args.host_role == "demo" and not args.declared_demo_hardware:
        parser.error("--host-role demo requires --declared-demo-hardware")
    if args.declared_demo_hardware and args.host_role != "demo":
        parser.error("--declared-demo-hardware requires --host-role demo")
    if not args.operator.strip():
        parser.error("--operator must not be empty")
    _validate_output_dir(args.output_dir)
    return case


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    case = validate_args(args, parser)
    started_at = _utc_now()
    source = _open_source(case, args)
    pipeline = ChromaLensPipeline(MediaPipeSegmenter(), stream_id=source.name)
    session = run_pipeline_session(
        source,
        pipeline,
        controls=RuntimeControls(
            profile=CVDProfile(args.profile),
            severity=args.severity,
            view=PipelineView.ASSISTIVE,
        ),
        display=case.display_mode == "gui",
        duration_seconds=args.measurement_seconds,
        metrics_warmup_seconds=args.warmup_seconds,
        window_title=args.window_title,
    )
    ended_at = _utc_now()
    payload = build_result_payload(
        case=case,
        snapshot=session.metrics,
        source_name=session.source_name,
        resolution=session.resolution,
        backend_name=session.backend_name,
        warmup_seconds=args.warmup_seconds,
        measurement_seconds=args.measurement_seconds,
        profile=args.profile,
        severity=args.severity,
        operator=args.operator,
        host_role=args.host_role,
        declared_demo_hardware=args.declared_demo_hardware,
        command=" ".join(sys.argv),
        started_at_utc=started_at,
        ended_at_utc=ended_at,
        stop_reason=session.stop_reason,
    )
    output_path = write_result(payload, args.output_dir)
    print(f"T09 benchmark artifact written: {output_path}")
    print("official_benchmark=" + str(is_official_duration(args.warmup_seconds, args.measurement_seconds)).lower())
    return 0


def build_result_payload(
    *,
    case: BenchmarkCase,
    snapshot: RuntimeMetricsSnapshot,
    source_name: str,
    resolution: tuple[int, int] | None,
    backend_name: str,
    warmup_seconds: float,
    measurement_seconds: float,
    profile: str,
    severity: float,
    operator: str,
    host_role: str,
    declared_demo_hardware: bool,
    command: str,
    started_at_utc: str,
    ended_at_utc: str,
    stop_reason: str,
) -> dict[str, Any]:
    """Map one runtime snapshot to the frozen schema metric records."""

    official = is_official_duration(warmup_seconds, measurement_seconds)
    samples_complete = _samples_complete(case, snapshot)
    completion_reasons = _completion_reasons(
        case=case,
        snapshot=snapshot,
        warmup_seconds=warmup_seconds,
        measurement_seconds=measurement_seconds,
        stop_reason=stop_reason,
        resolution=resolution,
        samples_complete=samples_complete,
    )
    result_status = (
        "INVALID" if not samples_complete
        else "COMPLETE" if official and not completion_reasons else "PARTIAL"
    )
    created = ended_at_utc
    result_id = "t09-performance-" + case.case_id.lower() + "-" + _timestamp_id(created)
    metrics = snapshot_to_schema_metrics(case, snapshot, declared_demo_hardware)
    source_resolution = _resolution_dict(resolution or case.requested_resolution)
    backend_device = backend_name.rsplit("/", 1)[-1] if "/" in backend_name else "unknown"
    notes = (
        "Official-duration measurement." if official else
        "SMOKE/OVERRIDE RESULT ONLY: duration differs from the frozen 15 s warm-up + 120 s measurement and is not an official benchmark."
    )
    if completion_reasons:
        notes += " Completion gate not met: " + "; ".join(completion_reasons) + "."
    return {
        "protocol_version": "1.0.0",
        "schema_version": "1.0.0",
        "metric_registry_version": "1.0.0",
        "result_id": result_id,
        "workstream": WORKSTREAM,
        "result_status": result_status,
        "git_commit": _git_commit(),
        "created_at_utc": created,
        "operator": {"role": "performance_evaluator", "identifier": operator},
        "environment": {
            **collect_environment(),
            "host_role": host_role,
            "declared_demo_hardware": declared_demo_hardware,
            "camera_or_source": source_name,
            "backend_name": backend_name,
            "backend_device": backend_device,
            "source_kind": case.source_kind,
            "source_resolution": source_resolution,
            "render_resolution": source_resolution,
            "display_mode": case.display_mode,
            "warmup_seconds": warmup_seconds,
            "measurement_seconds": measurement_seconds,
        },
        "cases": [{
            "case_id": case.case_id,
            "status": result_status,
            "fixture_id": case.fixture_id,
            "artifact_ids": [],
            "reason": notes + f" Stop reason: {stop_reason}.",
        }],
        "configuration": {
            "cvd_profile": profile,
            "severity": severity,
            "thresholds": {
                "metrics_warmup_seconds": warmup_seconds,
                "measurement_seconds": measurement_seconds,
                "required_render_samples": snapshot.total_frames,
                "required_display_samples": 0 if case.display_mode == "headless" else snapshot.total_frames,
            },
            "settings": {"recolor_enabled": True, "view": "assistive"},
        },
        "metrics": metrics,
        "artifacts": [],
        "commands": [{
            "command": command,
            "exit_code": 0,
            "started_at_utc": started_at_utc,
            "ended_at_utc": ended_at_utc,
            "output_summary": "No raw frames, video, or per-frame traces were written.",
        }],
        "failure_cases": [],
        "limitations": [
            "sensor_to_photon_ms is NOT_MEASURED without synchronized external apparatus.",
            "This result is scoped to the recorded host, source, resolution, backend, and device.",
            "The MediaPipe backend is a person-derived torso heuristic, not calibrated semantic garment parsing.",
        ],
        "responsible_ai": {
            "runtime_local_offline": True,
            "frames_saved_by_default": False,
            "frames_uploaded_by_default": False,
            "medical_diagnosis_claim": False,
            "user_selected_profile": True,
            "privacy_summary": "The benchmark uses local inference and writes only aggregate JSON metrics; it does not save or upload camera frames by default.",
            "bias_coverage_summary": "A performance run does not validate demographic, garment, lighting, camera, or display coverage.",
            "environmental_summary": "The result records backend, device, FPS, and RSS as an efficiency proxy; it makes no energy-use claim.",
            "license_summary": "This runner reuses the repository's locked dependencies and does not add a model, dataset, or dependency.",
            "user_validation_status": "NOT_MEASURED",
        },
        "notes": notes,
    }


def snapshot_to_schema_metrics(
    case: BenchmarkCase,
    snapshot: RuntimeMetricsSnapshot,
    declared_demo_hardware: bool,
) -> list[dict[str, Any]]:
    """Return every case-required T09 performance metric in registry units."""

    ids = [case.case_id]
    demo_fps = _threshold(snapshot.processed_fps, ">=", 5.0, declared_demo_hardware)
    records = [
        _metric("processed_fps", "single", "frames/s", snapshot.processed_fps, ids, "demo_floor", demo_fps, "processed frames / measured elapsed seconds"),
        *_percentiles("source_read_to_render_ms", snapshot.source_read_to_render_p50_ms, snapshot.source_read_to_render_p95_ms, ids, "observation_only"),
        _metric("source_read_to_render_slope_ms_per_minute", "whole_session", "ms/min", snapshot.source_read_to_render_slope_ms_per_minute, ids, "observation_only", "NOT_EVALUATED", "ordinary least-squares slope over retained render samples"),
        *_display_metrics(case, snapshot, ids, declared_demo_hardware),
        *_not_measured_sensor_metrics(ids),
        *_percentiles("frame_processing_to_render_ms", snapshot.frame_processing_to_render_p50_ms, snapshot.frame_processing_to_render_p95_ms, ids, "observation_only"),
        _metric("rss_mib", "start", "MiB", snapshot.rss_start_mib, ids, "observation_only", "NOT_EVALUATED", "process RSS/working set at measurement start"),
        _metric("rss_mib", "end", "MiB", snapshot.rss_end_mib, ids, "observation_only", "NOT_EVALUATED", "process RSS/working set at measurement end"),
        _metric("rss_mib", "peak", "MiB", snapshot.rss_peak_mib, ids, "observation_only", "NOT_EVALUATED", "peak retained process RSS/working-set sample"),
        _metric("rss_delta_mib", "whole_session", "MiB", snapshot.rss_delta_mib, ids, "observation_only", "NOT_EVALUATED", "RSS end minus start"),
        _metric("rss_slope_mib_per_minute", "whole_session", "MiB/min", snapshot.rss_slope_mib_per_minute, ids, "observation_only", "NOT_EVALUATED", "ordinary least-squares RSS slope"),
        _metric("latency_continuous_growth_flag", "single", "boolean", snapshot.latency_continuous_growth_flag, ids, "required", _boolean_threshold(snapshot.latency_continuous_growth_flag), "frozen four 30-second render-latency median diagnostic"),
        _metric("rss_continuous_growth_flag", "single", "boolean", snapshot.rss_continuous_growth_flag, ids, "required", _boolean_threshold(snapshot.rss_continuous_growth_flag), "frozen four 30-second RSS median diagnostic"),
        _metric("processed_frame_count", "count", "frame", snapshot.total_frames, ids, "must_be_positive", "PASS" if snapshot.total_frames > 0 else "FAIL", "frames completing render in measurement interval"),
    ]
    if case.source_kind == "webcam":
        records.append(_metric("dropped_capture_frame_count", "count", "frame", snapshot.dropped_capture_frames, ids, "observation_only", "NOT_EVALUATED", "newest-frame mailbox overwrites in measurement interval"))
    degraded_rate = None if snapshot.total_frames == 0 else snapshot.degraded_frames / snapshot.total_frames
    render_samples_ok = snapshot.retained_source_read_to_render_samples == snapshot.total_frames
    expected_display_samples = 0 if case.display_mode == "headless" else snapshot.total_frames
    display_samples = snapshot.retained_source_read_to_display_submit_samples
    records.extend((
        _metric("degraded_frame_rate", "single", "ratio", degraded_rate, ids, "observation_only", "NOT_EVALUATED", "degraded frames / processed frames"),
        _metric("retained_source_read_to_render_sample_count", "count", "count", snapshot.retained_source_read_to_render_samples, ids, "no_truncation", "PASS" if render_samples_ok else "FAIL", "retained source-read-to-render samples"),
        _metric("retained_source_read_to_display_submit_sample_count", "count", "count", display_samples, ids, "no_truncation_gui", "PASS" if display_samples == expected_display_samples else "FAIL", "retained display-submit samples; must be zero in headless mode"),
    ))
    return records


def _display_metrics(case: BenchmarkCase, snapshot: RuntimeMetricsSnapshot, ids: list[str], declared_demo_hardware: bool) -> list[dict[str, Any]]:
    if case.display_mode == "headless":
        reason = "headless run has no OpenCV GUI submission"
        return [
            _metric("source_read_to_display_submit_ms", "p50", "ms", None, ids, "demo_floor_p50", "NOT_EVALUATED", reason, status="NOT_MEASURED"),
            _metric("source_read_to_display_submit_ms", "p95", "ms", None, ids, None, "NOT_EVALUATED", reason, status="NOT_MEASURED"),
        ]
    p50_threshold = _threshold(snapshot.source_read_to_display_submit_p50_ms, "<=", 350.0, declared_demo_hardware)
    return [
        _metric("source_read_to_display_submit_ms", "p50", "ms", snapshot.source_read_to_display_submit_p50_ms, ids, "demo_floor_p50", p50_threshold, "post-cv2.imshow software submission latency"),
        _metric("source_read_to_display_submit_ms", "p95", "ms", snapshot.source_read_to_display_submit_p95_ms, ids, None, "NOT_EVALUATED", "post-cv2.imshow software submission latency"),
    ]


def _not_measured_sensor_metrics(ids: list[str]) -> list[dict[str, Any]]:
    reason = "no synchronized external photodiode/high-speed-camera apparatus was used"
    return [_metric("sensor_to_photon_ms", aggregation, "ms", None, ids, "external_apparatus_required", "NOT_EVALUATED", reason, status="NOT_MEASURED") for aggregation in ("p50", "p95")]


def _percentiles(name: str, p50: float | None, p95: float | None, ids: list[str], threshold_id: str) -> list[dict[str, Any]]:
    return [
        _metric(name, "p50", "ms", p50, ids, threshold_id, "NOT_EVALUATED", "runtime metric p50 over every retained measurement sample"),
        _metric(name, "p95", "ms", p95, ids, threshold_id, "NOT_EVALUATED", "runtime metric p95 over every retained measurement sample"),
    ]


def _metric(name: str, aggregation: str, unit: str, value: Any, case_ids: list[str], threshold_id: str | None, threshold_result: str, method: str, *, status: str | None = None) -> dict[str, Any]:
    measured = value is not None if status is None else status == "MEASURED"
    return {
        "name": name, "aggregation": aggregation, "unit": unit,
        "status": "MEASURED" if measured else "NOT_MEASURED",
        "value": value if measured else None,
        "case_ids": case_ids, "threshold_id": threshold_id,
        "threshold_result": threshold_result,
        "reason": "" if measured else method,
        "method": method,
    }


def _threshold(value: float | None, comparator: str, boundary: float, enabled: bool) -> str:
    if not enabled or value is None:
        return "NOT_EVALUATED"
    return "PASS" if (value >= boundary if comparator == ">=" else value <= boundary) else "FAIL"


def _boolean_threshold(value: bool | None) -> str:
    if value is None:
        return "NOT_EVALUATED"
    return "PASS" if value is False else "FAIL"


def is_official_duration(warmup_seconds: float, measurement_seconds: float) -> bool:
    return warmup_seconds == DEFAULT_WARMUP_SECONDS and measurement_seconds == DEFAULT_MEASUREMENT_SECONDS


def _samples_complete(case: BenchmarkCase, snapshot: RuntimeMetricsSnapshot) -> bool:
    expected_display_samples = (
        0 if case.display_mode == "headless" else snapshot.total_frames
    )
    return (
        snapshot.retained_source_read_to_render_samples == snapshot.total_frames
        and snapshot.retained_source_read_to_display_submit_samples
        == expected_display_samples
    )


def _completion_reasons(
    *,
    case: BenchmarkCase,
    snapshot: RuntimeMetricsSnapshot,
    warmup_seconds: float,
    measurement_seconds: float,
    stop_reason: str,
    resolution: tuple[int, int] | None,
    samples_complete: bool,
) -> list[str]:
    reasons: list[str] = []
    if warmup_seconds != DEFAULT_WARMUP_SECONDS:
        reasons.append(f"warm-up was {warmup_seconds:g}s, not 15s")
    if measurement_seconds != DEFAULT_MEASUREMENT_SECONDS:
        reasons.append(f"requested measurement was {measurement_seconds:g}s, not 120s")
    if stop_reason != "duration_limit":
        reasons.append(f"stop reason was {stop_reason!r}, not 'duration_limit'")
    if snapshot.elapsed_seconds < measurement_seconds:
        reasons.append(
            f"measured elapsed time was {snapshot.elapsed_seconds:.3f}s, below requested {measurement_seconds:g}s"
        )
    if snapshot.total_frames <= 0:
        reasons.append("no frames completed render during measurement")
    if not samples_complete:
        reasons.append("retained latency sample counts are incomplete")
    if resolution != case.requested_resolution:
        actual = "unavailable" if resolution is None else f"{resolution[0]}x{resolution[1]}"
        expected = f"{case.requested_resolution[0]}x{case.requested_resolution[1]}"
        reasons.append(f"source resolution was {actual}, not frozen {expected}")
    return reasons


def write_result(payload: dict[str, Any], output_dir: Path) -> Path:
    _validate_output_dir(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    path = output_dir / f"{payload['result_id']}.json"
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    return path


def collect_environment() -> dict[str, Any]:
    """Collect non-sensitive host/package data without a new dependency."""
    manufacturer, model = _windows_computer_identity()
    return {
        "manufacturer": manufacturer,
        "model": model,
        "operating_system": platform.platform(),
        "cpu": platform.processor() or platform.machine() or "unknown",
        "physical_core_count": _physical_core_count(),
        "logical_processor_count": os.cpu_count() or 1,
        "ram_gib": _ram_gib(),
        "gpu": _windows_video_controllers(),
        "npu": "not detected",
        "python_version": platform.python_version(),
        "package_versions": _package_versions(),
        "lock_sha256": _sha256(LOCK_FILE),
    }


def _open_source(case: BenchmarkCase, args: argparse.Namespace) -> FrameSource:
    if case.source_kind == "webcam":
        width, height = case.requested_resolution
        return open_webcam(args.camera_index, width=width, height=height)
    assert args.video is not None
    return LoopingVideoSource(args.video)


def _validate_output_dir(path: Path) -> None:
    root = (Path.cwd() / DEFAULT_OUTPUT_DIR).resolve()
    try:
        (Path.cwd() / path).resolve().relative_to(root)
    except ValueError as exc:
        raise ValueError("--output-dir must remain under artifacts/t09/performance_responsible_ai") from exc


def _package_versions() -> dict[str, str]:
    result = {"chromalens-ai": __version__}
    for distribution in ("numpy", "opencv-contrib-python", "mediapipe", "daltonlens"):
        try:
            result[distribution] = importlib.metadata.version(distribution)
        except importlib.metadata.PackageNotFoundError:
            result[distribution] = "not_installed"
    return result


def _git_commit() -> str:
    try:
        commit = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            check=True,
            capture_output=True,
            text=True,
        ).stdout.strip()
    except (OSError, subprocess.CalledProcessError) as exc:
        raise RuntimeError("could not determine the required Git commit SHA") from exc
    if re.fullmatch(r"[0-9a-f]{40}", commit) is None:
        raise RuntimeError(f"git rev-parse HEAD returned invalid SHA: {commit!r}")
    return commit


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _windows_computer_identity() -> tuple[str, str]:
    output = _powershell("(Get-CimInstance Win32_ComputerSystem | Select-Object -Property Manufacturer,Model | ConvertTo-Json -Compress)")
    try:
        value = json.loads(output)
        return str(value.get("Manufacturer") or "unknown"), str(value.get("Model") or "unknown")
    except (json.JSONDecodeError, AttributeError):
        return "unknown", platform.node() or "unknown"


def _windows_video_controllers() -> str:
    output = _powershell("(Get-CimInstance Win32_VideoController | Select-Object -ExpandProperty Name | ConvertTo-Json -Compress)")
    try:
        values = json.loads(output)
    except json.JSONDecodeError:
        return "not detected"
    if isinstance(values, list):
        return "; ".join(str(item) for item in values) or "not detected"
    return str(values) if values else "not detected"


def _powershell(command: str) -> str:
    if os.name != "nt":
        return ""
    try:
        return subprocess.run(["powershell", "-NoProfile", "-Command", command], check=True, capture_output=True, text=True, timeout=5).stdout.strip()
    except (OSError, subprocess.CalledProcessError, subprocess.TimeoutExpired):
        return ""


def _physical_core_count() -> int:
    output = _powershell("(Get-CimInstance Win32_Processor | Measure-Object -Property NumberOfCores -Sum).Sum")
    try:
        return max(1, int(output))
    except ValueError:
        return os.cpu_count() or 1


def _ram_gib() -> float:
    if os.name == "nt":
        import ctypes
        class MemoryStatus(ctypes.Structure):
            _fields_ = [("dwLength", ctypes.c_ulong), ("dwMemoryLoad", ctypes.c_ulong), ("ullTotalPhys", ctypes.c_ulonglong), ("ullAvailPhys", ctypes.c_ulonglong), ("ullTotalPageFile", ctypes.c_ulonglong), ("ullAvailPageFile", ctypes.c_ulonglong), ("ullTotalVirtual", ctypes.c_ulonglong), ("ullAvailVirtual", ctypes.c_ulonglong), ("ullAvailExtendedVirtual", ctypes.c_ulonglong)]
        status = MemoryStatus()
        status.dwLength = ctypes.sizeof(MemoryStatus)
        if ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(status)):
            return status.ullTotalPhys / (1024.0 ** 3)
    return max(0.001, float(os.sysconf("SC_PAGE_SIZE") * os.sysconf("SC_PHYS_PAGES")) / (1024.0 ** 3))


def _resolution_dict(resolution: tuple[int, int]) -> dict[str, int]:
    return {"width": resolution[0], "height": resolution[1]}


def _timestamp_id(value: str) -> str:
    return datetime.fromisoformat(value.replace("Z", "+00:00")).strftime("%Y%m%dt%H%M%Sz").lower()


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _positive_float(value: str) -> float:
    parsed = float(value)
    if parsed <= 0.0:
        raise argparse.ArgumentTypeError("must be positive")
    return parsed


def _non_negative_float(value: str) -> float:
    parsed = float(value)
    if parsed < 0.0:
        raise argparse.ArgumentTypeError("must be non-negative")
    return parsed


def _non_negative_int(value: str) -> int:
    parsed = int(value)
    if parsed < 0:
        raise argparse.ArgumentTypeError("must be non-negative")
    return parsed


def _severity(value: str) -> float:
    parsed = float(value)
    if not 0.0 <= parsed <= 1.0:
        raise argparse.ArgumentTypeError("must be within [0, 1]")
    return parsed


if __name__ == "__main__":
    raise SystemExit(main())
