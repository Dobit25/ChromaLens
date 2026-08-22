"""Hardware-independent contract tests for the T09 manual-ROI baseline tool."""

from __future__ import annotations

from datetime import datetime, timezone
import importlib.util
import json
from pathlib import Path
import shutil
import subprocess
import sys

import pytest


ROOT = Path(__file__).resolve().parents[2]
MODULE_PATH = ROOT / "scripts" / "t09_responsible_ai_manual_roi.py"
SPEC = importlib.util.spec_from_file_location("t09_manual_roi", MODULE_PATH)
assert SPEC and SPEC.loader
manual = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = manual
SPEC.loader.exec_module(manual)

FIXTURE_DIR = ROOT / "tests" / "samples" / "t02"
COMMIT = "a" * 40
STARTED = datetime(2026, 8, 22, 12, 0, 0, tzinfo=timezone.utc)
ENDED = datetime(2026, 8, 22, 12, 1, 0, tzinfo=timezone.utc)
ENVIRONMENT = {
    "manufacturer": "Intel", "model": "Mock laptop", "operating_system": "Windows 11",
    "cpu": "Mock CPU", "physical_core_count": 8, "logical_processor_count": 16,
    "ram_gib": 32.0, "gpu": "Mock GPU", "npu": "not detected", "python_version": "3.10.20",
    "package_versions": {"chromalens-ai": "0.1", "numpy": "2.0", "opencv-contrib-python": "4.0",
                         "mediapipe": "0.10", "daltonlens": "0.1"},
    "lock_sha256": "b" * 64,
}


class Clock:
    def __init__(self, values: list[float]) -> None:
        self.values = iter(values)

    def __call__(self) -> float:
        return next(self.values)


def _verified() -> tuple[object, ...]:
    return manual.verify_fixtures(FIXTURE_DIR)


def _selector(recorded: list[str] | None = None):
    def select(path: Path, _instructions: str, ready) -> object:
        if recorded is not None:
            recorded.append(path.name)
        ready()
        return manual.Roi(1, 2, 30, 40)
    return select


def _trials() -> tuple[object, ...]:
    return manual.run_trials(
        _verified(), _selector(), clock=Clock([0, 3, 4, 5, 6, 11, 12, 14, 15, 19])
    )


def _resolution(path: Path) -> dict[str, int]:
    values = {
        "astronaut.png": {"width": 512, "height": 512},
        "cc0_woman.jpg": {"width": 360, "height": 720},
        "loc_lincoln.jpg": {"width": 640, "height": 480},
        "loc_man.jpg": {"width": 800, "height": 600},
        "nasa_shepard.jpg": {"width": 240, "height": 360},
    }
    return values[path.name]


def _payload(**overrides: object) -> dict[str, object]:
    args: dict[str, object] = {
        "operator": "Trinh", "command": "manual-roi --operator Trinh", "git_commit": COMMIT,
        "started_at_utc": STARTED, "ended_at_utc": ENDED, "environment": ENVIRONMENT,
        "resolution_reader": _resolution,
    }
    args.update(overrides)
    return manual.build_payload(
        _verified(), _trials(), **args,
    )


def _copy_fixture_set(destination: Path) -> None:
    destination.mkdir()
    for spec in manual.FIXTURES:
        shutil.copy2(FIXTURE_DIR / spec.name, destination / spec.name)


