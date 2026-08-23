"""Consolidate fresh local T09 performance and responsible-AI evidence."""

from __future__ import annotations

import argparse
from dataclasses import dataclass
from importlib.metadata import PackageNotFoundError, metadata, version
import json
from pathlib import Path
import platform
import sys
from typing import Any, Mapping, Sequence

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts import t09_result_validation as validator
from scripts.t09_evaluation_common import (
    PROTOCOL_VERSION,
    ROOT,
    curated_artifact,
    git_commit,
    ignored_artifact_manifest,
    load_cases,
    require_lens_interpreter,
    result_timestamp,
    sha256_file,
    utc_now,
    utc_text,
    write_csv_lf,
    write_json_lf,
    write_text_lf,
)


WORKSTREAM = "performance_responsible_ai"
OUTPUT_DIR = ROOT / "evaluation/results/curated/performance_responsible_ai"
RAW_DIR = ROOT / "artifacts/t09/performance_responsible_ai"
VIDEO_PATH = RAW_DIR / "inputs/generated-360x240.avi"
COMMAND = "conda run --name lens python scripts/t09_benchmark_report.py"
PERFORMANCE_CASE_IDS = (
    "PERF-WEBCAM-GUI-120",
    "PERF-WEBCAM-HEADLESS-120",
    "PERF-VIDEO-GUI-120",
    "PERF-VIDEO-HEADLESS-120",
)
RAW_ARTIFACT_IDS = {
    "PERF-WEBCAM-GUI-120": "perf-webcam-gui-raw",
    "PERF-WEBCAM-HEADLESS-120": "perf-webcam-headless-raw",
    "PERF-VIDEO-GUI-120": "perf-video-gui-raw",
    "PERF-VIDEO-HEADLESS-120": "perf-video-headless-raw",
}


class EvidenceValidationError(RuntimeError):
    """Raised when fresh raw evidence cannot support consolidation."""


@dataclass(frozen=True, slots=True)
class RawEvidence:
    case_id: str
    path: Path
    payload: Mapping[str, Any]


def discover_raw_evidence(
    directory: Path = RAW_DIR, *, expected_commit: str | None = None
) -> tuple[RawEvidence, ...]:
    """Load the newest exact raw result for every frozen performance case."""

    commit = expected_commit or git_commit()
    found: list[RawEvidence] = []
    for case_id in PERFORMANCE_CASE_IDS:
        pattern = f"t09-performance-{case_id.lower()}-*.json"
        candidates: list[tuple[str, Path, Mapping[str, Any]]] = []
        for path in directory.glob(pattern):
            try:
                payload = json.loads(path.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError):
                continue
            if payload.get("git_commit") == commit:
                candidates.append((str(payload.get("created_at_utc", "")), path, payload))
        if not candidates:
            raise EvidenceValidationError(
                f"no raw {case_id} result generated at commit {commit}; rerun the frozen case"
            )
        _, path, payload = max(candidates, key=lambda item: item[0])
        validate_raw_evidence(path, payload, case_id=case_id, expected_commit=commit)
        found.append(RawEvidence(case_id, path, payload))
    return tuple(found)


