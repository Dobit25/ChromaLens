"""Regenerate tracked T09 performance/RAI evidence from Trinh's observations."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
import sys
from typing import Any, Mapping, Sequence

if str(Path(__file__).resolve().parents[1]) not in sys.path:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts.t09_evaluation_common import (
    PROTOCOL_VERSION,
    ROOT,
    curated_artifact,
    git_commit,
    ignored_artifact_manifest,
    load_cases,
    result_timestamp,
    utc_now,
    utc_text,
    write_csv_lf,
    write_json_lf,
    write_text_lf,
)


WORKSTREAM = "performance_responsible_ai"
OUTPUT_DIR = ROOT / "evaluation/results/curated/performance_responsible_ai"
COMMAND = "conda run --name lens python scripts/t09_benchmark_report.py"
SOURCE_BRANCH_TIP = "b5da1c0e4975f3f4b07f08cec83bf0ada457bf2e"
MEASUREMENT_COMMIT = "7bc76d0526b34e7e366fe0cef730dc86680f5ef3"
MANUAL_COMMIT = "c0e3e7a759e6ffeb8b2b903583b8cf05927b8416"
RAI_COMMIT = "3bd976bb09bdc4605bb3149089d9c00d4c11f470"
LOCK_SHA256 = "3abb7af836d5721db3bb3de753816f8b41994a2d20c71fd96c25d80e136a071a"
MANUAL_ROI_MEDIAN_SECONDS = 3.016


OBSERVATIONS: Mapping[str, Mapping[str, Any]] = {
    "PERF-WEBCAM-GUI-120": {
        "created_at": "2026-08-21T16:53:24.455978Z",
        "source": "webcam:0",
        "source_kind": "webcam",
        "mode": "gui",
        "width": 640,
        "height": 480,
        "fps": 18.497687789026372,
        "render_p50": 62.0,
        "render_p95": 156.0,
        "render_slope": -6.965429760462803,
        "display_p50": 62.0,
        "display_p95": 156.0,
        "processing_p50": 32.0,
        "processing_p95": 140.0,
        "frames": 2220,
        "dropped": 1382,
        "degraded_rate": 0.9355855855855856,
        "retained_render": 2220,
        "retained_display": 2220,
        "rss_start": 187.12890625,
        "rss_end": 178.34765625,
        "rss_peak": 218.8671875,
        "rss_delta": -8.78125,
        "rss_slope": 6.900712044036851,
        "latency_growth": False,
        "rss_growth": True,
    },
    "PERF-WEBCAM-HEADLESS-120": {
        "created_at": "2026-08-21T16:45:54.457154Z",
        "source": "webcam:0",
        "source_kind": "webcam",
        "mode": "headless",
        "width": 640,
        "height": 480,
        "fps": 21.25,
        "render_p50": 47.0,
        "render_p95": 125.0,
        "render_slope": 9.796190674127388,
        "display_p50": None,
        "display_p95": None,
        "processing_p50": 32.0,
        "processing_p95": 94.0,
        "frames": 2550,
        "dropped": 1051,
        "degraded_rate": 0.876078431372549,
        "retained_render": 2550,
        "retained_display": 0,
        "rss_start": 191.671875,
        "rss_end": 165.87109375,
        "rss_peak": 216.68359375,
        "rss_delta": -25.80078125,
        "rss_slope": 6.966297357784202,
        "latency_growth": False,
        "rss_growth": True,
    },
    "PERF-VIDEO-GUI-120": {
        "created_at": "2026-08-21T17:03:51.436035Z",
        "source": "video:generated-360x240.avi",
        "source_kind": "video",
        "mode": "gui",
        "width": 360,
        "height": 240,
        "fps": 30.0,
        "render_p50": 16.0,
        "render_p95": 32.0,
        "render_slope": -0.5640926120804822,
        "display_p50": 16.0,
        "display_p95": 32.0,
        "processing_p50": 16.0,
        "processing_p95": 32.0,
        "frames": 3600,
        "dropped": None,
        "degraded_rate": 0.9833333333333333,
        "retained_render": 3600,
        "retained_display": 3600,
        "rss_start": 138.265625,
        "rss_end": 120.1953125,
        "rss_peak": 148.99609375,
        "rss_delta": -18.0703125,
        "rss_slope": 3.6218831940234897,
        "latency_growth": False,
        "rss_growth": False,
    },
    "PERF-VIDEO-HEADLESS-120": {
        "created_at": "2026-08-21T17:00:11.851923Z",
        "source": "video:generated-360x240.avi",
        "source_kind": "video",
        "mode": "headless",
        "width": 360,
        "height": 240,
        "fps": 48.95,
        "render_p50": 16.0,
        "render_p95": 32.0,
        "render_slope": -0.023785868979778566,
        "display_p50": None,
        "display_p95": None,
        "processing_p50": 16.0,
        "processing_p95": 32.0,
        "frames": 5874,
        "dropped": None,
        "degraded_rate": 0.9838270343888321,
        "retained_render": 5874,
        "retained_display": 0,
        "rss_start": 131.2578125,
        "rss_end": 116.23828125,
        "rss_peak": 151.30078125,
        "rss_delta": -15.01953125,
        "rss_slope": 6.678754087905211,
        "latency_growth": False,
        "rss_growth": True,
    },
}


RAW_MANIFESTS = (
    ("perf-webcam-gui-raw", ["PERF-WEBCAM-GUI-120"], "artifacts/t09/performance_responsible_ai/t09-performance-perf-webcam-gui-120-20260821t165324z.json", "f1576bfc3d1ff11f2c84bae4b8f15e52792a441dc2512de690f10b5d84f6d04b", 12901, "application/json", "2026-08-21T16:53:24.455978Z", "derived_artifact", "Trinh benchmark runner", "Apache-2.0"),
    ("perf-webcam-headless-raw", ["PERF-WEBCAM-HEADLESS-120"], "artifacts/t09/performance_responsible_ai/t09-performance-perf-webcam-headless-120-20260821t164554z.json", "f4b287d69cdcee658de57a4dda4ebf825fdc698cc6009cf2798bb51d95b73b37", 13102, "application/json", "2026-08-21T16:45:54.457154Z", "derived_artifact", "Trinh benchmark runner", "Apache-2.0"),
    ("perf-video-gui-raw", ["PERF-VIDEO-GUI-120"], "artifacts/t09/performance_responsible_ai/t09-performance-perf-video-gui-120-20260821t170351z.json", "e26674d85c7940ecd99e39259f5d6add6e643f089301f2c05cdd2ff0e3155a45", 12544, "application/json", "2026-08-21T17:03:51.436035Z", "derived_artifact", "Trinh benchmark runner", "Apache-2.0"),
    ("perf-video-headless-raw", ["PERF-VIDEO-HEADLESS-120"], "artifacts/t09/performance_responsible_ai/t09-performance-perf-video-headless-120-20260821t170011z.json", "9ec98841c1d3e3f6eee4cad4139001535391db516959e07a3d78c4d63ebfd517", 12758, "application/json", "2026-08-21T17:00:11.851923Z", "derived_artifact", "Trinh benchmark runner", "Apache-2.0"),
    ("generated-video-input", ["PERF-VIDEO-GUI-120", "PERF-VIDEO-HEADLESS-120"], "artifacts/t09/performance_responsible_ai/inputs/generated-360x240.avi", "3361444ba0a6c9119e10cc677fe5214f7035c2a2dda0e86c35be52a6d99d0244", 1357144, "video/x-msvideo", None, "project_synthetic", "ChromaLens generated video", "Apache-2.0"),
    ("manual-roi-raw", ["BASELINE-MANUAL-ROI"], "artifacts/t09/performance_responsible_ai/t09-manual-roi-f59b5913-20260822t172922z.json", "a2392deae77829d358d86a22f9929d48b4e3c3d61f3cf943d8ab39c445a57d02", 5307, "application/json", "2026-08-22T17:29:22Z", "derived_artifact", "Trinh manual ROI timer", "Apache-2.0"),
    ("responsible-ai-audit-raw", ["PERF-SENSOR-EXTERNAL", "BASELINE-FIXED-RGB", "RAI-ARTIFACT-INTEGRITY", "RAI-PRIVACY", "RAI-LICENSE", "RAI-LIMITATIONS", "RAI-USER-VALIDATION"], "artifacts/t09/performance_responsible_ai/t09-responsible-ai-audit-63d6a1c9-20260822t185636z.json", "cd703496b87dcb90ec438ff935f5100e7cfb7d313a489da3012ceec6e89244a5", 22107, "application/json", "2026-08-22T18:56:36Z", "derived_artifact", "Trinh responsible-AI audit", "Apache-2.0"),
)


def observation_metrics() -> list[dict[str, Any]]:
    metrics: list[dict[str, Any]] = []
    for case_id, observation in OBSERVATIONS.items():
        dimensions = {
            "source_kind": observation["source_kind"],
            "display_mode": observation["mode"],
            "resolution": f"{observation['width']}x{observation['height']}",
            "measurement_git_commit": MEASUREMENT_COMMIT,
            "evidence_class": "development_host_observation",
        }
        values = (
            ("processed_fps", "single", "frames/s", observation["fps"], "demo_floor", "NOT_EVALUATED"),
            ("source_read_to_render_ms", "p50", "ms", observation["render_p50"], "observation_only", "NOT_EVALUATED"),
            ("source_read_to_render_ms", "p95", "ms", observation["render_p95"], "observation_only", "NOT_EVALUATED"),
            ("source_read_to_render_slope_ms_per_minute", "whole_session", "ms/min", observation["render_slope"], "observation_only", "NOT_EVALUATED"),
            ("frame_processing_to_render_ms", "p50", "ms", observation["processing_p50"], "observation_only", "NOT_EVALUATED"),
            ("frame_processing_to_render_ms", "p95", "ms", observation["processing_p95"], "observation_only", "NOT_EVALUATED"),
            ("rss_mib", "start", "MiB", observation["rss_start"], "observation_only", "NOT_EVALUATED"),
            ("rss_mib", "end", "MiB", observation["rss_end"], "observation_only", "NOT_EVALUATED"),
            ("rss_mib", "peak", "MiB", observation["rss_peak"], "observation_only", "NOT_EVALUATED"),
            ("rss_delta_mib", "whole_session", "MiB", observation["rss_delta"], "observation_only", "NOT_EVALUATED"),
            ("rss_slope_mib_per_minute", "whole_session", "MiB/min", observation["rss_slope"], "observation_only", "NOT_EVALUATED"),
            ("latency_continuous_growth_flag", "single", "boolean", observation["latency_growth"], "required", "PASS" if not observation["latency_growth"] else "FAIL"),
            ("rss_continuous_growth_flag", "single", "boolean", observation["rss_growth"], "required", "PASS" if not observation["rss_growth"] else "FAIL"),
            ("processed_frame_count", "count", "frame", observation["frames"], "report_coverage", "NOT_EVALUATED"),
            ("degraded_frame_rate", "overall", "ratio", observation["degraded_rate"], "observation_only", "NOT_EVALUATED"),
            ("retained_source_read_to_render_sample_count", "count", "count", observation["retained_render"], "untruncated_required", "PASS" if observation["retained_render"] == observation["frames"] else "FAIL"),
            ("retained_source_read_to_display_submit_sample_count", "count", "count", observation["retained_display"], "gui_equals_processed_headless_zero", "PASS" if (observation["retained_display"] == observation["frames"] if observation["mode"] == "gui" else observation["retained_display"] == 0) else "FAIL"),
        )
        for name, aggregation, unit, value, threshold_id, threshold_result in values:
            metrics.append(metric(name, aggregation, unit, value, [case_id], threshold_id, threshold_result, dimensions))
        if observation["source_kind"] == "webcam":
            metrics.append(metric("dropped_capture_frame_count", "count", "frame", observation["dropped"], [case_id], "report_coverage", "NOT_EVALUATED", dimensions))
        else:
            metrics.append(unmeasured("dropped_capture_frame_count", "count", "frame", [case_id], "report_coverage", "Sequential finite-video mode has no capture overwrite count.", dimensions, status="NOT_APPLICABLE"))
        if observation["mode"] == "gui":
            metrics.extend(
                [
                    metric("source_read_to_display_submit_ms", "p50", "ms", observation["display_p50"], [case_id], "demo_floor_p50", "NOT_EVALUATED", dimensions),
                    metric("source_read_to_display_submit_ms", "p95", "ms", observation["display_p95"], [case_id], None, "NOT_EVALUATED", dimensions),
                ]
            )
        else:
            metrics.extend(
                [
                    unmeasured("source_read_to_display_submit_ms", "p50", "ms", [case_id], "demo_floor_p50", "Headless run has no OpenCV GUI submission.", dimensions),
                    unmeasured("source_read_to_display_submit_ms", "p95", "ms", [case_id], None, "Headless run has no OpenCV GUI submission.", dimensions),
                ]
            )
        metrics.extend(
            [
                unmeasured("sensor_to_photon_ms", "p50", "ms", [case_id], "external_apparatus_required", "No external synchronized apparatus was used.", dimensions, method="No external apparatus; software timestamps cannot measure sensor-to-photon"),
                unmeasured("sensor_to_photon_ms", "p95", "ms", [case_id], "external_apparatus_required", "No external synchronized apparatus was used.", dimensions, method="No external apparatus; software timestamps cannot measure sensor-to-photon"),
            ]
        )
    metrics.extend(
        [
            unmeasured("sensor_to_photon_ms", "p50", "ms", ["PERF-SENSOR-EXTERNAL"], "external_apparatus_required", "External photodiode/high-speed-camera apparatus was not available.", {"evidence_scope": "external_apparatus_case"}, method="No external apparatus; sensor-to-photon remains NOT_MEASURED"),
            unmeasured("sensor_to_photon_ms", "p95", "ms", ["PERF-SENSOR-EXTERNAL"], "external_apparatus_required", "External photodiode/high-speed-camera apparatus was not available.", {"evidence_scope": "external_apparatus_case"}, method="No external apparatus; sensor-to-photon remains NOT_MEASURED"),
            metric("manual_baseline_completion_seconds", "median", "second", MANUAL_ROI_MEDIAN_SECONDS, ["BASELINE-MANUAL-ROI"], "observation_only", "NOT_EVALUATED", {"trial_count": 5, "measurement_git_commit": MANUAL_COMMIT}),
            metric("artifact_checksum_mismatch_count", "count", "count", 0, ["BASELINE-FIXED-RGB"], "required", "PASS", {"scope": "tracked_curated_report_and_metrics_csv"}, reason="Coordinator recomputed exact bytes for tracked curated artifacts."),
            unmeasured("artifact_checksum_mismatch_count", "count", "count", ["RAI-ARTIFACT-INTEGRITY"], "required", "Contributor supplied SHA-256/size manifests, but the seven ignored raw artifacts are absent on the coordinator host and were not independently rehashed.", {"scope": "ignored_contributor_raw_artifacts"}),
            metric("unconsented_tracked_media_count", "count", "count", 0, ["RAI-PRIVACY"], "required", "PASS", {"scope": "git_tracked_media_audit"}, reason="No private/raw T09 media is tracked in mvp."),
            metric("artifact_checksum_mismatch_count", "count", "count", 0, ["RAI-LICENSE"], "required", "PASS", {"scope": "tracked_license_evidence_files"}, reason="Tracked license-evidence files referenced by the report were readable; license metadata gaps remain separately recorded."),
            metric("unconsented_tracked_media_count", "count", "count", 0, ["RAI-LIMITATIONS"], "required", "PASS", {"scope": "tracked_repository"}, reason="Failure/bias report cites no unconsented tracked media."),
            unmeasured("unconsented_tracked_media_count", "count", "count", ["RAI-USER-VALIDATION"], "required", "No participant study was conducted; no participant or consent record is simulated.", {"scope": "user_validation"}),
        ]
    )
    return metrics


def metric(
    name: str,
    aggregation: str,
    unit: str,
    value: Any,
    case_ids: Sequence[str],
    threshold_id: str | None,
    threshold_result: str,
    dimensions: Mapping[str, Any],
    *,
    reason: str = "Development-host observation retained from Trinh's validated report.",
    method: str = "T09 protocol 1.0.0; contributor raw result summarized at branch tip b5da1c0",
) -> dict[str, Any]:
    return {
        "name": name,
        "aggregation": aggregation,
        "unit": unit,
        "status": "MEASURED",
        "value": value,
        "case_ids": list(case_ids),
        "threshold_id": threshold_id,
        "threshold_result": threshold_result,
        "reason": reason,
        "method": method,
        "dimensions": dict(dimensions),
    }


def unmeasured(
    name: str,
    aggregation: str,
    unit: str,
    case_ids: Sequence[str],
    threshold_id: str | None,
    reason: str,
    dimensions: Mapping[str, Any],
    *,
    status: str = "NOT_MEASURED",
    method: str = "T09 protocol 1.0.0 explicit unmeasured boundary",
) -> dict[str, Any]:
    output = metric(name, aggregation, unit, None, case_ids, threshold_id, "NOT_APPLICABLE" if status == "NOT_APPLICABLE" else "NOT_EVALUATED", dimensions, reason=reason, method=method)
    output["status"] = status
    return output


def build_cases() -> list[dict[str, Any]]:
    status = {
        **{case_id: "COMPLETE" for case_id in OBSERVATIONS},
        "PERF-SENSOR-EXTERNAL": "NOT_RUN",
        "BASELINE-MANUAL-ROI": "COMPLETE",
        "BASELINE-FIXED-RGB": "COMPLETE",
        "RAI-ARTIFACT-INTEGRITY": "PARTIAL",
        "RAI-PRIVACY": "COMPLETE",
        "RAI-LICENSE": "PARTIAL",
        "RAI-LIMITATIONS": "COMPLETE",
        "RAI-USER-VALIDATION": "NOT_RUN",
    }
    reasons = {
        "PERF-SENSOR-EXTERNAL": "No synchronized external measurement apparatus; sensor_to_photon_ms is NOT_MEASURED.",
        "BASELINE-MANUAL-ROI": "Five public-fixture ROI trials completed; timing only, no ROI geometry or image saved.",
        "BASELINE-FIXED-RGB": "Human-readable comparison explains that fixed RGB thresholds do not automatically localize garments.",
        "RAI-ARTIFACT-INTEGRITY": "Tracked curated bytes are verified; contributor raw manifests are preserved but raw files are absent for coordinator rehash.",
        "RAI-PRIVACY": "No default save/upload and zero private/raw T09 media tracked in mvp.",
        "RAI-LICENSE": "Inventory is recorded with unresolved runtime-package/SCHP attribution gaps; not a compliance PASS.",
        "RAI-LIMITATIONS": "Privacy, bias, failure, environmental, and claim boundaries are documented.",
        "RAI-USER-VALIDATION": "No ethically consented participant study was performed; NOT_MEASURED.",
    }
    registry = load_cases(WORKSTREAM)
    return [
        {
            "case_id": row["case_id"],
            "status": status[row["case_id"]],
            "fixture_id": row["fixture_id"],
            "artifact_ids": case_artifact_ids(row["case_id"]),
            "reason": reasons.get(row["case_id"], "Frozen 15-second warm-up plus 120-second development-host observation retained from Trinh's workstream."),
        }
        for row in registry
    ]


def case_artifact_ids(case_id: str) -> list[str]:
    ids = ["performance-rai-report"]
    if case_id in OBSERVATIONS:
        ids.extend(["performance-metrics", {
            "PERF-WEBCAM-GUI-120": "perf-webcam-gui-raw",
            "PERF-WEBCAM-HEADLESS-120": "perf-webcam-headless-raw",
            "PERF-VIDEO-GUI-120": "perf-video-gui-raw",
            "PERF-VIDEO-HEADLESS-120": "perf-video-headless-raw",
        }[case_id]])
        if case_id.startswith("PERF-VIDEO"):
            ids.append("generated-video-input")
    elif case_id == "BASELINE-MANUAL-ROI":
        ids.append("manual-roi-raw")
    elif case_id not in {"BASELINE-FIXED-RGB"}:
        ids.append("responsible-ai-audit-raw")
    return ids


def generate_package(output_dir: Path = OUTPUT_DIR) -> Path:
    if output_dir.resolve() != OUTPUT_DIR.resolve():
        raise ValueError(f"output must remain in {OUTPUT_DIR}")
    started = utc_now()
    metrics = observation_metrics()
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
    write_text_lf(report_path, render_report())
    finished = utc_now()

    frozen_ids = [row["case_id"] for row in load_cases(WORKSTREAM)]
    tracked = [
        curated_artifact(
            metrics_path,
            artifact_id="performance-metrics",
            case_ids=list(OBSERVATIONS),
            media_type="text/csv",
            generation_command=COMMAND,
            created_at=finished,
            creator="Trinh observations, coordinator-regenerated",
        ),
        curated_artifact(
            report_path,
            artifact_id="performance-rai-report",
            case_ids=frozen_ids,
            media_type="text/markdown",
            generation_command=COMMAND,
            created_at=finished,
            creator="ChromaLens coordinators",
            derived_from=("performance-metrics",),
        ),
    ]
    ignored = [
        ignored_artifact_manifest(
            artifact_id=item[0],
            case_ids=item[1],
            relative_path=item[2],
            sha256=item[3],
            byte_size=item[4],
            media_type=item[5],
            generation_command=(
                "conda run --name lens python scripts/t09_benchmark_performance.py"
                if item[0].startswith("perf-")
                else "retained contributor workstream command; see report"
            ),
            created_at_utc=item[6],
            provenance_class=item[7],
            creator_or_source=item[8],
            license_id=item[9],
            license_evidence=(
                f"Contributor report at {SOURCE_BRANCH_TIP}; coordinator did not "
                "receive ignored raw bytes for independent rehash"
            ),
        )
        for item in RAW_MANIFESTS
    ]
    payload = {
        "protocol_version": PROTOCOL_VERSION,
        "schema_version": PROTOCOL_VERSION,
        "metric_registry_version": PROTOCOL_VERSION,
        "result_id": f"t09-performance-rai-{result_timestamp(finished)}",
        "workstream": WORKSTREAM,
        "result_status": "PARTIAL",
        "git_commit": git_commit(),
        "created_at_utc": utc_text(finished),
        "operator": {"role": "coordinator", "identifier": "coordinator-regeneration-from-trinh"},
        "environment": {
            "host_role": "development",
            "declared_demo_hardware": False,
            "manufacturer": "LENOVO",
            "model": "83JC",
            "operating_system": "Windows-10-10.0.26200-SP0",
            "cpu": "AMD64 Family 25 Model 68 Stepping 1, AuthenticAMD",
            "physical_core_count": 4,
            "logical_processor_count": 8,
            "ram_gib": 15.692100524902344,
            "gpu": "NVIDIA GeForce RTX 3050 6GB Laptop GPU (not used)",
            "npu": None,
            "camera_or_source": "mixed: webcam:0 and generated-360x240.avi",
            "python_version": "3.10.20",
            "package_versions": {"chromalens-ai": "0.1.0", "daltonlens": "0.1.5", "mediapipe": "0.10.21", "numpy": "1.26.4", "opencv-contrib-python": "4.10.0.84"},
            "lock_sha256": LOCK_SHA256,
            "backend_name": "mediapipe-selfie-torso/cpu",
            "backend_device": "cpu",
            "source_kind": "generated",
            "source_resolution": {"width": 640, "height": 480},
            "render_resolution": {"width": 640, "height": 480},
            "display_mode": "not_applicable",
            "warmup_seconds": 15.0,
            "measurement_seconds": 120.0,
            "external_measurement_apparatus": None,
        },
        "cases": build_cases(),
        "configuration": {"cvd_profile": "deutan", "severity": 0.8, "random_seed": None, "thresholds": {"demo_fps_floor": 5.0, "demo_display_p50_ms_floor": 350.0, "project_fps_target": 10.0, "project_display_p50_ms_target": 200.0}, "settings": {"measurement_git_commit": MEASUREMENT_COMMIT, "manual_roi_git_commit": MANUAL_COMMIT, "responsible_ai_git_commit": RAI_COMMIT, "source_branch_tip": SOURCE_BRANCH_TIP, "evidence_scope": "development_host_only"}},
        "metrics": metrics,
        "artifacts": tracked + ignored,
        "commands": [{"command": COMMAND, "exit_code": 0, "started_at_utc": utc_text(started), "ended_at_utc": utc_text(finished), "output_summary": "Regenerated one exact 12-case tracked schema result from Trinh's measured report; tracked hashes recomputed; seven absent ignored manifests retained without claiming coordinator re-verification."}],
        "failure_cases": failure_cases(),
        "limitations": ["All performance values are development-host observations and are not demo-hardware acceptance evidence.", "High degraded-frame rates were observed in all four runs.", "The RSS continuous-growth diagnostic failed three of four runs and remains an open long-run-memory risk.", "Seven contributor raw artifacts are absent on the coordinator host; their recorded hashes are preserved but not independently reverified here.", "sensor_to_photon_ms and user validation remain NOT_MEASURED.", "Five public fixtures do not establish demographic or garment-diversity validation.", "Runtime package attribution gaps are recorded rather than labeled compliant."],
        "responsible_ai": {"runtime_local_offline": True, "frames_saved_by_default": False, "frames_uploaded_by_default": False, "medical_diagnosis_claim": False, "user_selected_profile": True, "privacy_summary": "Runtime does not save/upload frames by default; tracked repository audit found zero private/raw T09 media.", "bias_coverage_summary": "Five public images and one contributor host do not cover skin tones, body presentation, garment type/material/pattern, lighting, occlusion, camera, or display diversity.", "environmental_summary": "No training from scratch; pretrained MediaPipe CPU inference was reused. FPS/RSS are reported, but energy use was not measured.", "license_summary": "Apache-2.0 project license and fixture rights are recorded. DaltonLens, MediaPipe, NumPy, OpenCV package evidence and deferred SCHP attribution remain gaps, so license status is GAPS_RECORDED rather than PASS.", "user_validation_status": "NOT_MEASURED"},
        "notes": "Coordinator regeneration from Trinh's branch. Mixed-source details are carried per metric dimensions; the top-level environment identifies the single development host only.",
    }
    write_json_lf(result_path, payload)
    return result_path


def failure_cases() -> list[dict[str, Any]]:
    return [
        {"failure_id": "FAIL-PERF-DEGRADED-RATE", "case_ids": list(OBSERVATIONS), "observed_behavior": "Degraded-frame rates ranged from 0.8761 to 0.9838.", "expected_behavior": "A substantially larger share of frames should retain all required analytical stages.", "user_impact": "The user frequently sees explicit degraded/unavailable output instead of full assistance.", "reproduction": "Run the four frozen 15 s warm-up + 120 s benchmark cases on Trinh's recorded development host.", "mitigation": "Investigate MediaPipe mask adequacy and pipeline degradation causes before making reliability claims.", "status": "OPEN"},
        {"failure_id": "FAIL-PERF-RSS-GROWTH", "case_ids": ["PERF-WEBCAM-GUI-120", "PERF-WEBCAM-HEADLESS-120", "PERF-VIDEO-HEADLESS-120"], "observed_behavior": "The frozen RSS four-window continuous-growth flag was true in three runs.", "expected_behavior": "The diagnostic flag must be false.", "user_impact": "Longer demo/runtime sessions may retain increasing memory and become unstable.", "reproduction": "Repeat the frozen benchmark and inspect rss_continuous_growth_flag.", "mitigation": "Profile allocation retention and repeat on the declared demo machine; keep the bounded queue invariant.", "status": "OPEN"},
        {"failure_id": "FAIL-PERF-DEMO-HARDWARE-UNDECLARED", "case_ids": list(OBSERVATIONS), "observed_behavior": "Measurements came from a development host, not owner-declared demo hardware.", "expected_behavior": "Final performance acceptance is measured on the declared demo laptop.", "user_impact": "Current FPS/latency values cannot predict or certify the competition demo machine.", "reproduction": "Inspect environment.host_role and declared_demo_hardware.", "mitigation": "Declare the demo laptop and rerun the same frozen cases before T11 claims.", "status": "OPEN"},
        {"failure_id": "FAIL-PERF-RAW-UNAVAILABLE", "case_ids": ["RAI-ARTIFACT-INTEGRITY"], "observed_behavior": "Seven ignored contributor artifacts are absent on the coordinator host.", "expected_behavior": "The data custodian independently rehashes every report artifact before final evidence acceptance.", "user_impact": "Raw provenance cannot currently be independently audited from this checkout.", "reproduction": "Run the validator with --require-untracked-artifacts.", "mitigation": "Recover the exact ignored bytes from the contributor/data custodian or rerun benchmarks on the declared demo host.", "status": "OPEN"},
    ]


def render_report() -> str:
    lines = [
        "# T09 Performance and Responsible-AI Workstream",
        "",
        "Status: `PARTIAL`. Performance runs and the manual ROI observation are retained; "
        "demo-hardware acceptance, raw-artifact coordinator re-verification, external "
        "sensor latency, license closure, and user validation are incomplete.",
        "",
        f"Source: Trinh branch tip `{SOURCE_BRANCH_TIP}`. Performance measurement commit "
        f"`{MEASUREMENT_COMMIT}`; manual ROI commit `{MANUAL_COMMIT}`; responsible-AI "
        f"audit commit `{RAI_COMMIT}`.",
        "",
        "## Claim boundary",
        "",
        "All numbers are development-host observations for LENOVO 83JC, AMD64 Family 25 "
        "Model 68, 4 physical/8 logical cores, 15.69 GiB RAM, MediaPipe CPU. They are "
        "not generalized to the undeclared demo machine.",
        "",
        "- `source_read_to_render_ms`: capture-read return to renderer completion.",
        "- `source_read_to_display_submit_ms`: capture-read return to return from "
        "`cv2.imshow`; GUI only.",
        "- `sensor_to_photon_ms`: `NOT_MEASURED`; no external synchronized apparatus.",
        "",
        "## Performance observations",
        "",
        "| Case | FPS | Render p50/p95 ms | Display-submit p50/p95 ms | RSS start/end/peak MiB | Degraded rate | RSS growth |",
        "| --- | ---: | ---: | ---: | ---: | ---: | --- |",
    ]
    for case_id, row in OBSERVATIONS.items():
        display = "NOT_MEASURED" if row["display_p50"] is None else f"{row['display_p50']} / {row['display_p95']}"
        lines.append(
            f"| {case_id} | {row['fps']} | {row['render_p50']} / {row['render_p95']} | "
            f"{display} | {row['rss_start']} / {row['rss_end']} / {row['rss_peak']} | "
            f"{row['degraded_rate']:.6f} | {'FAIL' if row['rss_growth'] else 'PASS'} |"
        )
    lines.extend(
        [
            "",
            "Every render-latency continuous-growth flag was false. RSS growth was true "
            "in three of four runs and remains an open diagnostic failure.",
            "",
            "## Manual/non-AI baseline",
            "",
            f"Five public-fixture manual ROI trials had median completion time "
            f"`{MANUAL_ROI_MEDIAN_SECONDS:.3f} s`. This measures human selection effort; "
            "it does not automatically locate garments in moving/unconstrained scenes. "
            "Fixed RGB thresholding also cannot determine garment location independently "
            "of background, illumination, pose, and material. AI is needed for automatic "
            "per-pixel localization; deterministic color science remains appropriate after localization.",
            "",
            "## Artifact integrity",
            "",
            "The machine result contains complete size/SHA-256/provenance manifests for "
            "the four raw benchmark JSON files, generated video, manual ROI JSON, and RAI "
            "audit JSON. Those ignored files were present for Trinh's report generation but "
            "are absent in this coordinator checkout. Their recorded hashes are preserved, "
            "not falsely reported as independently reverified. Tracked `report.md` and "
            "`performance_metrics.csv` are rehashed and tested from exact LF bytes.",
            "",
            "## Privacy, bias, environmental impact, and license gaps",
            "",
            "- Local/offline runtime; camera frames are neither saved nor uploaded by default.",
            "- No private/raw T09 media is tracked. Evaluation capture remains explicit opt-in.",
            "- The product is assistive and non-diagnostic; profile/severity are user selected.",
            "- Five public fixtures are not demographic validation. Coverage gaps include skin "
            "tone, body presentation, garment type/material/pattern, lighting, occlusion, camera, and display.",
            "- Pretrained MediaPipe CPU inference avoids training from scratch. FPS/RSS are "
            "reported; energy consumption is not measured.",
            "- License status is `GAPS_RECORDED`, not PASS. Open items: DaltonLens, MediaPipe, "
            "NumPy, OpenCV package evidence and deferred SCHP-ATR attribution/weights review.",
            "- User/accessibility validation is `NOT_MEASURED`; no participant is simulated.",
            "",
            "## Known failures",
            "",
            "1. Degraded-frame rates are high in every run.",
            "2. RSS continuous-growth diagnostic fails in three runs.",
            "3. The measured host is not declared demo hardware.",
            "4. Ignored raw bytes are unavailable for coordinator-side independent rehash.",
        ]
    )
    return "\n".join(lines)


def main() -> int:
    path = generate_package()
    print(f"Wrote {path.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
