from __future__ import annotations

import csv
from pathlib import Path

import numpy as np
import pytest

from scripts import t09_segmentation_eval as evaluator


def test_letterbox_preserves_aspect_and_aligns_mask() -> None:
    image = np.full((100, 200, 3), 127, dtype=np.uint8)
    mask = np.zeros((100, 200), dtype=np.bool_)
    mask[25:75, 50:150] = True

    normalized, geometry = evaluator.letterbox_bgr(image, width=320, height=240)
    normalized_mask = evaluator.letterbox_mask(
        mask, geometry, width=320, height=240
    )

    assert normalized.shape == (240, 320, 3)
    assert geometry == (0, 40, 320, 160)
    assert normalized_mask.shape == (240, 320)
    assert normalized_mask.dtype == np.bool_
    assert not normalized_mask[:40].any()
    assert not normalized_mask[200:].any()


def test_segmentation_iou_and_empty_union_contract() -> None:
    predicted = np.array([[True, True], [False, False]])
    annotation = np.array([[True, False], [True, False]])

    assert evaluator.segmentation_iou(predicted, annotation) == pytest.approx(1 / 3)
    assert evaluator.segmentation_iou(
        np.zeros((2, 2), dtype=np.bool_), np.zeros((2, 2), dtype=np.bool_)
    ) is None


def test_manual_ratings_require_exact_coverage_and_reasons(tmp_path: Path) -> None:
    ratings = tmp_path / "ratings.csv"
    with ratings.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=("case_id", "rating", "reason"))
        writer.writeheader()
        writer.writerow({"case_id": "SEG-A", "rating": 2, "reason": "usable"})
        writer.writerow({"case_id": "SEG-B", "rating": 1, "reason": "omission"})

    assert evaluator.load_ratings(ratings, ["SEG-A", "SEG-B"]) == {
        "SEG-A": (2, "usable"),
        "SEG-B": (1, "omission"),
    }

    with pytest.raises(ValueError, match="exactly once"):
        evaluator.load_ratings(ratings, ["SEG-A"])


def test_frozen_registry_has_exact_twenty_segmentation_cases() -> None:
    cases = evaluator.load_cases(evaluator.WORKSTREAM)

    assert len(cases) == 20
    assert len({case["case_id"] for case in cases}) == 20
    assert sum(case["input_kind"] == "video" for case in cases) == 2