def test_happy_path_uses_all_five_in_fixed_order_and_reports_median() -> None:
    fixtures = _verified()
    seen: list[str] = []
    trials = manual.run_trials(
        fixtures, _selector(seen), clock=Clock([0, 3, 4, 5, 6, 11, 12, 14, 15, 19])
    )
    payload = manual.build_payload(
        fixtures, trials, operator="Trinh", command="manual-roi", git_commit=COMMIT,
        started_at_utc=STARTED, ended_at_utc=ENDED, environment=ENVIRONMENT,
        resolution_reader=_resolution,
    )

    assert seen == [spec.name for spec in manual.FIXTURES]
    assert [trial.completion_seconds for trial in trials] == [3, 1, 5, 2, 4]
    metric = payload["metrics"][0]
    assert metric == {
        "name": "manual_baseline_completion_seconds", "aggregation": "median", "unit": "second",
        "status": "MEASURED", "value": 3, "case_ids": ["BASELINE-MANUAL-ROI"],
        "threshold_id": "observation_only", "threshold_result": "NOT_EVALUATED", "reason": "",
        "method": "Monotonic wall-clock time from image-ready notification to confirmed valid manual ROI.",
    }
    assert payload["result_status"] == "COMPLETE"
    assert payload["cases"][0]["case_id"] == "BASELINE-MANUAL-ROI"
    assert payload["cases"][0]["fixture_id"] == "manual-roi-public-fixtures"


def test_fixture_verification_rejects_missing_extra_and_hash_mismatch(tmp_path: Path) -> None:
    missing = tmp_path / "missing"
    _copy_fixture_set(missing)
    (missing / manual.FIXTURES[-1].name).unlink()
    with pytest.raises(manual.FixtureValidationError, match="missing"):
        manual.verify_fixtures(missing)

    extra = tmp_path / "extra"
    _copy_fixture_set(extra)
    (extra / "unlocked.jpg").write_bytes(b"not a fixture")
    with pytest.raises(manual.FixtureValidationError, match="extra"):
        manual.verify_fixtures(extra)

    wrong_hash = tmp_path / "wrong-hash"
    _copy_fixture_set(wrong_hash)
    (wrong_hash / manual.FIXTURES[0].name).write_bytes(b"tampered")
    with pytest.raises(manual.FixtureValidationError, match="SHA-256 mismatch"):
        manual.verify_fixtures(wrong_hash)


@pytest.mark.parametrize("roi", [None, manual.Roi(0, 0, 0, 10), manual.Roi(0, 0, 10, 0)])
def test_cancel_or_empty_roi_fails_closed(roi: object) -> None:
    def select(_path: Path, _instructions: str, ready) -> object:
        ready()
        return roi

    with pytest.raises(manual.ManualRoiError):
        manual.run_trials(_verified(), select, clock=Clock([0]))


def test_build_payload_rejects_incomplete_trials_or_wrong_order() -> None:
    fixtures = _verified()
    with pytest.raises(manual.ManualRoiError, match="exactly five"):
        manual.build_payload(
            fixtures, _trials()[:-1], operator="Trinh", command="manual-roi", git_commit=COMMIT,
            started_at_utc=STARTED, ended_at_utc=ENDED, environment=ENVIRONMENT,
            resolution_reader=_resolution,
        )
    with pytest.raises(manual.FixtureValidationError, match="fixed order"):
        manual.run_trials(tuple(reversed(fixtures)), _selector(), clock=Clock([0, 1]))


@pytest.mark.parametrize("values", [[-1], [float("nan")], [float("inf")], [2, 1]])
def test_invalid_clock_values_fail_closed(values: list[float]) -> None:
    with pytest.raises(manual.ManualRoiError):
        manual.run_trials(_verified(), _selector(), clock=Clock(values))


def test_git_sha_failure_is_explicit(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        manual.subprocess, "run",
        lambda *args, **kwargs: subprocess.CompletedProcess(args[0], 1, "", "not a repo"),
    )
    with pytest.raises(RuntimeError, match="cannot determine git commit"):
        manual._git_commit()
    monkeypatch.setattr(
        manual.subprocess, "run",
        lambda *args, **kwargs: subprocess.CompletedProcess(args[0], 0, "A" * 40 + "\n", ""),
    )
    with pytest.raises(RuntimeError, match="lowercase"):
        manual._git_commit()


