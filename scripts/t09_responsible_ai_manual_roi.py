"""Fail-closed manual-ROI baseline recorder for T09.

This utility records only operator timing and locked-fixture hashes.  It never
writes an image, crop, screenshot, ROI pixel data, or a partial result.
"""

from __future__ import annotations

import argparse
from dataclasses import dataclass
from datetime import datetime, timezone
import hashlib
import importlib.metadata
import json
import math
import os
from pathlib import Path
import platform
import re
import secrets
import statistics
import subprocess
import sys
import tempfile
import time
from typing import Any, Callable, Mapping, Sequence

from chromalens import __version__


ROOT = Path(__file__).resolve().parents[1]
CASE_ID = "BASELINE-MANUAL-ROI"
FIXTURE_ID = "manual-roi-public-fixtures"
WORKSTREAM = "performance_responsible_ai"
DEFAULT_INPUT_DIR = ROOT / "tests" / "samples" / "t02"
DEFAULT_OUTPUT_DIR = ROOT / "artifacts" / "t09" / WORKSTREAM
LOCK_PATH = ROOT / "requirements" / "segment-mediapipe-py310-win64.lock"
GIT_SHA = re.compile(r"^[0-9a-f]{40}$")
RESULT_ID = re.compile(r"^t09-manual-roi-[a-z0-9]+-[0-9]{8}t[0-9]{6}z$")
REQUIRED_PYTHON_VERSION = "3.10.20"
DISPLAY_CANVAS_RESOLUTION = (1024, 768)

INSTRUCTIONS = (
    "Manual ROI baseline: for this image select exactly one rectangle around the "
    "most visible upper-body/garment region. Press ENTER or SPACE to confirm a "
    "non-empty rectangle; press C or close the window to cancel. This is a timed "
    "trial and has no practice round."
)


class ManualRoiError(RuntimeError):
    """A condition that must prevent creation of a COMPLETE artifact."""


class FixtureValidationError(ManualRoiError):
    """The fixed public-fixture contract was not met."""


class SelectionCancelledError(ManualRoiError):
    """The operator did not confirm a valid rectangle."""


@dataclass(frozen=True)
class FixtureSpec:
    name: str
    sha256: str


@dataclass(frozen=True)
class VerifiedFixture:
    name: str
    path: Path
    sha256: str


@dataclass(frozen=True)
class Roi:
    x: int
    y: int
    width: int
    height: int

    @property
    def valid(self) -> bool:
        return self.width > 0 and self.height > 0


@dataclass(frozen=True)
class Trial:
    fixture_name: str
    completion_seconds: float


FIXTURES: tuple[FixtureSpec, ...] = (
    FixtureSpec("astronaut.png", "88431cd9653ccd539741b555fb0a46b61558b301d4110412b5bc28b5e3ea6cb5"),
    FixtureSpec("cc0_woman.jpg", "9659315a44a6d3eadf8814b314193aacc78033097aa4dee4da0fadbfcaec025d"),
    FixtureSpec("loc_lincoln.jpg", "a305c6630a3ac49dc9fe2ebe9f218ba7bb91df715c2dd860d038a585e030c15f"),
    FixtureSpec("loc_man.jpg", "50eb295eb7cf909350c67c74b3b306a1e7018261505c866f88f77b035ada0d94"),
    FixtureSpec("nasa_shepard.jpg", "3f8ef484565605683cfe5b4aec510c165afafbfe00477899faecfb521a097488"),
)

ReadyCallback = Callable[[], None]
Selector = Callable[[Path, str, ReadyCallback], Roi | None]
Clock = Callable[[], float]
ResolutionReader = Callable[[Path], dict[str, int]]


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def verify_fixtures(
    input_dir: Path, *, expected_input_dir: Path | None = None
) -> tuple[VerifiedFixture, ...]:
    """Verify the exact names, count, order, and bytes before any GUI opens."""
    if expected_input_dir is not None and input_dir.resolve() != expected_input_dir.resolve():
        raise FixtureValidationError(
            f"fixture directory must be the canonical directory: {expected_input_dir.resolve()}"
        )
    if not input_dir.is_dir():
        raise FixtureValidationError(f"fixture directory is unavailable: {input_dir}")
    expected_names = {fixture.name for fixture in FIXTURES}
    actual_names = {
        path.name for path in input_dir.iterdir()
        if path.is_file() and path.name != "README.md"
    }
    if actual_names != expected_names:
        missing = sorted(expected_names - actual_names)
        extra = sorted(actual_names - expected_names)
        raise FixtureValidationError(f"locked fixture set mismatch; missing={missing}, extra={extra}")
    verified: list[VerifiedFixture] = []
    for fixture in FIXTURES:
        path = input_dir / fixture.name
        observed = _sha256(path)
        if observed != fixture.sha256:
            raise FixtureValidationError(
                f"SHA-256 mismatch for {fixture.name}: expected {fixture.sha256}, got {observed}"
            )
        verified.append(VerifiedFixture(fixture.name, path, observed))
    return tuple(verified)


