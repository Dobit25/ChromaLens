"""Machado 2009 CVD simulation with an explicit uint8 sRGB boundary.

DaltonLens owns the sRGB gamma decoding, linear-RGB Machado transform, gamut
clipping, and sRGB encoding for every non-zero severity. ChromaLens only maps
its user-selected profile enum to DaltonLens and validates the public contract.
"""

from __future__ import annotations

import numpy as np
from daltonlens import simulate

from chromalens.color_naming import RGBColor
from chromalens.config import CVDProfile
from chromalens.contracts import ColorFrame


class CVDSimulationError(RuntimeError):
    """Raised when the verified simulation backend violates its contract."""


_DALTONLENS_DEFICIENCIES: dict[CVDProfile, simulate.Deficiency] = {
    CVDProfile.PROTAN: simulate.Deficiency.PROTAN,
    CVDProfile.DEUTAN: simulate.Deficiency.DEUTAN,
    CVDProfile.TRITAN: simulate.Deficiency.TRITAN,
}


class MachadoSimulator:
    """Apply DaltonLens's Machado 2009 model to RGB images or RGB colors.

    Input and output are gamma-encoded sRGB channel order, never OpenCV BGR.
    Severity zero returns an independent exact copy. That identity shortcut
    avoids a one-code-value round-trip loss in DaltonLens 0.1.5 while retaining
    the library's documented linear-light path for every non-zero severity.
    """

    backend_name = "daltonlens-machado2009"

    def __init__(self) -> None:
        self._backend = simulate.Simulator_Machado2009()

    def simulate_rgb(
        self,
        image_rgb: ColorFrame,
        *,
        profile: CVDProfile,
        severity: float,
    ) -> ColorFrame:
        """Return a simulated copy of a uint8 ``H x W x 3`` sRGB image."""

        _validate_rgb_image(image_rgb)
        deficiency = _deficiency_for_profile(profile)
        validated_severity = validate_severity(severity)
        if validated_severity == 0.0:
            return image_rgb.copy()

        try:
            simulated = self._backend.simulate_cvd(
                image_rgb.copy(),
                deficiency,
                validated_severity,
            )
        except Exception as exc:  # pragma: no cover - defensive backend boundary
            raise CVDSimulationError(
                "DaltonLens Machado simulation failed for validated uint8 sRGB input"
            ) from exc
        if (
            not isinstance(simulated, np.ndarray)
            or simulated.dtype != np.uint8
            or simulated.shape != image_rgb.shape
        ):
            raise CVDSimulationError(
                "DaltonLens returned an invalid result; expected aligned uint8 RGB"
            )
        return simulated.copy()

    def simulate_color(
        self,
        rgb: RGBColor,
        *,
        profile: CVDProfile,
        severity: float,
    ) -> RGBColor:
        """Simulate one original corrected sRGB color tuple."""

        _validate_rgb_color(rgb)
        image = np.asarray(rgb, dtype=np.uint8).reshape((1, 1, 3))
        simulated = self.simulate_rgb(
            image,
            profile=profile,
            severity=severity,
        )[0, 0]
        return (int(simulated[0]), int(simulated[1]), int(simulated[2]))


def validate_severity(severity: float) -> float:
    """Return severity as a finite float within the user-controlled range."""

    if isinstance(severity, (bool, np.bool_)):
        raise ValueError("severity must be a finite number within [0, 1]")
    try:
        value = float(severity)
    except (TypeError, ValueError) as exc:
        raise ValueError("severity must be a finite number within [0, 1]") from exc
    if not np.isfinite(value) or not 0.0 <= value <= 1.0:
        raise ValueError("severity must be a finite number within [0, 1]")
    return value


def _deficiency_for_profile(profile: CVDProfile) -> simulate.Deficiency:
    if not isinstance(profile, CVDProfile):
        raise TypeError("profile must be a CVDProfile selected by the user")
    return _DALTONLENS_DEFICIENCIES[profile]


def _validate_rgb_image(image_rgb: ColorFrame) -> None:
    if image_rgb.dtype != np.uint8 or image_rgb.ndim != 3 or image_rgb.shape[2] != 3:
        raise ValueError("image_rgb must be a uint8 H x W x 3 RGB image")
    if image_rgb.shape[0] == 0 or image_rgb.shape[1] == 0:
        raise ValueError("image_rgb dimensions must be non-empty")


def _validate_rgb_color(rgb: RGBColor) -> None:
    if len(rgb) != 3 or any(
        not isinstance(channel, (int, np.integer)) or not 0 <= int(channel) <= 255
        for channel in rgb
    ):
        raise ValueError("rgb must contain three integer channels within [0, 255]")
