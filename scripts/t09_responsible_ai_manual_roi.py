"""Time the frozen five-image manual ROI baseline without saving image/ROI data."""

from __future__ import annotations

import argparse
from dataclasses import dataclass
from pathlib import Path
from time import perf_counter
from typing import Any, Callable, Sequence

import cv2
import numpy as np

from scripts.t09_evaluation_common import (
    PROTOCOL_VERSION,
    ROOT,
    collect_environment,
    git_commit,
    result_timestamp,
    sha256_file,
    utc_now,
    utc_text,
    write_json_lf,
)


CASE_ID = "BASELINE-MANUAL-ROI"
FIXTURE_ID = "manual-roi-public-fixtures"
OUTPUT_DIR = ROOT / "artifacts/t09/performance_responsible_ai"
LOCK_PATH = ROOT / "requirements/py310-win64.lock"
FIXTURE_DIR = ROOT / "tests/samples/t02"
FIXTURES = {
    "astronaut.png": "88431cd9653ccd539741b555fb0a46b61558b301d4110412b5bc28b5e3ea6cb5",
    "cc0_woman.jpg": "9659315a44a6d3eadf8814b314193aacc78033097aa4dee4da0fadbfcaec025d",
    "loc_lincoln.jpg": "a305c6630a3ac49dc9fe2ebe9f218ba7bb91df715c2dd860d038a585e030c15f",
    "loc_man.jpg": "50eb295eb7cf909350c67c74b3b306a1e7018261505c866f88f77b035ada0d94",
    "nasa_shepard.jpg": "3f8ef484565605683cfe5b4aec510c165afafbfe00477899faecfb521a097488",
}


class ManualRoiError(RuntimeError):
    """Raised when the manual baseline cannot produce valid timing evidence."""


@dataclass(frozen=True, slots=True)
class Trial:
    fixture_name: str
    fixture_sha256: str
    completion_seconds: float


Selector = Callable[[Path], bool]
Clock = Callable[[], float]


def verify_fixtures() -> tuple[Path, ...]:
    paths = tuple(FIXTURE_DIR / name for name in FIXTURES)
    actual_names = {path.name for path in FIXTURE_DIR.iterdir() if path.suffix.lower() in {".png", ".jpg", ".jpeg"}}
    if actual_names != set(FIXTURES):
        raise ManualRoiError(
            f"manual ROI fixture set changed: {sorted(actual_names)}"
        )
    for path in paths:
        if sha256_file(path) != FIXTURES[path.name]:
            raise ManualRoiError(f"fixture checksum mismatch: {path.name}")
    return paths


def run_trials(
    paths: Sequence[Path],
    *,
    selector: Selector,
    clock: Clock = perf_counter,
) -> tuple[Trial, ...]:
    """Measure only selection duration; never return or persist ROI geometry."""

    trials: list[Trial] = []
    for path in paths:
        started = float(clock())
        selected = selector(path)
        ended = float(clock())
        duration = ended - started
        if not selected:
            raise ManualRoiError(f"selection cancelled or empty for {path.name}")
        if not np.isfinite(duration) or duration <= 0.0:
            raise ManualRoiError(f"invalid completion time for {path.name}: {duration}")
        trials.append(
            Trial(
                fixture_name=path.name,
                fixture_sha256=sha256_file(path),
                completion_seconds=duration,
            )
        )
    return tuple(trials)


def select_roi(path: Path) -> bool:
    image = cv2.imread(str(path), cv2.IMREAD_COLOR)
    if image is None:
        raise ManualRoiError(f"OpenCV cannot read {path}")
    window = "T09 Manual ROI - select garment, Enter confirms, C cancels"
    try:
        roi = cv2.selectROI(window, image, showCrosshair=True, fromCenter=False)
    finally:
        cv2.destroyWindow(window)
    _x, _y, width, height = (int(value) for value in roi)
    return width > 0 and height > 0