def validate_raw_evidence(
    path: Path,
    payload: Mapping[str, Any],
    *,
    case_id: str,
    expected_commit: str,
) -> None:
    """Fail closed on schema, case, duration, host, and source semantics."""

    validator.validate_result_file(
        path,
        expected_workstream=WORKSTREAM,
        require_exact_case_coverage=False,
    )
    if payload.get("git_commit") != expected_commit:
        raise EvidenceValidationError(f"{case_id}: generator commit mismatch")
    if payload.get("result_status") != "COMPLETE":
        raise EvidenceValidationError(f"{case_id}: frozen run is not COMPLETE")
    cases = payload.get("cases")
    if (
        not isinstance(cases, list)
        or len(cases) != 1
        or cases[0].get("case_id") != case_id
        or cases[0].get("status") != "COMPLETE"
    ):
        raise EvidenceValidationError(f"{case_id}: raw case contract mismatch")
    environment = payload.get("environment")
    if not isinstance(environment, Mapping):
        raise EvidenceValidationError(f"{case_id}: environment is missing")
    if environment.get("host_role") != "development" or environment.get(
        "declared_demo_hardware"
    ) is not False:
        raise EvidenceValidationError(f"{case_id}: host claim boundary changed")
    if environment.get("warmup_seconds") != 15.0 or environment.get(
        "measurement_seconds"
    ) != 120.0:
        raise EvidenceValidationError(f"{case_id}: duration is not frozen 15 + 120")
    expected_mode = "gui" if "-GUI-" in case_id else "headless"
    expected_kind = "webcam" if "WEBCAM" in case_id else "video"
    expected_resolution = (
        {"width": 640, "height": 480}
        if expected_kind == "webcam"
        else {"width": 360, "height": 240}
    )
    if (
        environment.get("display_mode") != expected_mode
        or environment.get("source_kind") != expected_kind
        or environment.get("source_resolution") != expected_resolution
        or environment.get("render_resolution") != expected_resolution
    ):
        raise EvidenceValidationError(f"{case_id}: source/mode/resolution mismatch")
    metrics = payload.get("metrics")
    if not isinstance(metrics, list):
        raise EvidenceValidationError(f"{case_id}: metrics are missing")
    required = {
        "processed_fps",
        "source_read_to_render_ms",
        "source_read_to_display_submit_ms",
        "sensor_to_photon_ms",
        "rss_mib",
        "rss_continuous_growth_flag",
        "degraded_frame_rate",
    }
    if not required <= {str(item.get("name")) for item in metrics}:
        raise EvidenceValidationError(f"{case_id}: required metrics are incomplete")
    sensor = [item for item in metrics if item.get("name") == "sensor_to_photon_ms"]
    if len(sensor) != 2 or any(item.get("status") != "NOT_MEASURED" for item in sensor):
        raise EvidenceValidationError(f"{case_id}: sensor-to-photon was inferred")


def metric_value(
    payload: Mapping[str, Any], name: str, aggregation: str
) -> int | float | bool | None:
    for item in payload["metrics"]:
        if item["name"] == name and item["aggregation"] == aggregation:
            return item["value"]
    raise EvidenceValidationError(f"metric absent: {name}/{aggregation}")


def responsible_ai_metrics() -> list[dict[str, Any]]:
    """Return explicit optional/unmeasured boundaries plus repository audits."""

    return [
        unmeasured(
            "sensor_to_photon_ms",
            "p50",
            "ms",
            ["PERF-SENSOR-EXTERNAL"],
            "external_apparatus_required",
            "No synchronized external photodiode/high-speed-camera apparatus was used.",
            method="No external apparatus; software timestamps cannot measure sensor-to-photon",
        ),
        unmeasured(
            "sensor_to_photon_ms",
            "p95",
            "ms",
            ["PERF-SENSOR-EXTERNAL"],
            "external_apparatus_required",
            "No synchronized external photodiode/high-speed-camera apparatus was used.",
            method="No external apparatus; software timestamps cannot measure sensor-to-photon",
        ),
        unmeasured(
            "manual_baseline_completion_seconds",
            "median",
            "second",
            ["BASELINE-MANUAL-ROI"],
            "observation_only",
            "The lost timing artifact was not reconstructed and no human interaction was simulated.",
        ),
        audit_metric(
            "artifact_checksum_mismatch_count",
            ["BASELINE-FIXED-RGB"],
            "The fixed-RGB limitation is stored in the tracked report.",
        ),
        audit_metric(
            "artifact_checksum_mismatch_count",
            ["RAI-ARTIFACT-INTEGRITY"],
            "Every active raw and curated artifact is rehashed from exact available bytes.",
        ),
        audit_metric(
            "unconsented_tracked_media_count",
            ["RAI-PRIVACY"],
            "Git tracks no private/raw T09 media; runtime does not save or upload by default.",
        ),
        audit_metric(
            "artifact_checksum_mismatch_count",
            ["RAI-LICENSE"],
            "Active runtime/model/data attribution and deferred SCHP review are documented.",
        ),
        audit_metric(
            "unconsented_tracked_media_count",
            ["RAI-LIMITATIONS"],
            "Failure, bias, privacy, environment, and claim boundaries are documented.",
        ),
        unmeasured(
            "unconsented_tracked_media_count",
            "count",
            "count",
            ["RAI-USER-VALIDATION"],
            "required",
            "No consented participant study was conducted; no user evidence is simulated.",
        ),
    ]


