"""Validate four official T09 benchmark JSON files and atomically write a report.

Only aggregate JSON metadata and the checksum of the generated comparison video
are read.  This script never copies, rewrites, or stores source frames/video.
"""

from __future__ import annotations

import argparse
from dataclasses import dataclass
import hashlib
import json
from math import isfinite
import os
from pathlib import Path
import re
from typing import Any, Sequence


PROTOCOL_VERSION = "1.0.0"
ARTIFACT_DIR = Path("artifacts/t09/performance_responsible_ai")
VIDEO_PATH = ARTIFACT_DIR / "inputs/generated-360x240.avi"
REPORT_PATH = Path("evaluation/results/curated/performance_responsible_ai/report.md")
CURATED_NAMESPACE = REPORT_PATH.parent
GIT_SHA_PATTERN = re.compile(r"[0-9a-f]{40}\Z")


@dataclass(frozen=True, slots=True)
class CaseExpectation:
    case_id: str
    fixture_id: str
    resolution: tuple[int, int]
    display_mode: str
    source_kind: str


CASE_ORDER = (
    "PERF-WEBCAM-GUI-120",
    "PERF-WEBCAM-HEADLESS-120",
    "PERF-VIDEO-GUI-120",
    "PERF-VIDEO-HEADLESS-120",
)
CASE_EXPECTATIONS = {
    "PERF-WEBCAM-GUI-120": CaseExpectation(
        "PERF-WEBCAM-GUI-120", "webcam-gui-640x480", (640, 480), "gui", "webcam"
    ),
    "PERF-WEBCAM-HEADLESS-120": CaseExpectation(
        "PERF-WEBCAM-HEADLESS-120", "webcam-headless-640x480", (640, 480), "headless", "webcam"
    ),
    "PERF-VIDEO-GUI-120": CaseExpectation(
        "PERF-VIDEO-GUI-120", "generated-video-gui-360x240", (360, 240), "gui", "video"
    ),
    "PERF-VIDEO-HEADLESS-120": CaseExpectation(
        "PERF-VIDEO-HEADLESS-120", "generated-video-headless-360x240", (360, 240), "headless", "video"
    ),
}

REQUIRED_METRICS = (
    ("processed_fps", "single"),
    ("source_read_to_render_ms", "p50"),
    ("source_read_to_render_ms", "p95"),
    ("source_read_to_render_slope_ms_per_minute", "whole_session"),
    ("source_read_to_display_submit_ms", "p50"),
    ("source_read_to_display_submit_ms", "p95"),
    ("sensor_to_photon_ms", "p50"),
    ("sensor_to_photon_ms", "p95"),
    ("frame_processing_to_render_ms", "p50"),
    ("frame_processing_to_render_ms", "p95"),
    ("processed_frame_count", "count"),
    ("degraded_frame_rate", "single"),
    ("rss_mib", "start"),
    ("rss_mib", "end"),
    ("rss_mib", "peak"),
    ("rss_delta_mib", "whole_session"),
    ("rss_slope_mib_per_minute", "whole_session"),
    ("latency_continuous_growth_flag", "single"),
    ("rss_continuous_growth_flag", "single"),
    ("retained_source_read_to_render_sample_count", "count"),
    ("retained_source_read_to_display_submit_sample_count", "count"),
)

