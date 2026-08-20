"""Controlled tests for deterministic T04 color naming."""

from __future__ import annotations

import math

import pytest

from chromalens.color.naming import (
    BASIC_COLOR_PROTOTYPES,
    ColorNamingConfig,
    ColorPrototype,
    name_cielab,
    name_rgb,
    rgb_to_cielab,
)


@pytest.mark.parametrize("prototype", BASIC_COLOR_PROTOTYPES)
def test_each_basic_color_maps_to_its_vietnamese_name(
    prototype: ColorPrototype,
) -> None:
    result = name_rgb(prototype.rgb)

    assert result.name == prototype.vietnamese_name
    assert (
        max(result.scores, key=result.scores.__getitem__)
        == prototype.vietnamese_name
    )
    assert len(result.scores) == 11
    assert sum(result.scores.values()) == pytest.approx(1.0)
    assert result.margin > 0.0


def test_float_lab_convention_has_expected_neutral_endpoints() -> None:
    black = rgb_to_cielab((0, 0, 0))
    white = rgb_to_cielab((255, 255, 255))

    assert black == pytest.approx((0.0, 0.0, 0.0), abs=0.02)
    assert white == pytest.approx((100.0, 0.0, 0.0), abs=0.02)


def test_rgb_channel_order_is_not_accidentally_bgr() -> None:
    red = rgb_to_cielab((255, 0, 0))
    blue = rgb_to_cielab((0, 0, 255))

    assert red[1] > 0.0
    assert red[2] > 0.0
    assert blue[1] > 0.0
    assert blue[2] < 0.0
    assert red != pytest.approx(blue)


def test_naming_is_deterministic_and_margin_matches_top_scores() -> None:
    lab = rgb_to_cielab((180, 80, 60))

    first = name_cielab(lab)
    second = name_cielab(lab)
    ranked_scores = sorted(first.scores.values(), reverse=True)

    assert first == second
    assert first.margin == pytest.approx(
        ranked_scores[0] - ranked_scores[1]
    )


@pytest.mark.parametrize(
    "invalid_rgb",
    [
        (-1, 0, 0),
        (256, 0, 0),
        (True, 0, 0),
        (0.0, 0, 0),
    ],
)
def test_invalid_rgb_fails_fast(invalid_rgb: tuple[object, ...]) -> None:
    with pytest.raises(ValueError):
        rgb_to_cielab(invalid_rgb)  # type: ignore[arg-type]


@pytest.mark.parametrize(
    "invalid_lab",
    [
        (-0.1, 0.0, 0.0),
        (100.1, 0.0, 0.0),
        (math.nan, 0.0, 0.0),
    ],
)
def test_invalid_lab_fails_fast(
    invalid_lab: tuple[float, float, float],
) -> None:
    with pytest.raises(ValueError):
        name_cielab(invalid_lab)


@pytest.mark.parametrize(
    "temperature",
    [0.0, -1.0, math.inf, math.nan],
)
def test_invalid_score_temperature_fails_fast(
    temperature: float,
) -> None:
    with pytest.raises(ValueError):
        ColorNamingConfig(score_temperature_delta_e=temperature)