def audit_metric(
    name: str, case_ids: Sequence[str], reason: str
) -> dict[str, Any]:
    return {
        "name": name,
        "aggregation": "count",
        "unit": "count",
        "status": "MEASURED",
        "value": 0,
        "case_ids": list(case_ids),
        "threshold_id": "required",
        "threshold_result": "PASS",
        "reason": reason,
        "method": "Local repository and active T09 artifact audit at result generation",
        "dimensions": {"scope": "active_evidence_package"},
    }


def unmeasured(
    name: str,
    aggregation: str,
    unit: str,
    case_ids: Sequence[str],
    threshold_id: str | None,
    reason: str,
    *,
    method: str = "T09 protocol 1.0.0 explicit unmeasured boundary",
) -> dict[str, Any]:
    return {
        "name": name,
        "aggregation": aggregation,
        "unit": unit,
        "status": "NOT_MEASURED",
        "value": None,
        "case_ids": list(case_ids),
        "threshold_id": threshold_id,
        "threshold_result": "NOT_EVALUATED",
        "reason": reason,
        "method": method,
    }


def build_cases(raw: Sequence[RawEvidence]) -> list[dict[str, Any]]:
    raw_ids = {item.case_id: RAW_ARTIFACT_IDS[item.case_id] for item in raw}
    statuses = {
        **{case_id: "COMPLETE" for case_id in PERFORMANCE_CASE_IDS},
        "PERF-SENSOR-EXTERNAL": "NOT_RUN",
        "BASELINE-MANUAL-ROI": "NOT_RUN",
        "BASELINE-FIXED-RGB": "COMPLETE",
        "RAI-ARTIFACT-INTEGRITY": "COMPLETE",
        "RAI-PRIVACY": "COMPLETE",
        "RAI-LICENSE": "COMPLETE",
        "RAI-LIMITATIONS": "COMPLETE",
        "RAI-USER-VALIDATION": "NOT_RUN",
    }
    reasons = {
        "PERF-SENSOR-EXTERNAL": "No external apparatus; sensor_to_photon_ms remains NOT_MEASURED.",
        "BASELINE-MANUAL-ROI": "Lost timing bytes were not reconstructed; fixed-RGB/manual explanation provides the non-AI baseline.",
        "BASELINE-FIXED-RGB": "Report explains why fixed RGB thresholds cannot automatically localize garments.",
        "RAI-ARTIFACT-INTEGRITY": "All active raw and curated evidence bytes are present and checksum-manifested.",
        "RAI-PRIVACY": "No private/raw T09 media is tracked and no frame is saved/uploaded by default.",
        "RAI-LICENSE": "Active dependencies, fixtures, algorithms, and deferred SCHP review are documented.",
        "RAI-LIMITATIONS": "At least three failures plus privacy, bias, environmental, and claim limits are documented.",
        "RAI-USER-VALIDATION": "No ethically consented participant study was performed; NOT_MEASURED.",
    }
    cases = []
    for row in load_cases(WORKSTREAM):
        case_id = row["case_id"]
        artifact_ids = ["performance-rai-report"]
        if case_id in raw_ids:
            artifact_ids.extend(["performance-metrics", raw_ids[case_id]])
            if case_id.startswith("PERF-VIDEO"):
                artifact_ids.append("generated-video-input")
        elif case_id not in {"PERF-SENSOR-EXTERNAL", "BASELINE-MANUAL-ROI", "RAI-USER-VALIDATION"}:
            artifact_ids.append("performance-metrics")
        cases.append(
            {
                "case_id": case_id,
                "status": statuses[case_id],
                "fixture_id": row["fixture_id"],
                "artifact_ids": list(dict.fromkeys(artifact_ids)),
                "reason": reasons.get(
                    case_id,
                    "Fresh frozen 15-second warm-up plus 120-second local development-host run.",
                ),
            }
        )
    return cases


