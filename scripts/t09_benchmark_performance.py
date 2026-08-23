"""Run one frozen T09 benchmark case and write raw JSON below ignored artifacts/."""

from __future__ import annotations

import argparse
from dataclasses import dataclass
from pathlib import Path
from time import monotonic_ns
from typing import Any, Mapping, Sequence

import cv2
import numpy as np

from chromalens.app import RuntimeControls, run_pipeline_session
from chromalens.camera import (
    FrameSource,
    FrameSourceClosedError,
    FrameSourceOpenError,
    FrameSourceReadError,
    open_webcam,
)
from chromalens.config import CVDProfile
from chromalens.contracts import FramePacket
from chromalens.metrics import RuntimeMetricsSnapshot
from chromalens.pipeline import ChromaLensPipeline
from chromalens.segmentation import MediaPipeSegmenter
from scripts.t09_evaluation_common import (
    PROTOCOL_VERSION,
    ROOT,
    collect_environment,
    git_commit,
    result_timestamp,
    utc_now,
    utc_text,
    write_json_lf,
)


WORKSTREAM = "performance_responsible_ai"
OUTPUT_DIR = ROOT / "artifacts/t09/performance_responsible_ai"
LOCK_PATH = ROOT / "requirements/segment-mediapipe-py310-win64.lock"
DEFAULT_WARMUP_SECONDS = 15.0
DEFAULT_MEASUREMENT_SECONDS = 120.0


@dataclass(frozen=True, slots=True)
class BenchmarkCase:
    case_id: str
    fixture_id: str
    source_kind: str
    display: bool
    width: int
    height: int


CASES = {
    case.case_id: case
    for case in (
        BenchmarkCase(
            "PERF-WEBCAM-GUI-120", "webcam-gui-640x480", "webcam", True, 640, 480
        ),
        BenchmarkCase(
            "PERF-WEBCAM-HEADLESS-120",
            "webcam-headless-640x480",
            "webcam",
            False,
            640,
            480,
        ),
        BenchmarkCase(
            "PERF-VIDEO-GUI-120",
            "generated-video-gui-360x240",
            "video",
            True,
            360,
            240,
        ),
        BenchmarkCase(
            "PERF-VIDEO-HEADLESS-120",
            "generated-video-headless-360x240",
            "video",
            False,
            360,
            240,
        ),
    )
}


class LoopingVideoSource(FrameSource):
    """Finite-video bytes replayed sequentially for a fixed measurement window."""

    def __init__(self, path: Path) -> None:
        self.path = path.resolve()
        if not self.path.is_file():
            raise FrameSourceOpenError(f"benchmark video does not exist: {self.path}")
        self._capture = cv2.VideoCapture(str(self.path))
        if not self._capture.isOpened():
            self._capture.release()
            raise FrameSourceOpenError(f"cannot decode benchmark video: {self.path}")
        self._closed = False
        self._frame_id = 0
        self._resolution = (
            int(self._capture.get(cv2.CAP_PROP_FRAME_WIDTH)),
            int(self._capture.get(cv2.CAP_PROP_FRAME_HEIGHT)),
        )
        fps = float(self._capture.get(cv2.CAP_PROP_FPS))
        self._fps = fps if np.isfinite(fps) and fps > 0 else None

    @property
    def name(self) -> str:
        return f"video-loop:{self.path.name}"

    @property
    def is_live(self) -> bool:
        return False

    @property
    def resolution(self) -> tuple[int, int] | None:
        return self._resolution

    @property
    def nominal_fps(self) -> float | None:
        return self._fps

    def read(self) -> FramePacket | None:
        if self._closed:
            raise FrameSourceClosedError("looping benchmark video is closed")
        ok, frame = self._capture.read()
        if not ok or frame is None:
            if not self._capture.set(cv2.CAP_PROP_POS_FRAMES, 0.0):
                raise FrameSourceReadError("benchmark video could not rewind")
            ok, frame = self._capture.read()
        if not ok or frame is None:
            raise FrameSourceReadError("benchmark video returned no frame after rewind")
        if frame.dtype != np.uint8 or frame.ndim != 3 or frame.shape[2] != 3:
            raise FrameSourceReadError("benchmark video returned a non-uint8 BGR frame")
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


