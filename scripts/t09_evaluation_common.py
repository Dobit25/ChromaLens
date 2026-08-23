"""Shared coordinator utilities for reproducible T09 result generation."""

from __future__ import annotations

import csv
from datetime import datetime, timezone
import hashlib
from importlib import metadata
import json
import os
from pathlib import Path
import platform
import subprocess
import sys
from typing import Any, Iterable, Mapping, Sequence


ROOT = Path(__file__).resolve().parents[1]
REQUIRED_PYTHON = "3.10.20"
PROTOCOL_VERSION = "1.0.0"


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def utc_text(value: datetime) -> str:
    return value.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def result_timestamp(value: datetime) -> str:
    return value.astimezone(timezone.utc).strftime("%Y%m%dt%H%M%Sz").lower()


def git_commit() -> str:
    value = subprocess.check_output(
        ["git", "rev-parse", "HEAD"], cwd=ROOT, text=True
    ).strip()
    if len(value) != 40 or any(character not in "0123456789abcdef" for character in value):
        raise RuntimeError(f"git rev-parse returned an invalid commit: {value!r}")
    return value


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def load_cases(workstream: str) -> list[dict[str, str]]:
    path = ROOT / "evaluation/fixtures/test_cases.csv"
    with path.open(encoding="utf-8", newline="") as handle:
        return [row for row in csv.DictReader(handle) if row["workstream"] == workstream]


def package_versions(names: Iterable[str]) -> dict[str, str]:
    versions: dict[str, str] = {}
    for name in names:
        try:
            versions[name] = metadata.version(name)
        except metadata.PackageNotFoundError:
            versions[name] = "NOT_INSTALLED"
    return versions


def collect_environment(
    *,
    lock_path: Path,
    backend_name: str,
    backend_device: str,
    camera_or_source: str,
    source_kind: str,
    source_resolution: tuple[int, int],
    render_resolution: tuple[int, int],
    display_mode: str,
    warmup_seconds: float,
    measurement_seconds: float,
    package_names: Sequence[str] = (
        "chromalens-ai",
        "numpy",
        "opencv-contrib-python",
        "mediapipe",
        "daltonlens",
    ),
) -> dict[str, Any]:
    """Collect host/package values at runtime; never substitute demo claims."""

    python_version = platform.python_version()
    if python_version != REQUIRED_PYTHON:
        raise RuntimeError(
            f"T09 requires Python {REQUIRED_PYTHON}; active interpreter is {python_version}"
        )
    manufacturer, model, ram_gib = _computer_identity()
    cpu, physical_cores, logical_processors = _processor_identity()
    width, height = source_resolution
    render_width, render_height = render_resolution
    return {
        "host_role": "development",
        "declared_demo_hardware": False,
        "manufacturer": manufacturer,
        "model": model,
        "operating_system": platform.platform(),
        "cpu": cpu,
        "physical_core_count": physical_cores,
        "logical_processor_count": logical_processors,
        "ram_gib": ram_gib,
        "gpu": _video_controllers(),
        "npu": _npu_names(),
        "camera_or_source": camera_or_source,
        "python_version": python_version,
        "package_versions": package_versions(package_names),
        "lock_sha256": sha256_file(lock_path),
        "backend_name": backend_name,
        "backend_device": backend_device,
        "source_kind": source_kind,
        "source_resolution": {"width": width, "height": height},
        "render_resolution": {"width": render_width, "height": render_height},
        "display_mode": display_mode,
        "warmup_seconds": warmup_seconds,
        "measurement_seconds": measurement_seconds,
        "external_measurement_apparatus": None,
    }


def curated_artifact(
    path: Path,
    *,
    artifact_id: str,
    case_ids: Sequence[str],
    media_type: str,
    generation_command: str,
    created_at: datetime,
    creator: str,
    derived_from: Sequence[str] = (),
) -> dict[str, Any]:
    resolved = path.resolve()
    if not resolved.is_relative_to(ROOT.resolve()):
        raise ValueError(f"artifact path escapes repository: {path}")
    return {
        "artifact_id": artifact_id,
        "case_ids": list(case_ids),
        "relative_path": resolved.relative_to(ROOT.resolve()).as_posix(),
        "sha256": sha256_file(resolved),
        "byte_size": resolved.stat().st_size,
        "media_type": media_type,
        "tracked_in_git": True,
        "derived_from": list(derived_from),
        "generation_command": generation_command,
        "provenance": {
            "provenance_class": "curated_result",
            "creator_or_source": creator,
            "source_url": None,
            "created_or_captured_at_utc": utc_text(created_at),
            "license_id": "Apache-2.0",
            "license_evidence": "Repository LICENSE and T09 protocol Section 10",
            "consent_status": "NOT_APPLICABLE_NO_PERSON",
            "consent_record_ref": None,
            "contains_personal_data": False,
        },
    }