WEBCAM_ONLY_METRICS = (("dropped_capture_frame_count", "count"),)
METRIC_UNITS = {
    "processed_fps": "frames/s",
    "source_read_to_render_ms": "ms",
    "source_read_to_render_slope_ms_per_minute": "ms/min",
    "source_read_to_display_submit_ms": "ms",
    "sensor_to_photon_ms": "ms",
    "frame_processing_to_render_ms": "ms",
    "processed_frame_count": "frame",
    "dropped_capture_frame_count": "frame",
    "degraded_frame_rate": "ratio",
    "rss_mib": "MiB",
    "rss_delta_mib": "MiB",
    "rss_slope_mib_per_minute": "MiB/min",
    "latency_continuous_growth_flag": "boolean",
    "rss_continuous_growth_flag": "boolean",
    "retained_source_read_to_render_sample_count": "count",
    "retained_source_read_to_display_submit_sample_count": "count",
}
COUNT_METRICS = {
    "processed_frame_count",
    "dropped_capture_frame_count",
    "retained_source_read_to_render_sample_count",
    "retained_source_read_to_display_submit_sample_count",
}
NON_NEGATIVE_METRICS = {
    "processed_fps",
    "source_read_to_render_ms",
    "source_read_to_display_submit_ms",
    "frame_processing_to_render_ms",
    "rss_mib",
    *COUNT_METRICS,
}
GROWTH_FLAGS = {"latency_continuous_growth_flag", "rss_continuous_growth_flag"}
DEMO_THRESHOLD_IDS = {
    "demo_floor", "project_target", "demo_floor_p50", "project_target_p50"
}
COMMON_ENVIRONMENT_FIELDS = (
    "manufacturer", "model", "operating_system", "cpu", "physical_core_count",
    "logical_processor_count", "ram_gib", "gpu", "npu", "python_version",
    "package_versions", "lock_sha256", "backend_name", "backend_device",
    "host_role", "declared_demo_hardware",
)


class EvidenceValidationError(RuntimeError):
    """Raised when an official performance evidence contract is not met."""


@dataclass(frozen=True, slots=True)
class ValidatedArtifact:
    path: Path
    payload: dict[str, Any]
    metrics: dict[tuple[str, str], dict[str, Any]]
    sha256: str
    byte_size: int

    @property
    def case_id(self) -> str:
        return self.payload["cases"][0]["case_id"]


@dataclass(frozen=True, slots=True)
class PerformanceEvidence:
    artifacts: tuple[ValidatedArtifact, ...]
    video_path: Path
    video_sha256: str
    video_byte_size: int


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--artifact-dir", type=Path, default=ARTIFACT_DIR)
    parser.add_argument("--video-path", type=Path, default=VIDEO_PATH)
    parser.add_argument("--output", type=Path, default=REPORT_PATH)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        _validate_cli_output(args.output)
    except EvidenceValidationError as exc:
        parser.error(str(exc))
    evidence = load_and_validate(args.artifact_dir, args.video_path)
    write_report_atomic(evidence, args.output)
    print(f"T09 performance report written: {args.output}")
    return 0


def load_and_validate(
    artifact_dir: Path = ARTIFACT_DIR,
    video_path: Path = VIDEO_PATH,
) -> PerformanceEvidence:
    """Load exactly four approved case artifacts and fail before any report write."""

    paths = sorted(artifact_dir.glob("t09-performance-*.json"))
    if len(paths) != len(CASE_ORDER):
        raise EvidenceValidationError(
            f"expected exactly {len(CASE_ORDER)} benchmark JSON artifacts, found {len(paths)}"
        )
    artifacts = tuple(_load_artifact(path) for path in paths)
    case_ids = [artifact.case_id for artifact in artifacts]
    if len(case_ids) != len(set(case_ids)):
        raise EvidenceValidationError(f"duplicate benchmark case IDs: {case_ids}")
    if set(case_ids) != set(CASE_ORDER):
        raise EvidenceValidationError(
            f"case set must be exactly {CASE_ORDER}; found {tuple(sorted(case_ids))}"
        )
    commits = {artifact.payload["git_commit"] for artifact in artifacts}
    if len(commits) != 1:
        raise EvidenceValidationError("four benchmark artifacts have mixed Git SHA values")
    _validate_common_environment(artifacts)
    if not video_path.is_file():
        raise EvidenceValidationError(f"generated comparison video is missing: {video_path}")
    ordered = tuple(
        next(artifact for artifact in artifacts if artifact.case_id == case_id)
        for case_id in CASE_ORDER
    )
    return PerformanceEvidence(
        artifacts=ordered,
        video_path=video_path,
        video_sha256=sha256_file(video_path),
        video_byte_size=video_path.stat().st_size,
    )


