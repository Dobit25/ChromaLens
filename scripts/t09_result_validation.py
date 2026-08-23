"""Validate curated T09 results without adding a JSON-Schema dependency."""

from __future__ import annotations

import argparse
import csv
from dataclasses import dataclass
from datetime import datetime
import hashlib
import json
from pathlib import Path
import re
from typing import Any, Iterable, Mapping, Sequence
from urllib.parse import urlparse


ROOT = Path(__file__).resolve().parents[1]
SCHEMA_PATH = ROOT / "evaluation/schema/t09-result.schema.json"
REGISTRY_PATH = ROOT / "evaluation/schema/metric_registry.json"
CASES_PATH = ROOT / "evaluation/fixtures/test_cases.csv"


class ResultValidationError(RuntimeError):
    """Raised when a curated result violates the frozen T09 contract."""


@dataclass(frozen=True, slots=True)
class ValidationSummary:
    result_path: Path
    workstream: str
    case_count: int
    metric_count: int
    tracked_artifact_count: int
    verified_untracked_artifact_count: int
    missing_untracked_artifact_count: int


def sha256_file(path: Path) -> str:
    """Return SHA-256 over the exact bytes at *path*."""

    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def load_case_registry() -> list[dict[str, str]]:
    with CASES_PATH.open(encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def validate_result_file(
    result_path: Path,
    *,
    expected_workstream: str | None = None,
    require_exact_case_coverage: bool = True,
    require_untracked_artifacts: bool = False,
) -> ValidationSummary:
    """Validate schema, registries, references, and available exact bytes.

    Tracked artifacts are always required and byte-verified. Ignored raw
    artifacts are verified when present. CI may omit them so tests remain
    independent of private footage and bulk artifacts; a release/evidence
    custodian can opt into strict raw verification with
    ``require_untracked_artifacts=True``.
    """

    path = result_path.resolve()
    payload = json.loads(path.read_text(encoding="utf-8"))
    schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
    registry = json.loads(REGISTRY_PATH.read_text(encoding="utf-8"))
    _validate_schema(payload, schema, schema, "$", strict_formats=True)

    workstream = str(payload["workstream"])
    if expected_workstream is not None and workstream != expected_workstream:
        raise ResultValidationError(
            f"{path}: workstream {workstream!r} != {expected_workstream!r}"
        )

    case_rows = [row for row in load_case_registry() if row["workstream"] == workstream]
    frozen_case_ids = {row["case_id"] for row in case_rows}
    result_case_ids = [str(item["case_id"]) for item in payload["cases"]]
    if len(result_case_ids) != len(set(result_case_ids)):
        raise ResultValidationError(f"{path}: duplicate case_id in result")
    extras = set(result_case_ids) - frozen_case_ids
    missing = frozen_case_ids - set(result_case_ids)
    if extras or (require_exact_case_coverage and missing):
        raise ResultValidationError(
            f"{path}: frozen case coverage mismatch; extras={sorted(extras)}, "
            f"missing={sorted(missing)}"
        )

    metric_specs = {item["name"]: item for item in registry["metrics"]}
    for index, metric in enumerate(payload["metrics"]):
        location = f"{path}: metrics[{index}]"
        name = str(metric["name"])
        spec = metric_specs.get(name)
        if spec is None:
            raise ResultValidationError(f"{location}: unregistered metric {name}")
        if metric["unit"] != spec["unit"]:
            raise ResultValidationError(
                f"{location}: unit {metric['unit']!r} != {spec['unit']!r}"
            )
        if metric["aggregation"] not in spec["allowed_aggregations"]:
            raise ResultValidationError(
                f"{location}: aggregation {metric['aggregation']!r} is not allowed"
            )
        threshold_ids = {item["id"] for item in spec["thresholds"]}
        if metric["threshold_id"] is not None and metric["threshold_id"] not in threshold_ids:
            raise ResultValidationError(
                f"{location}: unknown threshold {metric['threshold_id']!r}"
            )
        metric_cases = set(metric["case_ids"])
        if not metric_cases <= frozen_case_ids:
            raise ResultValidationError(
                f"{location}: non-frozen case IDs {sorted(metric_cases - frozen_case_ids)}"
            )
        if metric["status"] == "MEASURED":
            _validate_registry_value(metric["value"], spec["value_type"], location)
        elif metric["threshold_result"] not in {"NOT_APPLICABLE", "NOT_EVALUATED"}:
            raise ResultValidationError(
                f"{location}: an unmeasured metric cannot PASS or FAIL"
            )

    artifacts = payload["artifacts"]
    artifact_ids = [str(item["artifact_id"]) for item in artifacts]
    if len(artifact_ids) != len(set(artifact_ids)):
        raise ResultValidationError(f"{path}: duplicate artifact_id")
    known_artifact_ids = set(artifact_ids)
    for case in payload["cases"]:
        unknown = set(case["artifact_ids"]) - known_artifact_ids
        if unknown:
            raise ResultValidationError(
                f"{path}: case {case['case_id']} references unknown artifacts {sorted(unknown)}"
            )

    tracked = 0
    verified_untracked = 0
    missing_untracked = 0
    for artifact in artifacts:
        artifact_cases = set(artifact["case_ids"])
        if not artifact_cases <= frozen_case_ids:
            raise ResultValidationError(
                f"{path}: artifact {artifact['artifact_id']} has non-frozen case IDs"
            )
        artifact_path = _repository_path(str(artifact["relative_path"]))
        if artifact["tracked_in_git"]:
            tracked += 1
            _verify_artifact_bytes(artifact_path, artifact, required=True)
        elif artifact_path.is_file():
            verified_untracked += 1
            _verify_artifact_bytes(artifact_path, artifact, required=True)
        else:
            missing_untracked += 1
            if require_untracked_artifacts:
                raise ResultValidationError(
                    f"{path}: required ignored artifact is absent: "
                    f"{artifact['relative_path']}"
                )

    return ValidationSummary(
        result_path=path,
        workstream=workstream,
        case_count=len(result_case_ids),
        metric_count=len(payload["metrics"]),
        tracked_artifact_count=tracked,
        verified_untracked_artifact_count=verified_untracked,
        missing_untracked_artifact_count=missing_untracked,
    )


def _repository_path(relative_path: str) -> Path:
    candidate = (ROOT / Path(relative_path)).resolve()
    if not candidate.is_relative_to(ROOT.resolve()):
        raise ResultValidationError(f"artifact path escapes repository: {relative_path}")
    return candidate


def _verify_artifact_bytes(
    path: Path, artifact: Mapping[str, Any], *, required: bool
) -> None:
    if not path.is_file():
        if required:
            raise ResultValidationError(f"artifact is absent: {path}")
        return
    actual_size = path.stat().st_size
    actual_sha256 = sha256_file(path)
    if actual_size != artifact["byte_size"] or actual_sha256 != artifact["sha256"]:
        raise ResultValidationError(
            f"artifact mismatch for {artifact['artifact_id']}: "
            f"size {actual_size}/{artifact['byte_size']}, "
            f"sha256 {actual_sha256}/{artifact['sha256']}"
        )


def _validate_registry_value(value: Any, value_type: str, location: str) -> None:
    valid = {
        "number": _is_number(value),
        "integer": isinstance(value, int) and not isinstance(value, bool),
        "boolean": isinstance(value, bool),
    }.get(value_type, False)
    if not valid:
        raise ResultValidationError(
            f"{location}: value {value!r} does not match registry type {value_type}"
        )


def _validate_schema(
    value: Any,
    schema: Mapping[str, Any],
    root_schema: Mapping[str, Any],
    location: str,
    *,
    strict_formats: bool,
) -> None:
    if "$ref" in schema:
        ref = str(schema["$ref"])
        if not ref.startswith("#/"):
            raise ResultValidationError(f"{location}: unsupported schema reference {ref}")
        target: Any = root_schema
        for part in ref[2:].split("/"):
            target = target[part.replace("~1", "/").replace("~0", "~")]
        _validate_schema(value, target, root_schema, location, strict_formats=strict_formats)
        return

    for nested in schema.get("allOf", []):
        _validate_schema(value, nested, root_schema, location, strict_formats=strict_formats)
    if "if" in schema:
        branch = "then" if _schema_matches(value, schema["if"], root_schema) else "else"
        if branch in schema:
            _validate_schema(
                value,
                schema[branch],
                root_schema,
                location,
                strict_formats=strict_formats,
            )

    if "const" in schema and value != schema["const"]:
        raise ResultValidationError(
            f"{location}: expected constant {schema['const']!r}, got {value!r}"
        )
    if "enum" in schema and value not in schema["enum"]:
        raise ResultValidationError(f"{location}: {value!r} is outside enum")
    if "type" in schema and not _matches_type(value, schema["type"]):
        raise ResultValidationError(
            f"{location}: {type(value).__name__} does not match {schema['type']!r}"
        )

    if isinstance(value, dict):
        required = set(schema.get("required", []))
        missing = required - set(value)
        if missing:
            raise ResultValidationError(f"{location}: missing keys {sorted(missing)}")
        properties = schema.get("properties", {})
        additional = schema.get("additionalProperties", True)
        for key, item in value.items():
            child = f"{location}.{key}"
            if key in properties:
                _validate_schema(
                    item,
                    properties[key],
                    root_schema,
                    child,
                    strict_formats=strict_formats,
                )
            elif additional is False:
                raise ResultValidationError(f"{location}: unexpected key {key!r}")
            elif isinstance(additional, dict):
                _validate_schema(
                    item,
                    additional,
                    root_schema,
                    child,
                    strict_formats=strict_formats,
                )
        if len(value) < int(schema.get("minProperties", 0)):
            raise ResultValidationError(f"{location}: too few properties")

    if isinstance(value, list):
        if len(value) < int(schema.get("minItems", 0)):
            raise ResultValidationError(f"{location}: too few items")
        if schema.get("uniqueItems"):
            normalized = [json.dumps(item, sort_keys=True) for item in value]
            if len(normalized) != len(set(normalized)):
                raise ResultValidationError(f"{location}: items are not unique")
        if "items" in schema:
            for index, item in enumerate(value):
                _validate_schema(
                    item,
                    schema["items"],
                    root_schema,
                    f"{location}[{index}]",
                    strict_formats=strict_formats,
                )

    if isinstance(value, str):
        if len(value) < int(schema.get("minLength", 0)):
            raise ResultValidationError(f"{location}: string is too short")
        if "pattern" in schema and re.search(str(schema["pattern"]), value) is None:
            raise ResultValidationError(
                f"{location}: {value!r} does not match {schema['pattern']!r}"
            )
        if strict_formats and schema.get("format") == "date-time":
            try:
                datetime.fromisoformat(value.replace("Z", "+00:00"))
            except ValueError as error:
                raise ResultValidationError(f"{location}: invalid date-time") from error
        if strict_formats and schema.get("format") == "uri":
            if not urlparse(value).scheme:
                raise ResultValidationError(f"{location}: invalid URI")

    if _is_number(value):
        if "minimum" in schema and value < schema["minimum"]:
            raise ResultValidationError(f"{location}: below minimum")
        if "exclusiveMinimum" in schema and value <= schema["exclusiveMinimum"]:
            raise ResultValidationError(f"{location}: below exclusive minimum")
        if "maximum" in schema and value > schema["maximum"]:
            raise ResultValidationError(f"{location}: above maximum")


def _schema_matches(value: Any, schema: Mapping[str, Any], root: Mapping[str, Any]) -> bool:
    try:
        _validate_schema(value, schema, root, "$if", strict_formats=False)
    except ResultValidationError:
        return False
    return True


def _matches_type(value: Any, expected: str | Iterable[str]) -> bool:
    names = [expected] if isinstance(expected, str) else list(expected)
    return any(
        {
            "object": isinstance(value, dict),
            "array": isinstance(value, list),
            "string": isinstance(value, str),
            "number": _is_number(value),
            "integer": isinstance(value, int) and not isinstance(value, bool),
            "boolean": isinstance(value, bool),
            "null": value is None,
        }.get(name, False)
        for name in names
    )


def _is_number(value: Any) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "paths",
        nargs="*",
        type=Path,
        help="result.json files; defaults to every curated workstream result",
    )
    parser.add_argument(
        "--require-untracked-artifacts",
        action="store_true",
        help="fail if an ignored raw artifact in a manifest is absent",
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    paths = args.paths or sorted(
        (ROOT / "evaluation/results/curated").glob("*/result.json")
    )
    if not paths:
        print("No curated T09 result.json files found.")
        return 0
    try:
        for path in paths:
            summary = validate_result_file(
                path,
                expected_workstream=path.parent.name,
                require_untracked_artifacts=args.require_untracked_artifacts,
            )
            print(
                f"PASS {path}: {summary.case_count} cases, "
                f"{summary.metric_count} metrics, "
                f"{summary.tracked_artifact_count} tracked artifacts verified, "
                f"{summary.verified_untracked_artifact_count} ignored artifacts verified, "
                f"{summary.missing_untracked_artifact_count} ignored artifacts unavailable"
            )
    except (OSError, ValueError, ResultValidationError) as error:
        print(f"FAIL: {error}")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