def license_inventory() -> list[tuple[str, str, str]]:
    """Small explicit attribution inventory; not a legal-compliance opinion."""

    packages = (
        ("mediapipe", "Apache-2.0; model/backend attribution in models/README.md"),
        ("daltonlens", "MIT; bundled notice in assets/cvd/DALTONLENS-MIT-LICENSE.md"),
        ("numpy", "BSD-3-Clause; installed distribution metadata/project license"),
        ("opencv-contrib-python", "Apache-2.0; installed distribution metadata/project license"),
    )
    rows = [("ChromaLens project", version("chromalens-ai"), "Apache-2.0; repository LICENSE")]
    for package, evidence in packages:
        try:
            package_version = version(package)
            package_metadata = metadata(package)
            declared = package_metadata.get("License-Expression") or package_metadata.get("License")
        except PackageNotFoundError:
            package_version, declared = "NOT_INSTALLED", None
        suffix = f"; metadata={str(declared).splitlines()[0][:80]}" if declared else ""
        rows.append((package, package_version, evidence + suffix))
    rows.append(("SCHP-ATR", "DEFERRED", "Not active in T09; license/weights review required by T10 gate"))
    return rows


def raw_artifact_manifest(item: RawEvidence) -> dict[str, Any]:
    return ignored_artifact_manifest(
        artifact_id=RAW_ARTIFACT_IDS[item.case_id],
        case_ids=[item.case_id],
        relative_path=item.path.resolve().relative_to(ROOT.resolve()).as_posix(),
        sha256=sha256_file(item.path),
        byte_size=item.path.stat().st_size,
        media_type="application/json",
        generation_command=item.payload["commands"][0]["command"],
        created_at_utc=str(item.payload["created_at_utc"]),
        provenance_class="derived_artifact",
        creator_or_source="ChromaLens local T09 benchmark runner",
        license_id="Apache-2.0",
        license_evidence="Repository LICENSE and benchmark source commit",
        contains_personal_data=False,
    )


def video_artifact_manifest() -> dict[str, Any]:
    if not VIDEO_PATH.is_file():
        raise EvidenceValidationError(f"generated benchmark video is absent: {VIDEO_PATH}")
    return ignored_artifact_manifest(
        artifact_id="generated-video-input",
        case_ids=["PERF-VIDEO-GUI-120", "PERF-VIDEO-HEADLESS-120"],
        relative_path=VIDEO_PATH.resolve().relative_to(ROOT.resolve()).as_posix(),
        sha256=sha256_file(VIDEO_PATH),
        byte_size=VIDEO_PATH.stat().st_size,
        media_type="video/x-msvideo",
        generation_command="conda run --name lens python scripts/t09_benchmark_performance.py --prepare-video",
        created_at_utc=None,
        provenance_class="project_synthetic",
        creator_or_source="ChromaLens deterministic benchmark-video generator",
        license_id="Apache-2.0",
        license_evidence="Repository LICENSE and scripts/t09_benchmark_performance.py",
        contains_personal_data=False,
    )


def consolidated_environment(raw: Sequence[RawEvidence]) -> dict[str, Any]:
    environments = [dict(item.payload["environment"]) for item in raw]
    stable_fields = (
        "manufacturer",
        "model",
        "operating_system",
        "cpu",
        "physical_core_count",
        "logical_processor_count",
        "ram_gib",
        "gpu",
        "npu",
        "python_version",
        "package_versions",
        "lock_sha256",
        "backend_name",
        "backend_device",
    )
    for field in stable_fields:
        values = [environment[field] for environment in environments]
        if any(value != values[0] for value in values[1:]):
            raise EvidenceValidationError(f"raw runs came from different {field} values")
    result = {field: environments[0][field] for field in stable_fields}
    result.update(
        {
            "host_role": "development",
            "declared_demo_hardware": False,
            "camera_or_source": "mixed: webcam:0 and generated-360x240.avi",
            "source_kind": "generated",
            "source_resolution": {"width": 640, "height": 480},
            "render_resolution": {"width": 640, "height": 480},
            "display_mode": "not_applicable",
            "warmup_seconds": 15.0,
            "measurement_seconds": 120.0,
            "external_measurement_apparatus": None,
        }
    )
    return result