def _load_artifact(path: Path) -> ValidatedArtifact:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise EvidenceValidationError(f"cannot read benchmark artifact {path}: {exc}") from exc
    if not isinstance(payload, dict):
        raise EvidenceValidationError(f"benchmark artifact {path} must be a JSON object")
    _validate_payload(path, payload)
    case_id = payload["cases"][0]["case_id"]
    metrics = _index_metrics(path, payload["metrics"], case_id)
    _validate_metric_semantics(
        path, payload["environment"]["display_mode"], case_id, metrics
    )
    return ValidatedArtifact(
        path=path,
        payload=payload,
        metrics=metrics,
        sha256=sha256_file(path),
        byte_size=path.stat().st_size,
    )


def _validate_payload(path: Path, payload: dict[str, Any]) -> None:
    for version_key in ("protocol_version", "schema_version", "metric_registry_version"):
        if payload.get(version_key) != PROTOCOL_VERSION:
            raise EvidenceValidationError(
                f"{path}: {version_key} must be {PROTOCOL_VERSION!r}"
            )
    if payload.get("result_status") != "COMPLETE":
        raise EvidenceValidationError(f"{path}: result_status must be COMPLETE")
    commit = payload.get("git_commit")
    if not isinstance(commit, str) or GIT_SHA_PATTERN.fullmatch(commit) is None:
        raise EvidenceValidationError(f"{path}: git_commit must be 40 lowercase hex characters")
    if payload.get("workstream") != "performance_responsible_ai":
        raise EvidenceValidationError(f"{path}: workstream must be performance_responsible_ai")
    cases = payload.get("cases")
    if not isinstance(cases, list) or len(cases) != 1 or not isinstance(cases[0], dict):
        raise EvidenceValidationError(f"{path}: exactly one case record is required")
    case = cases[0]
    case_id = case.get("case_id")
    expectation = CASE_EXPECTATIONS.get(case_id)
    if expectation is None:
        raise EvidenceValidationError(f"{path}: unexpected case_id {case_id!r}")
    if case.get("fixture_id") != expectation.fixture_id:
        raise EvidenceValidationError(f"{path}: fixture_id does not match {case_id}")
    if case.get("status") != "COMPLETE":
        raise EvidenceValidationError(f"{path}: case status must be COMPLETE")
    environment = payload.get("environment")
    if not isinstance(environment, dict):
        raise EvidenceValidationError(f"{path}: environment object is required")
    configuration = payload.get("configuration")
    if not isinstance(configuration, dict):
        raise EvidenceValidationError(f"{path}: configuration object is required")
    if configuration.get("cvd_profile") != "deutan":
        raise EvidenceValidationError(f"{path}: configuration.cvd_profile must be deutan")
    if configuration.get("severity") != 0.8:
        raise EvidenceValidationError(f"{path}: configuration.severity must be 0.8")
    _validate_environment_fields(path, environment)
    if environment.get("source_kind") != expectation.source_kind:
        raise EvidenceValidationError(f"{path}: source_kind does not match {case_id}")
    if environment.get("display_mode") != expectation.display_mode:
        raise EvidenceValidationError(f"{path}: display_mode does not match {case_id}")
    for resolution_key in ("source_resolution", "render_resolution"):
        if _resolution(environment.get(resolution_key)) != expectation.resolution:
            raise EvidenceValidationError(
                f"{path}: {resolution_key} does not match frozen {expectation.resolution}"
            )
    if environment.get("warmup_seconds") != 15.0:
        raise EvidenceValidationError(f"{path}: warmup_seconds must be 15")
    if environment.get("measurement_seconds") != 120.0:
        raise EvidenceValidationError(f"{path}: measurement_seconds must be 120")
    if environment.get("host_role") != "development" or environment.get("declared_demo_hardware") is not False:
        raise EvidenceValidationError(
            f"{path}: this consolidated report is limited to development-host observations"
        )
    if not isinstance(payload.get("metrics"), list):
        raise EvidenceValidationError(f"{path}: metrics array is required")


