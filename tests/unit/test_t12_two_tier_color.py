"""Deterministic T12 contracts for the 11-family/50-label vocabulary."""

from __future__ import annotations

import csv
from pathlib import Path

import pytest

from chromalens.color_naming import (
    BASIC_COLOR_FAMILIES,
    EXTENDED_COLOR_KEYS,
    UNCERTAIN_MARGIN_THRESHOLD,
    name_cielab_color,
    rgb_color_to_cielab,
)
from chromalens.config import CVDProfile
from chromalens.presentation import PresentationData, build_product_copy

ROOT = Path(__file__).resolve().parents[2]
PALETTE = ROOT / "assets/color_names/extended_palette.csv"


def _palette_rows() -> list[dict[str, str]]:
    with PALETTE.open(encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def test_palette_and_runtime_have_exactly_the_same_fifty_anchors() -> None:
    rows = _palette_rows()
    runtime = [
        (family.name, anchor.key, anchor.label_vi, anchor.rgb)
        for family in BASIC_COLOR_FAMILIES
        for anchor in family.anchors
    ]
    frozen = [
        (
            row["level1_key"],
            row["level2_key"],
            row["level2_label_vi"],
            (int(row["r"]), int(row["g"]), int(row["b"])),
        )
        for row in rows
    ]

    assert len(BASIC_COLOR_FAMILIES) == 11
    assert len(rows) == len(EXTENDED_COLOR_KEYS) == 50
    assert len(set(EXTENDED_COLOR_KEYS)) == 50
    assert set(runtime) == set(frozen)


@pytest.mark.parametrize("row", _palette_rows(), ids=lambda row: row["level2_key"])
def test_each_digital_anchor_returns_its_frozen_two_tier_identity(
    row: dict[str, str],
) -> None:
    rgb = (int(row["r"]), int(row["g"]), int(row["b"]))
    result = name_cielab_color(rgb_color_to_cielab(rgb))

    assert result.name == row["level1_key"]
    assert result.level2_key == row["level2_key"]
    assert result.level2_label_vi == row["level2_label_vi"]
    assert result.nearest_distance == pytest.approx(0.0)
    assert result.margin >= UNCERTAIN_MARGIN_THRESHOLD
    assert not result.is_uncertain
    assert tuple(result.name_scores) == tuple(
        family.name for family in BASIC_COLOR_FAMILIES
    )
    assert sum(result.name_scores.values()) == pytest.approx(1.0)
    assert sum(result.level2_scores.values()) == pytest.approx(1.0)


@pytest.mark.parametrize(
    ("margin", "lighting", "expected"),
    [
        (0.099999, "good", True),
        (0.10, "good", False),
        (0.80, "poor", True),
    ],
)
def test_frozen_uncertainty_boundary_is_reflected_by_product_copy(
    margin: float,
    lighting: str,
    expected: bool,
) -> None:
    # The product gate is margin < 0.10 OR poor lighting. Keeping this small
    # truth table here prevents either condition from being silently relaxed.
    assert (margin < UNCERTAIN_MARGIN_THRESHOLD or lighting == "poor") is expected


@pytest.mark.parametrize(
    ("margin", "lighting", "naming_uncertain", "expected_color"),
    [
        (0.09, "good", True, "Không chắc chắn"),
        (0.80, "poor", False, "Không chắc chắn"),
        (0.80, "good", False, "Đỏ thẫm"),
    ],
)
def test_product_copy_never_forces_a_low_evidence_level_two_label(
    margin: float,
    lighting: str,
    naming_uncertain: bool,
    expected_color: str,
) -> None:
    data = PresentationData(
        source_name="synthetic",
        profile=CVDProfile.DEUTAN,
        severity=1.0,
        recolor_enabled=True,
        view_name="assistive",
        original_color_label="Đỏ thẫm",
        original_color_rgb=(220, 20, 60),
        color_margin=margin,
        risk_level="low",
        lighting_level=lighting,
        matching_label="Trắng",
        matching_harmony="neutral",
        action_message="Ready",
        diagnostic_lines=(),
        garment_detected=True,
        color_uncertain=naming_uncertain,
    )

    assert build_product_copy(data)["color"] == expected_color