def validate_verified_fixtures(
    fixtures: Sequence[VerifiedFixture], *, expected_input_dir: Path = DEFAULT_INPUT_DIR
) -> tuple[VerifiedFixture, ...]:
    """Re-check caller-supplied fixture objects and their bytes after trials."""
    if len(fixtures) != len(FIXTURES):
        raise FixtureValidationError("exactly five locked fixtures are required")
    expected_root = expected_input_dir.resolve()
    checked: list[VerifiedFixture] = []
    for supplied, locked in zip(fixtures, FIXTURES, strict=True):
        if not isinstance(supplied, VerifiedFixture):
            raise FixtureValidationError("fixture must be a VerifiedFixture from locked verification")
        if supplied.name != locked.name or supplied.path.name != locked.name:
            raise FixtureValidationError(f"fixture identity/path mismatch for {locked.name}")
        if supplied.path.resolve() != (expected_root / locked.name).resolve():
            raise FixtureValidationError(f"fixture path is not canonical for {locked.name}")
        if supplied.sha256 != locked.sha256:
            raise FixtureValidationError(f"fixture SHA declaration mismatch for {locked.name}")
        if not supplied.path.is_file():
            raise FixtureValidationError(f"locked fixture disappeared: {locked.name}")
        if _sha256(supplied.path) != locked.sha256:
            raise FixtureValidationError(f"locked fixture changed during measurement: {locked.name}")
        checked.append(supplied)
    return tuple(checked)


def validate_python_version(version: str | None = None) -> str:
    """Require the frozen interpreter before loading a fixture or opening a GUI."""
    observed = platform.python_version() if version is None else version
    if observed != REQUIRED_PYTHON_VERSION:
        raise ManualRoiError(
            f"Manual ROI baseline requires Python {REQUIRED_PYTHON_VERSION}; observed {observed}"
        )
    return observed


