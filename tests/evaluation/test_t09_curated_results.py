from __future__ import annotations

import json
from pathlib import Path
import subprocess

import pytest

from scripts import t09_result_validation as validator


ROOT = Path(__file__).resolve().parents[2]
COLOR_RESULT = ROOT / "evaluation/results/curated/color_science/result.json"
PERFORMANCE_RESULT = (
    ROOT
    / "evaluation/results/curated/performance_responsible_ai/result.json"
)
SEGMENTATION_RESULT = ROOT / "evaluation/results/curated/segmentation/result.json"
END_TO_END_RESULT = ROOT / "evaluation/results/curated/end_to_end/result.json"


def payload(path: Path) -> dict[str, object]:
    return json.loads(path.read_text(encoding="utf-8"))


def test_curated_color_result_passes_schema_registry_coverage_and_checksums() -> None:
    summary = validator.validate_result_file(
        COLOR_RESULT, expected_workstream="color_science"
    )
    result = payload(COLOR_RESULT)
    physical = [case for case in result["cases"] if case["case_id"].startswith("COL-") and not case["case_id"].startswith("COL-CONTRACT-")]
    contract = [case for case in result["cases"] if case["case_id"].startswith("COL-CONTRACT-")]

    assert summary.case_count == 50
    assert summary.tracked_artifact_count == 5
    assert summary.missing_untracked_artifact_count == 0
    assert len(physical) == 33 and all(case["status"] == "NOT_RUN" for case in physical)
    assert len(contract) == 11 and all(case["status"] == "COMPLETE" for case in contract)


def test_curated_performance_result_passes_with_fresh_ignored_raw_files() -> None:
    summary = validator.validate_result_file(
        PERFORMANCE_RESULT, expected_workstream="performance_responsible_ai"
    )
    result = payload(PERFORMANCE_RESULT)
    sensor = [metric for metric in result["metrics"] if metric["name"] == "sensor_to_photon_ms"]

    assert summary.case_count == 12
    assert summary.tracked_artifact_count == 2
    assert summary.verified_untracked_artifact_count == 5
    assert summary.missing_untracked_artifact_count == 0
    assert all(metric["status"] == "NOT_MEASURED" for metric in sensor)
    assert result["result_status"] == "COMPLETE"
    assert result["environment"]["host_role"] == "development"
    assert result["environment"]["declared_demo_hardware"] is False


def test_curated_segmentation_result_covers_twenty_real_backend_cases() -> None:
    summary = validator.validate_result_file(
        SEGMENTATION_RESULT, expected_workstream="segmentation"
    )
    result = payload(SEGMENTATION_RESULT)
    ratings = [
        metric
        for metric in result["metrics"]
        if metric["name"] == "segmentation_adequacy_rating"
    ]
    ious = [
        metric
        for metric in result["metrics"]
        if metric["name"] == "segmentation_iou"
    ]

    assert summary.case_count == 20
    assert summary.tracked_artifact_count == 2
    assert (
        summary.verified_untracked_artifact_count
        + summary.missing_untracked_artifact_count
        == 39
    )
    assert len(ratings) == 20
    assert sum(metric["value"] >= 2 for metric in ratings) == 9
    assert len(ious) == 3
    assert result["environment"]["backend_name"] == "mediapipe-selfie-torso"


def test_curated_end_to_end_result_covers_invariants_and_real_video() -> None:
    summary = validator.validate_result_file(
        END_TO_END_RESULT, expected_workstream="end_to_end"
    )
    result = payload(END_TO_END_RESULT)
    invariants = [
        metric
        for metric in result["metrics"]
        if metric["name"]
        in {
            "analysis_frame_id_mismatch_count",
            "outside_recolor_mask_changed_pixel_count",
        }
    ]
    moving = next(
        case for case in result["cases"] if case["case_id"] == "E2E-MOVING-TEMPORAL"
    )

    assert summary.case_count == 10
    assert summary.tracked_artifact_count == 2
    assert (
        summary.verified_untracked_artifact_count
        + summary.missing_untracked_artifact_count
        == 20
    )
    assert all(metric["value"] == 0 for metric in invariants)
    assert all(metric["threshold_result"] == "PASS" for metric in invariants)
    assert moving["status"] == "COMPLETE"
    assert result["environment"]["declared_demo_hardware"] is False


@pytest.mark.parametrize(
    "path",
    [COLOR_RESULT, PERFORMANCE_RESULT, SEGMENTATION_RESULT, END_TO_END_RESULT],
)
def test_result_names_the_existing_code_commit_that_generated_it(path: Path) -> None:
    commit = str(payload(path)["git_commit"])

    completed = subprocess.run(
        ["git", "cat-file", "-e", f"{commit}^{{commit}}"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    assert completed.returncode == 0, completed.stderr


def test_checksum_verifier_detects_changed_exact_bytes(tmp_path: Path) -> None:
    artifact_path = tmp_path / "artifact.csv"
    artifact_path.write_bytes(b"a,b\n1,2\n")
    manifest = {
        "artifact_id": "temporary-artifact",
        "byte_size": artifact_path.stat().st_size,
        "sha256": validator.sha256_file(artifact_path),
    }
    validator._verify_artifact_bytes(artifact_path, manifest, required=True)

    artifact_path.write_bytes(b"a,b\n1,3\n")
    with pytest.raises(validator.ResultValidationError, match="artifact mismatch"):
        validator._verify_artifact_bytes(artifact_path, manifest, required=True)