def _index_metrics(
    path: Path, records: list[Any], case_id: str
) -> dict[tuple[str, str], dict[str, Any]]:
    indexed: dict[tuple[str, str], dict[str, Any]] = {}
    for record in records:
        if not isinstance(record, dict):
            raise EvidenceValidationError(f"{path}: metric record must be an object")
        key = (record.get("name"), record.get("aggregation"))
        if key in indexed:
            raise EvidenceValidationError(f"{path}: duplicate metric {key}")
        indexed[key] = record
    for key in REQUIRED_METRICS:
        if key not in indexed:
            raise EvidenceValidationError(f"{path}: missing required metric {key}")
    if CASE_EXPECTATIONS[case_id].source_kind == "webcam":
        for key in WEBCAM_ONLY_METRICS:
            if key not in indexed:
                raise EvidenceValidationError(f"{path}: missing required metric {key}")
    required = set(REQUIRED_METRICS)
    if CASE_EXPECTATIONS[case_id].source_kind == "webcam":
        required.update(WEBCAM_ONLY_METRICS)
    for key in required:
        _validate_metric_record(path, case_id, indexed[key])
    return indexed


def _validate_metric_semantics(
    path: Path,
    display_mode: str,
    case_id: str,
    metrics: dict[tuple[str, str], dict[str, Any]],
) -> None:
    for aggregation in ("p50", "p95"):
        sensor = metrics[("sensor_to_photon_ms", aggregation)]
        if sensor.get("status") != "NOT_MEASURED" or sensor.get("value") is not None:
            raise EvidenceValidationError(
                f"{path}: sensor_to_photon_ms must remain NOT_MEASURED/null"
            )
        display = metrics[("source_read_to_display_submit_ms", aggregation)]
        if display_mode == "headless" and (
            display.get("status") != "NOT_MEASURED" or display.get("value") is not None
        ):
            raise EvidenceValidationError(
                f"{path}: headless display-submit metric must remain NOT_MEASURED/null"
            )
        if display_mode == "gui" and display.get("status") != "MEASURED":
            raise EvidenceValidationError(
                f"{path}: GUI display-submit metric must be MEASURED"
            )
    frame_count = _metric_number(metrics[("processed_frame_count", "count")])
    if metrics[("retained_source_read_to_render_sample_count", "count")].get("value") != frame_count:
        raise EvidenceValidationError(f"{path}: retained render samples must equal processed frame count")
    expected_display_samples = 0 if display_mode == "headless" else frame_count
    if metrics[("retained_source_read_to_display_submit_sample_count", "count")].get("value") != expected_display_samples:
        raise EvidenceValidationError(f"{path}: retained display samples do not match display mode")
    for name in GROWTH_FLAGS:
        record = metrics[(name, "single")]
        expected = "PASS" if record["value"] is False else "FAIL"
        if record.get("threshold_result") != expected:
            raise EvidenceValidationError(f"{path}: {name} threshold_result must be {expected}")
    for record in metrics.values():
        if record.get("threshold_id") in DEMO_THRESHOLD_IDS and record.get("threshold_result") != "NOT_EVALUATED":
            raise EvidenceValidationError(
                f"{path}: development-host demo threshold must be NOT_EVALUATED"
            )


