"""Generate a reproducible controlled evaluation table for T04."""

from __future__ import annotations

import argparse
import csv
from pathlib import Path

import numpy as np

from chromalens.color import (
    ColorExtractionConfig,
    extract_garment_colors,
)
from chromalens.contracts import GarmentRegion

DEFAULT_INPUT = Path("evaluation/t04_controlled_color_samples.csv")
DEFAULT_OUTPUT = Path(
    "evaluation/results/t04_color_naming_results.csv"
)

OUTPUT_FIELDS = (
    "expected_name",
    "predicted_name",
    "correct",
    "r",
    "g",
    "b",
    "lab_l",
    "lab_a",
    "lab_b",
    "cluster_ratio",
    "best_name_score",
    "color_margin",
    "retained_pixels",
    "note",
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Evaluate the complete T04 pipeline on 11 controlled "
            "basic-color patches."
        )
    )
    parser.add_argument(
        "--input",
        type=Path,
        default=DEFAULT_INPUT,
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=DEFAULT_OUTPUT,
    )
    return parser.parse_args()


def evaluate_sample(
    sample: dict[str, str],
) -> dict[str, object]:
    rgb = (
        int(sample["r"]),
        int(sample["g"]),
        int(sample["b"]),
    )

    corrected_rgb = np.full(
        (20, 20, 3),
        rgb,
        dtype=np.uint8,
    )
    garment_mask = np.ones((20, 20), dtype=np.bool_)
    garment = GarmentRegion(
        track_id=None,
        class_name="controlled-patch",
        mask=garment_mask,
        mask_confidence=1.0,
    )

    clusters = extract_garment_colors(
        corrected_rgb,
        garment,
        ColorExtractionConfig(mode="median"),
    )

    if len(clusters) != 1:
        raise RuntimeError(
            "a uniform controlled patch must produce exactly one cluster"
        )

    cluster = clusters[0]
    expected_name = sample["expected_name"]
    predicted_name = cluster.original_name

    return {
        "expected_name": expected_name,
        "predicted_name": predicted_name,
        "correct": predicted_name == expected_name,
        "r": rgb[0],
        "g": rgb[1],
        "b": rgb[2],
        "lab_l": f"{cluster.lab[0]:.6f}",
        "lab_a": f"{cluster.lab[1]:.6f}",
        "lab_b": f"{cluster.lab[2]:.6f}",
        "cluster_ratio": f"{cluster.ratio:.6f}",
        "best_name_score": (
            f"{cluster.name_scores[predicted_name]:.6f}"
        ),
        "color_margin": (
            ""
            if cluster.color_margin is None
            else f"{cluster.color_margin:.6f}"
        ),
        "retained_pixels": int(
            np.count_nonzero(cluster.submask)
        ),
        "note": sample["note"],
    }


def main() -> int:
    args = parse_args()

    with args.input.open(
        "r",
        encoding="utf-8-sig",
        newline="",
    ) as input_file:
        samples = list(csv.DictReader(input_file))

    if len(samples) != 11:
        raise ValueError(
            f"expected exactly 11 controlled samples, got {len(samples)}"
        )

    results = [evaluate_sample(sample) for sample in samples]

    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open(
        "w",
        encoding="utf-8-sig",
        newline="",
    ) as output_file:
        writer = csv.DictWriter(
            output_file,
            fieldnames=OUTPUT_FIELDS,
        )
        writer.writeheader()
        writer.writerows(results)

    correct_count = sum(
        result["correct"] is True for result in results
    )
    accuracy = correct_count / len(results)

    print(f"Samples: {len(results)}")
    print(f"Correct: {correct_count}")
    print(f"Accuracy: {accuracy:.2%}")
    print(f"Results: {args.output}")

    for result in results:
        status = "PASS" if result["correct"] else "FAIL"
        print(
            f"{status}: {result['expected_name']} "
            f"-> {result['predicted_name']}"
        )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())