"""Dominant corrected-color extraction inside validated garment masks."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

import cv2
import numpy as np
from numpy.typing import NDArray

from chromalens.color_naming import (
    LabColor,
    cielab_to_rgb_color,
    name_cielab_color,
    rgb_image_to_cielab,
)
from chromalens.contracts import (
    BinaryMask,
    ColorCluster,
    ColorFrame,
    FramePacket,
    GarmentRegion,
)

ConfidenceMap = NDArray[np.floating]


class ColorExtractionError(RuntimeError):
    """Base class for actionable dominant-color extraction failures."""


class CorrectedFrameUnavailableError(ColorExtractionError):
    """Raised when T03 corrected RGB has not been produced for the packet."""


class InsufficientColorPixelsError(ColorExtractionError):
    """Raised when filtering leaves too few pixels for a defensible estimate."""


class ColorExtractionMode(str, Enum):
    """Supported P0/P1 dominant-color estimators."""

    MEDIAN = "median"
    KMEANS_2 = "kmeans-2"


@dataclass(frozen=True, slots=True)
class ColorExtractionConfig:
    """Validated mask, pixel, clustering, and naming thresholds."""

    erosion_kernel_size: int = 3
    erosion_iterations: int = 1
    dark_threshold: int = 16
    clipped_threshold: int = 250
    minimum_pixel_confidence: float = 0.50
    minimum_valid_pixels: int = 16
    minimum_cluster_ratio: float = 0.10
    kmeans_seed: int = 17
    kmeans_max_iterations: int = 30
    kmeans_tolerance: float = 1e-3
    naming_temperature: float = 20.0

    def __post_init__(self) -> None:
        if self.erosion_kernel_size <= 0 or self.erosion_kernel_size % 2 == 0:
            raise ValueError("erosion_kernel_size must be a positive odd integer")
        if self.erosion_iterations <= 0:
            raise ValueError("erosion_iterations must be positive")
        for field_name in ("dark_threshold", "clipped_threshold"):
            value = getattr(self, field_name)
            if not isinstance(value, int) or not 0 <= value <= 255:
                raise ValueError(f"{field_name} must be an integer within [0, 255]")
        if self.dark_threshold >= self.clipped_threshold:
            raise ValueError("dark_threshold must be less than clipped_threshold")
        if not 0.0 <= self.minimum_pixel_confidence <= 1.0:
            raise ValueError("minimum_pixel_confidence must be within [0, 1]")
        if self.minimum_valid_pixels <= 0:
            raise ValueError("minimum_valid_pixels must be positive")
        if not 0.0 < self.minimum_cluster_ratio <= 0.5:
            raise ValueError("minimum_cluster_ratio must be within (0, 0.5]")
        if self.kmeans_seed < 0:
            raise ValueError("kmeans_seed must be non-negative")
        if self.kmeans_max_iterations <= 0:
            raise ValueError("kmeans_max_iterations must be positive")
        if not np.isfinite(self.kmeans_tolerance) or self.kmeans_tolerance <= 0.0:
            raise ValueError("kmeans_tolerance must be positive and finite")
        if not np.isfinite(self.naming_temperature) or self.naming_temperature <= 0.0:
            raise ValueError("naming_temperature must be positive and finite")


class DominantColorExtractor:
    """Extract one robust median or up to two deterministic color clusters."""

    def __init__(self, config: ColorExtractionConfig | None = None) -> None:
        self.config = config or ColorExtractionConfig()

    def extract(
        self,
        packet: FramePacket,
        region: GarmentRegion,
        *,
        mode: ColorExtractionMode = ColorExtractionMode.MEDIAN,
        pixel_confidence: ConfidenceMap | None = None,
    ) -> tuple[ColorCluster, ...]:
        """Extract named original colors from T03 corrected RGB.

        ``pixel_confidence`` is optional because the P0 MediaPipe backend
        exposes a thresholded mask and region-level score, not a reusable
        aligned probability map. Backends that expose such a map can pass it
        here to reject low-confidence pixels explicitly.
        """

        corrected_rgb = packet.corrected_rgb
        if corrected_rgb is None:
            raise CorrectedFrameUnavailableError(
                "FramePacket.corrected_rgb is required; run T03 white balance "
                "before dominant-color extraction."
            )
        _validate_corrected_rgb(corrected_rgb, packet.original_bgr.shape)
        if region.mask.shape != corrected_rgb.shape[:2]:
            raise ValueError("garment mask must align with corrected_rgb")
        valid_mask = build_valid_color_mask(
            corrected_rgb,
            region.mask,
            config=self.config,
            pixel_confidence=pixel_confidence,
        )
        valid_count = int(np.count_nonzero(valid_mask))
        if valid_count < self.config.minimum_valid_pixels:
            raise InsufficientColorPixelsError(
                f"Only {valid_count} valid garment pixels remain; at least "
                f"{self.config.minimum_valid_pixels} are required. Improve the "
                "mask/lighting or lower a documented threshold."
            )

        lab_image = rgb_image_to_cielab(corrected_rgb)
        if mode is ColorExtractionMode.MEDIAN:
            representative = np.median(lab_image[valid_mask], axis=0)
            return (
                _build_cluster(
                    representative,
                    ratio=1.0,
                    submask=valid_mask.copy(),
                    naming_temperature=self.config.naming_temperature,
                ),
            )
        if mode is ColorExtractionMode.KMEANS_2:
            return self._extract_kmeans_two(lab_image, valid_mask)
        raise ValueError(f"unsupported color extraction mode: {mode!r}")

    def _extract_kmeans_two(
        self,
        lab_image: NDArray[np.float32],
        valid_mask: BinaryMask,
    ) -> tuple[ColorCluster, ...]:
        pixels = lab_image[valid_mask].astype(np.float64)
        if np.unique(pixels, axis=0).shape[0] < 2:
            representative = np.median(pixels, axis=0)
            return (
                _build_cluster(
                    representative,
                    ratio=1.0,
                    submask=valid_mask.copy(),
                    naming_temperature=self.config.naming_temperature,
                ),
            )

        labels, centers = _deterministic_kmeans_two(pixels, self.config)
        valid_flat_indices = np.flatnonzero(valid_mask)
        total_count = pixels.shape[0]
        retained: list[tuple[float, int, ColorCluster]] = []
        for cluster_index in range(2):
            member_selector = labels == cluster_index
            member_count = int(np.count_nonzero(member_selector))
            ratio = member_count / total_count
            if ratio < self.config.minimum_cluster_ratio:
                continue
            submask = np.zeros(valid_mask.shape, dtype=np.bool_)
            submask.flat[valid_flat_indices[member_selector]] = True
            cluster = _build_cluster(
                centers[cluster_index],
                ratio=ratio,
                submask=submask,
                naming_temperature=self.config.naming_temperature,
            )
            retained.append((ratio, cluster_index, cluster))

        if not retained:
            raise InsufficientColorPixelsError(
                "K=2 produced no cluster above minimum_cluster_ratio"
            )
        retained.sort(key=lambda item: (-item[0], item[1]))
        return tuple(item[2] for item in retained)


def erode_garment_mask(
    mask: BinaryMask,
    *,
    kernel_size: int = 3,
    iterations: int = 1,
) -> BinaryMask:
    """Erode a boolean garment mask with an explicit zero-valued border."""

    _validate_binary_mask(mask)
    if kernel_size <= 0 or kernel_size % 2 == 0:
        raise ValueError("kernel_size must be a positive odd integer")
    if iterations <= 0:
        raise ValueError("iterations must be positive")
    kernel = np.ones((kernel_size, kernel_size), dtype=np.uint8)
    eroded = cv2.erode(
        mask.astype(np.uint8),
        kernel,
        iterations=iterations,
        borderType=cv2.BORDER_CONSTANT,
        borderValue=0,
    )
    return eroded.astype(np.bool_)


def build_valid_color_mask(
    corrected_rgb: ColorFrame,
    garment_mask: BinaryMask,
    *,
    config: ColorExtractionConfig | None = None,
    pixel_confidence: ConfidenceMap | None = None,
) -> BinaryMask:
    """Return eroded garment pixels valid for original-color measurement."""

    active_config = config or ColorExtractionConfig()
    _validate_corrected_rgb(corrected_rgb, corrected_rgb.shape)
    _validate_binary_mask(garment_mask)
    if garment_mask.shape != corrected_rgb.shape[:2]:
        raise ValueError("garment_mask must align with corrected_rgb")
    eroded = erode_garment_mask(
        garment_mask,
        kernel_size=active_config.erosion_kernel_size,
        iterations=active_config.erosion_iterations,
    )
    brightest_channel = np.max(corrected_rgb, axis=2)
    valid = eroded & (brightest_channel > active_config.dark_threshold)
    valid &= ~np.any(corrected_rgb >= active_config.clipped_threshold, axis=2)

    if pixel_confidence is not None:
        _validate_confidence_map(pixel_confidence, garment_mask.shape)
        valid &= pixel_confidence >= active_config.minimum_pixel_confidence
    return valid


def _deterministic_kmeans_two(
    pixels: NDArray[np.float64],
    config: ColorExtractionConfig,
) -> tuple[NDArray[np.int64], NDArray[np.float64]]:
    rng = np.random.default_rng(config.kmeans_seed)
    first_index = int(rng.integers(0, pixels.shape[0]))
    first_center = pixels[first_index]
    squared_distances = np.sum((pixels - first_center) ** 2, axis=1)
    probabilities = squared_distances / float(np.sum(squared_distances))
    second_index = int(rng.choice(pixels.shape[0], p=probabilities))
    centers = np.stack((first_center, pixels[second_index])).astype(np.float64)

    labels = np.zeros(pixels.shape[0], dtype=np.int64)
    for _ in range(config.kmeans_max_iterations):
        distances = np.sum((pixels[:, None, :] - centers[None, :, :]) ** 2, axis=2)
        labels = np.argmin(distances, axis=1).astype(np.int64)
        new_centers = centers.copy()
        for cluster_index in range(2):
            members = pixels[labels == cluster_index]
            if members.size == 0:
                assigned_distances = distances[np.arange(pixels.shape[0]), labels]
                replacement_index = int(np.argmax(assigned_distances))
                new_centers[cluster_index] = pixels[replacement_index]
            else:
                new_centers[cluster_index] = np.mean(members, axis=0)
        maximum_shift = float(np.max(np.linalg.norm(new_centers - centers, axis=1)))
        centers = new_centers
        if maximum_shift <= config.kmeans_tolerance:
            break
    final_distances = np.sum(
        (pixels[:, None, :] - centers[None, :, :]) ** 2,
        axis=2,
    )
    final_labels = np.argmin(final_distances, axis=1).astype(np.int64)
    return final_labels, centers


def _build_cluster(
    lab: NDArray[np.floating],
    *,
    ratio: float,
    submask: BinaryMask,
    naming_temperature: float,
) -> ColorCluster:
    lab_tuple: LabColor = (float(lab[0]), float(lab[1]), float(lab[2]))
    naming = name_cielab_color(lab_tuple, temperature=naming_temperature)
    return ColorCluster(
        lab=lab_tuple,
        rgb=cielab_to_rgb_color(lab_tuple),
        ratio=ratio,
        submask=submask,
        original_name=naming.name,
        name_scores=naming.name_scores,
        color_margin=naming.margin,
    )


def _validate_corrected_rgb(frame: ColorFrame, reference_shape: tuple[int, ...]) -> None:
    if frame.dtype != np.uint8 or frame.ndim != 3 or frame.shape[2] != 3:
        raise ValueError("corrected_rgb must be a uint8 H x W x 3 RGB image")
    if frame.shape != reference_shape:
        raise ValueError("corrected_rgb must align with original_bgr")
    if frame.shape[0] == 0 or frame.shape[1] == 0:
        raise ValueError("corrected_rgb dimensions must be non-empty")


def _validate_binary_mask(mask: BinaryMask) -> None:
    if mask.dtype != np.bool_ or mask.ndim != 2:
        raise ValueError("garment_mask must be a boolean H x W mask")


def _validate_confidence_map(confidence: ConfidenceMap, shape: tuple[int, int]) -> None:
    if confidence.ndim != 2 or confidence.shape != shape:
        raise ValueError("pixel_confidence must be an H x W map aligned with the mask")
    if not np.issubdtype(confidence.dtype, np.floating):
        raise ValueError("pixel_confidence must use a floating-point dtype")
    if not np.all(np.isfinite(confidence)) or np.any(
        (confidence < 0.0) | (confidence > 1.0)
    ):
        raise ValueError("pixel_confidence values must be finite within [0, 1]")