def _validate_metric_record(
    path: Path, case_id: str, record: dict[str, Any]
) -> None:
    name = record.get("name")
    if record.get("unit") != METRIC_UNITS[name]:
        raise EvidenceValidationError(f"{path}: {name} has an invalid unit")
    if record.get("case_ids") != [case_id]:
        raise EvidenceValidationError(f"{path}: {name} case_ids must be [{case_id!r}]")
    status = record.get("status")
    value = record.get("value")
    if status not in {"MEASURED", "NOT_MEASURED"}:
        raise EvidenceValidationError(f"{path}: {name} has invalid status {status!r}")
    threshold_result = record.get("threshold_result")
    if threshold_result not in {"PASS", "FAIL", "NOT_APPLICABLE", "NOT_EVALUATED"}:
        raise EvidenceValidationError(f"{path}: {name} has invalid threshold_result")
    if status == "NOT_MEASURED":
        if value is not None:
            raise EvidenceValidationError(f"{path}: {name} NOT_MEASURED value must be null")
        if name not in {"sensor_to_photon_ms", "source_read_to_display_submit_ms"}:
            raise EvidenceValidationError(f"{path}: {name} must be MEASURED")
        return
    if name in GROWTH_FLAGS:
        if type(value) is not bool:
            raise EvidenceValidationError(f"{path}: {name} must be boolean")
        return
    if name in COUNT_METRICS:
        if type(value) is not int or value < 0:
            raise EvidenceValidationError(f"{path}: {name} must be a non-negative integer")
        if name == "processed_frame_count" and value <= 0:
            raise EvidenceValidationError(f"{path}: processed_frame_count must be positive")
        return
    if not _is_finite_number(value):
        raise EvidenceValidationError(f"{path}: {name} must be a finite numeric value")
    if name in NON_NEGATIVE_METRICS and value < 0:
        raise EvidenceValidationError(f"{path}: {name} must be non-negative")
    if name == "degraded_frame_rate" and not 0.0 <= value <= 1.0:
        raise EvidenceValidationError(f"{path}: degraded_frame_rate must be within [0, 1]")


def _metric_number(record: dict[str, Any]) -> int:
    value = record.get("value")
    if type(value) is not int:
        raise EvidenceValidationError("processed_frame_count must be an integer")
    return value


def _is_finite_number(value: object) -> bool:
    return (
        isinstance(value, (int, float))
        and not isinstance(value, bool)
        and isfinite(float(value))
    )


def _validate_environment_fields(path: Path, environment: dict[str, Any]) -> None:
    required = (*COMMON_ENVIRONMENT_FIELDS, "source_kind")
    missing = [name for name in required if name not in environment]
    if missing:
        raise EvidenceValidationError(f"{path}: missing environment fields {missing}")
    for name in ("manufacturer", "model", "operating_system", "cpu", "gpu", "npu", "python_version", "backend_name", "backend_device"):
        if not isinstance(environment[name], str) or not environment[name]:
            raise EvidenceValidationError(f"{path}: environment.{name} must be a non-empty string")
    for name in ("physical_core_count", "logical_processor_count"):
        if type(environment[name]) is not int or environment[name] <= 0:
            raise EvidenceValidationError(f"{path}: environment.{name} must be positive integer")
    if not _is_finite_number(environment["ram_gib"]) or environment["ram_gib"] <= 0:
        raise EvidenceValidationError(f"{path}: environment.ram_gib must be positive finite number")
    if not isinstance(environment["package_versions"], dict) or not environment["package_versions"]:
        raise EvidenceValidationError(f"{path}: environment.package_versions must be non-empty object")
    if not isinstance(environment["lock_sha256"], str) or re.fullmatch(r"[0-9a-f]{64}", environment["lock_sha256"]) is None:
        raise EvidenceValidationError(f"{path}: environment.lock_sha256 must be lowercase SHA-256")


def _validate_common_environment(artifacts: tuple[ValidatedArtifact, ...]) -> None:
    reference = artifacts[0].payload["environment"]
    for artifact in artifacts[1:]:
        environment = artifact.payload["environment"]
        for field in COMMON_ENVIRONMENT_FIELDS:
            if environment[field] != reference[field]:
                raise EvidenceValidationError(
                    f"four benchmark artifacts disagree on environment.{field}"
                )


def _validate_cli_output(output_path: Path) -> None:
    namespace = (Path.cwd() / CURATED_NAMESPACE).resolve()
    candidate = (Path.cwd() / output_path).resolve()
    try:
        candidate.relative_to(namespace)
    except ValueError as exc:
        raise EvidenceValidationError(
            "--output must remain under evaluation/results/curated/performance_responsible_ai/"
        ) from exc