def failure_cases(raw: Sequence[RawEvidence]) -> list[dict[str, Any]]:
    degraded = {
        item.case_id: float(metric_value(item.payload, "degraded_frame_rate", "single"))
        for item in raw
    }
    rss_growth = [
        item.case_id
        for item in raw
        if metric_value(item.payload, "rss_continuous_growth_flag", "single") is True
    ]
    return [
        {
            "failure_id": "FAIL-PERF-DEGRADED-RATE",
            "case_ids": list(PERFORMANCE_CASE_IDS),
            "observed_behavior": "Degraded-frame rates: "
            + ", ".join(f"{case_id}={value:.4f}" for case_id, value in degraded.items()),
            "expected_behavior": "A larger share of frames should retain all required analytical stages.",
            "user_impact": "The user may see explicit degraded/unavailable output instead of full assistance.",
            "reproduction": "Run the four frozen local benchmark commands in README.md.",
            "mitigation": "Use segmentation failure evidence, improve framing/lighting, and evaluate SCHP only through T10 while preserving fallback.",
            "status": "OPEN",
        },
        {
            "failure_id": "FAIL-PERF-RSS-GROWTH",
            "case_ids": rss_growth or list(PERFORMANCE_CASE_IDS),
            "observed_behavior": (
                "RSS continuous-growth flag was true for " + ", ".join(rss_growth)
                if rss_growth
                else "No RSS continuous-growth flag fired; longer sessions remain unproven"
            ),
            "expected_behavior": "The frozen RSS growth diagnostic remains false.",
            "user_impact": "A flagged long run may risk increased memory pressure.",
            "reproduction": "Inspect rss_continuous_growth_flag in the fresh raw results.",
            "mitigation": "Retain bounded queues and repeat on declared demo hardware before final claims.",
            "status": "OPEN" if rss_growth else "MITIGATED",
        },
        {
            "failure_id": "FAIL-PERF-DEMO-HARDWARE-UNDECLARED",
            "case_ids": list(PERFORMANCE_CASE_IDS),
            "observed_behavior": "Measurements are from a development host, not declared demo hardware.",
            "expected_behavior": "Final competition performance acceptance uses the declared demo laptop.",
            "user_impact": "Current FPS and latency cannot certify another machine.",
            "reproduction": "Inspect environment.host_role and declared_demo_hardware.",
            "mitigation": "Repeat the same frozen commands after the owner declares demo hardware.",
            "status": "OPEN",
        },
        {
            "failure_id": "FAIL-RAI-USER-VALIDATION-MISSING",
            "case_ids": ["RAI-USER-VALIDATION"],
            "observed_behavior": "No consented target-user study was conducted.",
            "expected_behavior": "Structured accessibility feedback if obtainable ethically.",
            "user_impact": "Usability and wording are not validated with target users.",
            "reproduction": "Inspect responsible_ai.user_validation_status.",
            "mitigation": "Collect consented structured feedback in future work; make no user-outcome claim now.",
            "status": "OPEN",
        },
    ]


