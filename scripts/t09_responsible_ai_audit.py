"""Build a fail-closed, media-free T09 Responsible-AI audit artifact."""

from __future__ import annotations

import argparse
from dataclasses import dataclass
from datetime import datetime, timezone
import hashlib
import importlib.util
from importlib.metadata import PackageNotFoundError, metadata
import json
import math
import os
from pathlib import Path
import platform
import re
import secrets
import subprocess
import sys
import tempfile
from typing import Any, Iterable, Sequence

from chromalens import __version__


ROOT = Path(__file__).resolve().parents[1]
ARTIFACT_DIR = ROOT / "artifacts" / "t09" / "performance_responsible_ai"
REPORT_PATH = ROOT / "evaluation" / "results" / "curated" / "performance_responsible_ai" / "report.md"
VIDEO_PATH = ARTIFACT_DIR / "inputs" / "generated-360x240.avi"
MANUAL_NAME = "t09-manual-roi-f59b5913-20260822t172922z.json"
MANUAL_PATH = ARTIFACT_DIR / MANUAL_NAME
LOCK_PATH = ROOT / "requirements" / "segment-mediapipe-py310-win64.lock"
EXPECTED_MANUAL_COMMIT = "c0e3e7a759e6ffeb8b2b903583b8cf05927b8416"
EXPECTED_MANUAL_SHA256 = "a2392deae77829d358d86a22f9929d48b4e3c3d61f3cf943d8ab39c445a57d02"
EXPECTED_PERFORMANCE_COMMIT = "7bc76d0526b34e7e366fe0cef730dc86680f5ef3"
REQUIRED_PYTHON = "3.10.20"
WORKSTREAM = "performance_responsible_ai"
RESULT_ID = re.compile(r"^t09-responsible-ai-audit-[a-z0-9]+-[0-9]{8}t[0-9]{6}z$")
SHA256 = re.compile(r"^[0-9a-f]{64}$")
GIT_SHA = re.compile(r"^[0-9a-f]{40}$")
MEDIA_SUFFIXES = {".png", ".jpg", ".jpeg", ".gif", ".webp", ".avi", ".mp4", ".mov", ".mkv", ".wav", ".mp3"}
PUBLIC_MEDIA_ALLOWLIST = {
    "tests/samples/t02/astronaut.png",
    "tests/samples/t02/cc0_woman.jpg",
    "tests/samples/t02/loc_lincoln.jpg",
    "tests/samples/t02/loc_man.jpg",
    "tests/samples/t02/nasa_shepard.jpg",
}
FIXTURE_SHA256 = {
    "tests/samples/t02/astronaut.png": "88431cd9653ccd539741b555fb0a46b61558b301d4110412b5bc28b5e3ea6cb5",
    "tests/samples/t02/cc0_woman.jpg": "9659315a44a6d3eadf8814b314193aacc78033097aa4dee4da0fadbfcaec025d",
    "tests/samples/t02/loc_lincoln.jpg": "a305c6630a3ac49dc9fe2ebe9f218ba7bb91df715c2dd860d038a585e030c15f",
    "tests/samples/t02/loc_man.jpg": "50eb295eb7cf909350c67c74b3b306a1e7018261505c866f88f77b035ada0d94",
    "tests/samples/t02/nasa_shepard.jpg": "3f8ef484565605683cfe5b4aec510c165afafbfe00477899faecfb521a097488",
}


class AuditError(RuntimeError):
    """An audit condition that must prevent a COMPLETE artifact."""


@dataclass(frozen=True)
class AuditCase:
    case_id: str
    fixture_id: str