def _finite_clock_value(value: float, label: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ManualRoiError(f"{label} clock value is not numeric")
    numeric = float(value)
    if not math.isfinite(numeric) or numeric < 0:
        raise ManualRoiError(f"{label} clock value must be finite and non-negative")
    return numeric


def run_trials(
    fixtures: Sequence[VerifiedFixture], selector: Selector, *, clock: Clock = time.monotonic
) -> tuple[Trial, ...]:
    """Run exactly the five required trials; the selector marks image readiness."""
    if tuple(item.name for item in fixtures) != tuple(item.name for item in FIXTURES):
        raise FixtureValidationError("trials require the five locked fixtures in their fixed order")
    trials: list[Trial] = []
    for fixture in fixtures:
        started_at: float | None = None

        def ready() -> None:
            nonlocal started_at
            if started_at is not None:
                raise ManualRoiError("selector marked one image ready more than once")
            started_at = _finite_clock_value(clock(), "start")

        roi = selector(fixture.path, INSTRUCTIONS, ready)
        if roi is None:
            raise SelectionCancelledError(f"selection cancelled for {fixture.name}")
        if not isinstance(roi, Roi) or not roi.valid:
            raise SelectionCancelledError(f"empty or invalid ROI for {fixture.name}")
        if started_at is None:
            raise ManualRoiError(f"selector did not mark image ready for {fixture.name}")
        ended_at = _finite_clock_value(clock(), "end")
        elapsed = ended_at - started_at
        if not math.isfinite(elapsed) or elapsed <= 0:
            raise ManualRoiError(f"completion time must be finite and greater than zero for {fixture.name}")
        trials.append(Trial(fixture.name, elapsed))
    if len(trials) != len(FIXTURES):
        raise ManualRoiError("all five valid trials are required")
    return tuple(trials)


def _letterbox_to_canvas(image: Any, cv2: Any) -> Any:
    """Fit every native fixture into one declared canvas without cropping."""
    canvas_width, canvas_height = DISPLAY_CANVAS_RESOLUTION
    image_height, image_width = image.shape[:2]
    scale = min(canvas_width / image_width, canvas_height / image_height)
    resized_width = max(1, round(image_width * scale))
    resized_height = max(1, round(image_height * scale))
    resized = cv2.resize(image, (resized_width, resized_height), interpolation=cv2.INTER_AREA)
    left = (canvas_width - resized_width) // 2
    right = canvas_width - resized_width - left
    top = (canvas_height - resized_height) // 2
    bottom = canvas_height - resized_height - top
    return cv2.copyMakeBorder(resized, top, bottom, left, right, cv2.BORDER_CONSTANT, value=(0, 0, 0))


def select_roi_opencv(path: Path, instructions: str, ready: ReadyCallback) -> Roi | None:
    """Interactive selector, imported lazily so unit tests never require a GUI."""
    try:
        import cv2  # type: ignore[import-not-found]
    except ImportError as exc:  # pragma: no cover - environment-specific
        raise ManualRoiError("OpenCV is required for interactive manual ROI selection") from exc
    image = cv2.imread(str(path))
    if image is None:
        raise FixtureValidationError(f"OpenCV could not read locked fixture: {path.name}")
    window = "ChromaLens T09 manual ROI"
    primary_error: BaseException | None = None
    try:
        preview = _letterbox_to_canvas(image, cv2)
        y = 24
        for line in ("Select one visible upper-body/garment rectangle.", "ENTER/SPACE confirms; C/c or close cancels."):
            cv2.putText(preview, line, (10, y), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (0, 255, 255), 2)
            y += 26
        cv2.namedWindow(window, cv2.WINDOW_NORMAL)
        cv2.imshow(window, preview)
        cv2.waitKey(1)  # the instruction and image are visible before timing starts
        if cv2.getWindowProperty(window, cv2.WND_PROP_VISIBLE) < 1:
            return None
        ready()
        x, y, width, height = cv2.selectROI(window, preview, showCrosshair=True, fromCenter=False)
        if cv2.getWindowProperty(window, cv2.WND_PROP_VISIBLE) < 1:
            return None
        return Roi(int(x), int(y), int(width), int(height))
    except BaseException as exc:
        primary_error = exc
        raise
    finally:
        try:
            cv2.destroyWindow(window)
        except Exception as cleanup_error:
            if primary_error is None:
                raise ManualRoiError("could not clean up Manual ROI OpenCV window") from cleanup_error


def _git_commit() -> str:
    completed = subprocess.run(
        ["git", "rev-parse", "HEAD"], cwd=ROOT, text=True,
        capture_output=True, check=False,
    )
    if completed.returncode != 0:
        detail = completed.stderr.strip() or completed.stdout.strip() or "unknown git error"
        raise RuntimeError(f"cannot determine git commit: {detail}")
    commit = completed.stdout.strip()
    if not GIT_SHA.fullmatch(commit):
        raise RuntimeError(f"git commit must be 40 lowercase hexadecimal characters: {commit!r}")
    return commit


def _package_versions() -> dict[str, str]:
    versions = {"chromalens-ai": __version__}
    for name in ("numpy", "opencv-contrib-python", "mediapipe", "daltonlens"):
        try:
            versions[name] = importlib.metadata.version(name)
        except importlib.metadata.PackageNotFoundError:
            versions[name] = "not_installed"
    return versions


def _powershell(command: str) -> str:
    if os.name != "nt":
        return ""
    try:
        return subprocess.run(
            ["powershell", "-NoProfile", "-Command", command], check=True,
            capture_output=True, text=True, timeout=5,
        ).stdout.strip()
    except (OSError, subprocess.CalledProcessError, subprocess.TimeoutExpired):
        return ""


def _windows_computer_identity() -> tuple[str, str]:
    output = _powershell(
        "(Get-CimInstance Win32_ComputerSystem | Select-Object -Property Manufacturer,Model | ConvertTo-Json -Compress)"
    )
    try:
        value = json.loads(output)
        return str(value.get("Manufacturer") or "unknown"), str(value.get("Model") or "unknown")
    except (json.JSONDecodeError, AttributeError):
        return "unknown", platform.node() or "unknown"


def _physical_core_count() -> int:
    output = _powershell("(Get-CimInstance Win32_Processor | Measure-Object -Property NumberOfCores -Sum).Sum")
    try:
        return max(1, int(output))
    except ValueError:
        return os.cpu_count() or 1


def _windows_video_controllers() -> str:
    output = _powershell(
        "(Get-CimInstance Win32_VideoController | Select-Object -ExpandProperty Name | ConvertTo-Json -Compress)"
    )
    try:
        values = json.loads(output)
    except json.JSONDecodeError:
        return "not detected"
    if isinstance(values, list):
        return "; ".join(str(value) for value in values) or "not detected"
    return str(values) if values else "not detected"


def _ram_gib() -> float:
    if os.name == "nt":
        import ctypes

        class MemoryStatus(ctypes.Structure):
            _fields_ = [("dwLength", ctypes.c_ulong), ("dwMemoryLoad", ctypes.c_ulong),
                       ("ullTotalPhys", ctypes.c_ulonglong), ("ullAvailPhys", ctypes.c_ulonglong),
                       ("ullTotalPageFile", ctypes.c_ulonglong), ("ullAvailPageFile", ctypes.c_ulonglong),
                       ("ullTotalVirtual", ctypes.c_ulonglong), ("ullAvailVirtual", ctypes.c_ulonglong),
                       ("ullAvailExtendedVirtual", ctypes.c_ulonglong)]

        status = MemoryStatus()
        status.dwLength = ctypes.sizeof(status)
        if ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(status)):
            return status.ullTotalPhys / (1024.0 ** 3)
    return max(0.001, float(os.sysconf("SC_PAGE_SIZE") * os.sysconf("SC_PHYS_PAGES")) / (1024.0 ** 3))


