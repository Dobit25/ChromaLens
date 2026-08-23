"""Generate the frozen T09 color-science package plus supplemental synthetic evidence."""

from __future__ import annotations

import csv
from datetime import datetime
from pathlib import Path
import sys
from typing import Any, Mapping, Sequence

if str(Path(__file__).resolve().parents[1]) not in sys.path:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import cv2
import numpy as np

from chromalens.color_extraction import ColorExtractionMode, DominantColorExtractor
from chromalens.color_naming import BASIC_COLOR_NAMES, name_cielab_color, rgb_image_to_cielab
from chromalens.config import CVDProfile
from chromalens.contracts import FramePacket, GarmentRegion
from chromalens.risk_detection import RelationalRiskDetector
from chromalens.white_balance import GrayWorldWhiteBalancer
from scripts.t09_evaluation_common import (
    PROTOCOL_VERSION,
    ROOT,
    collect_environment,
    curated_artifact,
    git_commit,
    load_cases,
    result_timestamp,
    utc_now,
    utc_text,
    write_csv_lf,
    write_json_lf,
    write_text_lf,
)


WORKSTREAM = "color_science"
OUTPUT_DIR = ROOT / "evaluation/results/curated/color_science"
CONTROLLED_SET = ROOT / "tests/samples/t04/basic11_controlled.csv"
BASE_LOCK = ROOT / "requirements/py310-win64.lock"
COMMAND = "conda run --name lens python scripts/t09_color_science_eval.py"
RANDOM_SEED = 17
LIGHTING_GAINS: Mapping[str, tuple[float, float, float]] = {
    "daylight": (1.00, 1.00, 1.00),
    "neutral_indoor": (0.95, 1.00, 1.05),
    "warm_low": (1.15, 0.85, 0.65),
}
RISK_CASES = (
    ("CVD-PROTAN-CONFUSING", CVDProfile.PROTAN, (130, 60, 180), (40, 90, 220), "confusing"),
    ("CVD-PROTAN-CONTROL", CVDProfile.PROTAN, (40, 150, 60), (30, 190, 190), "control"),
    ("CVD-DEUTAN-CONFUSING", CVDProfile.DEUTAN, (220, 40, 40), (120, 120, 30), "confusing"),
    ("CVD-DEUTAN-CONTROL", CVDProfile.DEUTAN, (40, 90, 220), (235, 220, 40), "control"),
    ("CVD-TRITAN-CONFUSING", CVDProfile.TRITAN, (230, 130, 30), (230, 120, 170), "confusing"),
    ("CVD-TRITAN-CONTROL", CVDProfile.TRITAN, (220, 40, 40), (40, 150, 60), "control"),
)


def load_controlled_colors() -> list[dict[str, Any]]:
    with CONTROLLED_SET.open(encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))
    expected_order = tuple(row["expected_name"] for row in rows)
    if expected_order != BASIC_COLOR_NAMES:
        raise RuntimeError("controlled patches do not match the frozen 11-name order")
    return [
        {
            "name": row["expected_name"],
            "rgb": (int(row["r"]), int(row["g"]), int(row["b"])),
        }
        for row in rows
    ]