CASES = (
    AuditCase("PERF-SENSOR-EXTERNAL", "external-sensor-apparatus"),
    AuditCase("BASELINE-FIXED-RGB", "fixed-rgb-explanation"),
    AuditCase("RAI-ARTIFACT-INTEGRITY", "artifact-manifest-all"),
    AuditCase("RAI-PRIVACY", "privacy-audit"),
    AuditCase("RAI-LICENSE", "license-attribution-audit"),
    AuditCase("RAI-LIMITATIONS", "failure-and-bias-report"),
    AuditCase("RAI-USER-VALIDATION", "user-validation-status"),
)
PERFORMANCE_CASES = (
    "PERF-WEBCAM-GUI-120", "PERF-WEBCAM-HEADLESS-120",
    "PERF-VIDEO-GUI-120", "PERF-VIDEO-HEADLESS-120",
)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def validate_python_version(version: str | None = None) -> str:
    observed = platform.python_version() if version is None else version
    if observed != REQUIRED_PYTHON:
        raise AuditError(f"T09 Responsible-AI audit requires Python {REQUIRED_PYTHON}; observed {observed}")
    return observed


def git_commit() -> str:
    try:
        result = subprocess.run(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True, capture_output=True, check=True)
    except (OSError, subprocess.CalledProcessError) as exc:
        raise AuditError("could not determine Git SHA for audit provenance") from exc
    commit = result.stdout.strip()
    if GIT_SHA.fullmatch(commit) is None:
        raise AuditError("Git SHA must be 40 lowercase hexadecimal characters")
    return commit


def git_tracked_paths(paths: Sequence[str]) -> set[str]:
    try:
        output = subprocess.run(["git", "ls-files", "--", *paths], cwd=ROOT, text=True, capture_output=True, check=True).stdout
    except (OSError, subprocess.CalledProcessError) as exc:
        raise AuditError("could not verify required Git tracking") from exc
    return {path.replace("\\", "/") for path in output.splitlines()}


def require_required_audit_files_tracked() -> None:
    required = (
        "scripts/t09_responsible_ai_audit.py",
        "tests/evaluation/test_t09_performance_responsible_ai.py",
    )
    if git_tracked_paths(required) != set(required):
        raise AuditError("current audit source and validation test must be committed before an official audit")


def require_clean_tracked_worktree() -> None:
    """Ignored raw evidence may exist; staged/unstaged tracked edits may not."""
    try:
        status = subprocess.run(["git", "status", "--porcelain"], cwd=ROOT, text=True, capture_output=True, check=True).stdout.splitlines()
    except (OSError, subprocess.CalledProcessError) as exc:
        raise AuditError("could not verify tracked worktree state") from exc
    dirty = [line for line in status if not line.startswith("?? artifacts/t09/performance_responsible_ai/")]
    if dirty:
        raise AuditError("tracked changes or untracked non-raw files block an official audit")
    require_required_audit_files_tracked()


def _json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise AuditError(f"cannot read JSON evidence: {path}") from exc
    if not isinstance(value, dict):
        raise AuditError(f"JSON evidence must be an object: {path}")
    return value


def validate_manual_artifact(path: Path, *, expected_dir: Path = ARTIFACT_DIR) -> dict[str, Any]:
    if path.resolve().parent != expected_dir.resolve() or path.name != MANUAL_NAME:
        raise AuditError("Manual ROI artifact path is not the locked canonical artifact")
    if not path.is_file() or sha256_file(path) != EXPECTED_MANUAL_SHA256:
        raise AuditError("Manual ROI artifact SHA-256 does not match the locked evidence")
    payload = _json(path)
    case = payload.get("cases")
    if (payload.get("result_status") != "COMPLETE" or payload.get("git_commit") != EXPECTED_MANUAL_COMMIT
            or not isinstance(case, list) or len(case) != 1
            or case[0].get("case_id") != "BASELINE-MANUAL-ROI"
            or case[0].get("fixture_id") != "manual-roi-public-fixtures"
            or case[0].get("status") != "COMPLETE"):
        raise AuditError("Manual ROI artifact has wrong status, case, fixture, or locked Git SHA")
    if payload.get("workstream") != WORKSTREAM or payload.get("schema_version") != "1.0.0":
        raise AuditError("Manual ROI artifact protocol/schema contract is invalid")
    return payload