def _native_resolution(path: Path) -> dict[str, int]:
    try:
        import cv2  # type: ignore[import-not-found]
    except ImportError as exc:  # pragma: no cover - installed in supported environment
        raise ManualRoiError("OpenCV is required to record fixture resolution") from exc
    image = cv2.imread(str(path))
    if image is None:
        raise FixtureValidationError(f"OpenCV could not read locked fixture: {path.name}")
    height, width = image.shape[:2]
    return {"width": int(width), "height": int(height)}


def collect_environment() -> dict[str, object]:
    """Use the same host/provenance collection contract as the performance runner."""
    manufacturer, model = _windows_computer_identity()
    return {
        "manufacturer": manufacturer,
        "model": model,
        "operating_system": platform.platform() or "unknown",
        "cpu": platform.processor() or platform.machine() or "unknown",
        "physical_core_count": _physical_core_count(),
        "logical_processor_count": os.cpu_count() or 1,
        "ram_gib": _ram_gib(),
        "gpu": _windows_video_controllers(),
        "npu": "not detected",
        "python_version": validate_python_version(),
        "package_versions": _package_versions(),
        "lock_sha256": _sha256(LOCK_PATH),
    }


def _utc_now() -> datetime:
    return datetime.now(timezone.utc).replace(microsecond=0)


def _timestamp(value: datetime) -> str:
    return value.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def make_result_id(created_at: datetime, *, token: str | None = None) -> str:
    safe_token = token or secrets.token_hex(4)
    if not re.fullmatch(r"[a-z0-9]+", safe_token):
        raise ValueError("result-id token must contain lowercase letters and digits only")
    result_id = f"t09-manual-roi-{safe_token}-{created_at.astimezone(timezone.utc):%Y%m%dt%H%M%Sz}"
    if RESULT_ID.fullmatch(result_id) is None:  # defensive contract assertion
        raise ManualRoiError("generated result_id does not match the frozen Manual ROI format")
    return result_id


def _metadata_note(
    fixtures: Sequence[VerifiedFixture], trials: Sequence[Trial], native_resolutions: Sequence[dict[str, int]]
) -> str:
    trial_data = [
        {"fixture_name": fixture.name, "fixture_sha256": fixture.sha256,
         "native_width": resolution["width"], "native_height": resolution["height"],
         "completion_seconds": trial.completion_seconds}
        for fixture, trial, resolution in zip(fixtures, trials, native_resolutions, strict=True)
    ]
    return "manual_roi_trial_metadata=" + json.dumps(trial_data, sort_keys=True, separators=(",", ":"))


