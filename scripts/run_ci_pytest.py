"""Run pytest and expose a bounded failure tail as a GitHub annotation."""

from __future__ import annotations

import os
import subprocess
import sys
from typing import Sequence


_MAX_ANNOTATION_CHARACTERS = 12_000


def github_command_escape(value: str) -> str:
    """Escape text for the single-line GitHub workflow command protocol."""

    return (
        value.replace("%", "%25")
        .replace("\r", "%0D")
        .replace("\n", "%0A")
    )


def run(argv: Sequence[str] | None = None) -> int:
    """Run pytest unchanged and annotate its bounded output tail on failure."""

    arguments = list(sys.argv[1:] if argv is None else argv)
    completed = subprocess.run(
        [sys.executable, "-m", "pytest", *arguments],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=False,
    )
    output = completed.stdout or ""
    sys.stdout.write(output)
    if completed.returncode != 0 and os.environ.get("GITHUB_ACTIONS") == "true":
        tail = output[-_MAX_ANNOTATION_CHARACTERS:]
        print(
            "::error title=Pytest failure details::"
            + github_command_escape(tail)
        )
    return completed.returncode


if __name__ == "__main__":
    raise SystemExit(run())