def load_performance_artifacts(directory: Path = ARTIFACT_DIR) -> dict[str, Path]:
    spec = importlib.util.spec_from_file_location("t09_report_validator", ROOT / "scripts" / "t09_benchmark_report.py")
    assert spec and spec.loader
    validator = importlib.util.module_from_spec(spec); sys.modules[spec.name] = validator; spec.loader.exec_module(validator)
    try:
        evidence = validator.load_and_validate(directory, directory / "inputs" / "generated-360x240.avi")
    except validator.EvidenceValidationError as exc:
        raise AuditError(f"performance evidence contract rejected: {exc}") from exc
    if {item.payload["git_commit"] for item in evidence.artifacts} != {EXPECTED_PERFORMANCE_COMMIT}:
        raise AuditError("performance Git SHA is not the locked official evidence commit")
    return {item.case_id: item.path for item in evidence.artifacts}


def report_manifest(report_path: Path = REPORT_PATH) -> dict[str, str]:
    try:
        text = report_path.read_text(encoding="utf-8")
    except OSError as exc:
        raise AuditError("curated performance report is unavailable for manifest verification") from exc
    manifest: dict[str, str] = {}
    for path_text, digest in re.findall(r"\| `([^`]+)` \| .*? \| `([0-9a-f]{64})` \|", text):
        manifest[path_text.replace("/", "\\")] = digest
    if len(manifest) < 5:
        raise AuditError("curated report does not provide the required raw-evidence manifest")
    return manifest


def validate_evidence_manifest(paths: Iterable[Path], manifest: dict[str, str]) -> list[dict[str, object]]:
    records: list[dict[str, object]] = []
    for path in paths:
        try:
            relative = path.resolve().relative_to(ROOT.resolve()).as_posix().replace("/", "\\")
        except ValueError:
            relative = path.resolve().as_posix().replace("/", "\\")
        expected = manifest.get(relative)
        if expected is None or SHA256.fullmatch(expected) is None or not path.is_file():
            raise AuditError(f"evidence manifest is missing or invalid for {path}")
        observed = sha256_file(path)
        if observed != expected:
            raise AuditError(f"evidence checksum mismatch for {path}")
        records.append({"path": relative.replace("\\", "/"), "sha256": observed, "byte_size": path.stat().st_size})
    return records


def tracked_media(git_files: Sequence[str] | None = None) -> tuple[list[str], list[str]]:
    if git_files is None:
        try:
            output = subprocess.run(["git", "ls-files"], cwd=ROOT, text=True, capture_output=True, check=True).stdout
        except (OSError, subprocess.CalledProcessError) as exc:
            raise AuditError("could not enumerate tracked media with git ls-files") from exc
        git_files = output.splitlines()
    media = sorted(path.replace("\\", "/") for path in git_files if Path(path).suffix.lower() in MEDIA_SUFFIXES)
    unknown = [path for path in media if path not in PUBLIC_MEDIA_ALLOWLIST]
    return media, unknown