def build_payload(
    fixtures: Sequence[VerifiedFixture], trials: Sequence[Trial], *, operator: str,
    command: str, started_at_utc: datetime, ended_at_utc: datetime,
    git_commit: str | None = None, environment: Mapping[str, object] | None = None,
    resolution_reader: ResolutionReader = _native_resolution,
    expected_input_dir: Path = DEFAULT_INPUT_DIR,
) -> dict[str, object]:
    """Create a COMPLETE schema-shaped payload only after five valid trials."""
    checked_fixtures = validate_verified_fixtures(fixtures, expected_input_dir=expected_input_dir)
    if len(trials) != len(FIXTURES):
        raise ManualRoiError("COMPLETE requires exactly five verified fixtures and trials")
    if tuple(trial.fixture_name for trial in trials) != tuple(spec.name for spec in FIXTURES):
        raise ManualRoiError("trial fixture order does not match the locked contract")
    if not operator.strip():
        raise ManualRoiError("operator identifier is required")
    values: list[float] = []
    for trial in trials:
        if not isinstance(trial, Trial):
            raise ManualRoiError("each completion time must be a Trial")
        value = trial.completion_seconds
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            raise ManualRoiError("completion_seconds must be a numeric non-bool value")
        numeric = float(value)
        if not math.isfinite(numeric) or numeric <= 0:
            raise ManualRoiError("completion_seconds must be finite and greater than zero")
        values.append(numeric)
    median = statistics.median(values)
    if not math.isfinite(median):
        raise ManualRoiError("manual baseline median must be finite")
    commit = git_commit if git_commit is not None else _git_commit()
    if not GIT_SHA.fullmatch(commit):
        raise RuntimeError("git commit must be a real 40-character lowercase SHA")
    started = _require_utc_timestamp(started_at_utc, "started_at_utc")
    ended = _require_utc_timestamp(ended_at_utc, "ended_at_utc")
    if started > ended:
        raise ManualRoiError("started_at_utc must not be after ended_at_utc")
    native_resolutions = [_validated_resolution(resolution_reader(item.path), item.name) for item in checked_fixtures]
    collected = dict(collect_environment() if environment is None else environment)
    if collected.get("python_version") != REQUIRED_PYTHON_VERSION:
        raise ManualRoiError("environment python_version must be the frozen Python 3.10.20")
    canvas_resolution = {"width": DISPLAY_CANVAS_RESOLUTION[0], "height": DISPLAY_CANVAS_RESOLUTION[1]}
    payload: dict[str, object] = {
        "protocol_version": "1.0.0", "schema_version": "1.0.0", "metric_registry_version": "1.0.0",
        "result_id": make_result_id(ended), "workstream": WORKSTREAM, "result_status": "COMPLETE",
        "git_commit": commit, "created_at_utc": _timestamp(ended),
        "operator": {"role": "performance_evaluator", "identifier": operator.strip()},
        "environment": {
            **collected,
            "host_role": "development", "declared_demo_hardware": False,
            "camera_or_source": "canonical in-memory 1024x768 letterbox canvas (no crop); individual native resolutions are in timing-only notes",
            "backend_name": "manual-human-roi", "backend_device": "human-operator", "source_kind": "manual_baseline",
            "source_resolution": canvas_resolution, "render_resolution": canvas_resolution, "display_mode": "not_applicable",
            "warmup_seconds": 0, "measurement_seconds": 0, "external_measurement_apparatus": None,
        },
        "cases": [{"case_id": CASE_ID, "status": "COMPLETE", "fixture_id": FIXTURE_ID,
                   "artifact_ids": [], "reason": "All five locked fixtures received one confirmed non-empty ROI."}],
        "configuration": {"cvd_profile": "not_applicable", "severity": None,
                          "thresholds": {"roi_width_must_be_positive": True, "roi_height_must_be_positive": True},
                          "settings": {"fixture_count": 5, "practice_trials_included": False,
                                       "display_canvas_width": DISPLAY_CANVAS_RESOLUTION[0],
                                       "display_canvas_height": DISPLAY_CANVAS_RESOLUTION[1],
                                       "display_scaling": "letterbox_no_crop"}},
        "metrics": [{"name": "manual_baseline_completion_seconds", "aggregation": "median", "unit": "second",
                     "status": "MEASURED", "value": median, "case_ids": [CASE_ID],
                     "threshold_id": "observation_only", "threshold_result": "NOT_EVALUATED", "reason": "",
                     "method": "Monotonic wall-clock time from image-ready notification to confirmed valid manual ROI."}],
        "artifacts": [],
        "commands": [{"command": command, "exit_code": 0, "started_at_utc": _timestamp(started),
                      "ended_at_utc": _timestamp(ended), "output_summary": "Recorded timing and fixture hashes only; no image-derived media saved."}],
        "failure_cases": [],
        "limitations": ["Manual ROI is a non-AI baseline and measures one operator's selection time on five public fixtures.",
                        "No practice trial is included; this artifact contains timing and fixture hashes only, never image pixels or crops."],
        "responsible_ai": {"runtime_local_offline": True, "frames_saved_by_default": False, "frames_uploaded_by_default": False,
                           "medical_diagnosis_claim": False, "user_selected_profile": True,
                           "privacy_summary": "The tool saves no frames, screenshots, crops, or pixel values.",
                           "bias_coverage_summary": "This five-image public fixture set is not demographic validation.",
                           "environmental_summary": "No model training or network service is used for this manual baseline.",
                           "license_summary": "Fixture rights and hashes are locked in tests/samples/t02/README.md.",
                           "user_validation_status": "NOT_MEASURED"},
        "notes": _metadata_note(checked_fixtures, trials, native_resolutions),
    }
    return payload