def test_output_is_confined_and_existing_result_is_not_overwritten(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(manual, "DEFAULT_OUTPUT_DIR", tmp_path / "allowed")
    with pytest.raises(manual.ManualRoiError, match="inside"):
        manual.validate_output_dir(tmp_path / "outside")

    created = ENDED
    one = manual.make_result_id(created, token="one")
    two = manual.make_result_id(created, token="two")
    assert one != two
    assert one.endswith("20260822t120100z")

    allowed = manual.DEFAULT_OUTPUT_DIR / "pytest-manual-roi"
    payload = _payload()
    payload["result_id"] = one
    try:
        written = manual.write_payload(payload, allowed)
        assert written.name == f"{one}.json"
        with pytest.raises(manual.ManualRoiError, match="overwrite"):
            manual.write_payload(payload, allowed)
    finally:
        if 'written' in locals() and written.exists():
            written.unlink()
        if allowed.exists() and not any(allowed.iterdir()):
            allowed.rmdir()


def test_payload_is_timing_only_and_never_embeds_visual_media() -> None:
    payload = _payload()
    encoded_notes = payload["notes"].lower()
    assert payload["artifacts"] == []
    assert "completion_seconds" in payload["notes"]
    assert "fixture_sha256" in payload["notes"]
    assert '"x"' not in payload["notes"]
    assert '"width"' not in payload["notes"]
    assert "crop" not in encoded_notes
    assert "screenshot" not in encoded_notes
    assert "data:image" not in encoded_notes
    assert "base64" not in encoded_notes


def test_failure_before_payload_creation_cannot_leave_complete_artifact(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(manual, "DEFAULT_OUTPUT_DIR", tmp_path / "allowed")
    output = manual.DEFAULT_OUTPUT_DIR / "pytest-no-complete"
    before = set(output.glob("*.json")) if output.exists() else set()
    with pytest.raises(manual.ManualRoiError):
        manual.run_trials(_verified(), lambda *_args: None, clock=Clock([]))
    after = set(output.glob("*.json")) if output.exists() else set()
    assert after == before


def test_wrong_python_fails_before_fixture_or_gui_work(monkeypatch: pytest.MonkeyPatch) -> None:
    with pytest.raises(manual.ManualRoiError, match="3.10.20"):
        manual.validate_python_version("3.11.9")
    monkeypatch.setattr(manual.platform, "python_version", lambda: "3.11.9")
    monkeypatch.setattr(manual, "verify_fixtures", lambda _path: pytest.fail("fixtures must not be opened"))
    assert manual.main([]) == 2


def test_collect_environment_matches_benchmark_hardware_and_package_contract(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(manual, "_windows_computer_identity", lambda: ("Intel", "MockBook"))
    monkeypatch.setattr(manual, "_physical_core_count", lambda: 8)
    monkeypatch.setattr(manual.os, "cpu_count", lambda: 16)
    monkeypatch.setattr(manual, "_windows_video_controllers", lambda: "Intel Arc")
    monkeypatch.setattr(manual, "_ram_gib", lambda: 32.0)
    monkeypatch.setattr(manual.platform, "platform", lambda: "Windows 11")
    monkeypatch.setattr(manual.platform, "processor", lambda: "Mock CPU")
    monkeypatch.setattr(manual, "_package_versions", lambda: ENVIRONMENT["package_versions"])
    monkeypatch.setattr(manual, "_sha256", lambda _path: "c" * 64)

    environment = manual.collect_environment()
    assert environment["manufacturer"] == "Intel"
    assert environment["model"] == "MockBook"
    assert environment["physical_core_count"] == 8
    assert environment["logical_processor_count"] == 16
    assert environment["gpu"] == "Intel Arc"
    assert set(environment["package_versions"]) == {
        "chromalens-ai", "numpy", "opencv-contrib-python", "mediapipe", "daltonlens"
    }
    assert environment["lock_sha256"] == "c" * 64


def test_payload_rejects_forged_or_changed_fixture_after_trial(tmp_path: Path) -> None:
    forged = list(_verified())
    forged[0] = manual.VerifiedFixture(forged[0].name, tmp_path / forged[0].name, forged[0].sha256)
    with pytest.raises(manual.FixtureValidationError, match="not canonical"):
        manual.build_payload(
            forged, _trials(), operator="Trinh", command="manual-roi", git_commit=COMMIT,
            started_at_utc=STARTED, ended_at_utc=ENDED, environment=ENVIRONMENT, resolution_reader=_resolution,
        )

    mutable = tmp_path / "mutable"
    _copy_fixture_set(mutable)
    verified = manual.verify_fixtures(mutable)
    (mutable / manual.FIXTURES[0].name).write_bytes(b"changed after selection")
    with pytest.raises(manual.FixtureValidationError, match="changed during measurement"):
        manual.build_payload(
            verified, _trials(), operator="Trinh", command="manual-roi", git_commit=COMMIT,
            started_at_utc=STARTED, ended_at_utc=ENDED, environment=ENVIRONMENT, resolution_reader=_resolution,
            expected_input_dir=mutable,
        )


@pytest.mark.parametrize("value", [True, "1.2", 0, float("nan"), float("inf")])
def test_completion_seconds_must_be_positive_finite_non_bool(value: object) -> None:
    trials = list(_trials())
    trials[0] = manual.Trial(manual.FIXTURES[0].name, value)
    with pytest.raises(manual.ManualRoiError, match="completion_seconds"):
        manual.build_payload(
            _verified(), trials, operator="Trinh", command="manual-roi", git_commit=COMMIT,
            started_at_utc=STARTED, ended_at_utc=ENDED, environment=ENVIRONMENT, resolution_reader=_resolution,
        )


def test_command_timestamps_and_mixed_native_resolution_metadata_are_honest() -> None:
    payload = _payload()
    command = payload["commands"][0]
    assert command["started_at_utc"] == "2026-08-22T12:00:00Z"
    assert command["ended_at_utc"] == "2026-08-22T12:01:00Z"
    metadata = json.loads(payload["notes"].removeprefix("manual_roi_trial_metadata="))
    assert [(row["native_width"], row["native_height"]) for row in metadata] == [
        (512, 512), (360, 720), (640, 480), (800, 600), (240, 360)
    ]
    assert payload["environment"]["source_resolution"] == {"width": 1024, "height": 768}
    assert payload["configuration"]["settings"]["display_scaling"] == "letterbox_no_crop"
    with pytest.raises(manual.ManualRoiError, match="must not be after"):
        _payload(started_at_utc=ENDED, ended_at_utc=STARTED)


def test_atomic_write_cleans_temporary_and_never_publishes_partial_json(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(manual, "DEFAULT_OUTPUT_DIR", tmp_path / "allowed")
    payload = _payload()
    payload["result_id"] = manual.make_result_id(ENDED, token="atomic")
    destination_dir = manual.DEFAULT_OUTPUT_DIR / "atomic"
    destination = destination_dir / f"{payload['result_id']}.json"

    def fail_dump(*_args: object, **_kwargs: object) -> None:
        raise TypeError("serialize failure")

    monkeypatch.setattr(manual.json, "dump", fail_dump)
    with pytest.raises(manual.ManualRoiError, match="atomically"):
        manual.write_payload(payload, destination_dir)
    assert not destination.exists()
    assert not list(destination_dir.glob("*.tmp"))


def test_cleanup_failure_does_not_hide_primary_opencv_failure(monkeypatch: pytest.MonkeyPatch) -> None:
    class Image:
        shape = (10, 10, 3)

    class FakeCv2:
        INTER_AREA = 1
        BORDER_CONSTANT = 2
        FONT_HERSHEY_SIMPLEX = 3
        WINDOW_NORMAL = 4

        @staticmethod
        def imread(_path: str) -> Image:
            return Image()

        @staticmethod
        def resize(image: Image, _size: tuple[int, int], interpolation: int) -> Image:
            return image

        @staticmethod
        def copyMakeBorder(image: Image, *_args: object, **_kwargs: object) -> Image:
            return image

        @staticmethod
        def putText(*_args: object, **_kwargs: object) -> None:
            return None

        @staticmethod
        def namedWindow(*_args: object, **_kwargs: object) -> None:
            raise ValueError("primary GUI failure")

        @staticmethod
        def destroyWindow(*_args: object, **_kwargs: object) -> None:
            raise RuntimeError("cleanup failure")

    monkeypatch.setitem(sys.modules, "cv2", FakeCv2)
    with pytest.raises(ValueError, match="primary GUI failure"):
        manual.select_roi_opencv(FIXTURE_DIR / "astronaut.png", "instruction", lambda: None)


def test_canonical_fixture_directory_is_required_even_for_identical_copies(tmp_path: Path) -> None:
    copied = tmp_path / "identical-copies"
    _copy_fixture_set(copied)
    copied_fixtures = manual.verify_fixtures(copied)
    with pytest.raises(manual.FixtureValidationError, match="not canonical"):
        manual.build_payload(
            copied_fixtures, _trials(), operator="Trinh", command="manual-roi", git_commit=COMMIT,
            started_at_utc=STARTED, ended_at_utc=ENDED, environment=ENVIRONMENT, resolution_reader=_resolution,
        )
    with pytest.raises(manual.FixtureValidationError, match="canonical directory"):
        manual.verify_fixtures(copied, expected_input_dir=manual.DEFAULT_INPUT_DIR)


def test_cli_has_no_fixture_directory_override() -> None:
    with pytest.raises(SystemExit):
        manual.parse_args(["--input-dir", str(FIXTURE_DIR)])


@pytest.mark.parametrize("result_id", [
    "../escape", "..\\escape", "t09-manual-roi-token-20260822t120000z/extra",
    "t09-manual-roi-token-20260822t120000", "t09-manual-roi-Token-20260822t120000z",
    "C:\\outside.json",
])
def test_result_id_cannot_escape_or_create_temporary_files(
    result_id: str, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(manual, "DEFAULT_OUTPUT_DIR", tmp_path / "allowed")
    payload = _payload()
    payload["result_id"] = result_id
    destination_dir = manual.DEFAULT_OUTPUT_DIR / "nested"
    with pytest.raises(manual.ManualRoiError, match="result_id"):
        manual.write_payload(payload, destination_dir)
    assert not list(manual.DEFAULT_OUTPUT_DIR.rglob("*.json"))
    assert not list(manual.DEFAULT_OUTPUT_DIR.rglob("*.tmp"))
    assert not (tmp_path / "escape").exists()
    assert not (tmp_path / "outside.json").exists()


def test_cleanup_only_opencv_failure_is_fail_closed(monkeypatch: pytest.MonkeyPatch) -> None:
    class Image:
        shape = (10, 10, 3)

    class FakeCv2:
        INTER_AREA = 1
        BORDER_CONSTANT = 2
        FONT_HERSHEY_SIMPLEX = 3
        WINDOW_NORMAL = 4
        WND_PROP_VISIBLE = 5

        @staticmethod
        def imread(_path: str) -> Image:
            return Image()

        @staticmethod
        def resize(image: Image, _size: tuple[int, int], interpolation: int) -> Image:
            return image

        @staticmethod
        def copyMakeBorder(image: Image, *_args: object, **_kwargs: object) -> Image:
            return image

        @staticmethod
        def putText(*_args: object, **_kwargs: object) -> None:
            return None

        @staticmethod
        def namedWindow(*_args: object, **_kwargs: object) -> None:
            return None

        @staticmethod
        def imshow(*_args: object, **_kwargs: object) -> None:
            return None

        @staticmethod
        def waitKey(*_args: object, **_kwargs: object) -> int:
            return 0

        @staticmethod
        def getWindowProperty(*_args: object, **_kwargs: object) -> float:
            return 1.0

        @staticmethod
        def selectROI(*_args: object, **_kwargs: object) -> tuple[int, int, int, int]:
            return 1, 1, 2, 2

        @staticmethod
        def destroyWindow(*_args: object, **_kwargs: object) -> None:
            raise RuntimeError("cleanup only failure")

    monkeypatch.setitem(sys.modules, "cv2", FakeCv2)
    with pytest.raises(manual.ManualRoiError, match="clean up"):
        manual.select_roi_opencv(FIXTURE_DIR / "astronaut.png", "instruction", lambda: None)
