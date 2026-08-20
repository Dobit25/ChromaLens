"""Robust median and deterministic K=2 garment-color estimation."""

from __future__ import annotations

from dataclasses import dataclass
from math import isfinite

import cv2
import numpy as np
from numpy.typing import NDArray

from chromalens.color.naming import LabColor, RGBColor

BooleanVector = NDArray[np.bool_]
RGBPixels = NDArray[np.uint8]
LabPixels = NDArray[np.float64]


@dataclass(frozen=True, slots=True)
class ClusteringConfig:
    """Validated settings for deterministic two-cluster estimation."""

    maximum_iterations: int = 25
    convergence_tolerance: float = 1e-4
    minimum_cluster_ratio: float = 0.10

    def __post_init__(self) -> None:
        if (
            isinstance(self.maximum_iterations, bool)
            or not isinstance(self.maximum_iterations, int)
            or self.maximum_iterations < 1
        ):
            raise ValueError(
                "maximum_iterations must be a positive integer"
            )

        if (
            not isfinite(self.convergence_tolerance)
            or self.convergence_tolerance < 0.0
        ):
            raise ValueError(
                "convergence_tolerance must be finite and non-negative"
            )

        if (
            not isfinite(self.minimum_cluster_ratio)
            or not 0.0 < self.minimum_cluster_ratio <= 0.5
        ):
            raise ValueError(
                "minimum_cluster_ratio must be within (0, 0.5]"
            )


@dataclass(frozen=True, slots=True)
class ClusterEstimate:
    """One estimated color and membership over the selected pixel array."""

    lab: LabColor
    rgb: RGBColor
    ratio: float
    members: BooleanVector

    def __post_init__(self) -> None:
        if not 0.0 < self.ratio <= 1.0:
            raise ValueError("ratio must be within (0, 1]")
        if self.members.dtype != np.bool_ or self.members.ndim != 1:
            raise ValueError("members must be a one-dimensional boolean array")


def robust_median_estimate(
    pixels_rgb: RGBPixels,
) -> ClusterEstimate:
    """Return one robust component-wise median estimate in CIE Lab."""

    _validate_pixels_rgb(pixels_rgb)

    pixels_lab = _rgb_pixels_to_cielab(pixels_rgb)
    median_lab_array = np.median(pixels_lab, axis=0)
    members = np.ones(len(pixels_rgb), dtype=np.bool_)

    return _build_estimate(
        center_lab=median_lab_array,
        members=members,
        total_count=len(pixels_rgb),
    )


def deterministic_k2_estimates(
    pixels_rgb: RGBPixels,
    config: ClusteringConfig | None = None,
) -> tuple[ClusterEstimate, ...]:
    """Return up to two deterministic Lab clusters.

    Initialization uses the point farthest from the global median followed by
    the point farthest from that first center. Lloyd iterations then use a
    deterministic lowest-index tie break. Clusters below the configured ratio
    are discarded rather than relabelled as garment colors.
    """

    _validate_pixels_rgb(pixels_rgb)
    selected_config = config or ClusteringConfig()
    pixels_lab = _rgb_pixels_to_cielab(pixels_rgb)

    if len(np.unique(pixels_lab, axis=0)) < 2:
        return (robust_median_estimate(pixels_rgb),)

    global_median = np.median(pixels_lab, axis=0)
    first_index = int(
        np.argmax(np.linalg.norm(pixels_lab - global_median, axis=1))
    )
    second_index = int(
        np.argmax(
            np.linalg.norm(
                pixels_lab - pixels_lab[first_index],
                axis=1,
            )
        )
    )

    centers = np.vstack(
        (pixels_lab[first_index], pixels_lab[second_index])
    ).astype(np.float64)

    for _ in range(selected_config.maximum_iterations):
        labels = _assign_labels(pixels_lab, centers)
        new_centers = centers.copy()

        for cluster_index in range(2):
            cluster_members = labels == cluster_index
            if not np.any(cluster_members):
                return (robust_median_estimate(pixels_rgb),)

            new_centers[cluster_index] = np.mean(
                pixels_lab[cluster_members],
                axis=0,
                dtype=np.float64,
            )

        maximum_shift = float(
            np.max(np.linalg.norm(new_centers - centers, axis=1))
        )
        centers = new_centers

        if maximum_shift <= selected_config.convergence_tolerance:
            break

    labels = _assign_labels(pixels_lab, centers)
    estimates: list[ClusterEstimate] = []
    total_count = len(pixels_rgb)

    for cluster_index in range(2):
        members = labels == cluster_index
        member_count = int(np.count_nonzero(members))
        ratio = member_count / total_count

        if ratio < selected_config.minimum_cluster_ratio:
            continue

        center_lab = np.mean(
            pixels_lab[members],
            axis=0,
            dtype=np.float64,
        )
        estimates.append(
            _build_estimate(
                center_lab=center_lab,
                members=members,
                total_count=total_count,
            )
        )

    estimates.sort(
        key=lambda estimate: (
            -estimate.ratio,
            estimate.lab,
        )
    )
    return tuple(estimates)


def _assign_labels(
    pixels_lab: LabPixels,
    centers: LabPixels,
) -> NDArray[np.int64]:
    distances = np.linalg.norm(
        pixels_lab[:, np.newaxis, :] - centers[np.newaxis, :, :],
        axis=2,
    )
    return np.argmin(distances, axis=1).astype(np.int64)


def _build_estimate(
    *,
    center_lab: NDArray[np.float64],
    members: BooleanVector,
    total_count: int,
) -> ClusterEstimate:
    lab = (
        float(center_lab[0]),
        float(center_lab[1]),
        float(center_lab[2]),
    )
    member_copy = members.astype(np.bool_, copy=True)

    return ClusterEstimate(
        lab=lab,
        rgb=_cielab_to_rgb(lab),
        ratio=int(np.count_nonzero(member_copy)) / total_count,
        members=member_copy,
    )


def _rgb_pixels_to_cielab(
    pixels_rgb: RGBPixels,
) -> LabPixels:
    normalized_rgb = (
        pixels_rgb.astype(np.float32).reshape((1, -1, 3)) / 255.0
    )
    converted = cv2.cvtColor(
        normalized_rgb,
        cv2.COLOR_RGB2Lab,
    ).reshape((-1, 3))

    return converted.astype(np.float64)


def _cielab_to_rgb(lab: LabColor) -> RGBColor:
    lab_image = np.asarray(
        lab,
        dtype=np.float32,
    ).reshape((1, 1, 3))

    normalized_rgb = cv2.cvtColor(
        lab_image,
        cv2.COLOR_Lab2RGB,
    )[0, 0]

    rgb = np.rint(
        np.clip(normalized_rgb, 0.0, 1.0) * 255.0
    ).astype(np.uint8)

    return int(rgb[0]), int(rgb[1]), int(rgb[2])


def _validate_pixels_rgb(pixels_rgb: RGBPixels) -> None:
    if (
        pixels_rgb.dtype != np.uint8
        or pixels_rgb.ndim != 2
        or pixels_rgb.shape[1] != 3
    ):
        raise ValueError(
            "pixels_rgb must be a uint8 N x 3 RGB array"
        )

    if len(pixels_rgb) == 0:
        raise ValueError(
            "pixels_rgb must contain at least one pixel"
        )