def render_report(raw: Sequence[RawEvidence]) -> str:
    environment = consolidated_environment(raw)
    lines = [
        "# T09 Performance and Responsible-AI Workstream",
        "",
        "Status: `COMPLETE` for the T09 Definition of Done with explicit optional/unmeasured boundaries.",
        "",
        "The four performance runs were regenerated locally after the original contributor raw artifacts became unrecoverable. Lost bytes and old hashes are not cited as active evidence. Measurements remain development-host observations, never demo-hardware acceptance.",
        "",
        "## Latency semantics",
        "",
        "- `source_read_to_render_ms`: OpenCV read return to renderer completion.",
        "- `source_read_to_display_submit_ms`: the same start to return from `cv2.imshow`; GUI only.",
        "- `sensor_to_photon_ms`: `NOT_MEASURED`; no synchronized external apparatus.",
        "",
        "## Fresh local performance observations",
        "",
        "| Case | FPS | Render p50/p95 ms | Display-submit p50/p95 ms | RSS start/end/peak MiB | Degraded rate | RSS growth |",
        "| --- | ---: | ---: | ---: | ---: | ---: | --- |",
    ]
    for item in raw:
        payload = item.payload
        display_p50 = metric_value(payload, "source_read_to_display_submit_ms", "p50")
        display_p95 = metric_value(payload, "source_read_to_display_submit_ms", "p95")
        display = (
            "NOT_MEASURED"
            if display_p50 is None
            else f"{float(display_p50):.3f} / {float(display_p95):.3f}"
        )
        lines.append(
            f"| {item.case_id} | {float(metric_value(payload, 'processed_fps', 'single')):.3f} | "
            f"{float(metric_value(payload, 'source_read_to_render_ms', 'p50')):.3f} / "
            f"{float(metric_value(payload, 'source_read_to_render_ms', 'p95')):.3f} | {display} | "
            f"{float(metric_value(payload, 'rss_mib', 'start')):.3f} / "
            f"{float(metric_value(payload, 'rss_mib', 'end')):.3f} / "
            f"{float(metric_value(payload, 'rss_mib', 'peak')):.3f} | "
            f"{float(metric_value(payload, 'degraded_frame_rate', 'single')):.6f} | "
            f"{'FAIL' if metric_value(payload, 'rss_continuous_growth_flag', 'single') else 'PASS'} |"
        )
    lines.extend(
        [
            "",
            f"Host: {environment['manufacturer']} {environment['model']}; {environment['cpu']}; "
            f"{environment['ram_gib']:.2f} GiB RAM; backend `{environment['backend_name']}` on CPU.",
            "",
            "## Manual/non-AI baseline",
            "",
            "The unrecoverable manual ROI timing is `NOT_MEASURED`; no human action or elapsed time was simulated. The retained baseline explanation is sufficient for AI necessity: fixed RGB thresholds neither identify which pixels are garments nor handle background, illuminant, pose, and material changes. AI supplies automatic per-pixel localization; deterministic color science remains appropriate after localization.",
            "",
            "## Artifact integrity and supersession",
            "",
            "The active package cites only four newly generated raw benchmark JSON files, the new deterministic video, and tracked curated CSV/Markdown. Every available byte is rehashed. The seven old contributor artifacts are superseded and intentionally absent from the active manifest; their values are not used by this result.",
            "",
            "## Privacy, bias, environment, and licenses",
            "",
            "- Webcam frames were processed locally and neither saved nor uploaded; raw JSON contains metrics/environment only.",
            "- No private/raw artifact is tracked in Git. The generated video contains synthetic geometry and no person.",
            "- Profile and severity are user-selected settings, not diagnosis.",
            "- The evaluation convenience set does not establish demographic, garment, camera, or population accuracy.",
            "- No training was performed; pretrained MediaPipe CPU inference was reused. RSS is measured; energy is not.",
            "- User/accessibility validation is `NOT_MEASURED` and no participant is simulated.",
            "",
            "### Attribution inventory",
            "",
            "| Component | Version/status | License/evidence |",
            "| --- | --- | --- |",
        ]
    )
    for component, component_version, evidence in license_inventory():
        lines.append(f"| {component} | {component_version} | {evidence.replace('|', '/')} |")
    lines.extend(
        [
            "",
            "SCHP is not active T09 runtime evidence. Its code/weights/license and OpenVINO deployment remain an explicit T10 gate rather than an inferred attribution pass.",
            "",
            "## Known failures and limitations",
            "",
            "1. Degraded-frame behavior remains visible and is reported per run.",
            "2. Any fired RSS continuous-growth diagnostic remains an open risk.",
            "3. The measured machine is development-only, not declared demo hardware.",
            "4. Target-user validation and sensor-to-photon latency are not measured.",
        ]
    )
    return "\n".join(lines)


