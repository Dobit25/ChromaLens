"""Validate protocol-2.0.0 results and exact available artifact bytes."""

from __future__ import annotations

import argparse
import csv
from dataclasses import dataclass
import json
from pathlib import Path
from typing import Any, Sequence

try:
    from scripts.t09_result_validation import (
        ResultValidationError,
        _validate_schema,
        sha256_file,
    )
except ModuleNotFoundError:  # Direct `python scripts/...` execution.
    from t09_result_validation import ResultValidationError, _validate_schema, sha256_file


ROOT = Path(__file__).resolve().parents[1]
SCHEMA_PATH = ROOT / "evaluation/schema/post-mvp-result.schema.json"
REGISTRY_PATH = ROOT / "evaluation/schema/post-mvp-metric-registry.json"
CASES_PATH = ROOT / "evaluation/fixtures/post-mvp-cases.csv"
DEFAULT_RESULTS = (ROOT / "evaluation/results/curated/post_mvp/gate0/result.json",)


@dataclass(frozen=True, slots=True)
class ValidationSummary:
    result_path: Path
    case_count: int
    metric_count: int
    verified_artifact_count: int
    unavailable_ignored_artifact_count: int


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _load_cases() -> dict[str, dict[str, str]]:
    with CASES_PATH.open(encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))
    case_ids = [row["case_id"] for row in rows]
    if len(case_ids) != len(set(case_ids)):
        raise ResultValidationError("post-MVP fixture registry has duplicate case IDs")
    return {row["case_id"]: row for row in rows}


def _repository_path(relative: str) -> Path:
    candidate = (ROOT / Path(relative)).resolve()
    if not candidate.is_relative_to(ROOT.resolve()):
        raise ResultValidationError(f"artifact path escapes repository: {relative}")
    return candidate


def _validate_value(value: object, value_type: str, location: str) -> None:
    if value_type == "number" and (not isinstance(value, (int, float)) or isinstance(value, bool)):
        raise ResultValidationError(f"{location}: expected number")
    if value_type == "integer" and (not isinstance(value, int) or isinstance(value, bool)):
        raise ResultValidationError(f"{location}: expected integer")
    if value_type == "boolean" and not isinstance(value, bool):
        raise ResultValidationError(f"{location}: expected boolean")


def validate_result_file(
    result_path: Path,
    *,
    require_ignored_artifacts: bool = False,
) -> ValidationSummary:
    payload = _load_json(result_path)
    schema = _load_json(SCHEMA_PATH)
    registry = _load_json(REGISTRY_PATH)
    _validate_schema(payload, schema, schema, "$", strict_formats=True)

    cases = _load_cases()
    result_case_ids = [item["case_id"] for item in payload["cases"]]
    if len(result_case_ids) != len(set(result_case_ids)):
        raise ResultValidationError(f"{result_path}: duplicate result case IDs")
    unknown_cases = set(result_case_ids) - set(cases)
    if unknown_cases:
        raise ResultValidationError(f"{result_path}: unknown cases {sorted(unknown_cases)}")
    for item in payload["cases"]:
        frozen = cases[item["case_id"]]
        if item["fixture_id"] != frozen["fixture_id"]:
            raise ResultValidationError(
                f"{result_path}: fixture mismatch for {item['case_id']}"
            )
        if payload["task_id"] != frozen["task_id"]:
            raise ResultValidationError(
                f"{result_path}: task mismatch for {item['case_id']}"
            )

    specs = {item["name"]: item for item in registry["metrics"]}
    for index, metric in enumerate(payload["metrics"]):
        location = f"{result_path}: metrics[{index}]"
        spec = specs.get(metric["name"])
        if spec is None:
            raise ResultValidationError(f"{location}: unknown metric")
        if metric["unit"] != spec["unit"]:
            raise ResultValidationError(f"{location}: unit mismatch")
        if metric["aggregation"] not in spec["allowed_aggregations"]:
            raise ResultValidationError(f"{location}: aggregation mismatch")
        threshold_ids = {item["id"] for item in spec["thresholds"]}
        if metric["threshold_id"] is not None and metric["threshold_id"] not in threshold_ids:
            raise ResultValidationError(f"{location}: unknown threshold")
        if not set(metric["case_ids"]) <= set(result_case_ids):
            raise ResultValidationError(f"{location}: metric references absent case")
        if metric["status"] in {"MEASURED", "COMPUTED"}:
            _validate_value(metric["value"], spec["value_type"], location)
        elif metric["value"] is not None:
            raise ResultValidationError(f"{location}: unmeasured metric must be null")
        elif metric["threshold_result"] not in {"NOT_APPLICABLE", "NOT_EVALUATED"}:
            raise ResultValidationError(f"{location}: unmeasured metric cannot pass/fail")

    artifact_ids = [item["artifact_id"] for item in payload["artifacts"]]
    if len(artifact_ids) != len(set(artifact_ids)):
        raise ResultValidationError(f"{result_path}: duplicate artifact IDs")
    for case in payload["cases"]:
        if not set(case["artifact_ids"]) <= set(artifact_ids):
            raise ResultValidationError(f"{result_path}: case references unknown artifact")

    verified = 0
    unavailable = 0
    for artifact in payload["artifacts"]:
        path = _repository_path(artifact["path"])
        required = artifact["tracking"] == "tracked_curated" or require_ignored_artifacts
        if not path.is_file():
            if required:
                raise ResultValidationError(f"missing required artifact: {artifact['path']}")
            unavailable += 1
            continue
        if artifact["availability"] != "AVAILABLE":
            raise ResultValidationError(f"present artifact not marked AVAILABLE: {artifact['path']}")
        if path.stat().st_size != artifact["bytes"]:
            raise ResultValidationError(f"artifact byte-size mismatch: {artifact['path']}")
        if sha256_file(path) != artifact["sha256"]:
            raise ResultValidationError(f"artifact SHA-256 mismatch: {artifact['path']}")
        verified += 1

    return ValidationSummary(
        result_path=result_path,
        case_count=len(result_case_ids),
        metric_count=len(payload["metrics"]),
        verified_artifact_count=verified,
        unavailable_ignored_artifact_count=unavailable,
    )


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("result", type=Path, nargs="*", default=list(DEFAULT_RESULTS))
    parser.add_argument("--require-ignored-artifacts", action="store_true")
    args = parser.parse_args(argv)
    for path in args.result:
        summary = validate_result_file(
            path.resolve(), require_ignored_artifacts=args.require_ignored_artifacts
        )
        print(
            f"PASS {summary.result_path}: cases={summary.case_count} "
            f"metrics={summary.metric_count} artifacts_verified="
            f"{summary.verified_artifact_count} ignored_unavailable="
            f"{summary.unavailable_ignored_artifact_count}"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