def _resolution(value: object) -> tuple[int, int] | None:
    if not isinstance(value, dict):
        return None
    width, height = value.get("width"), value.get("height")
    if not isinstance(width, int) or not isinstance(height, int):
        return None
    return width, height


def write_report_atomic(evidence: PerformanceEvidence, output_path: Path = REPORT_PATH) -> None:
    """Replace the curated report only after fully validated text is prepared."""
    content = render_report(evidence)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    temporary = output_path.with_name(f".{output_path.name}.{os.getpid()}.tmp")
    try:
        with temporary.open("x", encoding="utf-8", newline="\n") as handle:
            handle.write(content)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, output_path)
    finally:
        if temporary.exists():
            temporary.unlink()


def render_report(evidence: PerformanceEvidence) -> str:
    common_environment = evidence.artifacts[0].payload["environment"]
    commit = evidence.artifacts[0].payload["git_commit"]
    lines = [
        "# T09 Performance Evidence",
        "",
        "Status: `COMPLETE` for the four frozen performance cases. Responsible-AI evidence remains `PENDING` for the next Trinh work item.",
        "",
        "These are development-host observations (`host_role=development`, `declared_demo_hardware=false`). No demo-floor or project-target PASS claim is made here.",
        "",
        "## Provenance and environment",
        "",
        f"- Git commit: `{commit}`",
        "- The following environment fields were validated identical across all four artifacts.",
        f"- Hardware: {common_environment['manufacturer']} {common_environment['model']}; CPU {common_environment['cpu']}; {common_environment['physical_core_count']} physical / {common_environment['logical_processor_count']} logical cores; RAM {common_environment['ram_gib']} GiB; GPU {common_environment['gpu']}; NPU {common_environment['npu']}.",
        f"- Operating system: {common_environment['operating_system']}",
        f"- Python: {common_environment['python_version']}",
        f"- Backend/device: {common_environment['backend_name']} / {common_environment['backend_device']}",
        f"- Lock SHA-256: `{common_environment['lock_sha256']}`",
        f"- Package versions: {_package_versions_text(common_environment['package_versions'])}",
        "",
        "## Run records",
        "",
        "| Case | Created UTC | Source | Resolution | Mode | Warm-up / measurement | Result |",
        "| --- | --- | --- | --- | --- | --- | --- |",
    ]
    for artifact in evidence.artifacts:
        payload, environment = artifact.payload, artifact.payload["environment"]
        lines.append(
            "| " + " | ".join((
                artifact.case_id,
                payload["created_at_utc"],
                environment["camera_or_source"],
                _resolution_text(environment["source_resolution"]),
                environment["display_mode"],
                f"{environment['warmup_seconds']} s / {environment['measurement_seconds']} s",
                payload["result_status"],
            )) + " |"
        )
    lines.extend((
        "",
        "## Throughput and latency",
        "",
        "`source_read_to_render_ms` ends after rendering. `source_read_to_display_submit_ms` ends after `cv2.imshow()` returns and is not sensor-to-photon latency. `NOT_MEASURED` is retained exactly where no measurement exists. Demo-threshold evaluation is `NOT_EVALUATED` for every case because this is development hardware; it is never interpreted as PASS.",
        "",
        "| Case | FPS | Render p50 / p95 (ms) | Render slope (ms/min) | Display-submit p50 / p95 (ms) | Sensor-to-photon p50 / p95 (ms) | Processing p50 / p95 (ms) | Frames | Dropped capture frames | Degraded rate | Retained render / display samples |",
        "| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- | ---: | ---: |",
    ))
    for artifact in evidence.artifacts:
        metric = artifact.metrics
        lines.append("| " + " | ".join((
            artifact.case_id,
            _value(metric, "processed_fps", "single"),
            _pair(metric, "source_read_to_render_ms"),
            _value(metric, "source_read_to_render_slope_ms_per_minute", "whole_session"),
            _pair(metric, "source_read_to_display_submit_ms"),
            _pair(metric, "sensor_to_photon_ms"),
            _pair(metric, "frame_processing_to_render_ms"),
            _value(metric, "processed_frame_count", "count"),
            _dropped_capture_frames(artifact),
            _value(metric, "degraded_frame_rate", "single"),
            _value(metric, "retained_source_read_to_render_sample_count", "count") + " / " + _value(metric, "retained_source_read_to_display_submit_sample_count", "count"),
        )) + " |")
    lines.extend((
        "",
        "## RSS and growth diagnostics",
        "",
        "A `true [FAIL]` RSS growth flag is reported as a diagnostic failure, not suppressed or reinterpreted as success. High degraded-frame rates remain observations of the measured pipeline state.",
        "",
        "| Case | RSS start / end / peak (MiB) | RSS delta (MiB) | RSS slope (MiB/min) | Render-latency growth flag | RSS growth flag |",
        "| --- | ---: | ---: | ---: | --- | --- |",
    ))
    for artifact in evidence.artifacts:
        metric = artifact.metrics
        lines.append("| " + " | ".join((
            artifact.case_id,
            " / ".join(_value(metric, "rss_mib", aggregation) for aggregation in ("start", "end", "peak")),
            _value(metric, "rss_delta_mib", "whole_session"),
            _value(metric, "rss_slope_mib_per_minute", "whole_session"),
            _flag(metric, "latency_continuous_growth_flag"),
            _flag(metric, "rss_continuous_growth_flag"),
        )) + " |")
    lines.extend((
        "",
        "## Ignored-artifact manifest",
        "",
        "The following raw benchmark JSON and generated video remain under ignored `artifacts/t09/`; this report records only their byte sizes and SHA-256 digests. They are not added to Git.",
        "",
        "| Artifact | Related case | Bytes | SHA-256 | Tracked in Git |",
        "| --- | --- | ---: | --- | --- |",
    ))
    for artifact in evidence.artifacts:
        lines.append(
            f"| `{artifact.path.as_posix()}` | {artifact.case_id} | {artifact.byte_size} | `{artifact.sha256}` | false |"
        )
    lines.append(
        f"| `{evidence.video_path.as_posix()}` | PERF-VIDEO-GUI-120; PERF-VIDEO-HEADLESS-120 | {evidence.video_byte_size} | `{evidence.video_sha256}` | false |"
    )
    lines.extend((
        "",
        "## Scope boundary",
        "",
        "This step consolidates measured performance and hardware evidence only. Responsible-AI evidence, including the full privacy, bias, limitations, license, and user-validation package, is `PENDING` for the next work item.",
        "",
    ))
    return "\n".join(lines)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _value(metrics: dict[tuple[str, str], dict[str, Any]], name: str, aggregation: str) -> str:
    record = metrics[(name, aggregation)]
    if record.get("status") == "NOT_MEASURED":
        return "NOT_MEASURED"
    value = record.get("value")
    if isinstance(value, bool):
        return str(value).lower()
    return repr(value)


def _pair(metrics: dict[tuple[str, str], dict[str, Any]], name: str) -> str:
    return _value(metrics, name, "p50") + " / " + _value(metrics, name, "p95")


def _flag(metrics: dict[tuple[str, str], dict[str, Any]], name: str) -> str:
    record = metrics[(name, "single")]
    return _value(metrics, name, "single") + f" [{record.get('threshold_result')}]"


def _dropped_capture_frames(artifact: ValidatedArtifact) -> str:
    if artifact.payload["environment"]["source_kind"] == "video":
        return "NOT_APPLICABLE"
    return _value(artifact.metrics, "dropped_capture_frame_count", "count")


def _resolution_text(value: object) -> str:
    resolution = _resolution(value)
    return "unavailable" if resolution is None else f"{resolution[0]}x{resolution[1]}"


def _package_versions_text(value: object) -> str:
    if not isinstance(value, dict):
        return "unavailable"
    return "; ".join(f"{name} {version}" for name, version in sorted(value.items()))


if __name__ == "__main__":
    raise SystemExit(main())
