"""Documented Two-Tier color naming in OpenCV's float CIELAB convention.

The family vocabulary follows the 11 basic English terms used by Van de
Weijer et al. as Level 1 categories. Level 2 contains ~46 specific common shades
and standard W3C CSS sRGB anchors for more detailed color identification.
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
class ExtendedColorAnchor:
    """One specific color shade (Level 2) and its sRGB anchor."""
    label_vi: str
    rgb: RGBColor


@dataclass(frozen=True, slots=True)
class BasicColorFamily:
    """One English/Vietnamese family (Level 1) containing specific shade anchors."""
    name: str
    label_vi: str
    anchors: tuple[ExtendedColorAnchor, ...]


@dataclass(frozen=True, slots=True)
class ColorNameResult:
    """One explainable, non-calibrated naming result with uncertainty feedback."""
    name: str                   # Level 1 name (e.g. 'red')
    label_vi: str               # Level 1 label (e.g. 'Đỏ')
    level2_label_vi: str        # Level 2 label (e.g. 'Đỏ sẫm')
    name_scores: dict[str, float] # Level 1 family probabilities (for backward compatibility)
    margin: float               # Margin between top 2 Level 2 anchors
    nearest_distance: float     # CIE76 distance to nearest anchor
    is_uncertain: bool          # Flag indicating if the color is ambiguous
    top_predictions: tuple[tuple[str, float], ...] # Top K Level 2 labels and their %


# Extended set of ~46 W3C CSS colors grouped by 11 Van de Weijer basic families
BASIC_COLOR_FAMILIES: tuple[BasicColorFamily, ...] = (
    BasicColorFamily("black", "Đen", (
        ExtendedColorAnchor("Đen", (0, 0, 0)),
        ExtendedColorAnchor("Đen nhạt", (105, 105, 105)),
    )),
    BasicColorFamily("blue", "Xanh dương", (
        ExtendedColorAnchor("Xanh dương", (0, 0, 255)),
        ExtendedColorAnchor("Xanh hải quân", (0, 0, 128)),
        ExtendedColorAnchor("Lục lam", (0, 255, 255)),
        ExtendedColorAnchor("Xanh da trời", (135, 206, 235)),
        ExtendedColorAnchor("Xanh hoàng gia", (65, 105, 225)),
        ExtendedColorAnchor("Xanh lam nhạt", (173, 216, 230)),
    )),
    BasicColorFamily("brown", "Nâu", (
        ExtendedColorAnchor("Nâu", (165, 42, 42)),
        ExtendedColorAnchor("Nâu sẫm", (139, 69, 19)),
        ExtendedColorAnchor("Da bò", (205, 133, 63)),
        ExtendedColorAnchor("Sô-cô-la", (210, 105, 30)),
        ExtendedColorAnchor("Nâu nhạt", (244, 164, 96)),
        ExtendedColorAnchor("Kaki đậm", (189, 183, 107)),
    )),
    BasicColorFamily("grey", "Xám", (
        ExtendedColorAnchor("Xám", (128, 128, 128)),
        ExtendedColorAnchor("Xám nhạt", (211, 211, 211)),
        ExtendedColorAnchor("Xám tro", (192, 192, 192)),
        ExtendedColorAnchor("Bạc", (169, 169, 169)),
        ExtendedColorAnchor("Ghi", (112, 128, 144)),
    )),
    BasicColorFamily("green", "Xanh lá", (
        ExtendedColorAnchor("Xanh lá", (0, 128, 0)),
        ExtendedColorAnchor("Xanh lá mạ", (0, 255, 0)),
        ExtendedColorAnchor("Xanh ô liu", (128, 128, 0)),
        ExtendedColorAnchor("Xanh mòng két", (0, 128, 128)),
        ExtendedColorAnchor("Xanh ngọc", (60, 179, 113)),
        ExtendedColorAnchor("Xanh rêu", (85, 107, 47)),
    )),
    BasicColorFamily("orange", "Cam", (
        ExtendedColorAnchor("Cam", (255, 165, 0)),
        ExtendedColorAnchor("Cam đậm", (255, 140, 0)),
        ExtendedColorAnchor("Cam đào", (255, 218, 185)),
        ExtendedColorAnchor("San hô", (255, 127, 80)),
    )),
    BasicColorFamily("pink", "Hồng", (
        ExtendedColorAnchor("Hồng", (255, 192, 203)),
        ExtendedColorAnchor("Hồng đậm", (255, 20, 147)),
        ExtendedColorAnchor("Hồng cánh sen", (255, 105, 180)),
        ExtendedColorAnchor("Hồng nhạt", (255, 182, 193)),
    )),
    BasicColorFamily("purple", "Tím", (
        ExtendedColorAnchor("Tím", (128, 0, 128)),
        ExtendedColorAnchor("Tím than", (75, 0, 130)),
        ExtendedColorAnchor("Tím nhạt", (238, 130, 238)),
        ExtendedColorAnchor("Hồng sẫm", (255, 0, 255)),
        ExtendedColorAnchor("Tím hoa cà", (186, 85, 211)),
    )),
    BasicColorFamily("red", "Đỏ", (
        ExtendedColorAnchor("Đỏ", (255, 0, 0)),
        ExtendedColorAnchor("Đỏ tía", (128, 0, 0)),
        ExtendedColorAnchor("Đỏ gạch", (178, 34, 34)),
        ExtendedColorAnchor("Đỏ thẫm", (220, 20, 60)),
    )),
    BasicColorFamily("white", "Trắng", (
        ExtendedColorAnchor("Trắng", (255, 255, 255)),
        ExtendedColorAnchor("Trắng ngà", (255, 255, 240)),
        ExtendedColorAnchor("Trắng khói", (245, 245, 245)),
        ExtendedColorAnchor("Be", (245, 245, 220)),
    )),
    BasicColorFamily("yellow", "Vàng", (
        ExtendedColorAnchor("Vàng", (255, 255, 0)),
        ExtendedColorAnchor("Vàng cát", (240, 230, 140)),
        ExtendedColorAnchor("Vàng đồng", (255, 215, 0)),
        ExtendedColorAnchor("Vàng chanh", (255, 255, 224)),
    )),
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
    """Name a Lab color using nearest specific extended anchors and normalized scores.

    Calculates distances to all Level 2 anchors, applies softmax, and aggregates
    probabilities by Level 1 families for backward compatibility. Identifies
    uncertainty if margin is low or distance is high.
    """

    if not np.isfinite(temperature) or temperature <= 0.0:
        raise ValueError("temperature must be a positive finite value")
    color = _validate_lab_color(lab)
    
    # Flatten anchors and track their lineage
    flat_anchors = []
    for family_idx, family in enumerate(BASIC_COLOR_FAMILIES):
        for anchor_idx, anchor in enumerate(family.anchors):
            flat_anchors.append((family_idx, anchor.label_vi, rgb_color_to_cielab(anchor.rgb)))
            
    distances = np.asarray(
        [
            float(np.linalg.norm(np.asarray(anchor_lab, dtype=np.float32) - color))
            for _, _, anchor_lab in flat_anchors
        ],
        dtype=np.float64,
    )
    
    logits = -distances / temperature
    weights = np.exp(logits - float(np.max(logits)))
    probabilities = weights / float(np.sum(weights))
    
    # Sort Level 2 probabilities
    sorted_indices = np.argsort(probabilities)[::-1]
    
    # Determine the best individual anchor
    best_idx = sorted_indices[0]
    best_family_idx = flat_anchors[best_idx][0]
    best_family = BASIC_COLOR_FAMILIES[best_family_idx]
    best_level2_label = flat_anchors[best_idx][1]
    best_distance = float(distances[best_idx])
    
    # Calculate Level 2 margin
    second_best_idx = sorted_indices[1]
    margin = float(probabilities[best_idx] - probabilities[second_best_idx])
    
    # Top K predictions for UI (Level 2 label and %)
    top_predictions = tuple(
        (flat_anchors[i][1], float(probabilities[i])) 
        for i in sorted_indices[:3] if probabilities[i] > 0.05
    )
    
    # Aggregate probabilities into Level 1 families
    family_scores = {family.name: 0.0 for family in BASIC_COLOR_FAMILIES}
    for idx, prob in enumerate(probabilities):
        fam_idx = flat_anchors[idx][0]
        fam_name = BASIC_COLOR_FAMILIES[fam_idx].name
        family_scores[fam_name] += float(prob)
        
    # Uncertainty heuristics (can be tuned later)
    # If the nearest distance is over 35 (CIE76) or margin between top 2 is less than 15%
    is_uncertain = best_distance > 35.0 or margin < 0.15

    return ColorNameResult(
        name=best_family.name,
        label_vi=best_family.label_vi,
        level2_label_vi=best_level2_label,
        name_scores=family_scores,
        margin=margin,
        nearest_distance=best_distance,
        is_uncertain=is_uncertain,
        top_predictions=top_predictions
    )


def vietnamese_color_label(name: str) -> str:
    """Return the Level 1 Vietnamese label for a supported canonical English name."""

    normalized = name.strip().lower()
    for family in BASIC_COLOR_FAMILIES:
        if family.name == normalized:
            return family.label_vi
    raise ValueError(f"unsupported basic color name: {name!r}")


@lru_cache(maxsize=1)
def _family_anchor_labs() -> tuple[NDArray[np.float32], ...]:
    # Backward compatible helper for anyone relying on old structure internally
    return tuple(
        np.asarray(
            [rgb_color_to_cielab(anchor.rgb) for anchor in family.anchors],
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
