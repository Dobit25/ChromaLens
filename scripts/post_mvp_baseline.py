"""Capture a current-product Gate 0 benchmark without saving camera frames."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
from importlib import metadata
import json
from pathlib import Path
import platform
import re
import subprocess
import sys
from typing import Sequence


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUTPUT = ROOT / "artifacts/post_mvp/gate0/current-baseline-raw.json"
SUMMARY_PREFIX = "Pipeline complete:"


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Run the existing ChromaLens webcam path and save only terminal "
            "telemetry; no frame or image is persisted."
        )
    )
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--backend", choices=("schp-atr", "mediapipe-selfie-torso"), default="schp-atr")
    parser.add_argument("--camera-index", type=int, default=0)
    parser.add_argument("--width", type=int, default=480)
    parser.add_argument("--height", type=int, default=360)
    parser.add_argument("--warmup-seconds", type=float, default=15.0)
    parser.add_argument("--measurement-seconds", type=float, default=60.0)
    return parser


def _parse_summary(stdout: str) -> dict[str, str]:
    lines = [line.strip() for line in stdout.splitlines() if line.startswith(SUMMARY_PREFIX)]
    if len(lines) != 1:
        raise RuntimeError(f"expected one {SUMMARY_PREFIX!r} line, found {len(lines)}")
    return dict(re.findall(r"([a-zA-Z0-9_]+)=([^ ]+)", lines[0]))


def _package_versions() -> dict[str, str]:
    names = (
        "chromalens-ai",
        "numpy",
        "opencv-contrib-python",
        "Pillow",
        "daltonlens",
        "openvino",
        "torch",
        "mediapipe",
    )
    versions: dict[str, str] = {}
    for name in names:
        try:
            versions[name] = metadata.version(name)
        except metadata.PackageNotFoundError:
            versions[name] = "NOT_INSTALLED"
    return versions


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def run(argv: Sequence[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    if args.warmup_seconds < 0 or args.measurement_seconds <= 0:
        raise ValueError("warmup must be non-negative and measurement must be positive")

    command = [
        sys.executable,
        "-m",
        "chromalens",
        "--webcam",
        "--no-display",
        "--backend",
        args.backend,
        "--camera-index",
        str(args.camera_index),
        "--width",
        str(args.width),
        "--height",
        str(args.height),
        "--metrics-warmup-seconds",
        str(args.warmup_seconds),
        "--duration-seconds",
        str(args.measurement_seconds),
    ]
    started = datetime.now(timezone.utc)
    completed = subprocess.run(
        command,
        cwd=ROOT,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=args.warmup_seconds + args.measurement_seconds + 300.0,
        check=False,
    )
    ended = datetime.now(timezone.utc)
    summary = _parse_summary(completed.stdout) if completed.returncode == 0 else {}
    git_commit = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=True,
    ).stdout.strip()
    lock_path = ROOT / "requirements/segment-schp-py310-win64.lock"
    payload = {
        "format": "chromalens-post-mvp-gate0-raw-1.0",
        "created_at_utc": ended.isoformat().replace("+00:00", "Z"),
        "started_at_utc": started.isoformat().replace("+00:00", "Z"),
        "git_commit": git_commit,
        "git_worktree_disclosure": "Gate files and unrelated pre-existing presentation files were dirty; measured product source was unchanged from git_commit.",
        "host_role": "development",
        "declared_demo_hardware": False,
        "platform": platform.platform(),
        "python_version": platform.python_version(),
        "python_executable": sys.executable,
        "package_versions": _package_versions(),
        "lock_path": lock_path.relative_to(ROOT).as_posix(),
        "lock_sha256": _sha256(lock_path),
        "command": command,
        "exit_code": completed.returncode,
        "stdout": completed.stdout,
        "stderr": completed.stderr,
        "parsed_summary": summary,
        "privacy": {
            "display_mode": "headless",
            "frames_saved_by_wrapper": 0,
            "frames_uploaded": 0,
            "camera_identifier_stored": "index only; no serial or instance ID",
        },
        "latency_semantics": {
            "source_read_to_render_ms": "after VideoCapture.read returned to render/compositor complete",
            "source_read_to_display_submit_ms": "NOT_MEASURED: headless run",
            "sensor_to_photon_ms": "NOT_MEASURED: no synchronized external apparatus",
        },
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8", newline="\n")
    print(f"wrote {args.output}")
    return completed.returncode


if __name__ == "__main__":
    raise SystemExit(run())
