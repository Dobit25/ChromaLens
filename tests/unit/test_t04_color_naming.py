"""Deterministic T04 tests for the documented 11-family name lookup."""

from __future__ import annotations

import csv
from pathlib import Path

import numpy as np
import pytest

from chromalens.color_naming import (
    BASIC_COLOR_NAMES,
    cielab_to_rgb_color,
    name_cielab_color,
    rgb_color_to_cielab,
    rgb_image_to_cielab,
    vietnamese_color_label,
)

CONTROLLED_SET = (
    Path(__file__).parents[1] / "samples" / "t04" / "basic11_controlled.csv"
)


def test_controlled_set_covers_and_names_all_eleven_families() -> None:
    rows = _controlled_rows()
    observed: list[str] = []

    for row in rows:
        rgb = (int(row["r"]), int(row["g"]), int(row["b"]))
        result = name_cielab_color(rgb_color_to_cielab(rgb))
        observed.append(result.name)
        assert result.name == row["expected_name"]
        assert result.label_vi == row["label_vi"]
        assert tuple(result.name_scores) == BASIC_COLOR_NAMES
        assert sum(result.name_scores.values()) == pytest.approx(1.0)
        assert result.margin > 0.0
        assert result.nearest_distance >= 0.0

    assert tuple(observed) == BASIC_COLOR_NAMES
    assert len(rows) == 11


def test_rgb_lab_conversion_uses_float_conventional_ranges_and_round_trips() -> None:
    rgb = np.asarray([[[30, 80, 220], [240, 240, 240]]], dtype=np.uint8)

    lab = rgb_image_to_cielab(rgb)

    assert lab.dtype == np.float32
    assert np.all((lab[:, :, 0] >= 0.0) & (lab[:, :, 0] <= 100.0))
    assert float(lab[0, 0, 2]) < 0.0  # Blue has a signed negative b* value.
    restored = cielab_to_rgb_color(tuple(float(value) for value in lab[0, 0]))
    np.testing.assert_allclose(restored, rgb[0, 0], atol=1)


def test_vietnamese_labels_are_explicit_and_unknown_name_fails() -> None:
    expected = {row["expected_name"]: row["label_vi"] for row in _controlled_rows()}

    assert {name: vietnamese_color_label(name) for name in BASIC_COLOR_NAMES} == expected
    with pytest.raises(ValueError, match="unsupported"):
        vietnamese_color_label("cyan")


@pytest.mark.parametrize(
    "invalid_lab",
    [(-1.0, 0.0, 0.0), (101.0, 0.0, 0.0), (50.0, float("nan"), 0.0)],
)
def test_invalid_lab_fails_fast(invalid_lab: tuple[float, float, float]) -> None:
    with pytest.raises(ValueError):
        name_cielab_color(invalid_lab)


def test_invalid_temperature_and_rgb_fail_fast() -> None:
    with pytest.raises(ValueError, match="temperature"):
        name_cielab_color((50.0, 0.0, 0.0), temperature=0.0)
    with pytest.raises(ValueError, match="uint8"):
        rgb_image_to_cielab(np.zeros((2, 2, 3), dtype=np.float32))
    with pytest.raises(ValueError, match="integer"):
        rgb_color_to_cielab((0, 0, 256))


def _controlled_rows() -> list[dict[str, str]]:
    with CONTROLLED_SET.open(encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))
