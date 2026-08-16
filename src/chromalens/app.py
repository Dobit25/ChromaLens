"""Hardware-independent command-line entry point for ChromaLens AI."""

from __future__ import annotations

import argparse
from collections.abc import Sequence

from chromalens import __version__


def build_parser() -> argparse.ArgumentParser:
    """Build the T00 CLI parser without loading camera or model backends."""

    parser = argparse.ArgumentParser(
        prog="chromalens",
        description=(
            "ChromaLens AI local color-vision assistance. "
            "Camera and video execution are introduced in T01."
        ),
    )
    parser.add_argument(
        "--version",
        action="version",
        version=f"%(prog)s {__version__}",
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    """Parse CLI arguments and return a process exit status."""

    parser = build_parser()
    parser.parse_args(argv)
    if argv is None or len(argv) == 0:
        parser.print_help()
    return 0