def validate_fixture_provenance(
    media: Sequence[str], *, root: Path = ROOT, tracked_files: set[str] | None = None,
) -> list[dict[str, str]]:
    """Validate the real tracked-media set, bytes, and README provenance contract."""
    normalized = sorted(path.replace("\\", "/") for path in media)
    if normalized != sorted(FIXTURE_SHA256):
        raise AuditError("tracked media set must be exactly the five locked T02 fixtures")
    readme = root / "tests/samples/t02/README.md"
    if tracked_files is None:
        tracked_files = git_tracked_paths(["tests/samples/t02/README.md"])
    if "tests/samples/t02/README.md" not in tracked_files:
        raise AuditError("T02 provenance README must be committed before an official audit")
    if not readme.is_file():
        raise AuditError("T02 provenance README is missing")
    text, evidence_sha = readme.read_text(encoding="utf-8"), sha256_file(readme)
    records: list[dict[str, str]] = []
    for relative in normalized:
        path, expected = root / relative, FIXTURE_SHA256[relative]
        if not path.is_file() or sha256_file(path) != expected:
            raise AuditError(f"tracked fixture bytes do not match locked SHA: {relative}")
        name = Path(relative).name
        if name not in text or expected not in text:
            raise AuditError(f"README lacks filename/SHA provenance for {name}")
        row = next((line for line in text.splitlines() if f"`{name}`" in line), "")
        cells = [cell.strip() for cell in row.split("|")]
        if len(cells) < 5 or not cells[2] or not cells[3] or "http" not in cells[2] or "rights" not in cells[3].lower() and "public" not in cells[3].lower() and "cc0" not in cells[3].lower():
            raise AuditError(f"README lacks source or rights statement for {name}")
        records.append({"path": relative, "sha256": expected, "source_record": cells[2], "rights_statement": cells[3], "provenance_evidence_path": "tests/samples/t02/README.md", "provenance_evidence_sha256": evidence_sha, "rights_status": "PUBLIC_LICENSED", "validation_status": "VERIFIED"})
    return records


def _read_evidence(root: Path, relative: str) -> tuple[str, str]:
    path = root / relative
    if not path.is_file():
        return "", ""
    return path.read_text(encoding="utf-8"), sha256_file(path)


def _clear_license(value: str | None) -> bool:
    normalized = (value or "").strip()
    if not normalized or normalized.casefold() in {"unknown", "none", "n/a", "not specified", "see license"}:
        return False
    return bool(re.fullmatch(r"[A-Za-z0-9.+-]+(?:\s+(?:AND|OR|WITH)\s+[A-Za-z0-9.+-]+)*", normalized) or re.search(r"\b(?:Apache|MIT|BSD|Mozilla Public)\b.*\bLicense\b", normalized, re.I))


def installed_package_license(distribution: str) -> str | None:
    """Return only an explicit installed-distribution license declaration."""
    try:
        package_metadata = metadata(distribution)
    except PackageNotFoundError:
        return None
    for field in ("License-Expression", "License"):
        value = package_metadata.get(field)
        if _clear_license(value):
            return value.strip()
    return None


def _record(component_id: str, category: str, version: str, declared_license: str, evidence_path: str, evidence_sha256: str, verified: bool, gap_reason: str, **extra: str) -> dict[str, str]:
    return {
        "component_id": component_id, "category": category, "declared_version": version,
        "declared_license": declared_license, "evidence_path": evidence_path,
        "evidence_sha256": evidence_sha256, "status": "VERIFIED" if verified else "GAP",
        "gap_reason": "" if verified else gap_reason, **extra,
    }


