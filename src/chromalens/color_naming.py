"""Documented 11-family color naming in OpenCV's float CIELAB convention.

The family vocabulary follows the 11 basic English terms used by Van de
Weijer et al. This module does not copy their learned lookup table. It uses a
small, transparent set of standardized W3C CSS sRGB anchors documented in
``assets/color_names/README.md`` and computes heuristic nearest-anchor scores.
"""

from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache

import cv2
import numpy as np
from numpy.typing import NDArray

from chromalens.contracts import ColorFrame

LabImage = NDArray[np.float32]
RGBColor = tuple[int, int, int]
LabColor = tuple[float, float, float]


@dataclass(frozen=True, slots=True)
class BasicColorFamily:
    """One English/Vietnamese family and its standardized sRGB anchors."""

    name: str
    label_vi: str
    anchors_rgb: tuple[RGBColor, ...]


@dataclass(frozen=True, slots=True)
class ColorNameResult:
    """One explainable, non-calibrated 11-family naming result."""

    name: str
    label_vi: str
    name_scores: dict[str, float]
    margin: float
    nearest_distance: float


# These exact sRGB values are standardized named colors in W3C CSS Color 4.
# The family selection/grouping and Vietnamese labels are ChromaLens-authored.
BASIC_COLOR_FAMILIES: tuple[BasicColorFamily, ...] = (
    BasicColorFamily("black", "Đen", ((0, 0, 0),)),
    BasicColorFamily(
        "blue",
        "Xanh dương",
        ((0, 0, 255), (0, 0, 128), (65, 105, 225), (135, 206, 235)),
    ),
    BasicColorFamily(
        "brown",
        "Nâu",
        ((165, 42, 42), (139, 69, 19), (160, 82, 45), (205, 133, 63)),
    ),
    BasicColorFamily(
        "grey",
        "Xám",
        ((128, 128, 128), (169, 169, 169), (105, 105, 105), (192, 192, 192)),
    ),
    BasicColorFamily(
        "green",
        "Xanh lá",
        ((0, 128, 0), (0, 255, 0), (34, 139, 34), (46, 139, 87)),
    ),
    BasicColorFamily("orange", "Cam", ((255, 165, 0), (255, 140, 0))),
    BasicColorFamily(
        "pink",
        "Hồng",
        ((255, 192, 203), (255, 105, 180), (255, 20, 147)),
    ),
    BasicColorFamily(
        "purple",
        "Tím",
        ((128, 0, 128), (102, 51, 153), (238, 130, 238), (186, 85, 211)),
    ),
    BasicColorFamily(
        "red",
        "Đỏ",
        ((255, 0, 0), (220, 20, 60), (178, 34, 34)),
    ),
    BasicColorFamily(
        "white",
        "Trắng",
        ((255, 255, 255), (245, 245, 245), (255, 250, 250)),
    ),
    BasicColorFamily(
        "yellow",
        "Vàng",
        ((255, 255, 0), (255, 215, 0), (240, 230, 140)),
    ),
)

BASIC_COLOR_NAMES: tuple[str, ...] = tuple(
    family.name for family in BASIC_COLOR_FAMILIES
)


def rgb_image_to_cielab(rgb: ColorFrame) -> LabImage:
    """Convert uint8 sRGB to float CIELAB with explicit channel/range rules.

    Input is RGB (not OpenCV's default BGR) in ``[0, 255]``. It is normalized
    to float32 ``[0, 1]`` before ``cv2.COLOR_RGB2LAB``. OpenCV then returns
    conventional CIELAB values: ``L*`` in ``[0, 100]`` and signed ``a*``/``b*``.
    """

    _validate_rgb_image(rgb)
    normalized_rgb = rgb.astype(np.float32) / 255.0
    return cv2.cvtColor(normalized_rgb, cv2.COLOR_RGB2LAB)


def rgb_color_to_cielab(rgb: RGBColor) -> LabColor:
    """Convert one uint8 sRGB tuple to conventional float CIELAB."""

    _validate_rgb_color(rgb)
    image = np.asarray(rgb, dtype=np.uint8).reshape((1, 1, 3))
    lab = rgb_image_to_cielab(image)[0, 0]
    return _lab_tuple(lab)