def snapshot_metrics(
    case: BenchmarkCase,
    snapshot: RuntimeMetricsSnapshot,
    *,
    declared_demo_hardware: bool,
) -> list[dict[str, Any]]:
    """Map T08's frozen timestamps to registry metrics without renaming them."""

    case_ids = [case.case_id]
    metrics = [
        measured(
            "processed_fps",
            "single",
            "frames/s",
            snapshot.processed_fps,
            case_ids,
            "demo_floor",
            "processed_frame_count / measured elapsed seconds",
            threshold_result=(
                numeric_threshold(snapshot.processed_fps, ">=", 5.0)
                if declared_demo_hardware
                else "NOT_EVALUATED"
            ),
        ),
        measured(
            "source_read_to_render_ms",
            "p50",
            "ms",
            snapshot.source_read_to_render_p50_ms,
            case_ids,
            "observation_only",
            "capture-return-to-render-complete latency; monotonic software timestamps",
        ),
        measured(
            "source_read_to_render_ms",
            "p95",
            "ms",
            snapshot.source_read_to_render_p95_ms,
            case_ids,
            "observation_only",
            "linear percentile over all retained measurement-window samples",
        ),
        measured(
            "source_read_to_render_slope_ms_per_minute",
            "whole_session",
            "ms/min",
            snapshot.source_read_to_render_slope_ms_per_minute,
            case_ids,
            "observation_only",
            "ordinary least-squares slope over the measured session",
        ),
        measured(
            "frame_processing_to_render_ms",
            "p50",
            "ms",
            snapshot.frame_processing_to_render_p50_ms,
            case_ids,
            "observation_only",
            "processing start to render complete",
        ),
        measured(
            "frame_processing_to_render_ms",
            "p95",
            "ms",
            snapshot.frame_processing_to_render_p95_ms,
            case_ids,
            "observation_only",
            "linear percentile over all retained measurement-window samples",
        ),
        measured("rss_mib", "start", "MiB", snapshot.rss_start_mib, case_ids, "observation_only", "process working set/RSS"),
        measured("rss_mib", "end", "MiB", snapshot.rss_end_mib, case_ids, "observation_only", "process working set/RSS"),
        measured("rss_mib", "peak", "MiB", snapshot.rss_peak_mib, case_ids, "observation_only", "process working set/RSS"),
        measured("rss_delta_mib", "whole_session", "MiB", snapshot.rss_delta_mib, case_ids, "observation_only", "RSS end minus start"),
        measured("rss_slope_mib_per_minute", "whole_session", "MiB/min", snapshot.rss_slope_mib_per_minute, case_ids, "observation_only", "ordinary least-squares RSS slope"),
        measured("latency_continuous_growth_flag", "single", "boolean", snapshot.latency_continuous_growth_flag, case_ids, "required", "frozen four-window diagnostic", threshold_result=boolean_threshold(snapshot.latency_continuous_growth_flag, False)),
        measured("rss_continuous_growth_flag", "single", "boolean", snapshot.rss_continuous_growth_flag, case_ids, "required", "frozen four-window diagnostic", threshold_result=boolean_threshold(snapshot.rss_continuous_growth_flag, False)),
        measured("processed_frame_count", "count", "frame", snapshot.total_frames, case_ids, "report_coverage", "frames processed in measurement window"),
        measured("dropped_capture_frame_count", "count", "frame", snapshot.dropped_capture_frames if case.source_kind == "webcam" else None, case_ids, "report_coverage", "capacity-one webcam mailbox overwrites; not applicable to sequential video", status="MEASURED" if case.source_kind == "webcam" else "NOT_APPLICABLE"),
        measured("degraded_frame_rate", "overall", "ratio", snapshot.degraded_frames / snapshot.total_frames if snapshot.total_frames else None, case_ids, "observation_only", "degraded frames / processed frames"),
        measured("retained_source_read_to_render_sample_count", "count", "count", snapshot.retained_source_read_to_render_samples, case_ids, "untruncated_required", "retained bounded samples"),
        measured("retained_source_read_to_display_submit_sample_count", "count", "count", snapshot.retained_source_read_to_display_submit_samples, case_ids, "gui_equals_processed_headless_zero", "GUI retains one display sample per frame; headless retains zero"),
    ]
    if case.display:
        metrics.extend(
            [
                measured("source_read_to_display_submit_ms", "p50", "ms", snapshot.source_read_to_display_submit_p50_ms, case_ids, "demo_floor_p50", "software timestamp immediately after cv2.imshow returns; not sensor-to-photon", threshold_result=numeric_threshold(snapshot.source_read_to_display_submit_p50_ms, "<=", 350.0) if declared_demo_hardware else "NOT_EVALUATED"),
                measured("source_read_to_display_submit_ms", "p95", "ms", snapshot.source_read_to_display_submit_p95_ms, case_ids, None, "software GUI submission observation only"),
            ]
        )
    else:
        metrics.extend(
            [
                measured("source_read_to_display_submit_ms", "p50", "ms", None, case_ids, "demo_floor_p50", "headless run has no OpenCV GUI submission", status="NOT_MEASURED"),
                measured("source_read_to_display_submit_ms", "p95", "ms", None, case_ids, None, "headless run has no OpenCV GUI submission", status="NOT_MEASURED"),
            ]
        )
    metrics.extend(
        [
            measured("sensor_to_photon_ms", "p50", "ms", None, case_ids, "external_apparatus_required", "NOT_MEASURED: no external synchronized apparatus", status="NOT_MEASURED", method="No external apparatus; software timestamps cannot measure sensor-to-photon"),
            measured("sensor_to_photon_ms", "p95", "ms", None, case_ids, "external_apparatus_required", "NOT_MEASURED: no external synchronized apparatus", status="NOT_MEASURED", method="No external apparatus; software timestamps cannot measure sensor-to-photon"),
        ]
    )
    return metrics