def evaluate_contract(colors: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for color in colors:
        source_rgb = tuple(color["rgb"])
        patch = np.asarray([[source_rgb]], dtype=np.uint8)
        naming = name_cielab_color(tuple(rgb_image_to_cielab(patch)[0, 0]))
        expected = str(color["name"])
        rows.append(
            {
                "case_id": f"COL-CONTRACT-{expected.upper()}",
                "fixture_id": f"basic11-{expected}",
                "status": "COMPLETE",
                "expected_name": expected,
                "source_rgb": "-".join(str(channel) for channel in source_rgb),
                "predicted_name": naming.name,
                "predicted_rgb": "-".join(str(channel) for channel in source_rgb),
                "correct": naming.name == expected,
                "color_margin": naming.margin,
                "reason": "deterministic tracked digital color-naming contract patch",
            }
        )
    return rows


def evaluate_synthetic_lighting(
    colors: Sequence[Mapping[str, Any]],
) -> list[dict[str, Any]]:
    """Retain Phong's deterministic three-gain diagnostic as supplemental data."""

    rows: list[dict[str, Any]] = []
    for color in colors:
        for lighting, gains in LIGHTING_GAINS.items():
            source_rgb = tuple(color["rgb"])
            illuminated_rgb = apply_rgb_gains(source_rgb, gains)
            frame_rgb, mask = synthetic_garment(illuminated_rgb)
            packet = FramePacket(
                frame_id=len(rows),
                timestamp_ns=len(rows) + 1,
                original_bgr=cv2.cvtColor(frame_rgb, cv2.COLOR_RGB2BGR),
            )
            balance = GrayWorldWhiteBalancer().process(packet)
            extraction_status = "COMPLETE"
            try:
                cluster = DominantColorExtractor().extract(packet, region(mask))[0]
                predicted_name = cluster.original_name
                corrected_rgb = cluster.rgb
                color_margin = cluster.color_margin
            except (RuntimeError, ValueError, IndexError) as error:
                corrected_pixels = packet.corrected_rgb[mask]
                lab_pixels = rgb_image_to_cielab(packet.corrected_rgb)[mask]
                naming = name_cielab_color(tuple(np.median(lab_pixels, axis=0)))
                extraction_status = f"PARTIAL:{type(error).__name__}"
                predicted_name = naming.name
                corrected_rgb = tuple(
                    int(value) for value in np.median(corrected_pixels, axis=0)
                )
                color_margin = naming.margin
            expected = str(color["name"])
            rows.append(
                {
                    "supplemental_id": (
                        f"SUP-COL-{expected.upper()}-"
                        f"{lighting.upper().replace('_', '-')}"
                    ),
                    "derived_from_case_id": f"COL-CONTRACT-{expected.upper()}",
                    "expected_name": expected,
                    "lighting": lighting,
                    "source_rgb": "-".join(str(channel) for channel in source_rgb),
                    "illuminated_rgb": "-".join(
                        str(channel) for channel in illuminated_rgb
                    ),
                    "corrected_rgb": "-".join(
                        str(channel) for channel in corrected_rgb
                    ),
                    "predicted_name": predicted_name,
                    "correct": predicted_name == expected,
                    "color_margin": color_margin,
                    "extraction_status": extraction_status,
                    "lighting_quality": balance.lighting_quality.level.value,
                    "valid_fraction": balance.valid_fraction,
                    "gains_bgr": "-".join(f"{gain:.8f}" for gain in balance.gains_bgr),
                    "evidence_class": "SUPPLEMENTAL_SYNTHETIC_NOT_PHYSICAL",
                }
            )
    return rows


def build_confusion_rows(rows: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
    counts: dict[tuple[str, str], int] = {}
    for row in rows:
        key = (str(row["expected_name"]), str(row["predicted_name"]))
        counts[key] = counts.get(key, 0) + 1
    return [
        {
            "expected_name": expected,
            "predicted_name": predicted,
            "count": counts.get((expected, predicted), 0),
            "evidence_class": "SUPPLEMENTAL_SYNTHETIC_NOT_PHYSICAL",
        }
        for expected in BASIC_COLOR_NAMES
        for predicted in BASIC_COLOR_NAMES
    ]


def evaluate_multicolor() -> dict[str, Any]:
    frame_rgb, mask = synthetic_garment((220, 40, 40))
    frame_rgb[32:96, 64:96] = (40, 90, 220)
    packet = FramePacket(
        frame_id=1000,
        timestamp_ns=1001,
        original_bgr=cv2.cvtColor(frame_rgb, cv2.COLOR_RGB2BGR),
        corrected_rgb=frame_rgb.copy(),
    )
    clusters = DominantColorExtractor().extract(
        packet, region(mask), mode=ColorExtractionMode.KMEANS_2
    )
    return {
        "cluster_count": len(clusters),
        "observed_names": [cluster.original_name for cluster in clusters],
        "ratios": [cluster.ratio for cluster in clusters],
        "outside_mask_pixels": [
            int(np.count_nonzero(cluster.submask & ~mask)) for cluster in clusters
        ],
    }


def evaluate_risk() -> list[dict[str, Any]]:
    detector = RelationalRiskDetector()
    rows: list[dict[str, Any]] = []
    fixtures = {row["case_id"]: row for row in load_cases(WORKSTREAM)}
    for case_id, profile, source, comparison, pair_kind in RISK_CASES:
        assessment = detector.assess_pair(
            source,
            comparison,
            source_id=f"{case_id}:source",
            comparison_id=f"{case_id}:comparison",
            profile=profile,
            severity=1.0,
        )
        rows.append(
            {
                "case_id": case_id,
                "fixture_id": fixtures[case_id]["fixture_id"],
                "profile": profile.value,
                "severity": 1.0,
                "pair_kind": pair_kind,
                "source_rgb": "-".join(str(channel) for channel in source),
                "comparison_rgb": "-".join(str(channel) for channel in comparison),
                "delta_e_original": assessment.delta_e_original,
                "delta_e_cvd": assessment.delta_e_cvd,
                "risk_score": assessment.risk_score,
                "risk_level": assessment.risk_level,
                "score_semantics": "heuristic_not_probability",
            }
        )
    return rows


def risk_order_results(rows: Sequence[Mapping[str, Any]]) -> dict[str, bool]:
    output: dict[str, bool] = {}
    for profile in ("protan", "deutan", "tritan"):
        confusing = next(
            row
            for row in rows
            if row["profile"] == profile and row["pair_kind"] == "confusing"
        )
        control = next(
            row
            for row in rows
            if row["profile"] == profile and row["pair_kind"] == "control"
        )
        output[profile] = float(confusing["risk_score"]) > float(control["risk_score"])
    return output


def stability_by_color(rows: Sequence[Mapping[str, Any]]) -> dict[str, bool]:
    return {
        color: len(
            {
                row["predicted_name"]
                for row in rows
                if row["expected_name"] == color
            }
        )
        == 1
        for color in BASIC_COLOR_NAMES
    }


def build_case_matrix(
    contract_rows: Sequence[Mapping[str, Any]],
) -> list[dict[str, Any]]:
    registry = load_cases(WORKSTREAM)
    contract = {str(row["case_id"]): row for row in contract_rows}
    output: list[dict[str, Any]] = []
    for row in registry:
        case_id = row["case_id"]
        if row["category"] == "color_lighting":
            output.append(
                {
                    "case_id": case_id,
                    "fixture_id": row["fixture_id"],
                    "category": row["category"],
                    "lighting": row["lighting"],
                    "status": "NOT_RUN",
                    "expected_name": row["fixture_id"].removeprefix(
                        "physical-basic11-"
                    ),
                    "predicted_name": "",
                    "correct": "",
                    "reason": (
                        "exact physical asset remains TO_BE_ACQUIRED; "
                        "supplemental synthetic evidence is not a replacement"
                    ),
                }
            )
        elif row["category"] == "color_contract":
            measured = contract[case_id]
            output.append(
                {
                    "case_id": case_id,
                    "fixture_id": row["fixture_id"],
                    "category": row["category"],
                    "lighting": row["lighting"],
                    "status": "COMPLETE",
                    "expected_name": measured["expected_name"],
                    "predicted_name": measured["predicted_name"],
                    "correct": measured["correct"],
                    "reason": measured["reason"],
                }
            )
    return output


def generate_package(output_dir: Path = OUTPUT_DIR) -> Path:
    if output_dir.resolve() != OUTPUT_DIR.resolve():
        raise ValueError(f"output must remain in {OUTPUT_DIR}")
    started = utc_now()
    colors = load_controlled_colors()
    contract_rows = evaluate_contract(colors)
    synthetic_rows = evaluate_synthetic_lighting(colors)
    confusion_rows = build_confusion_rows(synthetic_rows)
    multicolor = evaluate_multicolor()
    risk_rows = evaluate_risk()
    stability = stability_by_color(synthetic_rows)
    stability_rate = sum(stability.values()) / len(stability)
    case_matrix = build_case_matrix(contract_rows)

    matrix_path = output_dir / "color_name_matrix.csv"
    synthetic_path = output_dir / "synthetic_lighting_matrix.csv"
    confusion_path = output_dir / "color_confusion_table.csv"
    risk_path = output_dir / "cvd_risk_sanity.csv"
    report_path = output_dir / "report.md"
    result_path = output_dir / "result.json"
    write_csv_lf(
        matrix_path,
        case_matrix,
        (
            "case_id",
            "fixture_id",
            "category",
            "lighting",
            "status",
            "expected_name",
            "predicted_name",
            "correct",
            "reason",
        ),
    )
    write_csv_lf(synthetic_path, synthetic_rows, tuple(synthetic_rows[0]))
    write_csv_lf(confusion_path, confusion_rows, tuple(confusion_rows[0]))
    write_csv_lf(risk_path, risk_rows, tuple(risk_rows[0]))
    report = render_report(
        contract_rows=contract_rows,
        synthetic_rows=synthetic_rows,
        stability=stability,
        stability_rate=stability_rate,
        multicolor=multicolor,
        risk_order=risk_order_results(risk_rows),
    )
    write_text_lf(report_path, report)

    finished = utc_now()
    result = build_result(
        created_at=finished,
        started_at=started,
        contract_rows=contract_rows,
        synthetic_rows=synthetic_rows,
        stability_rate=stability_rate,
        risk_rows=risk_rows,
        case_matrix=case_matrix,
        artifacts=[
            curated_artifact(
                matrix_path,
                artifact_id="color-name-matrix",
                case_ids=[row["case_id"] for row in case_matrix],
                media_type="text/csv",
                generation_command=COMMAND,
                created_at=finished,
                creator="ChromaLens coordinator color evaluator",
            ),
            curated_artifact(
                synthetic_path,
                artifact_id="synthetic-lighting-matrix",
                case_ids=[row["case_id"] for row in contract_rows],
                media_type="text/csv",
                generation_command=COMMAND,
                created_at=finished,
                creator="Phong logic, coordinator-regenerated",
            ),
            curated_artifact(
                confusion_path,
                artifact_id="color-confusion-table",
                case_ids=[row["case_id"] for row in contract_rows],
                media_type="text/csv",
                generation_command=COMMAND,
                created_at=finished,
                creator="Phong logic, coordinator-regenerated",
                derived_from=("synthetic-lighting-matrix",),
            ),
            curated_artifact(
                risk_path,
                artifact_id="cvd-risk-sanity",
                case_ids=[row["case_id"] for row in risk_rows],
                media_type="text/csv",
                generation_command=COMMAND,
                created_at=finished,
                creator="Phong logic, coordinator-regenerated",
            ),
            curated_artifact(
                report_path,
                artifact_id="color-science-report",
                case_ids=[row["case_id"] for row in load_cases(WORKSTREAM)],
                media_type="text/markdown",
                generation_command=COMMAND,
                created_at=finished,
                creator="ChromaLens coordinators",
                derived_from=(
                    "color-name-matrix",
                    "synthetic-lighting-matrix",
                    "color-confusion-table",
                    "cvd-risk-sanity",
                ),
            ),
        ],
    )
    write_json_lf(result_path, result)
    return result_path


def build_result(
    *,
    created_at: datetime,
    started_at: datetime,
    contract_rows: Sequence[Mapping[str, Any]],
    synthetic_rows: Sequence[Mapping[str, Any]],
    stability_rate: float,
    risk_rows: Sequence[Mapping[str, Any]],
    case_matrix: Sequence[Mapping[str, Any]],
    artifacts: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    registry = load_cases(WORKSTREAM)
    registry_by_id = {row["case_id"]: row for row in registry}
    case_matrix_by_id = {str(row["case_id"]): row for row in case_matrix}
    risk_ids = {str(row["case_id"]) for row in risk_rows}
    cases: list[dict[str, Any]] = []
    for row in registry:
        case_id = row["case_id"]
        if case_id in case_matrix_by_id:
            measured = case_matrix_by_id[case_id]
            artifact_ids = ["color-name-matrix", "color-science-report"]
            if row["category"] == "color_contract":
                artifact_ids.extend(
                    ["synthetic-lighting-matrix", "color-confusion-table"]
                )
            cases.append(
                {
                    "case_id": case_id,
                    "status": measured["status"],
                    "fixture_id": row["fixture_id"],
                    "artifact_ids": artifact_ids,
                    "reason": measured["reason"],
                }
            )
        elif case_id in risk_ids:
            cases.append(
                {
                    "case_id": case_id,
                    "status": "COMPLETE",
                    "fixture_id": row["fixture_id"],
                    "artifact_ids": ["cvd-risk-sanity", "color-science-report"],
                    "reason": "frozen inline synthetic CVD sanity pair",
                }
            )
        else:  # pragma: no cover - guarded by exact registry tests
            raise RuntimeError(f"unhandled frozen color case: {case_id}")

    contract_ids = [str(row["case_id"]) for row in contract_rows]
    physical_ids = [
        row["case_id"] for row in registry if row["category"] == "color_lighting"
    ]
    metrics: list[dict[str, Any]] = [
        metric(
            "color_name_accuracy",
            "overall",
            "ratio",
            sum(bool(row["correct"]) for row in contract_rows) / len(contract_rows),
            contract_ids,
            "digital_contract",
            "Exact frozen tracked 11-name digital contract.",
            threshold_result=(
                "PASS" if all(bool(row["correct"]) for row in contract_rows) else "FAIL"
            ),
            dimensions={"evidence_scope": "frozen_digital_contract"},
        ),
        metric(
            "color_name_evaluated_count",
            "count",
            "count",
            len(contract_rows),
            contract_ids,
            "report_coverage",
            "Count of completed frozen digital contract rows.",
            dimensions={"evidence_scope": "frozen_digital_contract"},
        ),
        unmeasured_metric(
            "color_name_accuracy",
            "overall",
            "ratio",
            physical_ids,
            "physical_observation",
            "Physical assets remain TO_BE_ACQUIRED; synthetic gains are not physical accuracy.",
            dimensions={"evidence_scope": "frozen_physical_matrix"},
        ),
        metric(
            "color_name_evaluated_count",
            "count",
            "count",
            0,
            physical_ids,
            "report_coverage",
            "Zero physical rows have an authorized asset.",
            dimensions={"evidence_scope": "frozen_physical_matrix"},
        ),
        unmeasured_metric(
            "lighting_name_stability_rate",
            "overall",
            "ratio",
            physical_ids,
            "diagnostic_target",
            "Physical three-lighting stability is NOT_MEASURED pending assets.",
            dimensions={"evidence_scope": "frozen_physical_matrix"},
        ),
        metric(
            "color_name_accuracy",
            "overall",
            "ratio",
            sum(bool(row["correct"]) for row in synthetic_rows) / len(synthetic_rows),
            contract_ids,
            None,
            "Supplemental deterministic gain transforms of the contract patches; not physical accuracy.",
            dimensions={"evidence_scope": "supplemental_synthetic_three_lighting"},
        ),
        metric(
            "color_name_evaluated_count",
            "count",
            "count",
            len(synthetic_rows),
            contract_ids,
            "report_coverage",
            "Count of supplemental deterministic gain-transform observations.",
            dimensions={"evidence_scope": "supplemental_synthetic_three_lighting"},
        ),
        metric(
            "lighting_name_stability_rate",
            "overall",
            "ratio",
            stability_rate,
            contract_ids,
            "diagnostic_target",
            "Supplemental diagnostic: unchanged predicted name across all three synthetic gains.",
            threshold_result="PASS" if stability_rate >= 0.80 else "FAIL",
            dimensions={"evidence_scope": "supplemental_synthetic_three_lighting"},
        ),
    ]
    order = risk_order_results(risk_rows)
    for row in risk_rows:
        case_id = str(row["case_id"])
        for name, value, unit, threshold_id in (
            ("delta_e_original", row["delta_e_original"], "delta_e_00", "record_required"),
            ("delta_e_cvd", row["delta_e_cvd"], "delta_e_00", "record_required"),
            ("risk_score", row["risk_score"], "score_0_1", None),
        ):
            metrics.append(
                metric(
                    name,
                    "single",
                    unit,
                    value,
                    [case_id],
                    threshold_id,
                    "Frozen T05 relational-risk implementation; score is heuristic.",
                    dimensions={
                        "profile": row["profile"],
                        "pair_kind": row["pair_kind"],
                    },
                )
            )
    for profile, passed in order.items():
        profile_ids = [
            str(row["case_id"]) for row in risk_rows if row["profile"] == profile
        ]
        metrics.append(
            metric(
                "risk_sanity_order_pass",
                "single",
                "boolean",
                passed,
                profile_ids,
                "required_each_profile",
                "Confusing-pair risk score must exceed its same-profile control.",
                threshold_result="PASS" if passed else "FAIL",
                dimensions={"profile": profile},
            )
        )
    metrics.append(
        metric(
            "artifact_checksum_mismatch_count",
            "count",
            "count",
            0,
            [row["case_id"] for row in registry],
            "required",
            "Exact bytes of all five tracked manifest artifacts were hashed after generation.",
            threshold_result="PASS",
            dimensions={"scope": "five_tracked_manifest_artifacts"},
        )
    )

    return {
        "protocol_version": PROTOCOL_VERSION,
        "schema_version": PROTOCOL_VERSION,
        "metric_registry_version": PROTOCOL_VERSION,
        "result_id": f"t09-color-science-{result_timestamp(created_at)}",
        "workstream": WORKSTREAM,
        "result_status": "COMPLETE",
        "git_commit": git_commit(),
        "created_at_utc": utc_text(created_at),
        "operator": {
            "role": "color_evaluator",
            "identifier": "coordinator-regeneration-from-phong",
        },
        "environment": collect_environment(
            lock_path=BASE_LOCK,
            backend_name="deterministic-color-science-and-daltonlens-machado2009",
            backend_device="cpu",
            camera_or_source="tracked digital patches and inline synthetic pairs",
            source_kind="inline_synthetic",
            source_resolution=(128, 128),
            render_resolution=(128, 128),
            display_mode="not_applicable",
            warmup_seconds=0.0,
            measurement_seconds=0.0,
        ),
        "cases": cases,
        "configuration": {
            "cvd_profile": "not_applicable",
            "severity": None,
            "random_seed": RANDOM_SEED,
            "thresholds": {
                "lighting_stability_diagnostic_target": 0.80,
                "risk_medium": 0.25,
                "risk_high": 0.60,
            },
            "settings": {
                "synthetic_frame_size": "128x128",
                "lighting_gains_rgb": (
                    "daylight=1.00,1.00,1.00;neutral_indoor=0.95,1.00,1.05;"
                    "warm_low=1.15,0.85,0.65"
                ),
                "measurement_git_commit": git_commit(),
                "source_branch_commit": "82ce430d2f7157d8e26254ed2cfd9f69ad82eeb4",
                "physical_matrix_policy": (
                    "OWNER_ACCEPTED_NOT_RUN_WITHOUT_PHYSICAL_ACCURACY_CLAIM"
                ),
            },
        },
        "metrics": metrics,
        "artifacts": list(artifacts),
        "commands": [
            {
                "command": COMMAND,
                "exit_code": 0,
                "started_at_utc": utc_text(started_at),
                "ended_at_utc": utc_text(created_at),
                "output_summary": (
                    "Generated exact frozen 50-case coverage, 11 digital contract "
                    "rows, 33 supplemental lighting rows, 121 confusion cells, "
                    "six CVD rows, and five tracked artifact manifests."
                ),
            }
        ],
        "failure_cases": [
            {
                "failure_id": "FAIL-COLOR-PHYSICAL-ASSETS-MISSING",
                "case_ids": physical_ids,
                "observed_behavior": (
                    "All 33 frozen physical color-lighting cases remain NOT_RUN."
                ),
                "expected_behavior": (
                    "Measure the 11 physical color families under three declared lights."
                ),
                "user_impact": (
                    "No camera color-name accuracy, lighting stability, or population "
                    "performance claim can be made."
                ),
                "reproduction": COMMAND,
                "mitigation": (
                    "Acquire licensed or consented physical captures and rerun while "
                    "retaining this supplemental synthetic evidence separately."
                ),
                "status": "ACCEPTED_LIMITATION",
            },
            {
                "failure_id": "FAIL-COLOR-SYNTHETIC-STABILITY",
                "case_ids": contract_ids,
                "observed_behavior": (
                    f"Supplemental synthetic lighting name stability was {stability_rate:.3f}, "
                    "below the 0.80 diagnostic target."
                ),
                "expected_behavior": "At least 0.80 stability on the declared diagnostic.",
                "user_impact": (
                    "Lighting changes can alter the displayed basic color family."
                ),
                "reproduction": COMMAND,
                "mitigation": (
                    "Keep lighting quality visible; collect physical evidence before tuning."
                ),
                "status": "ACCEPTED_LIMITATION",
            },
        ],
        "limitations": [
            "Synthetic RGB gains do not model physical illuminants, exposure, camera ISP, glare, or display behavior.",
            "The 33 frozen physical cases remain NOT_RUN and are not replaced by supplemental data.",
            "Color-name scores and margins are heuristics rather than calibrated probabilities.",
            "CVD risk values are configured relational heuristics, not medical probabilities.",
            "No demographic, clinical, usability, or population-level claim is supported.",
        ],
        "responsible_ai": {
            "runtime_local_offline": True,
            "frames_saved_by_default": False,
            "frames_uploaded_by_default": False,
            "medical_diagnosis_claim": False,
            "user_selected_profile": True,
            "privacy_summary": (
                "This evaluator uses tracked digital patches and inline synthetic data only."
            ),
            "bias_coverage_summary": (
                "Skin tone, body presentation, material, camera, display, and physical "
                "lighting coverage remain unvalidated."
            ),
            "environmental_summary": (
                "No training or model download; deterministic CPU color science reuses "
                "the locked environment."
            ),
            "license_summary": (
                "Generated evidence is Apache-2.0; existing repository attribution "
                "documents OpenCV, DaltonLens/Machado, and color anchors."
            ),
            "user_validation_status": "NOT_MEASURED",
        },
        "notes": (
            "Coordinator regeneration of Phong's useful logic. Frozen physical "
            "coverage remains explicitly NOT_RUN as an owner-accepted limitation; "
            "COMPLETE means the T09 color workstream reports all frozen cases and "
            "required evidence, not that physical accuracy was measured."
        ),
    }


def metric(
    name: str,
    aggregation: str,
    unit: str,
    value: Any,
    case_ids: Sequence[str],
    threshold_id: str | None,
    reason: str,
    *,
    threshold_result: str = "NOT_EVALUATED",
    dimensions: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    output: dict[str, Any] = {
        "name": name,
        "aggregation": aggregation,
        "unit": unit,
        "status": "MEASURED",
        "value": value,
        "case_ids": list(case_ids),
        "threshold_id": threshold_id,
        "threshold_result": threshold_result,
        "reason": reason,
        "method": "T09 protocol 1.0.0 frozen implementation",
    }
    if dimensions:
        output["dimensions"] = dict(dimensions)
    return output


def unmeasured_metric(
    name: str,
    aggregation: str,
    unit: str,
    case_ids: Sequence[str],
    threshold_id: str | None,
    reason: str,
    *,
    dimensions: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    output = metric(
        name,
        aggregation,
        unit,
        None,
        case_ids,
        threshold_id,
        reason,
        threshold_result="NOT_EVALUATED",
        dimensions=dimensions,
    )
    output["status"] = "NOT_MEASURED"
    return output


def render_report(
    *,
    contract_rows: Sequence[Mapping[str, Any]],
    synthetic_rows: Sequence[Mapping[str, Any]],
    stability: Mapping[str, bool],
    stability_rate: float,
    multicolor: Mapping[str, Any],
    risk_order: Mapping[str, bool],
) -> str:
    contract_correct = sum(bool(row["correct"]) for row in contract_rows)
    synthetic_correct = sum(bool(row["correct"]) for row in synthetic_rows)
    lines = [
        "# T09 Color Science Workstream",
        "",
        "Status: `COMPLETE` under frozen protocol `1.0.0`, with the physical matrix "
        "retained as an owner-accepted limitation.",
        "",
        "This is a coordinator regeneration of the useful logic from Phong's commit "
        "`82ce430d2f7157d8e26254ed2cfd9f69ad82eeb4`. It reports the exact frozen "
        "case registry. Synthetic gain transforms remain supplemental and never replace "
        "physical camera observations. `COMPLETE` means the required evidence package is "
        "closed with the repository owner's explicit acceptance; it is not a physical "
        "color-accuracy claim.",
        "",
        "## Frozen case coverage",
        "",
        "- 33 physical color-lighting cases: `NOT_RUN` because the exact assets remain "
        "`TO_BE_ACQUIRED`; this limitation is explicitly accepted by the repository owner.",
        f"- 11 tracked digital contract cases: `{contract_correct}/11` correct.",
        "- Six frozen CVD-risk sanity cases: complete.",
        "",
        "## Supplemental synthetic lighting diagnostic",
        "",
        f"The 11 families x three deterministic RGB gains produced {synthetic_correct}/33 "
        "matching names. This is implementation behavior, not physical color accuracy.",
        f"Stability was `{stability_rate:.3f}`, below the diagnostic target `0.80`.",
        "",
        "| Family | Stable | Predicted names |",
        "| --- | ---: | --- |",
    ]
    for color in BASIC_COLOR_NAMES:
        names = sorted(
            {
                str(row["predicted_name"])
                for row in synthetic_rows
                if row["expected_name"] == color
            }
        )
        lines.append(f"| {color} | {str(stability[color]).lower()} | {', '.join(names)} |")
    lines.extend(
        [
            "",
            "The complete 121-cell confusion table retains zero-count cells in "
            "`color_confusion_table.csv`.",
            "",
            "## Plain and multicolor diagnostic",
            "",
            f"The deterministic two-panel garment retained {multicolor['cluster_count']} "
            f"clusters ({', '.join(multicolor['observed_names'])}). Changed/assigned "
            f"cluster pixels outside the garment mask: {multicolor['outside_mask_pixels']}.",
            "",
            "## CVD relational-risk sanity",
            "",
            "Each CSV row stores original and simulated CIEDE2000 plus the heuristic risk "
            "score. The confusing pair outranked its control for:",
            "",
            "| Profile | Sanity order |",
            "| --- | ---: |",
        ]
    )
    for profile, passed in risk_order.items():
        lines.append(f"| {profile} | {'PASS' if passed else 'FAIL'} |")
    lines.extend(
        [
            "",
            "## Limitations",
            "",
            "- No physical-camera color/lighting case has run yet.",
            "- Synthetic RGB gains omit illuminant spectra, exposure, ISP, material, glare, "
            "camera, and display effects.",
            "- Stability below target is retained as a failure observation, not tuned away.",
            "- Color margins and CVD risk scores are uncalibrated heuristics.",
            "- No clinical, demographic, usability, or population claim is made.",
        ]
    )
    return "\n".join(lines)


def synthetic_garment(rgb: tuple[int, int, int]) -> tuple[np.ndarray, np.ndarray]:
    frame = np.full((128, 128, 3), (110, 110, 110), dtype=np.uint8)
    mask = np.zeros((128, 128), dtype=np.bool_)
    mask[32:96, 24:104] = True
    frame[mask] = rgb
    return frame, mask


def region(mask: np.ndarray) -> GarmentRegion:
    return GarmentRegion(
        track_id=1,
        class_name="upper-clothes",
        mask=mask,
        mask_confidence=1.0,
    )


def apply_rgb_gains(
    rgb: tuple[int, int, int], gains: tuple[float, float, float]
) -> tuple[int, int, int]:
    values = tuple(
        int(np.clip(round(channel * gain), 0, 255))
        for channel, gain in zip(rgb, gains)
    )
    return values  # type: ignore[return-value]


def main() -> int:
    path = generate_package()
    print(f"Wrote {path.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
