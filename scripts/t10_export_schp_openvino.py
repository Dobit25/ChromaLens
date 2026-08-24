"""Export the verified SCHP-ATR checkpoint to a checksummed OpenVINO IR."""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
from pathlib import Path
from time import perf_counter


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Strict-load SCHP-ATR and export a reproducible OpenVINO IR.",
    )
    parser.add_argument(
        "--checkpoint",
        type=Path,
        default=Path("models/schp/exp-schp-201908301523-atr.pth"),
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("models/schp/openvino/schp-atr-512.xml"),
    )
    parser.add_argument("--input-size", type=int, default=512)
    return parser


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _git_state() -> tuple[str, bool]:
    commit = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()
    dirty = bool(
        subprocess.run(
            ["git", "status", "--short"],
            check=True,
            capture_output=True,
            text=True,
        ).stdout.strip()
    )
    return commit, dirty


def main() -> int:
    args = _parser().parse_args()
    if args.input_size < 64 or args.input_size % 32 != 0:
        raise SystemExit("--input-size must be at least 64 and divisible by 32")

    import openvino
    import torch

    from chromalens.segmentation.schp_backend import (
        SCHP_ATR_CHECKPOINT_SHA256,
        SCHPSegmenter,
        SCHPSegmenterConfig,
    )

    output = args.output.resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    started = perf_counter()
    with SCHPSegmenter(
        SCHPSegmenterConfig(
            checkpoint_path=args.checkpoint,
            input_size=args.input_size,
            runtime="pytorch",
        )
    ) as backend:
        loaded = perf_counter()
        example = torch.zeros(
            (1, 3, args.input_size, args.input_size),
            dtype=torch.float32,
        )
        converted = openvino.convert_model(
            backend._model,  # noqa: SLF001 - controlled T10 conversion boundary
            example_input=example,
        )
        openvino.save_model(converted, output, compress_to_fp16=False)
    finished = perf_counter()

    binary = output.with_suffix(".bin")
    if not binary.is_file():
        raise RuntimeError("OpenVINO conversion did not produce the expected .bin")
    project_commit, dirty = _git_state()
    checkpoint = args.checkpoint.resolve()
    manifest = {
        "schema_version": "1.0.0",
        "backend": "schp-atr/openvino",
        "input_size": args.input_size,
        "precision": "FP32",
        "source_checkpoint": {
            "path": checkpoint.as_posix(),
            "bytes": checkpoint.stat().st_size,
            "sha256": _sha256(checkpoint),
            "expected_sha256": SCHP_ATR_CHECKPOINT_SHA256,
        },
        "source_code": {
            "upstream_commit": "eb84c432cc697f494d99662a05f2335eb2f26095",
            "project_commit": project_commit,
            "project_worktree_dirty": dirty,
        },
        "versions": {
            "python_torch": torch.__version__,
            "openvino": openvino.__version__,
        },
        "conversion": {
            "command": (
                "python scripts/t10_export_schp_openvino.py "
                f"--checkpoint {args.checkpoint.as_posix()} "
                f"--output {args.output.as_posix()} --input-size {args.input_size}"
            ),
            "strict_checkpoint_load_seconds": round(loaded - started, 6),
            "conversion_and_save_seconds": round(finished - loaded, 6),
        },
        "artifacts": {
            "xml": {"bytes": output.stat().st_size, "sha256": _sha256(output)},
            "bin": {"bytes": binary.stat().st_size, "sha256": _sha256(binary)},
        },
    }
    if manifest["source_checkpoint"]["sha256"] != SCHP_ATR_CHECKPOINT_SHA256:
        raise RuntimeError("source checkpoint changed during conversion")
    manifest_path = output.with_suffix(".manifest.json")
    manifest_path.write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(manifest, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
