"""Two-tier color naming in OpenCV's float CIELAB convention.

The family vocabulary follows the 11 basic English terms used by Van de
Weijer et al. This module does not copy their learned lookup table. It uses a
small, transparent set of standardized W3C CSS sRGB anchors documented in
``assets/color_names/extended_palette.csv`` and computes heuristic scores.
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
    anchors: tuple["ExtendedColorAnchor", ...]

    @property
    def anchors_rgb(self) -> tuple[RGBColor, ...]:
        """Retain the T04 anchor-only view for compatible callers."""

        return tuple(anchor.rgb for anchor in self.anchors)


@dataclass(frozen=True, slots=True)
class ExtendedColorAnchor:
    """One stable level-two key, Vietnamese display label, and sRGB anchor."""

    key: str
    label_vi: str
    rgb: RGBColor


@dataclass(frozen=True, slots=True)
class ColorNameResult:
    """One explainable, non-calibrated two-tier naming result."""

    name: str
    label_vi: str
    name_scores: dict[str, float]
    margin: float
    nearest_distance: float
    level2_key: str
    level2_label_vi: str
    level2_scores: dict[str, float]
    top_predictions: tuple[tuple[str, float], ...]
    is_uncertain: bool


# These exact sRGB values are standardized named colors in W3C CSS Color 4.
# The family selection/grouping and Vietnamese labels are ChromaLens-authored.
BASIC_COLOR_FAMILIES: tuple[BasicColorFamily, ...] = (
    BasicColorFamily("black", "Đen", (
        ExtendedColorAnchor("black", "Đen", (0, 0, 0)),
    )),
    BasicColorFamily(
        "blue",
        "Xanh dương",
        (
            ExtendedColorAnchor("blue", "Xanh dương", (0, 0, 255)),
            ExtendedColorAnchor("navy", "Xanh hải quân", (0, 0, 128)),
            ExtendedColorAnchor("indigo", "Tím than", (75, 0, 130)),
            ExtendedColorAnchor("cyan", "Lục lam", (0, 255, 255)),
            ExtendedColorAnchor("sky_blue", "Xanh da trời", (135, 206, 235)),
            ExtendedColorAnchor("royal_blue", "Xanh hoàng gia", (65, 105, 225)),
            ExtendedColorAnchor("light_blue", "Xanh lam nhạt", (173, 216, 230)),
        ),
    ),
    BasicColorFamily(
        "brown",
        "Nâu",
        (
            ExtendedColorAnchor("brown", "Nâu", (165, 42, 42)),
            ExtendedColorAnchor("dark_brown", "Nâu sẫm", (139, 69, 19)),
            ExtendedColorAnchor("maroon", "Đỏ tía", (128, 0, 0)),
            ExtendedColorAnchor("olive", "Xanh ô liu", (128, 128, 0)),
            ExtendedColorAnchor("peru", "Da bò", (205, 133, 63)),
            ExtendedColorAnchor("chocolate", "Sô-cô-la", (210, 105, 30)),
            ExtendedColorAnchor("sandy_brown", "Nâu nhạt", (244, 164, 96)),
            ExtendedColorAnchor("coral", "San hô", (255, 127, 80)),
        ),
    ),
    BasicColorFamily(
        "grey",
        "Xám",
        (
            ExtendedColorAnchor("grey", "Xám", (128, 128, 128)),
            ExtendedColorAnchor("dim_gray", "Đen nhạt", (105, 105, 105)),
            ExtendedColorAnchor("light_grey", "Xám nhạt", (211, 211, 211)),
            ExtendedColorAnchor("ash_grey", "Xám tro", (192, 192, 192)),
            ExtendedColorAnchor("silver", "Bạc", (169, 169, 169)),
            ExtendedColorAnchor("slate_grey", "Ghi", (112, 128, 144)),
            ExtendedColorAnchor("teal", "Xanh mòng két", (0, 128, 128)),
        ),
    ),
    BasicColorFamily(
        "green",
        "Xanh lá",
        (
            ExtendedColorAnchor("green", "Xanh lá", (0, 128, 0)),
            ExtendedColorAnchor("lime", "Xanh lá mạ", (0, 255, 0)),
            ExtendedColorAnchor("sea_green", "Xanh ngọc", (60, 179, 113)),
            ExtendedColorAnchor("moss_green", "Xanh rêu", (85, 107, 47)),
        ),
    ),
    BasicColorFamily("orange", "Cam", (
        ExtendedColorAnchor("orange", "Cam", (255, 165, 0)),
        ExtendedColorAnchor("dark_orange", "Cam đậm", (255, 140, 0)),
    )),
    BasicColorFamily(
        "pink",
        "Hồng",
        (
            ExtendedColorAnchor("pink", "Hồng", (255, 192, 203)),
            ExtendedColorAnchor("deep_pink", "Hồng đậm", (255, 20, 147)),
            ExtendedColorAnchor("hot_pink", "Hồng cánh sen", (255, 105, 180)),
            ExtendedColorAnchor("light_pink", "Hồng nhạt", (255, 182, 193)),
        ),
    ),
    BasicColorFamily(
        "purple",
        "Tím",
        (
            ExtendedColorAnchor("purple", "Tím", (128, 0, 128)),
            ExtendedColorAnchor("violet", "Tím nhạt", (238, 130, 238)),
            ExtendedColorAnchor("magenta", "Hồng sẫm", (255, 0, 255)),
            ExtendedColorAnchor("orchid", "Tím hoa cà", (186, 85, 211)),
        ),
    ),
    BasicColorFamily(
        "red",
        "Đỏ",
        (
            ExtendedColorAnchor("red", "Đỏ", (255, 0, 0)),
            ExtendedColorAnchor("firebrick", "Đỏ gạch", (178, 34, 34)),
            ExtendedColorAnchor("crimson", "Đỏ thẫm", (220, 20, 60)),
        ),
    ),
    BasicColorFamily(
        "white",
        "Trắng",
        (
            ExtendedColorAnchor("white", "Trắng", (255, 255, 255)),
            ExtendedColorAnchor("ivory", "Trắng ngà", (255, 255, 240)),
            ExtendedColorAnchor("white_smoke", "Trắng khói", (245, 245, 245)),
            ExtendedColorAnchor("beige", "Be", (245, 245, 220)),
            ExtendedColorAnchor("peach", "Cam đào", (255, 218, 185)),
            ExtendedColorAnchor("light_yellow", "Vàng chanh", (255, 255, 224)),
        ),
    ),
    BasicColorFamily(
        "yellow",
        "Vàng",
        (
            ExtendedColorAnchor("yellow", "Vàng", (255, 255, 0)),
            ExtendedColorAnchor("khaki", "Vàng cát", (240, 230, 140)),
            ExtendedColorAnchor("gold", "Vàng đồng", (255, 215, 0)),
            ExtendedColorAnchor("dark_khaki", "Kaki đậm", (189, 183, 107)),
        ),
    ),
)

BASIC_COLOR_NAMES: tuple[str, ...] = tuple(
    family.name for family in BASIC_COLOR_FAMILIES
)
EXTENDED_COLOR_KEYS: tuple[str, ...] = tuple(
    anchor.key for family in BASIC_COLOR_FAMILIES for anchor in family.anchors
)
UNCERTAIN_MARGIN_THRESHOLD = 0.10

# T12 must not reinterpret the stable T04 level-one classifier. These are the
# exact pre-T12 family anchors; level two refines only inside that family.
_LEVEL1_ANCHORS_RGB: tuple[tuple[RGBColor, ...], ...] = (
    ((0, 0, 0),),
    ((0, 0, 255), (0, 0, 128), (65, 105, 225), (135, 206, 235)),
    ((165, 42, 42), (139, 69, 19), (160, 82, 45), (205, 133, 63)),
    ((128, 128, 128), (169, 169, 169), (105, 105, 105), (192, 192, 192)),
    ((0, 128, 0), (0, 255, 0), (34, 139, 34), (46, 139, 87)),
    ((255, 165, 0), (255, 140, 0)),
    ((255, 192, 203), (255, 105, 180), (255, 20, 147)),
    ((128, 0, 128), (102, 51, 153), (238, 130, 238), (186, 85, 211)),
    ((255, 0, 0), (220, 20, 60), (178, 34, 34)),
    ((255, 255, 255), (245, 245, 245), (255, 250, 250)),
    ((255, 255, 0), (255, 215, 0), (240, 230, 140)),
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
    level2_temperature: float = 5.0,
) -> ColorNameResult:
    """Name a Lab color using nearest level-two anchors and family scores.

    Each family distance is the minimum CIE76 distance to one of its anchors.
    Softmax over negative distances produces a complete, deterministic score
    distribution. These scores and their margin are heuristics, not calibrated
    probabilities.
    """

    if not np.isfinite(temperature) or temperature <= 0.0:
        raise ValueError("temperature must be a positive finite value")
    if not np.isfinite(level2_temperature) or level2_temperature <= 0.0:
        raise ValueError("level2_temperature must be a positive finite value")
    color = _validate_lab_color(lab)
    family_distances = np.asarray(
        [
            float(np.min(np.linalg.norm(anchors - color, axis=1)))
            for anchors in _family_anchor_labs()
        ],
        dtype=np.float64,
    )
    family_scores_array = _softmax_distances(family_distances, temperature)
    best_family_index = int(np.argmax(family_scores_array))
    family = BASIC_COLOR_FAMILIES[best_family_index]
    scores = {
        candidate.name: float(family_scores_array[index])
        for index, candidate in enumerate(BASIC_COLOR_FAMILIES)
    }
    level2_labs = _extended_family_anchor_labs()[best_family_index]
    level2_distances = np.asarray(
        [float(np.linalg.norm(anchor_lab - color)) for anchor_lab in level2_labs],
        dtype=np.float64,
    )
    level2_scores_array = _softmax_distances(level2_distances, level2_temperature)
    sorted_indices = np.argsort(level2_scores_array)[::-1]
    best_index = int(sorted_indices[0])
    best_anchor = family.anchors[best_index]
    level2_scores = {
        anchor.key: float(level2_scores_array[index])
        for index, anchor in enumerate(family.anchors)
    }
    margin = (
        1.0
        if len(sorted_indices) == 1
        else float(
            level2_scores_array[sorted_indices[0]]
            - level2_scores_array[sorted_indices[1]]
        )
    )
    return ColorNameResult(
        name=family.name,
        label_vi=family.label_vi,
        name_scores=scores,
        margin=margin,
        nearest_distance=float(level2_distances[best_index]),
        level2_key=best_anchor.key,
        level2_label_vi=best_anchor.label_vi,
        level2_scores=level2_scores,
        top_predictions=tuple(
            (
                family.anchors[int(index)].key,
                float(level2_scores_array[int(index)]),
            )
            for index in sorted_indices[:3]
        ),
        is_uncertain=margin < UNCERTAIN_MARGIN_THRESHOLD,
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
            [rgb_color_to_cielab(anchor) for anchor in anchors],
            dtype=np.float32,
        )
        for anchors in _LEVEL1_ANCHORS_RGB
    )


@lru_cache(maxsize=1)
def _extended_family_anchor_labs() -> tuple[NDArray[np.float32], ...]:
    return tuple(
        np.asarray(
            [rgb_color_to_cielab(anchor.rgb) for anchor in family.anchors],
            dtype=np.float32,
        )
        for family in BASIC_COLOR_FAMILIES
    )


def _softmax_distances(distances: NDArray[np.float64], temperature: float) -> NDArray[np.float64]:
    logits = -distances / temperature
    weights = np.exp(logits - float(np.max(logits)))
    return weights / float(np.sum(weights))


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