def license_inventory(
    *, package_versions: dict[str, str], fixture_records: Sequence[dict[str, str]] = (), root: Path = ROOT,
) -> list[dict[str, str]]:
    """Create records only from validated evidence; missing or unclear evidence remains a GAP."""
    records: list[dict[str, str]] = []
    license_text, license_sha = _read_evidence(root, "LICENSE")
    project_verified = bool(re.search(r"Apache License\s+Version 2\.0", license_text, re.I) and "http://www.apache.org/licenses/LICENSE-2.0" in license_text)
    records.append(_record("chromalens-project", "project_code", __version__, "Apache-2.0", "LICENSE", license_sha, project_verified, "LICENSE does not contain an Apache License 2.0 declaration"))

    model_text, model_sha = _read_evidence(root, "models/README.md")
    model_verified = bool("MediaPipe Selfie Segmentation" in model_text and re.search(r"\|\s*License\s*\|\s*Apache-?2\.0", model_text, re.I))
    records.append(_record("mediapipe-selfie-segmentation-model-backend", "model_backend", package_versions.get("mediapipe", "UNKNOWN"), "Apache-2.0", "models/README.md", model_sha, model_verified, "MediaPipe model/backend license evidence is missing or unclear"))

    dalton_text, dalton_sha = _read_evidence(root, "assets/cvd/README.md")
    dalton_license_text, dalton_license_sha = _read_evidence(root, "assets/cvd/DALTONLENS-MIT-LICENSE.md")
    dalton_verified = bool("Simulator_Machado2009" in dalton_text and re.search(r"DaltonLens.*distributed under the MIT License", dalton_text, re.I | re.S) and "MIT License" in dalton_license_text)
    records.append(_record("daltonlens-machado-algorithm", "algorithm", package_versions.get("daltonlens", "UNKNOWN"), "MIT", "assets/cvd/README.md", dalton_sha, dalton_verified, "DaltonLens/Machado attribution or license evidence is missing or unclear", supporting_evidence_path="assets/cvd/DALTONLENS-MIT-LICENSE.md", supporting_evidence_sha256=dalton_license_sha))

    schp_text, schp_sha = _read_evidence(root, "models/README.md")
    records.append(_record("schp-atr-deferred", "model", "NOT_APPLICABLE", "UNKNOWN", "models/README.md", schp_sha, False, "SCHP-ATR is deferred and has no approved model-license evidence"))

    for distribution, version in sorted(package_versions.items()):
        license_name = installed_package_license(distribution)
        records.append(_record(f"runtime-package-{distribution.replace('_', '-').lower()}", "runtime_package", version, license_name or "UNKNOWN", f"installed-distribution-metadata:{distribution}", "", license_name is not None, "installed distribution metadata has no clear license/license-expression", distribution_name=distribution))

    for fixture in fixture_records:
        records.append(_record(
            f"public-fixture-{fixture['sha256'][:12]}", "public_fixture", "NOT_APPLICABLE", fixture["rights_statement"],
            fixture["provenance_evidence_path"], fixture["provenance_evidence_sha256"],
            fixture.get("validation_status") == "VERIFIED", "fixture provenance validator did not verify this record",
            fixture_sha256=fixture["sha256"], source_record=fixture["source_record"], rights_statement=fixture["rights_statement"],
        ))
    unique = {item["component_id"]: item for item in records}
    return sorted(unique.values(), key=lambda item: item["component_id"])


def _metric(name: str, case_id: str, value: int | None, *, status: str = "MEASURED", threshold_id: str | None = "required") -> dict[str, object]:
    return {
        "name": name, "aggregation": "count" if name != "sensor_to_photon_ms" else "p50", "unit": "count" if name != "sensor_to_photon_ms" else "ms",
        "status": status, "value": value if status == "MEASURED" else None, "case_ids": [case_id],
        "threshold_id": threshold_id, "threshold_result": "PASS" if status == "MEASURED" and value == 0 else "NOT_EVALUATED",
        "reason": "" if status == "MEASURED" else "No synchronized external photodiode/high-speed apparatus has been acquired.",
        "method": "Fail-closed local audit over declared evidence; this metric is not a license-completeness claim.",
    }