def ignored_artifact_manifest(
    *,
    artifact_id: str,
    case_ids: Sequence[str],
    relative_path: str,
    sha256: str,
    byte_size: int,
    media_type: str,
    generation_command: str,
    created_at_utc: str | None,
    provenance_class: str,
    creator_or_source: str,
    license_id: str,
    license_evidence: str,
    derived_from: Sequence[str] = (),
    source_url: str | None = None,
    consent_status: str = "NOT_APPLICABLE_NO_PERSON",
    consent_record_ref: str | None = None,
    contains_personal_data: bool = False,
) -> dict[str, Any]:
    return {
        "artifact_id": artifact_id,
        "case_ids": list(case_ids),
        "relative_path": relative_path,
        "sha256": sha256,
        "byte_size": byte_size,
        "media_type": media_type,
        "tracked_in_git": False,
        "derived_from": list(derived_from),
        "generation_command": generation_command,
        "provenance": {
            "provenance_class": provenance_class,
            "creator_or_source": creator_or_source,
            "source_url": source_url,
            "created_or_captured_at_utc": created_at_utc,
            "license_id": license_id,
            "license_evidence": license_evidence,
            "consent_status": consent_status,
            "consent_record_ref": consent_record_ref,
            "contains_personal_data": contains_personal_data,
        },
    }


def write_json_lf(path: Path, value: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="\n") as handle:
        json.dump(value, handle, ensure_ascii=False, indent=2)
        handle.write("\n")


def write_text_lf(path: Path, value: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="\n") as handle:
        handle.write(value.rstrip() + "\n")


def write_csv_lf(
    path: Path, rows: Sequence[Mapping[str, Any]], fieldnames: Sequence[str]
) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def _powershell(script: str) -> str | None:
    if os.name != "nt":
        return None
    try:
        completed = subprocess.run(
            ["powershell", "-NoProfile", "-Command", script],
            cwd=ROOT,
            text=True,
            capture_output=True,
            timeout=10,
            check=True,
        )
    except (OSError, subprocess.SubprocessError):
        return None
    value = completed.stdout.strip()
    return value or None


def _computer_identity() -> tuple[str, str, float]:
    value = _powershell(
        "$v=Get-CimInstance Win32_ComputerSystem; "
        "\"$($v.Manufacturer)|$($v.Model)|$($v.TotalPhysicalMemory)\""
    )
    if value:
        parts = value.split("|", 2)
        if len(parts) == 3:
            try:
                ram_gib = int(parts[2]) / (1024.0**3)
            except ValueError:
                ram_gib = 1.0
            return parts[0] or "unknown", parts[1] or "unknown", max(ram_gib, 0.001)
    return platform.node() or "unknown", platform.machine() or "unknown", 1.0


def _processor_identity() -> tuple[str, int, int]:
    value = _powershell(
        "$v=Get-CimInstance Win32_Processor; "
        "\"$(($v.Name -join '; '))|$(($v.NumberOfCores | Measure-Object -Sum).Sum)|"
        "$(($v.NumberOfLogicalProcessors | Measure-Object -Sum).Sum)\""
    )
    logical_fallback = max(1, os.cpu_count() or 1)
    if value:
        parts = value.split("|", 2)
        if len(parts) == 3:
            try:
                return parts[0] or platform.processor() or "unknown", max(1, int(parts[1])), max(1, int(parts[2]))
            except ValueError:
                pass
    return platform.processor() or platform.machine() or "unknown", logical_fallback, logical_fallback


def _video_controllers() -> str | None:
    return _powershell("(Get-CimInstance Win32_VideoController).Name -join '; '")


def _npu_names() -> str | None:
    return _powershell(
        "$v=Get-PnpDevice -PresentOnly -ErrorAction SilentlyContinue | "
        "Where-Object {$_.FriendlyName -match 'NPU|Neural Processing'}; "
        "($v.FriendlyName -join '; ')"
    )


def require_lens_interpreter() -> None:
    """Fail if this is not the approved Python 3.10 lens interpreter."""

    if platform.python_version() != REQUIRED_PYTHON:
        raise RuntimeError(
            f"expected Python {REQUIRED_PYTHON}, got {platform.python_version()}"
        )
    executable = Path(sys.executable).as_posix().lower()
    if "/envs/lens/" not in executable:
        raise RuntimeError(f"expected conda environment lens, got {sys.executable}")