def _require_utc_timestamp(value: datetime, label: str) -> datetime:
    if not isinstance(value, datetime) or value.tzinfo is None:
        raise ManualRoiError(f"{label} must be a timezone-aware datetime")
    return value.astimezone(timezone.utc).replace(microsecond=0)


def _validated_resolution(value: Mapping[str, object], fixture_name: str) -> dict[str, int]:
    width, height = value.get("width"), value.get("height")
    if (isinstance(width, bool) or not isinstance(width, int) or width <= 0 or
            isinstance(height, bool) or not isinstance(height, int) or height <= 0):
        raise ManualRoiError(f"native resolution is invalid for {fixture_name}")
    return {"width": width, "height": height}


def validate_output_dir(output_dir: Path) -> Path:
    resolved = output_dir.resolve()
    allowed = DEFAULT_OUTPUT_DIR.resolve()
    try:
        resolved.relative_to(allowed)
    except ValueError as exc:
        raise ManualRoiError(f"output path must be inside {allowed}") from exc
    return resolved


def write_payload(payload: dict[str, object], output_dir: Path) -> Path:
    destination_dir = validate_output_dir(output_dir)
    destination_dir.mkdir(parents=True, exist_ok=True)
    result_id = _validated_result_id(payload.get("result_id"))
    destination = destination_dir / f"{result_id}.json"
    if destination.parent.resolve() != destination_dir.resolve():
        raise ManualRoiError("result destination escaped the allowed output directory")
    temporary_path: Path | None = None
    try:
        descriptor, temporary_name = tempfile.mkstemp(
            prefix=f".{result_id}.", suffix=".tmp", dir=destination_dir, text=True
        )
        temporary_path = Path(temporary_name)
        with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
            json.dump(payload, handle, ensure_ascii=False, indent=2, sort_keys=True)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        # os.link publishes only if destination does not exist; it cannot replace it.
        os.link(temporary_path, destination)
    except FileExistsError as exc:
        raise ManualRoiError(f"refusing to overwrite existing result: {destination}") from exc
    except (OSError, TypeError, ValueError) as exc:
        raise ManualRoiError(f"could not atomically write manual ROI result: {exc}") from exc
    finally:
        if temporary_path is not None:
            try:
                temporary_path.unlink(missing_ok=True)
            except OSError:
                pass
    return destination


def _validated_result_id(value: object) -> str:
    if not isinstance(value, str):
        raise ManualRoiError("payload has no valid result_id")
    if ("/" in value or "\\" in value or ".." in value or Path(value).is_absolute()
            or RESULT_ID.fullmatch(value) is None):
        raise ManualRoiError("result_id must match the frozen Manual ROI filename format")
    return value


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Record the T09 manual ROI baseline (no practice trials).")
    parser.add_argument("--operator", default="Trinh", help="non-sensitive operator identifier (default: Trinh)")
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)
    started_at = _utc_now()
    try:
        validate_python_version()
        fixtures = verify_fixtures(DEFAULT_INPUT_DIR, expected_input_dir=DEFAULT_INPUT_DIR)
        print(INSTRUCTIONS)
        trials = run_trials(fixtures, select_roi_opencv)
        ended_at = _utc_now()
        command = " ".join([Path(sys.argv[0]).name, *(argv if argv is not None else sys.argv[1:])])
        payload = build_payload(
            fixtures, trials, operator=args.operator, command=command,
            started_at_utc=started_at, ended_at_utc=ended_at,
        )
        destination = write_payload(payload, args.output_dir)
    except (ManualRoiError, RuntimeError) as exc:
        print(f"Manual ROI baseline failed closed: {exc}", file=sys.stderr)
        return 2
    print(f"Wrote timing-only manual baseline result: {destination}")
    return 0


if __name__ == "__main__":  # pragma: no cover - CLI entry point
    raise SystemExit(main())