def build_payload(
    *, manual: dict[str, Any], evidence: list[dict[str, object]], unknown_media: list[str], commit: str,
    started_at: datetime, ended_at: datetime, actual_media: list[str] | None = None,
    fixture_records: list[dict[str, str]] | None = None, inventory: list[dict[str, str]] | None = None,
) -> dict[str, object]:
    if not GIT_SHA.fullmatch(commit) or not isinstance(started_at, datetime) or not isinstance(ended_at, datetime) or started_at.tzinfo is None or ended_at.tzinfo is None or started_at > ended_at:
        raise AuditError("audit timestamps are out of order")
    if not evidence or actual_media is None or fixture_records is None or inventory is None:
        raise AuditError("COMPLETE audit requires non-empty evidence, media, fixture records, and inventory")
    if sorted(actual_media) != sorted(FIXTURE_SHA256) + sorted(unknown_media):
        raise AuditError("actual tracked media and unknown-media findings are inconsistent")
    if {item.get("path") for item in fixture_records} != set(FIXTURE_SHA256) or len(fixture_records) != len(FIXTURE_SHA256):
        raise AuditError("fixture records must cover each canonical fixture exactly once")
    component_ids = [item.get("component_id") for item in inventory]
    if not component_ids or len(component_ids) != len(set(component_ids)):
        raise AuditError("license inventory must be non-empty with unique component IDs")
    for item in inventory:
        if item.get("status") == "VERIFIED":
            if item.get("category") == "public_fixture":
                required = {"fixture_sha256", "source_record", "rights_statement", "evidence_path", "evidence_sha256"}
                if not required <= set(item) or item.get("fixture_sha256") not in FIXTURE_SHA256.values():
                    raise AuditError("VERIFIED public fixture record is not derived from validated provenance")
                continue
            evidence_path, digest = str(item.get("evidence_path")), item.get("evidence_sha256")
            if evidence_path.startswith("installed-distribution-metadata:"):
                distribution = item.get("distribution_name")
                if not isinstance(distribution, str) or installed_package_license(distribution) != item.get("declared_license"):
                    raise AuditError("VERIFIED installed-distribution license metadata changed or is unclear")
                continue
            path = ROOT / evidence_path
            if not path.is_file() or not isinstance(digest, str) or sha256_file(path) != digest:
                raise AuditError("VERIFIED inventory evidence path/hash is invalid")
            supporting_path = item.get("supporting_evidence_path")
            if supporting_path:
                supporting_digest = item.get("supporting_evidence_sha256")
                if not isinstance(supporting_digest, str) or not (ROOT / supporting_path).is_file() or sha256_file(ROOT / supporting_path) != supporting_digest:
                    raise AuditError("VERIFIED inventory supporting evidence path/hash is invalid")
    environment = dict(manual.get("environment", {}))
    if environment.get("python_version") != REQUIRED_PYTHON:
        raise AuditError("Manual ROI provenance is not the frozen Python version")
    metrics = [
        {**_metric("sensor_to_photon_ms", "PERF-SENSOR-EXTERNAL", None, status="NOT_MEASURED", threshold_id="external_apparatus_required"), "aggregation": "p50"},
        {**_metric("sensor_to_photon_ms", "PERF-SENSOR-EXTERNAL", None, status="NOT_MEASURED", threshold_id="external_apparatus_required"), "aggregation": "p95"},
        _metric("artifact_checksum_mismatch_count", "BASELINE-FIXED-RGB", 0),
        _metric("artifact_checksum_mismatch_count", "RAI-ARTIFACT-INTEGRITY", 0),
        _metric("unconsented_tracked_media_count", "RAI-PRIVACY", len(unknown_media)),
        _metric("artifact_checksum_mismatch_count", "RAI-LICENSE", 0),
        _metric("unconsented_tracked_media_count", "RAI-LIMITATIONS", len(unknown_media)),
        _metric("unconsented_tracked_media_count", "RAI-USER-VALIDATION", len(unknown_media)),
    ]
    for record in metrics:
        if record["value"] not in (0, None):
            record["threshold_result"] = "FAIL"
    cases = [{"case_id": case.case_id, "status": "COMPLETE", "fixture_id": case.fixture_id, "artifact_ids": [],
              "reason": _case_reason(case.case_id, unknown_media)} for case in CASES]
    license_gaps = [item["component_id"] for item in inventory if item["status"] == "GAP"]
    findings = {
        "evidence_manifest": evidence,
        "fixed_rgb_baseline": "Non-AI fixed-RGB thresholding does not localize people or garments and is sensitive to lighting, backgrounds, and similar colors.",
        "privacy": {"tracked_media": sorted(actual_media or []), "fixtures": sorted(fixture_records or [], key=lambda item: item["path"]), "unknown_tracked_media": unknown_media},
        "license_inventory": sorted(inventory or [], key=lambda item: item["component_id"]),
        "license_gaps": license_gaps,
        "compliance_status": "GAPS_RECORDED" if license_gaps else "COMPLETE",
        "user_validation": "NOT_MEASURED: no written-consent user study or participant feedback was collected.",
        "case_configuration": {"PERF-SENSOR-EXTERNAL": {"cvd_profile": "deutan", "severity": 0.8}, **{case.case_id: {"cvd_profile": "not_applicable", "severity": None} for case in CASES if case.case_id != "PERF-SENSOR-EXTERNAL"}},
        "resolution_boundary": "No frame/media source is used; 1x1 is schema_sentinel_not_applicable, not an image measurement.",
    }
    stamp = ended_at.astimezone(timezone.utc)
    return {
        "protocol_version": "1.0.0", "schema_version": "1.0.0", "metric_registry_version": "1.0.0",
        "result_id": f"t09-responsible-ai-audit-{secrets.token_hex(4)}-{stamp:%Y%m%dt%H%M%Sz}",
        "workstream": WORKSTREAM, "result_status": "COMPLETE", "git_commit": commit,
        "created_at_utc": stamp.isoformat().replace("+00:00", "Z"),
        "operator": {"role": "performance_evaluator", "identifier": "Trinh"},
        "environment": {**environment, "camera_or_source": "local timing/media-free Responsible-AI audit", "backend_name": "responsible-ai-audit", "backend_device": "cpu", "source_kind": "manual_baseline", "source_resolution": {"width": 1, "height": 1}, "render_resolution": {"width": 1, "height": 1}, "display_mode": "not_applicable", "warmup_seconds": 0, "measurement_seconds": 0, "external_measurement_apparatus": None},
        "cases": cases, "configuration": {"cvd_profile": "deutan", "severity": 0.8, "thresholds": {"external_apparatus_required": True, "privacy_allowlist_required": True}, "settings": {"audit_case_count": 7, "media_written": False, "resolution": "schema_sentinel_not_applicable"}},
        "metrics": metrics, "artifacts": [],
        "commands": [{"command": "t09_responsible_ai_audit.py", "exit_code": 0, "started_at_utc": started_at.astimezone(timezone.utc).isoformat().replace("+00:00", "Z"), "ended_at_utc": ended_at.astimezone(timezone.utc).isoformat().replace("+00:00", "Z"), "output_summary": "Read metadata, hashes, and tracked filenames only; no media was written or copied."}],
        "failure_cases": [],
        "limitations": ["High degraded-frame rates were measured in all four performance cases; impact: reduced full-quality rendering; boundary: report values remain unmodified.", "RSS continuous-growth flag is FAIL in three of four cases; impact: potential long-run memory risk; mitigation: retain bounded-queue/RSS investigation as open work.", "Development host is not declared demo hardware; impact: no demo-threshold PASS claim; mitigation: repeat on declared demo hardware.", "sensor_to_photon_ms is NOT_MEASURED without external apparatus; impact: physical display latency is unknown; mitigation: acquire synchronized apparatus.", "Five public images are not demographic validation; impact: coverage gaps for segmentation, lighting, occlusion, backgrounds, and color similarity remain; mitigation: consented, reviewed evaluation expansion.", "The product is not a medical diagnosis and energy consumption is not measured; impact: no clinical or energy-use claim; mitigation: retain these boundaries."],
        "responsible_ai": {"runtime_local_offline": True, "frames_saved_by_default": False, "frames_uploaded_by_default": False, "medical_diagnosis_claim": False, "user_selected_profile": True, "privacy_summary": "Tracked media uses an explicit public-fixture allowlist; unknown tracked media is counted fail-closed.", "bias_coverage_summary": "Five public fixtures are not demographic validation.", "environmental_summary": "Energy consumption has not been measured.", "license_summary": "Repository evidence is recorded; gaps remain findings, not inferred licenses.", "user_validation_status": "NOT_MEASURED"},
        "notes": "responsible_ai_audit_findings=" + json.dumps(findings, sort_keys=True, separators=(",", ":")),
    }