def measured(
    name: str,
    aggregation: str,
    unit: str,
    value: Any,
    case_ids: Sequence[str],
    threshold_id: str | None,
    reason: str,
    *,
    status: str = "MEASURED",
    threshold_result: str = "NOT_EVALUATED",
    method: str = "T09 protocol 1.0.0 frozen runtime instrumentation",
) -> dict[str, Any]:
    if status != "MEASURED":
        value = None
        threshold_result = "NOT_APPLICABLE" if status == "NOT_APPLICABLE" else "NOT_EVALUATED"
    elif value is None:
        status = "NOT_MEASURED"
        threshold_result = "NOT_EVALUATED"
    return {
        "name": name,
        "aggregation": aggregation,
        "unit": unit,
        "status": status,
        "value": value,
        "case_ids": list(case_ids),
        "threshold_id": threshold_id,
        "threshold_result": threshold_result,
        "reason": reason,
        "method": method,
    }


def numeric_threshold(value: float | None, comparator: str, boundary: float) -> str:
    if value is None:
        return "NOT_EVALUATED"
    passed = value >= boundary if comparator == ">=" else value <= boundary
    return "PASS" if passed else "FAIL"


def boolean_threshold(value: bool | None, required: bool) -> str:
    if value is None:
        return "NOT_EVALUATED"
    return "PASS" if value is required else "FAIL"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--case", required=True, choices=tuple(CASES))
    parser.add_argument("--video", type=Path, help="required for frozen video cases")
    parser.add_argument("--camera-index", type=int, default=0)
    parser.add_argument("--warmup-seconds", type=float, default=DEFAULT_WARMUP_SECONDS)
    parser.add_argument("--measurement-seconds", type=float, default=DEFAULT_MEASUREMENT_SECONDS)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    case = CASES[args.case]
    if args.warmup_seconds < 0 or args.measurement_seconds <= 0:
        raise SystemExit("warmup must be non-negative and measurement must be positive")
    if case.source_kind == "video" and args.video is None:
        raise SystemExit("--video is required for a video benchmark case")
    if case.source_kind == "webcam" and args.video is not None:
        raise SystemExit("--video is invalid for a webcam benchmark case")

    source: FrameSource = (
        open_webcam(args.camera_index, width=case.width, height=case.height)
        if case.source_kind == "webcam"
        else LoopingVideoSource(args.video)
    )
    pipeline = ChromaLensPipeline(MediaPipeSegmenter(), stream_id=source.name)
    started = utc_now()
    result = run_pipeline_session(
        source,
        pipeline,
        controls=RuntimeControls(profile=CVDProfile.DEUTAN, severity=0.8),
        display=case.display,
        duration_seconds=args.measurement_seconds,
        metrics_warmup_seconds=args.warmup_seconds,
        window_title=f"ChromaLens T09 {case.case_id}",
    )
    ended = utc_now()
    actual_resolution = result.resolution or (case.width, case.height)
    metrics = snapshot_metrics(case, result.metrics, declared_demo_hardware=False)
    official = (
        args.warmup_seconds == DEFAULT_WARMUP_SECONDS
        and args.measurement_seconds == DEFAULT_MEASUREMENT_SECONDS
        and actual_resolution == (case.width, case.height)
        and result.stop_reason == "duration_limit"
    )
    status = "COMPLETE" if official else "PARTIAL"
    payload = {
        "protocol_version": PROTOCOL_VERSION,
        "schema_version": PROTOCOL_VERSION,
        "metric_registry_version": PROTOCOL_VERSION,
        "result_id": f"t09-performance-{case.case_id.lower()}-{result_timestamp(ended)}",
        "workstream": WORKSTREAM,
        "result_status": status,
        "git_commit": git_commit(),
        "created_at_utc": utc_text(ended),
        "operator": {"role": "performance_evaluator", "identifier": "local-operator"},
        "environment": collect_environment(
            lock_path=LOCK_PATH,
            backend_name=result.backend_name,
            backend_device="cpu",
            camera_or_source=result.source_name,
            source_kind=case.source_kind,
            source_resolution=actual_resolution,
            render_resolution=actual_resolution,
            display_mode="gui" if case.display else "headless",
            warmup_seconds=args.warmup_seconds,
            measurement_seconds=args.measurement_seconds,
        ),
        "cases": [{"case_id": case.case_id, "status": status, "fixture_id": case.fixture_id, "artifact_ids": [], "reason": "official frozen run" if official else "non-official override or early termination"}],
        "configuration": {"cvd_profile": "deutan", "severity": 0.8, "random_seed": None, "thresholds": {"demo_fps_floor": 5.0, "demo_display_p50_ms_floor": 350.0}, "settings": {"official_duration": official, "latency_semantics": "source read return to renderer/display submit"}},
        "metrics": metrics,
        "artifacts": [],
        "commands": [{"command": f"conda run --name lens python scripts/t09_benchmark_performance.py --case {case.case_id}", "exit_code": 0, "started_at_utc": utc_text(started), "ended_at_utc": utc_text(ended), "output_summary": f"{result.metrics.total_frames} measured frames; stop={result.stop_reason}"}],
        "failure_cases": [],
        "limitations": ["Development-host result only; no demo-hardware acceptance claim.", "source_read_to_display_submit_ms is software submission, not visible-light latency.", "sensor_to_photon_ms is NOT_MEASURED without external apparatus."],
        "responsible_ai": {"runtime_local_offline": True, "frames_saved_by_default": False, "frames_uploaded_by_default": False, "medical_diagnosis_claim": False, "user_selected_profile": True, "privacy_summary": "No frame is saved or uploaded by the benchmark runner.", "bias_coverage_summary": "Performance is one host/source observation, not demographic validation.", "environmental_summary": "Reuses a pretrained CPU backend and reports RSS as a proxy; energy is not measured.", "license_summary": "Runtime component licenses remain subject to the repository attribution audit.", "user_validation_status": "NOT_MEASURED"},
        "notes": "Raw per-case result; the tracked coordinator report performs cross-case consolidation.",
    }
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    output = OUTPUT_DIR / f"{payload['result_id']}.json"
    write_json_lf(output, payload)
    print(f"Wrote ignored raw result {output.relative_to(ROOT)}")
    return 0 if official else 2


if __name__ == "__main__":
    raise SystemExit(main())