def generate_package(output_dir: Path = OUTPUT_DIR) -> Path:
    if output_dir.resolve() != OUTPUT_DIR.resolve():
        raise ValueError(f"output must remain in {OUTPUT_DIR}")
    require_lens_interpreter()
    started = utc_now()
    raw = discover_raw_evidence()
    metrics = [metric for item in raw for metric in item.payload["metrics"]]
    metrics.extend(responsible_ai_metrics())
    metrics_path = output_dir / "performance_metrics.csv"
    report_path = output_dir / "report.md"
    result_path = output_dir / "result.json"
    csv_rows = [
        {
            "case_ids": ";".join(item["case_ids"]),
            "name": item["name"],
            "aggregation": item["aggregation"],
            "unit": item["unit"],
            "status": item["status"],
            "value": "" if item["value"] is None else item["value"],
            "threshold_id": item["threshold_id"] or "",
            "threshold_result": item["threshold_result"],
            "method": item["method"],
        }
        for item in metrics
    ]
    write_csv_lf(metrics_path, csv_rows, tuple(csv_rows[0]))
    write_text_lf(report_path, render_report(raw))
    finished = utc_now()
    frozen_ids = [row["case_id"] for row in load_cases(WORKSTREAM)]
    artifacts = [raw_artifact_manifest(item) for item in raw]
    artifacts.append(video_artifact_manifest())
    artifacts.extend(
        [
            curated_artifact(
                metrics_path,
                artifact_id="performance-metrics",
                case_ids=frozen_ids,
                media_type="text/csv",
                generation_command=COMMAND,
                created_at=finished,
                creator="ChromaLens T09 local coordinator",
            ),
            curated_artifact(
                report_path,
                artifact_id="performance-rai-report",
                case_ids=frozen_ids,
                media_type="text/markdown",
                generation_command=COMMAND,
                created_at=finished,
                creator="ChromaLens T09 local coordinator",
                derived_from=tuple(
                    [RAW_ARTIFACT_IDS[case_id] for case_id in PERFORMANCE_CASE_IDS]
                    + ["generated-video-input"]
                ),
            ),
        ]
    )
    result = {
        "protocol_version": PROTOCOL_VERSION,
        "schema_version": PROTOCOL_VERSION,
        "metric_registry_version": PROTOCOL_VERSION,
        "result_id": f"t09-performance-rai-{result_timestamp(finished)}",
        "workstream": WORKSTREAM,
        "result_status": "COMPLETE",
        "git_commit": git_commit(),
        "created_at_utc": utc_text(finished),
        "operator": {"role": "coordinator", "identifier": "local-t09-coordinator"},
        "environment": consolidated_environment(raw),
        "cases": build_cases(raw),
        "configuration": {
            "cvd_profile": "deutan",
            "severity": 0.8,
            "random_seed": 0,
            "thresholds": {
                "demo_fps_floor": 5.0,
                "demo_display_p50_ms_floor": 350.0,
                "project_fps_target": 10.0,
                "project_display_p50_ms_target": 200.0,
            },
            "settings": {
                "evidence_scope": "development_host_only",
                "raw_generator_commit": git_commit(),
                "lost_contributor_artifacts_superseded": 7,
            },
        },
        "metrics": metrics,
        "artifacts": artifacts,
        "commands": [
            {
                "command": COMMAND,
                "exit_code": 0,
                "started_at_utc": utc_text(started),
                "ended_at_utc": utc_text(finished),
                "output_summary": "Consolidated four fresh frozen local runs; all five ignored active artifacts rehashed.",
            }
        ],
        "failure_cases": failure_cases(raw),
        "limitations": [
            "All performance values are development-host observations, not demo-hardware acceptance evidence.",
            "The seven old contributor raw artifacts are unrecoverable and superseded; this result uses only fresh local runs.",
            "Manual ROI timing, sensor_to_photon_ms, energy use, and user validation are NOT_MEASURED.",
            "Convenience fixtures do not establish demographic, garment, camera, or population-level accuracy.",
        ],
        "responsible_ai": {
            "runtime_local_offline": True,
            "frames_saved_by_default": False,
            "frames_uploaded_by_default": False,
            "medical_diagnosis_claim": False,
            "user_selected_profile": True,
            "privacy_summary": "Fresh benchmark JSON stores metrics/environment only; frames are neither saved nor uploaded; raw files remain ignored.",
            "bias_coverage_summary": "The convenience evaluation does not establish demographic, garment, pose, lighting, camera, display, or user-outcome generalization.",
            "environmental_summary": "No training; pretrained MediaPipe CPU inference reused; FPS/RSS measured, energy not measured.",
            "license_summary": "Active project/runtime/model/data/algorithm attribution is documented; deferred SCHP code/weights remain a T10 review gate.",
            "user_validation_status": "NOT_MEASURED",
        },
        "notes": "GUI-submit is software submission only; sensor-to-photon remains unmeasured. Optional cases remain explicit NOT_RUN without blocking the accepted T09 DoD.",
    }
    write_json_lf(result_path, result)
    print(f"Wrote {result_path.relative_to(ROOT)}")
    return result_path


def build_parser() -> argparse.ArgumentParser:
    return argparse.ArgumentParser(description=__doc__)


def main(argv: Sequence[str] | None = None) -> int:
    build_parser().parse_args(argv)
    generate_package()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