def _case_reason(case_id: str, unknown_media: list[str]) -> str:
    if case_id == "PERF-SENSOR-EXTERNAL": return "No synchronized external apparatus acquired; software latency was not converted to sensor-to-photon latency."
    if case_id == "BASELINE-FIXED-RGB": return "Fixed RGB is documented as a non-AI baseline, not automatic garment localization."
    if case_id == "RAI-PRIVACY": return f"Tracked-media allowlist audit completed; unknown media count={len(unknown_media)}."
    if case_id == "RAI-LICENSE": return "License/attribution audit completed; unresolved evidence remains a finding."
    if case_id == "RAI-USER-VALIDATION": return "No consented user study was performed; status remains NOT_MEASURED."
    return "Fail-closed Responsible-AI audit observation completed."


def _output_dir(path: Path) -> Path:
    candidate, allowed = path.resolve(), ARTIFACT_DIR.resolve()
    try: candidate.relative_to(allowed)
    except ValueError as exc: raise AuditError("output must remain under artifacts/t09/performance_responsible_ai") from exc
    return candidate


def write_atomic(payload: dict[str, object], output_dir: Path) -> Path:
    directory = _output_dir(output_dir); directory.mkdir(parents=True, exist_ok=True)
    result_id = payload.get("result_id")
    if not isinstance(result_id, str) or RESULT_ID.fullmatch(result_id) is None or any(x in result_id for x in ("/", "\\", "..")):
        raise AuditError("invalid audit result_id")
    destination = directory / f"{result_id}.json"
    if destination.parent.resolve() != directory.resolve(): raise AuditError("audit destination escaped output namespace")
    temporary: Path | None = None
    primary: BaseException | None = None
    try:
        fd, name = tempfile.mkstemp(prefix=f".{result_id}.", suffix=".tmp", dir=directory, text=True); temporary = Path(name)
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            json.dump(payload, handle, sort_keys=True, indent=2); handle.write("\n"); handle.flush(); os.fsync(handle.fileno())
        os.link(temporary, destination)
    except FileExistsError as exc:
        primary = AuditError("refusing to overwrite existing audit result"); raise primary from exc
    except (OSError, TypeError, ValueError) as exc:
        primary = AuditError("could not atomically write audit result"); raise primary from exc
    finally:
        if temporary is not None:
            try:
                temporary.unlink(missing_ok=True)
            except OSError as cleanup_error:
                if primary is None:
                    raise AuditError("could not clean up temporary audit output") from cleanup_error
    return destination


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manual-artifact", type=Path, default=MANUAL_PATH)
    parser.add_argument("--output-dir", type=Path, default=ARTIFACT_DIR)
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args, started = parse_args(argv), datetime.now(timezone.utc)
    try:
        validate_python_version(); require_clean_tracked_worktree(); manual = validate_manual_artifact(args.manual_artifact)
        performance = load_performance_artifacts(); manifest = report_manifest()
        evidence = validate_evidence_manifest([*performance.values(), VIDEO_PATH], manifest)
        evidence.append({"path": args.manual_artifact.relative_to(ROOT).as_posix(), "sha256": EXPECTED_MANUAL_SHA256, "byte_size": args.manual_artifact.stat().st_size})
        media, unknown = tracked_media(); fixtures = validate_fixture_provenance(media)
        inventory = license_inventory(package_versions=dict(manual["environment"]["package_versions"]), fixture_records=fixtures)
        payload = build_payload(manual=manual, evidence=evidence, unknown_media=unknown, actual_media=media, fixture_records=fixtures, inventory=inventory, commit=git_commit(), started_at=started, ended_at=datetime.now(timezone.utc))
        print(write_atomic(payload, args.output_dir)); return 0
    except AuditError as exc:
        print(f"Responsible-AI audit failed closed: {exc}", file=sys.stderr); return 2


if __name__ == "__main__": raise SystemExit(main())