def cielab_to_rgb_color(lab: LabColor) -> RGBColor:
    """Convert one conventional float CIELAB tuple to clipped uint8 sRGB."""

    lab_array = _validate_lab_color(lab).reshape((1, 1, 3)).astype(np.float32)
    rgb_float = cv2.cvtColor(lab_array, cv2.COLOR_LAB2RGB)[0, 0]
    rgb_uint8 = np.rint(np.clip(rgb_float, 0.0, 1.0) * 255.0).astype(np.uint8)
    return (int(rgb_uint8[0]), int(rgb_uint8[1]), int(rgb_uint8[2]))


def name_cielab_color(
    lab: LabColor,
    *,
    temperature: float = 20.0,
) -> ColorNameResult:
    """Name a Lab color using nearest family anchors and normalized scores.

    Each family distance is the minimum CIE76 distance to one of its anchors.
    Softmax over negative distances produces a complete, deterministic score
    distribution. These scores and their margin are heuristics, not calibrated
    probabilities.
    """

    if not np.isfinite(temperature) or temperature <= 0.0:
        raise ValueError("temperature must be a positive finite value")
    color = _validate_lab_color(lab)
    prototype_labs = _family_anchor_labs()
    distances = np.asarray(
        [
            float(np.min(np.linalg.norm(anchors - color, axis=1)))
            for anchors in prototype_labs
        ],
        dtype=np.float64,
    )
    logits = -distances / temperature
    weights = np.exp(logits - float(np.max(logits)))
    probabilities = weights / float(np.sum(weights))
    best_index = int(np.argmax(probabilities))
    sorted_scores = np.sort(probabilities)[::-1]
    family = BASIC_COLOR_FAMILIES[best_index]
    scores = {
        candidate.name: float(probabilities[index])
        for index, candidate in enumerate(BASIC_COLOR_FAMILIES)
    }
    return ColorNameResult(
        name=family.name,
        label_vi=family.label_vi,
        name_scores=scores,
        margin=float(sorted_scores[0] - sorted_scores[1]),
        nearest_distance=float(distances[best_index]),
    )


def vietnamese_color_label(name: str) -> str:
    """Return the Vietnamese label for a supported canonical English name."""

    normalized = name.strip().lower()
    for family in BASIC_COLOR_FAMILIES:
        if family.name == normalized:
            return family.label_vi
    raise ValueError(f"unsupported basic color name: {name!r}")


@lru_cache(maxsize=1)
def _family_anchor_labs() -> tuple[NDArray[np.float32], ...]:
    return tuple(
        np.asarray(
            [rgb_color_to_cielab(anchor) for anchor in family.anchors_rgb],
            dtype=np.float32,
        )
        for family in BASIC_COLOR_FAMILIES
    )


def _validate_rgb_image(rgb: ColorFrame) -> None:
    if rgb.dtype != np.uint8 or rgb.ndim != 3 or rgb.shape[2] != 3:
        raise ValueError("rgb must be a uint8 H x W x 3 RGB image")
    if rgb.shape[0] == 0 or rgb.shape[1] == 0:
        raise ValueError("rgb dimensions must be non-empty")


def _validate_rgb_color(rgb: RGBColor) -> None:
    if len(rgb) != 3 or any(
        not isinstance(channel, (int, np.integer)) or not 0 <= int(channel) <= 255
        for channel in rgb
    ):
        raise ValueError("rgb must contain three integer channels within [0, 255]")


def _validate_lab_color(lab: LabColor) -> NDArray[np.float64]:
    array = np.asarray(lab, dtype=np.float64)
    if array.shape != (3,) or not np.all(np.isfinite(array)):
        raise ValueError("lab must contain three finite values")
    if not 0.0 <= float(array[0]) <= 100.0:
        raise ValueError("Lab L* must be within [0, 100]")
    return array


def _lab_tuple(lab: NDArray[np.floating]) -> LabColor:
    return (float(lab[0]), float(lab[1]), float(lab[2]))