def build_payload(trials: Sequence[Trial], *, started_at: Any, ended_at: Any) -> dict[str, Any]:
    if len(trials) != len(FIXTURES):
        raise ManualRoiError("all five frozen fixtures are required")
    durations = np.asarray([trial.completion_seconds for trial in trials], dtype=np.float64)
    median = float(np.median(durations))
    metrics = [
        {
            "name": "manual_baseline_completion_seconds",
            "aggregation": "single",
            "unit": "second",
            "status": "MEASURED",
            "value": trial.completion_seconds,
            "case_ids": [CASE_ID],
            "threshold_id": "observation_only",
            "threshold_result": "NOT_EVALUATED",
            "reason": f"Manual garment ROI selection timing for {trial.fixture_name}.",
            "method": "Wall clock around cv2.selectROI; ROI geometry and image content are not saved.",
            "dimensions": {"fixture_name": trial.fixture_name, "fixture_sha256": trial.fixture_sha256},
        }
        for trial in trials
    ]
    metrics.append(
        {
            "name": "manual_baseline_completion_seconds",
            "aggregation": "median",
            "unit": "second",
            "status": "MEASURED",
            "value": median,
            "case_ids": [CASE_ID],
            "threshold_id": "observation_only",
            "threshold_result": "NOT_EVALUATED",
            "reason": "Median across all five frozen public fixtures.",
            "method": "NumPy linear median over five positive completion times.",
            "dimensions": {"trial_count": len(trials)},
        }
    )
    return {
        "protocol_version": PROTOCOL_VERSION,
        "schema_version": PROTOCOL_VERSION,
        "metric_registry_version": PROTOCOL_VERSION,
        "result_id": f"t09-manual-roi-{result_timestamp(ended_at)}",
        "workstream": "performance_responsible_ai",
        "result_status": "COMPLETE",
        "git_commit": git_commit(),
        "created_at_utc": utc_text(ended_at),
        "operator": {"role": "performance_evaluator", "identifier": "local-operator"},
        "environment": collect_environment(
            lock_path=LOCK_PATH,
            backend_name="manual-human-roi-baseline",
            backend_device="human",
            camera_or_source="five tracked public T02 fixtures",
            source_kind="manual_baseline",
            source_resolution=(1024, 768),
            render_resolution=(1024, 768),
            display_mode="gui",
            warmup_seconds=0.0,
            measurement_seconds=float(np.sum(durations)),
        ),
        "cases": [{"case_id": CASE_ID, "status": "COMPLETE", "fixture_id": FIXTURE_ID, "artifact_ids": [], "reason": "Five timing-only manual ROI trials completed."}],
        "configuration": {"cvd_profile": "not_applicable", "severity": None, "random_seed": None, "thresholds": {}, "settings": {"trial_count": len(trials), "roi_geometry_saved": False, "image_content_saved": False}},
        "metrics": metrics,
        "artifacts": [],
        "commands": [{"command": "conda run --name lens python scripts/t09_responsible_ai_manual_roi.py", "exit_code": 0, "started_at_utc": utc_text(started_at), "ended_at_utc": utc_text(ended_at), "output_summary": f"Five timing-only trials; median {median:.3f} s."}],
        "failure_cases": [],
        "limitations": ["Manual ROI is not automatic garment localization.", "Timing depends on operator familiarity and input display order.", "No ROI geometry, crop, screenshot, pixel array, or base64 content is stored."],
        "responsible_ai": {"runtime_local_offline": True, "frames_saved_by_default": False, "frames_uploaded_by_default": False, "medical_diagnosis_claim": False, "user_selected_profile": True, "privacy_summary": "Only fixture names, hashes, and timing are stored; no new personal media or ROI geometry is persisted.", "bias_coverage_summary": "Five public images are a workflow baseline, not demographic validation.", "environmental_summary": "No model inference or training is used for the manual baseline.", "license_summary": "Fixture provenance and rights are documented in tests/samples/t02/README.md.", "user_validation_status": "NOT_MEASURED"},
        "notes": "Raw timing-only artifact; tracked coordinator result retains the historical median separately.",
    }


def build_parser() -> argparse.ArgumentParser:
    return argparse.ArgumentParser(description=__doc__)


def main(argv: Sequence[str] | None = None) -> int:
    build_parser().parse_args(argv)
    paths = verify_fixtures()
    started = utc_now()
    trials = run_trials(paths, selector=select_roi)
    ended = utc_now()
    payload = build_payload(trials, started_at=started, ended_at=ended)
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    output = OUTPUT_DIR / f"{payload['result_id']}.json"
    write_json_lf(output, payload)
    print(f"Wrote ignored timing-only result {output.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

