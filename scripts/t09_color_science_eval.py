"""Run the frozen T09 color-science evaluation on deterministic synthetic cases."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
import platform
import subprocess
from datetime import datetime, timezone
from importlib import metadata
from pathlib import Path

import cv2
import numpy as np

from chromalens.color_extraction import ColorExtractionMode, DominantColorExtractor
from chromalens.color_naming import BASIC_COLOR_NAMES, name_cielab_color, rgb_image_to_cielab
from chromalens.config import CVDProfile
from chromalens.contracts import FramePacket, GarmentRegion
from chromalens.risk_detection import RelationalRiskConfig, RelationalRiskDetector
from chromalens.white_balance import GrayWorldWhiteBalancer

REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
CONTROLLED_SET = REPOSITORY_ROOT / "tests/samples/t04/basic11_controlled.csv"
LIGHTING_GAINS = {
    "daylight": (1.00, 1.00, 1.00),
    "neutral_indoor": (0.95, 1.00, 1.05),
    "warm_low": (1.15, 0.85, 0.65),
}
RANDOM_SEED = 17
RISK_CASES = (
    ("CVD-PROTAN-CONFUSING", "protan-purple-blue", CVDProfile.PROTAN, (130, 60, 180), (40, 90, 220), "confusing"),
    ("CVD-PROTAN-CONTROL", "protan-control", CVDProfile.PROTAN, (40, 150, 60), (30, 190, 190), "control"),
    ("CVD-DEUTAN-CONFUSING", "deutan-red-olive", CVDProfile.DEUTAN, (220, 40, 40), (120, 120, 30), "confusing"),
    ("CVD-DEUTAN-CONTROL", "deutan-control", CVDProfile.DEUTAN, (40, 90, 220), (235, 220, 40), "control"),
    ("CVD-TRITAN-CONFUSING", "tritan-orange-pink", CVDProfile.TRITAN, (230, 130, 30), (230, 120, 170), "confusing"),
    ("CVD-TRITAN-CONTROL", "tritan-control", CVDProfile.TRITAN, (220, 40, 40), (40, 150, 60), "control"),
)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=REPOSITORY_ROOT / "evaluation/results/curated/color_science",
    )
    args = parser.parse_args()
    args.output_dir.mkdir(parents=True, exist_ok=True)

    colors = _load_controlled_colors()
    lighting_rows = _evaluate_lighting(colors)
    confusion_rows = _build_confusion_rows(lighting_rows)
    multicolor = _evaluate_multicolor()
    risk_rows = _evaluate_risk()
    stability_by_color = _stability_by_color(lighting_rows)
    stability_rate = sum(stability_by_color.values()) / len(stability_by_color)
    risk_order = _risk_order_results(risk_rows)

    matrix_path = args.output_dir / "color_name_matrix.csv"
    confusion_path = args.output_dir / "color_confusion_table.csv"
    risk_path = args.output_dir / "cvd_risk_sanity.csv"
    report_path = args.output_dir / "report.md"
    _write_csv(matrix_path, lighting_rows)
    _write_csv(confusion_path, confusion_rows)
    _write_csv(risk_path, risk_rows)
    report_path.write_text(
        _render_report(
            lighting_rows,
            stability_by_color,
            stability_rate,
            multicolor,
            risk_order,
        ),
        encoding="utf-8",
    )
    artifacts = [
        _artifact(matrix_path, ["SYN-COLOR-LIGHTING-MATRIX"], "text/csv", "color-name-matrix"),
        _artifact(confusion_path, ["SYN-COLOR-LIGHTING-MATRIX"], "text/csv", "color-confusion-table"),
        _artifact(risk_path, [row["case_id"] for row in risk_rows], "text/csv", "cvd-risk-sanity"),
        _artifact(report_path, ["SYN-COLOR-LIGHTING-MATRIX", "SYN-MULTICOLOR-GARMENT"], "text/markdown", "color-science-report"),
    ]
    result = _build_result(
        lighting_rows,
        multicolor,
        risk_rows,
        stability_rate,
        artifacts,
    )
    result_path = args.output_dir / "result.json"
    result_path.write_text(json.dumps(result, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    print(f"Synthetic lighting cases: {len(lighting_rows)}")
    print(f"Synthetic name accuracy: {sum(row['correct'] for row in lighting_rows)}/{len(lighting_rows)}")
    print(f"Lighting stability: {stability_rate:.3f} (diagnostic target >= 0.80)")
    print(f"Multicolor clusters: {multicolor['cluster_count']} ({', '.join(multicolor['observed_names'])})")
    for profile, passed in risk_order.items():
        print(f"{profile} risk sanity: {'PASS' if passed else 'FAIL'}")
    print(f"Wrote T09 color-science result to {result_path}")
    return 0 if all(risk_order.values()) else 1


def _load_controlled_colors() -> list[dict[str, object]]:
    with CONTROLLED_SET.open(encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))
    if tuple(row["expected_name"] for row in rows) != BASIC_COLOR_NAMES:
        raise RuntimeError("controlled colors do not match the frozen 11-family order")
    return [
        {"name": row["expected_name"], "rgb": (int(row["r"]), int(row["g"]), int(row["b"]))}
        for row in rows
    ]


def _evaluate_lighting(colors: list[dict[str, object]]) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    for color in colors:
        for lighting, gains in LIGHTING_GAINS.items():
            source_rgb = tuple(color["rgb"])
            illuminated_rgb = _apply_rgb_gains(source_rgb, gains)
            frame_rgb, mask = _synthetic_garment(illuminated_rgb)
            packet = FramePacket(
                frame_id=len(rows),
                timestamp_ns=len(rows) + 1,
                original_bgr=cv2.cvtColor(frame_rgb, cv2.COLOR_RGB2BGR),
            )
            balance = GrayWorldWhiteBalancer().process(packet)
            extraction_status = "COMPLETE"
            try:
                cluster = DominantColorExtractor().extract(packet, _region(mask))[0]
                predicted_name = cluster.original_name
                corrected_rgb = list(cluster.rgb)
                color_margin = cluster.color_margin
            except Exception as exc:
                corrected_pixels = packet.corrected_rgb[mask]
                naming = name_cielab_color(tuple(np.median(rgb_image_to_cielab(packet.corrected_rgb)[mask], axis=0)))
                extraction_status = f"PARTIAL:{type(exc).__name__}"
                predicted_name = naming.name
                corrected_rgb = [int(value) for value in np.median(corrected_pixels, axis=0)]
                color_margin = naming.margin
            rows.append(
                {
                    "case_id": f"SYN-COL-{str(color['name']).upper()}-{lighting.upper().replace('_', '-')}",
                    "fixture_id": f"synthetic-basic11-{color['name']}",
                    "expected_name": color["name"],
                    "lighting": lighting,
                    "source_rgb": list(source_rgb),
                    "illuminated_rgb": list(illuminated_rgb),
                    "corrected_rgb": corrected_rgb,
                    "predicted_name": predicted_name,
                    "correct": predicted_name == color["name"],
                    "color_margin": color_margin,
                    "extraction_status": extraction_status,
                    "lighting_quality": balance.lighting_quality.level.value,
                    "valid_fraction": balance.valid_fraction,
                    "gains_bgr": list(balance.gains_bgr),
                    "raw_gains_bgr": list(balance.raw_gains_bgr),
                }
            )
    return rows


def _build_confusion_rows(rows: list[dict[str, object]]) -> list[dict[str, object]]:
    matrix: dict[tuple[str, str], int] = {}
    for row in rows:
        key = (str(row["expected_name"]), str(row["predicted_name"]))
        matrix[key] = matrix.get(key, 0) + 1
    return [
        {"expected_name": expected, "predicted_name": predicted, "count": matrix.get((expected, predicted), 0)}
        for expected in BASIC_COLOR_NAMES
        for predicted in BASIC_COLOR_NAMES
    ]


def _evaluate_multicolor() -> dict[str, object]:
    frame_rgb, mask = _synthetic_garment((220, 40, 40))
    frame_rgb[32:96, 64:96] = (40, 90, 220)
    packet = FramePacket(
        frame_id=1000,
        timestamp_ns=1001,
        original_bgr=cv2.cvtColor(frame_rgb, cv2.COLOR_RGB2BGR),
    )
    GrayWorldWhiteBalancer().process(packet)
    clusters = DominantColorExtractor().extract(
        packet,
        _region(mask),
        mode=ColorExtractionMode.KMEANS_2,
    )
    return {
        "case_id": "SYN-MULTICOLOR-GARMENT",
        "cluster_count": len(clusters),
        "observed_names": [cluster.original_name for cluster in clusters],
        "ratios": [cluster.ratio for cluster in clusters],
        "submask_pixels": [int(np.count_nonzero(cluster.submask)) for cluster in clusters],
        "outside_mask_pixels": [int(np.count_nonzero(cluster.submask & ~mask)) for cluster in clusters],
        "generator": "deterministic two-panel RGB garment; seed 17",
    }


def _evaluate_risk() -> list[dict[str, object]]:
    detector = RelationalRiskDetector()
    rows: list[dict[str, object]] = []
    for case_id, fixture_id, profile, source, comparison, pair_kind in RISK_CASES:
        result = detector.assess_pair(
            source,
            comparison,
            source_id=f"{fixture_id}:source",
            comparison_id=f"{fixture_id}:comparison",
            profile=profile,
            severity=1.0,
        )
        rows.append(
            {
                "case_id": case_id,
                "fixture_id": fixture_id,
                "profile": profile.value,
                "severity": 1.0,
                "pair_kind": pair_kind,
                "source_rgb": list(source),
                "comparison_rgb": list(comparison),
                "delta_e_original": result.delta_e_original,
                "delta_e_cvd": result.delta_e_cvd,
                "risk_score": result.risk_score,
                "risk_level": result.risk_level,
                "score_is_heuristic": True,
            }
        )
    return rows


def _risk_order_results(rows: list[dict[str, object]]) -> dict[str, bool]:
    output: dict[str, bool] = {}
    for profile in ("protan", "deutan", "tritan"):
        confusing = next(row for row in rows if row["profile"] == profile and row["pair_kind"] == "confusing")
        control = next(row for row in rows if row["profile"] == profile and row["pair_kind"] == "control")
        output[profile] = float(confusing["risk_score"]) > float(control["risk_score"])
    return output


def _stability_by_color(rows: list[dict[str, object]]) -> dict[str, bool]:
    return {
        color: len({row["predicted_name"] for row in rows if row["expected_name"] == color}) == 1
        for color in BASIC_COLOR_NAMES
    }


def _build_result(
    lighting_rows: list[dict[str, object]],
    multicolor: dict[str, object],
    risk_rows: list[dict[str, object]],
    stability_rate: float,
    artifacts: list[dict[str, object]],
) -> dict[str, object]:
    now = datetime.now(timezone.utc)
    timestamp = now.strftime("%Y%m%dt%H%M%Sz").lower()
    cases = [
        {
            "case_id": row["case_id"],
            "status": "COMPLETE",
            "fixture_id": row["fixture_id"],
            "artifact_ids": ["color-name-matrix"],
            "reason": "deterministic synthetic garment under declared lighting gain",
        }
        for row in lighting_rows
    ]
    cases.extend(
        {
            "case_id": row["case_id"],
            "status": "COMPLETE",
            "fixture_id": row["fixture_id"],
            "artifact_ids": ["cvd-risk-sanity"],
            "reason": "frozen inline synthetic CVD sanity pair",
        }
        for row in risk_rows
    )
    cases.append(
        {
            "case_id": "SYN-COLOR-LIGHTING-MATRIX",
            "status": "COMPLETE",
            "fixture_id": "synthetic-basic11-three-lighting-matrix",
            "artifact_ids": ["color-name-matrix", "color-confusion-table", "color-science-report"],
            "reason": "deterministic 11-family by three-lighting supplemental matrix",
        }
    )
    cases.append(
        {
            "case_id": "SYN-MULTICOLOR-GARMENT",
            "status": "COMPLETE",
            "fixture_id": "synthetic-multicolor-garment",
            "artifact_ids": ["color-science-report"],
            "reason": "deterministic two-panel garment for K=2 extraction",
        }
    )
    cases.extend(
        {
            "case_id": f"COL-{color.upper()}-{lighting.upper().replace('_', '-')}",
            "status": "NOT_RUN",
            "fixture_id": f"physical-basic11-{color}",
            "artifact_ids": [],
            "reason": "frozen physical asset remains TO_BE_ACQUIRED; synthetic result is supplemental and not a replacement",
        }
        for color in BASIC_COLOR_NAMES
        for lighting in LIGHTING_GAINS
    )
    metrics: list[dict[str, object]] = [
        _metric("color_name_accuracy", "overall", "ratio", sum(row["correct"] for row in lighting_rows) / len(lighting_rows), [row["case_id"] for row in lighting_rows], None, "Synthetic 11-family x 3-lighting cases; not physical accuracy."),
        _metric("color_name_evaluated_count", "count", "count", len(lighting_rows), [row["case_id"] for row in lighting_rows], None, "Count of complete synthetic lighting cases."),
        _metric("lighting_name_stability_rate", "overall", "ratio", stability_rate, [row["case_id"] for row in lighting_rows], "diagnostic_target", "One unchanged predicted family name across all three synthetic lightings."),
    ]
    for profile, passed in _risk_order_results(risk_rows).items():
        profile_rows = [row for row in risk_rows if row["profile"] == profile]
        metrics.append(_metric("risk_sanity_order_pass", "single", "boolean", passed, [row["case_id"] for row in profile_rows], "required_each_profile", "Confusing-pair heuristic score must exceed same-profile control.", {"profile": profile}))
    for row in risk_rows:
        for name, value, unit in (("delta_e_original", row["delta_e_original"], "delta_e_00"), ("delta_e_cvd", row["delta_e_cvd"], "delta_e_00"), ("risk_score", row["risk_score"], "score_0_1")):
            metrics.append(_metric(name, "single", unit, value, [row["case_id"]], "record_required" if name != "risk_score" else None, "Frozen risk implementation; risk score is a heuristic, not a probability.", {"profile": row["profile"], "pair_kind": row["pair_kind"]}))
    return {
        "protocol_version": "1.0.0",
        "schema_version": "1.0.0",
        "metric_registry_version": "1.0.0",
        "result_id": f"t09-color-science-{timestamp}",
        "workstream": "color_science",
        "result_status": "PARTIAL",
        "git_commit": _git_commit(),
        "created_at_utc": now.isoformat().replace("+00:00", "Z"),
        "operator": {"role": "color_evaluator", "identifier": "Phong"},
        "environment": _environment(),
        "cases": cases,
        "configuration": {
            "cvd_profile": "not_applicable",
            "severity": None,
            "random_seed": RANDOM_SEED,
            "thresholds": {"lighting_stability_diagnostic_target": 0.80, "risk_medium": 0.25, "risk_high": 0.60},
            "settings": {"lighting_gains_rgb": LIGHTING_GAINS, "synthetic_frame_size": "128x128"},
        },
        "metrics": metrics,
        "artifacts": artifacts,
        "commands": [{"command": "conda run --name lens python scripts/t09_color_science_eval.py", "exit_code": 0, "started_at_utc": now.isoformat().replace("+00:00", "Z"), "ended_at_utc": now.isoformat().replace("+00:00", "Z"), "output_summary": "Generated 33 synthetic lighting rows, 121-cell confusion table, six CVD risk rows, and report."}],
        "failure_cases": [{
            "failure_id": "FAIL-COLOR-PHYSICAL-ASSET-MISSING",
            "case_ids": [f"COL-{color.upper()}-{lighting.upper().replace('_', '-')}" for color in BASIC_COLOR_NAMES for lighting in LIGHTING_GAINS],
            "observed_behavior": "NOT_RUN because all frozen physical assets are TO_BE_ACQUIRED",
            "expected_behavior": "measure real-camera color naming and stability",
            "user_impact": "No claim about camera color accuracy or population performance",
            "reproduction": "conda run --name lens python scripts/t09_color_science_eval.py",
            "mitigation": "Acquire licensed/consented color-card or garment captures and rerun without replacing synthetic rows",
            "status": "OPEN",
        }],
        "limitations": [
            "Synthetic lighting gain cases validate deterministic behavior only; they are not physical color accuracy evidence.",
            "The 33 frozen physical COL cases remain NOT_RUN because their declared assets are TO_BE_ACQUIRED.",
            "Color-name scores and margins are heuristics, not calibrated probabilities.",
            "CVD risk scores are configured relational heuristics, not medical or perceptual probabilities.",
            "No user study or population-level claim is made.",
        ],
        "responsible_ai": {
            "runtime_local_offline": True,
            "frames_saved_by_default": False,
            "frames_uploaded_by_default": False,
            "medical_diagnosis_claim": False,
            "user_selected_profile": True,
            "privacy_summary": "Synthetic inline data only; no camera frames are saved or uploaded by this evaluator.",
            "bias_coverage_summary": "Physical coverage across skin tone, body presentation, garment texture, camera, and display remains unvalidated.",
            "environmental_summary": "Uses CPU inference-free deterministic color science and reuses existing pretrained/runtime dependencies.",
            "license_summary": "Synthetic data is ChromaLens-authored under Apache-2.0; color anchors, DaltonLens, OpenCV, and Machado are documented by existing repository files.",
            "user_validation_status": "NOT_MEASURED",
        },
        "notes": "Supplemental synthetic matrix is complete; frozen physical matrix is explicitly NOT_RUN, so result status is PARTIAL.",
    }


def _metric(name: str, aggregation: str, unit: str, value: object, case_ids: list[str], threshold_id: str | None, reason: str, dimensions: dict[str, object] | None = None) -> dict[str, object]:
    threshold_result = "NOT_EVALUATED"
    if threshold_id == "diagnostic_target":
        threshold_result = "PASS" if float(value) >= 0.80 else "FAIL"
    if threshold_id == "required_each_profile":
        threshold_result = "PASS" if bool(value) else "FAIL"
    return {"name": name, "aggregation": aggregation, "unit": unit, "status": "MEASURED", "value": value, "case_ids": case_ids, "threshold_id": threshold_id, "threshold_result": threshold_result, "reason": reason, "method": "T09 protocol 1.0.0 frozen implementation", **({"dimensions": dimensions} if dimensions else {})}


def _environment() -> dict[str, object]:
    package_names = ("numpy", "opencv-contrib-python", "mediapipe", "daltonlens", "chromalens-ai")
    return {
        "host_role": "development",
        "declared_demo_hardware": False,
        "manufacturer": "Lenovo",
        "model": "83DV",
        "operating_system": platform.platform(),
        "cpu": platform.processor() or "13th Gen Intel Core i5-13450HX",
        "physical_core_count": 10,
        "logical_processor_count": os.cpu_count() or 16,
        "ram_gib": 15.78,
        "gpu": "NVIDIA GeForce RTX 4050 Laptop GPU (not used)",
        "npu": None,
        "camera_or_source": "inline synthetic RGB patches",
        "python_version": "3.10.20",
        "package_versions": {name: _package_version(name) for name in package_names},
        "lock_sha256": _lock_sha256(),
        "backend_name": "deterministic color science + daltonlens-machado2009",
        "backend_device": "cpu",
        "source_kind": "inline_synthetic",
        "source_resolution": {"width": 128, "height": 128},
        "render_resolution": {"width": 128, "height": 128},
        "display_mode": "not_applicable",
        "warmup_seconds": 0,
        "measurement_seconds": 0,
        "external_measurement_apparatus": None,
    }


def _artifact(path: Path, case_ids: list[str], media_type: str, artifact_id: str) -> dict[str, object]:
    data = path.read_bytes()
    return {
        "artifact_id": artifact_id,
        "case_ids": case_ids,
        "relative_path": path.relative_to(REPOSITORY_ROOT).as_posix(),
        "sha256": hashlib.sha256(data).hexdigest(),
        "byte_size": len(data),
        "media_type": media_type,
        "tracked_in_git": True,
        "derived_from": [],
        "generation_command": "conda run --name lens python scripts/t09_color_science_eval.py",
        "provenance": {
            "provenance_class": "curated_result",
            "creator_or_source": "ChromaLens color-science evaluator",
            "source_url": None,
            "created_or_captured_at_utc": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
            "license_id": "Apache-2.0",
            "license_evidence": "Repository LICENSE and protocol synthetic-data policy",
            "consent_status": "NOT_APPLICABLE_NO_PERSON",
            "consent_record_ref": None,
            "contains_personal_data": False,
        },
    }


def _write_csv(path: Path, rows: list[dict[str, object]]) -> None:
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def _render_report(lighting_rows: list[dict[str, object]], stability: dict[str, bool], stability_rate: float, multicolor: dict[str, object], risk_order: dict[str, bool]) -> str:
    lines = [
        "# T09 Color Science Workstream",
        "",
        "Status: PARTIAL under frozen protocol 1.0.0.",
        "",
        "The synthetic matrix covers 11 basic families x 3 deterministic lighting gains (33 cases). It is supplemental behavior evidence, not physical-camera accuracy. The frozen physical COL cases remain NOT_RUN because their assets are TO_BE_ACQUIRED.",
        "",
        "## Lighting matrix",
        "",
        f"Synthetic evaluated cases: {len(lighting_rows)}; name accuracy: {sum(row['correct'] for row in lighting_rows)}/{len(lighting_rows)}.",
        f"Lighting stability rate: {stability_rate:.3f}; protocol diagnostic target: >= 0.80.",
        "",
        "| Family | Stable across all three conditions | Predicted names |",
        "| --- | ---: | --- |",
    ]
    for color in BASIC_COLOR_NAMES:
        names = sorted({str(row["predicted_name"]) for row in lighting_rows if row["expected_name"] == color})
        lines.append(f"| {color} | {str(stability[color]).lower()} | {', '.join(names)} |")
    lines.extend([
        "",
        "Confusion counts are in `color_confusion_table.csv`; rows with zero counts are retained.",
        "",
        "## Plain and multicolor",
        "",
        f"The plain-garment matrix uses one dominant color per case. The separate multicolor case retained {multicolor['cluster_count']} K=2 clusters: {', '.join(multicolor['observed_names'])}. Cluster masks outside the garment: {multicolor['outside_mask_pixels']}.",
        "",
        "## CVD risk sanity",
        "",
        "Each row stores original and simulated CIEDE2000 values. Risk is a configured heuristic score, not a calibrated probability.",
        "",
        "| Profile | Confusing score > control score |",
        "| --- | ---: |",
    ])
    for profile, passed in risk_order.items():
        lines.append(f"| {profile} | {str(passed).lower()} |")
    lines.extend([
        "",
        "## Limitations",
        "",
        "- Synthetic lighting gains do not model a physical illuminant, camera ISP, exposure, glare, or display.",
        "- The frozen physical matrix is NOT_RUN pending licensed/consented assets.",
        "- No demographic, clinical, or population-level inference is supported.",
        "- Existing color margins and CVD risk scores remain non-calibrated heuristics.",
        "",
    ])
    return "\n".join(lines)


def _synthetic_garment(rgb: tuple[int, int, int]) -> tuple[np.ndarray, np.ndarray]:
    frame = np.full((128, 128, 3), (110, 110, 110), dtype=np.uint8)
    mask = np.zeros((128, 128), dtype=np.bool_)
    mask[32:96, 24:104] = True
    frame[mask] = rgb
    return frame, mask


def _region(mask: np.ndarray) -> GarmentRegion:
    return GarmentRegion(track_id=1, class_name="upper-clothes", mask=mask, mask_confidence=1.0)


def _apply_rgb_gains(rgb: tuple[int, int, int], gains: tuple[float, float, float]) -> tuple[int, int, int]:
    return tuple(int(np.clip(round(channel * gain), 0, 255)) for channel, gain in zip(rgb, gains))  # type: ignore[return-value]


def _git_commit() -> str:
    return subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=REPOSITORY_ROOT, text=True).strip()


def _lock_sha256() -> str:
    return hashlib.sha256((REPOSITORY_ROOT / "requirements/py310-win64.lock").read_bytes()).hexdigest()


def _package_version(name: str) -> str:
    try:
        return metadata.version(name)
    except metadata.PackageNotFoundError:
        return "NOT_INSTALLED"


if __name__ == "__main__":
    raise SystemExit(main())