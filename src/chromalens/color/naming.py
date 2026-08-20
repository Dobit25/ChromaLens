"""Deterministic CIE Lab conversion and 11-name color mapping.

Prototype RGB values come from W3C CSS Color Module Level 4:
https://www.w3.org/TR/css-color-4/#named-colors

They form an explainable MVP heuristic, not a learned or perceptually
complete color-naming model. Vietnamese labels are project translations.
"""

from __future__ import annotations

from dataclasses import dataclass
from math import isfinite

import cv2
import numpy as np

LabColor = tuple[float, float, float]
RGBColor = tuple[int, int, int]


@dataclass(frozen=True, slots=True)
class ColorPrototype:
    """One W3C sRGB prototype and its Vietnamese label."""

    css_name: str
    vietnamese_name: str
    rgb: RGBColor


BASIC_COLOR_PROTOTYPES: tuple[ColorPrototype, ...] = (
    ColorPrototype("black", "đen", (0, 0, 0)),
    ColorPrototype("white", "trắng", (255, 255, 255)),
    ColorPrototype("red", "đỏ", (255, 0, 0)),
    ColorPrototype("green", "xanh lá", (0, 128, 0)),
    ColorPrototype("yellow", "vàng", (255, 255, 0)),
    ColorPrototype("blue", "xanh dương", (0, 0, 255)),
    ColorPrototype("brown", "nâu", (165, 42, 42)),
    ColorPrototype("purple", "tím", (128, 0, 128)),
    ColorPrototype("pink", "hồng", (255, 192, 203)),
    ColorPrototype("orange", "cam", (255, 165, 0)),
    ColorPrototype("gray", "xám", (128, 128, 128)),
)


@dataclass(frozen=True, slots=True)
class ColorNamingConfig:
    """Controls conversion of prototype distances into normalized scores."""

    score_temperature_delta_e: float = 20.0

    def __post_init__(self) -> None:
        temperature = self.score_temperature_delta_e
        if not isfinite(temperature) or temperature <= 0.0:
            raise ValueError(
                "score_temperature_delta_e must be finite and positive"
            )


@dataclass(frozen=True, slots=True)
class ColorNameResult:
    """Best Vietnamese name, normalized scores, and top-two margin."""

    lab: LabColor
    name: str
    scores: dict[str, float]
    margin: float


def rgb_to_cielab(rgb: RGBColor) -> LabColor:
    """Convert one sRGB tuple to conventional floating-point CIE Lab.

    Returns L* in [0, 100] and signed a*/b*. Normalized float32 input avoids
    OpenCV's uint8 Lab scaling and the +128 offsets for a* and b*.
    """

    _validate_rgb(rgb)

    rgb_image = (
        np.asarray(rgb, dtype=np.float32).reshape((1, 1, 3)) / 255.0
    )
    lab = cv2.cvtColor(rgb_image, cv2.COLOR_RGB2Lab)[0, 0]

    return float(lab[0]), float(lab[1]), float(lab[2])


def name_cielab(
    lab: LabColor,
    config: ColorNamingConfig | None = None,
) -> ColorNameResult:
    """Name a Lab color using nearest-prototype Delta-E 1976."""

    _validate_lab(lab)
    selected_config = config or ColorNamingConfig()

    target = np.asarray(lab, dtype=np.float64)
    prototype_labs = np.asarray(
        [
            rgb_to_cielab(prototype.rgb)
            for prototype in BASIC_COLOR_PROTOTYPES
        ],
        dtype=np.float64,
    )

    distances = np.linalg.norm(prototype_labs - target, axis=1)

    logits = (
        -distances / selected_config.score_temperature_delta_e
    )
    logits -= np.max(logits)

    weights = np.exp(logits)
    normalized_scores = weights / np.sum(weights)

    ranked_indices = sorted(
        range(len(BASIC_COLOR_PROTOTYPES)),
        key=lambda index: (-float(normalized_scores[index]), index),
    )
    best_index, second_index = ranked_indices[:2]

    scores = {
        prototype.vietnamese_name: float(normalized_scores[index])
        for index, prototype in enumerate(BASIC_COLOR_PROTOTYPES)
    }

    margin = float(
        normalized_scores[best_index] - normalized_scores[second_index]
    )

    return ColorNameResult(
        lab=(float(lab[0]), float(lab[1]), float(lab[2])),
        name=BASIC_COLOR_PROTOTYPES[best_index].vietnamese_name,
        scores=scores,
        margin=margin,
    )


def name_rgb(
    rgb: RGBColor,
    config: ColorNamingConfig | None = None,
) -> ColorNameResult:
    """Convert one RGB tuple to Lab and determine its basic name."""

    return name_cielab(rgb_to_cielab(rgb), config)


def _validate_rgb(rgb: RGBColor) -> None:
    if not isinstance(rgb, tuple) or len(rgb) != 3:
        raise ValueError("rgb must be a three-channel tuple")

    if any(
        isinstance(channel, bool)
        or not isinstance(channel, int)
        or not 0 <= channel <= 255
        for channel in rgb
    ):
        raise ValueError(
            "rgb channels must be integers within [0, 255]"
        )


def _validate_lab(lab: LabColor) -> None:
    if not isinstance(lab, tuple) or len(lab) != 3:
        raise ValueError("lab must be a three-component tuple")

    if any(isinstance(component, bool) for component in lab):
        raise ValueError("lab components must be finite numbers")

    try:
        components = tuple(float(component) for component in lab)
    except (TypeError, ValueError) as exc:
        raise ValueError(
            "lab components must be finite numbers"
        ) from exc

    if not all(isfinite(component) for component in components):
        raise ValueError("lab components must be finite numbers")

    if not 0.0 <= components[0] <= 100.0:
        raise ValueError("Lab L* must be within [0, 100]")