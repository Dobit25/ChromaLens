"""Selective, explainable assistive recoloring for risky garment pixels.

The transform is deliberately not a universal source-to-target color rule.
For each relational-risk context it generates lightness-preserving CIELCH
candidates, evaluates their separation after the selected CVD simulation, and
penalizes unnecessary departure from the original corrected cluster color.
"""

from __future__ import annotations

from collections import OrderedDict
from dataclasses import dataclass
import math

import cv2
import numpy as np
from numpy.typing import NDArray

from chromalens.color_naming import (
    LabColor,
    RGBColor,
    cielab_to_rgb_color,
    rgb_color_to_cielab,
)
from chromalens.config import CVDProfile
from chromalens.contracts import BinaryMask, ColorCluster, ColorFrame, RiskAssessment
from chromalens.cvd_simulation import MachadoSimulator, validate_severity
from chromalens.risk_detection import ciede2000

AlphaMask = NDArray[np.float32]


@dataclass(frozen=True, slots=True)
class RecolorConfig:
    """Validated thresholds for candidate choice, containment, and stability."""

    minimum_risk_score: float = 0.25
    feather_radius_px: float = 3.0
    candidate_hue_offsets_degrees: tuple[float, ...] = (
        -150.0,
        -120.0,
        -90.0,
        -60.0,
        -30.0,
        30.0,
        60.0,
        90.0,
        120.0,
        150.0,
        180.0,
    )
    candidate_chroma_scales: tuple[float, ...] = (0.75, 1.0, 1.25)
    minimum_candidate_chroma: float = 24.0
    maximum_candidate_chroma: float = 80.0
    identity_departure_penalty: float = 0.18
    minimum_simulated_improvement: float = 3.0
    switch_objective_margin: float = 2.0
    switch_confirmation_frames: int = 3
    candidate_equivalence_delta_e: float = 2.0
    max_state_entries: int = 32

    def __post_init__(self) -> None:
        finite_non_negative = (
            "minimum_risk_score",
            "feather_radius_px",
            "minimum_candidate_chroma",
            "maximum_candidate_chroma",
            "identity_departure_penalty",
            "minimum_simulated_improvement",
            "switch_objective_margin",
            "candidate_equivalence_delta_e",
        )
        for field_name in finite_non_negative:
            value = getattr(self, field_name)
            if not np.isfinite(value) or value < 0.0:
                raise ValueError(f"{field_name} must be finite and non-negative")
        if self.minimum_risk_score > 1.0:
            raise ValueError("minimum_risk_score must be within [0, 1]")
        if self.maximum_candidate_chroma <= 0.0:
            raise ValueError("maximum_candidate_chroma must be positive")
        if self.minimum_candidate_chroma > self.maximum_candidate_chroma:
            raise ValueError(
                "minimum_candidate_chroma must not exceed maximum_candidate_chroma"
            )
        if not self.candidate_hue_offsets_degrees:
            raise ValueError("candidate hue offsets must not be empty")
        if not self.candidate_chroma_scales:
            raise ValueError("candidate_chroma_scales must not be empty")
        if any(
            not np.isfinite(value) or value == 0.0
            for value in self.candidate_hue_offsets_degrees
        ):
            raise ValueError("candidate hue offsets must be finite and non-zero")
        if any(
            not np.isfinite(value) or value <= 0.0
            for value in self.candidate_chroma_scales
        ):
            raise ValueError("candidate chroma scales must be positive and finite")
        if self.switch_confirmation_frames <= 0:
            raise ValueError("switch_confirmation_frames must be positive")
        if self.max_state_entries <= 0:
            raise ValueError("max_state_entries must be positive")


@dataclass(frozen=True, slots=True)
class RecolorDebugData:
    """Machine-readable labels separating measured and display colors."""

    original_color_name: str
    original_corrected_rgb: RGBColor
    assistive_display_rgb: RGBColor
    comparison_original_rgb: RGBColor
    profile: CVDProfile
    severity: float
    risk_score: float
    risk_level: str
    original_simulated_delta_e: float
    assistive_simulated_delta_e: float
    candidate_objective: float
    applied: bool
    switched: bool
    decision_reason: str
    state_key: str

    def __post_init__(self) -> None:
        if not self.original_color_name.strip():
            raise ValueError("original_color_name must not be empty")
        _validate_rgb_color(self.original_corrected_rgb, "original_corrected_rgb")
        _validate_rgb_color(self.assistive_display_rgb, "assistive_display_rgb")
        _validate_rgb_color(self.comparison_original_rgb, "comparison_original_rgb")
        if not isinstance(self.profile, CVDProfile):
            raise TypeError("profile must be a CVDProfile selected by the user")
        validate_severity(self.severity)
        if not np.isfinite(self.risk_score) or not 0.0 <= self.risk_score <= 1.0:
            raise ValueError("risk_score must be finite within [0, 1]")
        if not self.risk_level.strip():
            raise ValueError("risk_level must not be empty")
        for field_name in (
            "original_simulated_delta_e",
            "assistive_simulated_delta_e",
        ):
            value = getattr(self, field_name)
            if not np.isfinite(value) or value < 0.0:
                raise ValueError(f"{field_name} must be finite and non-negative")
        if not np.isfinite(self.candidate_objective):
            raise ValueError("candidate_objective must be finite")
        if not self.decision_reason.strip():
            raise ValueError("decision_reason must not be empty")
        if not self.state_key.strip():
            raise ValueError("state_key must not be empty")
        if self.applied and self.original_corrected_rgb == self.assistive_display_rgb:
            raise ValueError("an applied assistive color must differ from the original")


@dataclass(frozen=True, slots=True)
class AssistiveRecolorResult:
    """A pre-overlay BGR result and the exact mask/alpha used to create it."""

    assistive_bgr: ColorFrame
    recolor_mask: BinaryMask
    alpha_mask: AlphaMask
    debug: RecolorDebugData

    def __post_init__(self) -> None:
        _validate_bgr_frame(self.assistive_bgr)
        _validate_binary_mask(self.recolor_mask, self.assistive_bgr.shape[:2], "recolor_mask")
        if (
            self.alpha_mask.dtype != np.float32
            or self.alpha_mask.ndim != 2
            or self.alpha_mask.shape != self.recolor_mask.shape
            or not np.all(np.isfinite(self.alpha_mask))
            or np.any((self.alpha_mask < 0.0) | (self.alpha_mask > 1.0))
        ):
            raise ValueError("alpha_mask must be an aligned finite float32 mask in [0, 1]")
        if np.any(self.alpha_mask[~self.recolor_mask] != 0.0):
            raise ValueError("alpha_mask must be exactly zero outside recolor_mask")
        if self.debug.applied and not np.any(self.alpha_mask > 0.0):
            raise ValueError("an applied recolor result must contain positive alpha")
        if not self.debug.applied and np.any(self.alpha_mask != 0.0):
            raise ValueError("an unapplied recolor result must have zero alpha")


@dataclass(frozen=True, slots=True)
class _CandidateScore:
    rgb: RGBColor
    simulated_delta_e: float
    departure_delta_e: float
    objective: float


@dataclass(slots=True)
class _SelectionState:
    display_rgb: RGBColor
    pending_rgb: RGBColor | None = None
    pending_count: int = 0


class SelectiveRecolorer:
    """Choose and apply a stable assistive color inside an exact mask.

    State is held per caller-provided key and bounded with least-recently-used
    eviction. The first eligible frame establishes a display color. A different
    proposal must beat the current objective by a margin for consecutive frames
    before it is allowed to switch.
    """

    backend_name = "chromalens-cielch-candidate-v1"

    def __init__(
        self,
        config: RecolorConfig | None = None,
        *,
        simulator: MachadoSimulator | None = None,
    ) -> None:
        self.config = config or RecolorConfig()
        self.simulator = simulator or MachadoSimulator()
        self._states: OrderedDict[str, _SelectionState] = OrderedDict()

    @property
    def state_count(self) -> int:
        """Return the bounded number of active temporal selection records."""

        return len(self._states)

    def reset(self, state_key: str | None = None) -> None:
        """Clear one stream/track state or every state when no key is given."""

        if state_key is None:
            self._states.clear()
            return
        self._states.pop(state_key, None)

    def recolor(
        self,
        source_bgr: ColorFrame,
        *,
        garment_mask: BinaryMask,
        cluster: ColorCluster,
        risk_mask: BinaryMask,
        comparison_rgb: RGBColor,
        risk: RiskAssessment,
        profile: CVDProfile,
        severity: float,
        state_key: str,
    ) -> AssistiveRecolorResult:
        """Return an assistive BGR copy without changing ``source_bgr``.

        ``cluster.rgb`` and ``comparison_rgb`` are original corrected color
        estimates. ``source_bgr`` is the display frame. Only the exact
        ``garment_mask & cluster.submask & risk_mask`` intersection is assigned;
        inward feathering never touches a pixel outside that hard mask.
        """

        _validate_bgr_frame(source_bgr)
        shape = source_bgr.shape[:2]
        _validate_binary_mask(garment_mask, shape, "garment_mask")
        _validate_binary_mask(cluster.submask, shape, "cluster.submask")
        _validate_binary_mask(risk_mask, shape, "risk_mask")
        _validate_rgb_color(comparison_rgb, "comparison_rgb")
        if not state_key.strip():
            raise ValueError("state_key must not be empty")
        validated_severity = validate_severity(severity)
        if not isinstance(profile, CVDProfile):
            raise TypeError("profile must be a CVDProfile selected by the user")

        hard_mask = garment_mask & cluster.submask & risk_mask
        inactive_reason: str | None = None
        if risk.risk_score < self.config.minimum_risk_score:
            inactive_reason = "risk_below_threshold"
        elif validated_severity == 0.0:
            inactive_reason = "severity_zero"
        elif not np.any(hard_mask):
            inactive_reason = "empty_mask_intersection"

        if inactive_reason is not None:
            self.reset(state_key)
            return self._unchanged_result(
                source_bgr,
                hard_mask,
                cluster=cluster,
                comparison_rgb=comparison_rgb,
                risk=risk,
                profile=profile,
                severity=validated_severity,
                state_key=state_key,
                reason=inactive_reason,
            )

        proposal, original_simulated_delta_e = self._best_candidate(
            cluster.rgb,
            comparison_rgb,
            profile=profile,
            severity=validated_severity,
        )
        improvement = proposal.simulated_delta_e - original_simulated_delta_e
        if (
            proposal.rgb == cluster.rgb
            or improvement < self.config.minimum_simulated_improvement
        ):
            self.reset(state_key)
            return self._unchanged_result(
                source_bgr,
                hard_mask,
                cluster=cluster,
                comparison_rgb=comparison_rgb,
                risk=risk,
                profile=profile,
                severity=validated_severity,
                state_key=state_key,
                reason="no_candidate_improvement",
                original_simulated_delta_e=original_simulated_delta_e,
            )

        selected, switched = self._stabilize_candidate(
            state_key,
            proposal,
            original_rgb=cluster.rgb,
            comparison_rgb=comparison_rgb,
            profile=profile,
            severity=validated_severity,
        )
        alpha_mask = inward_feather_alpha(
            hard_mask,
            radius_px=self.config.feather_radius_px,
        )
        assistive_bgr = apply_lightness_preserving_chroma_shift(
            source_bgr,
            hard_mask,
            alpha_mask,
            original_lab=cluster.lab,
            display_rgb=selected.rgb,
        )
        debug = RecolorDebugData(
            original_color_name=cluster.original_name,
            original_corrected_rgb=cluster.rgb,
            assistive_display_rgb=selected.rgb,
            comparison_original_rgb=comparison_rgb,
            profile=profile,
            severity=validated_severity,
            risk_score=risk.risk_score,
            risk_level=risk.risk_level,
            original_simulated_delta_e=original_simulated_delta_e,
            assistive_simulated_delta_e=selected.simulated_delta_e,
            candidate_objective=selected.objective,
            applied=True,
            switched=switched,
            decision_reason="candidate_applied",
            state_key=state_key,
        )
        return AssistiveRecolorResult(
            assistive_bgr=assistive_bgr,
            recolor_mask=hard_mask.copy(),
            alpha_mask=alpha_mask,
            debug=debug,
        )

    def _best_candidate(
        self,
        original_rgb: RGBColor,
        comparison_rgb: RGBColor,
        *,
        profile: CVDProfile,
        severity: float,
    ) -> tuple[_CandidateScore, float]:
        candidates = _generate_candidate_colors(original_rgb, self.config)
        simulated_comparison = self.simulator.simulate_color(
            comparison_rgb,
            profile=profile,
            severity=severity,
        )
        simulated_comparison_lab = rgb_color_to_cielab(simulated_comparison)
        candidate_image = np.asarray(candidates, dtype=np.uint8).reshape((1, -1, 3))
        simulated_candidates = self.simulator.simulate_rgb(
            candidate_image,
            profile=profile,
            severity=severity,
        )[0]
        original_lab = rgb_color_to_cielab(original_rgb)
        scores: list[_CandidateScore] = []
        for candidate_rgb, simulated_rgb_array in zip(
            candidates,
            simulated_candidates,
            strict=True,
        ):
            simulated_rgb: RGBColor = (
                int(simulated_rgb_array[0]),
                int(simulated_rgb_array[1]),
                int(simulated_rgb_array[2]),
            )
            simulated_delta_e = ciede2000(
                rgb_color_to_cielab(simulated_rgb),
                simulated_comparison_lab,
            )
            departure = ciede2000(
                rgb_color_to_cielab(candidate_rgb),
                original_lab,
            )
            scores.append(
                _CandidateScore(
                    rgb=candidate_rgb,
                    simulated_delta_e=simulated_delta_e,
                    departure_delta_e=departure,
                    objective=(
                        simulated_delta_e
                        - self.config.identity_departure_penalty * departure
                    ),
                )
            )
        original_score = next(score for score in scores if score.rgb == original_rgb)
        best = max(
            scores,
            key=lambda item: (item.objective, item.simulated_delta_e, item.rgb),
        )
        return best, original_score.simulated_delta_e

    def _stabilize_candidate(
        self,
        state_key: str,
        proposal: _CandidateScore,
        *,
        original_rgb: RGBColor,
        comparison_rgb: RGBColor,
        profile: CVDProfile,
        severity: float,
    ) -> tuple[_CandidateScore, bool]:
        state = self._states.get(state_key)
        if state is None:
            self._states[state_key] = _SelectionState(display_rgb=proposal.rgb)
            self._states.move_to_end(state_key)
            while len(self._states) > self.config.max_state_entries:
                self._states.popitem(last=False)
            return proposal, False

        self._states.move_to_end(state_key)
        if _colors_equivalent(
            state.display_rgb,
            proposal.rgb,
            tolerance=self.config.candidate_equivalence_delta_e,
        ):
            state.pending_rgb = None
            state.pending_count = 0
            return self._score_one_candidate(
                state.display_rgb,
                original_rgb=original_rgb,
                comparison_rgb=comparison_rgb,
                profile=profile,
                severity=severity,
            ), False

        current = self._score_one_candidate(
            state.display_rgb,
            original_rgb=original_rgb,
            comparison_rgb=comparison_rgb,
            profile=profile,
            severity=severity,
        )
        if proposal.objective < current.objective + self.config.switch_objective_margin:
            state.pending_rgb = None
            state.pending_count = 0
            return current, False

        if state.pending_rgb is not None and _colors_equivalent(
            state.pending_rgb,
            proposal.rgb,
            tolerance=self.config.candidate_equivalence_delta_e,
        ):
            state.pending_count += 1
            state.pending_rgb = proposal.rgb
        else:
            state.pending_rgb = proposal.rgb
            state.pending_count = 1

        if state.pending_count < self.config.switch_confirmation_frames:
            return current, False
        state.display_rgb = proposal.rgb
        state.pending_rgb = None
        state.pending_count = 0
        return proposal, True

    def _score_one_candidate(
        self,
        candidate_rgb: RGBColor,
        *,
        original_rgb: RGBColor,
        comparison_rgb: RGBColor,
        profile: CVDProfile,
        severity: float,
    ) -> _CandidateScore:
        simulated_candidate = self.simulator.simulate_color(
            candidate_rgb,
            profile=profile,
            severity=severity,
        )
        simulated_comparison = self.simulator.simulate_color(
            comparison_rgb,
            profile=profile,
            severity=severity,
        )
        simulated_delta_e = ciede2000(
            rgb_color_to_cielab(simulated_candidate),
            rgb_color_to_cielab(simulated_comparison),
        )
        departure = ciede2000(
            rgb_color_to_cielab(candidate_rgb),
            rgb_color_to_cielab(original_rgb),
        )
        return _CandidateScore(
            rgb=candidate_rgb,
            simulated_delta_e=simulated_delta_e,
            departure_delta_e=departure,
            objective=(
                simulated_delta_e
                - self.config.identity_departure_penalty * departure
            ),
        )

    def _unchanged_result(
        self,
        source_bgr: ColorFrame,
        hard_mask: BinaryMask,
        *,
        cluster: ColorCluster,
        comparison_rgb: RGBColor,
        risk: RiskAssessment,
        profile: CVDProfile,
        severity: float,
        state_key: str,
        reason: str,
        original_simulated_delta_e: float | None = None,
    ) -> AssistiveRecolorResult:
        if original_simulated_delta_e is None:
            original_simulated_delta_e = risk.delta_e_cvd
        return AssistiveRecolorResult(
            assistive_bgr=source_bgr.copy(),
            recolor_mask=hard_mask.copy(),
            alpha_mask=np.zeros(hard_mask.shape, dtype=np.float32),
            debug=RecolorDebugData(
                original_color_name=cluster.original_name,
                original_corrected_rgb=cluster.rgb,
                assistive_display_rgb=cluster.rgb,
                comparison_original_rgb=comparison_rgb,
                profile=profile,
                severity=severity,
                risk_score=risk.risk_score,
                risk_level=risk.risk_level,
                original_simulated_delta_e=original_simulated_delta_e,
                assistive_simulated_delta_e=original_simulated_delta_e,
                candidate_objective=original_simulated_delta_e,
                applied=False,
                switched=False,
                decision_reason=reason,
                state_key=state_key,
            ),
        )


def inward_feather_alpha(mask: BinaryMask, *, radius_px: float) -> AlphaMask:
    """Return inward-only feather alpha, exactly zero outside ``mask``."""

    _validate_binary_mask(mask, mask.shape, "mask")
    if not np.isfinite(radius_px) or radius_px < 0.0:
        raise ValueError("radius_px must be finite and non-negative")
    if radius_px == 0.0:
        return mask.astype(np.float32)
    distance = cv2.distanceTransform(mask.astype(np.uint8), cv2.DIST_L2, 3)
    alpha = np.clip(distance / radius_px, 0.0, 1.0).astype(np.float32)
    alpha[~mask] = 0.0
    return alpha


def apply_lightness_preserving_chroma_shift(
    source_bgr: ColorFrame,
    mask: BinaryMask,
    alpha_mask: AlphaMask,
    *,
    original_lab: LabColor,
    display_rgb: RGBColor,
) -> ColorFrame:
    """Shift Lab chroma under ``mask`` while retaining each pixel's source L*."""

    _validate_bgr_frame(source_bgr)
    shape = source_bgr.shape[:2]
    _validate_binary_mask(mask, shape, "mask")
    if (
        alpha_mask.dtype != np.float32
        or alpha_mask.shape != shape
        or alpha_mask.ndim != 2
        or not np.all(np.isfinite(alpha_mask))
        or np.any((alpha_mask < 0.0) | (alpha_mask > 1.0))
    ):
        raise ValueError("alpha_mask must be an aligned finite float32 mask in [0, 1]")
    if np.any(alpha_mask[~mask] != 0.0):
        raise ValueError("alpha_mask must be zero outside mask")
    original_lab_array = np.asarray(original_lab, dtype=np.float32)
    if (
        original_lab_array.shape != (3,)
        or not np.all(np.isfinite(original_lab_array))
        or not 0.0 <= float(original_lab_array[0]) <= 100.0
    ):
        raise ValueError("original_lab must contain conventional finite CIELAB values")
    _validate_rgb_color(display_rgb, "display_rgb")
    if not np.any(mask):
        return source_bgr.copy()

    source_float = source_bgr.astype(np.float32) / 255.0
    source_lab_image = cv2.cvtColor(source_float, cv2.COLOR_BGR2LAB)
    display_lab = np.asarray(rgb_color_to_cielab(display_rgb), dtype=np.float32)
    shifted_lab = source_lab_image.copy()
    shifted_lab[..., 1] = np.clip(
        shifted_lab[..., 1] + (display_lab[1] - original_lab_array[1]),
        -127.0,
        127.0,
    )
    shifted_lab[..., 2] = np.clip(
        shifted_lab[..., 2] + (display_lab[2] - original_lab_array[2]),
        -127.0,
        127.0,
    )
    # L* is intentionally untouched. Texture/shading encoded as lightness is
    # therefore retained before unavoidable sRGB gamut clipping/quantization.
    shifted_bgr_float = cv2.cvtColor(shifted_lab, cv2.COLOR_LAB2BGR)
    shifted_bgr = np.rint(np.clip(shifted_bgr_float, 0.0, 1.0) * 255.0).astype(
        np.uint8
    )
    alpha = alpha_mask[..., None]
    blended = np.rint(
        source_bgr.astype(np.float32) * (1.0 - alpha)
        + shifted_bgr.astype(np.float32) * alpha
    ).astype(np.uint8)
    result = source_bgr.copy()
    result[mask] = blended[mask]
    return result


def _generate_candidate_colors(
    original_rgb: RGBColor,
    config: RecolorConfig,
) -> tuple[RGBColor, ...]:
    original_lab = rgb_color_to_cielab(original_rgb)
    lightness, a_star, b_star = original_lab
    chroma = math.hypot(a_star, b_star)
    hue = math.degrees(math.atan2(b_star, a_star)) % 360.0
    base_chroma = max(chroma, config.minimum_candidate_chroma)
    candidates: list[RGBColor] = [original_rgb]
    seen = {original_rgb}
    for scale in config.candidate_chroma_scales:
        candidate_chroma = min(
            base_chroma * scale,
            config.maximum_candidate_chroma,
        )
        for offset in config.candidate_hue_offsets_degrees:
            candidate_hue = math.radians((hue + offset) % 360.0)
            candidate_lab: LabColor = (
                lightness,
                candidate_chroma * math.cos(candidate_hue),
                candidate_chroma * math.sin(candidate_hue),
            )
            candidate_rgb = cielab_to_rgb_color(candidate_lab)
            if candidate_rgb not in seen:
                seen.add(candidate_rgb)
                candidates.append(candidate_rgb)
    return tuple(candidates)


def _colors_equivalent(first: RGBColor, second: RGBColor, *, tolerance: float) -> bool:
    if first == second:
        return True
    return ciede2000(
        rgb_color_to_cielab(first),
        rgb_color_to_cielab(second),
    ) <= tolerance


def _validate_bgr_frame(frame: ColorFrame) -> None:
    if frame.dtype != np.uint8 or frame.ndim != 3 or frame.shape[2] != 3:
        raise ValueError("source_bgr must be a uint8 H x W x 3 BGR image")
    if frame.shape[0] == 0 or frame.shape[1] == 0:
        raise ValueError("source_bgr dimensions must be non-empty")


def _validate_binary_mask(
    mask: BinaryMask,
    shape: tuple[int, int],
    field_name: str,
) -> None:
    if mask.dtype != np.bool_ or mask.ndim != 2 or mask.shape != shape:
        raise ValueError(f"{field_name} must be an aligned boolean H x W mask")


def _validate_rgb_color(rgb: RGBColor, field_name: str) -> None:
    if len(rgb) != 3 or any(
        not isinstance(channel, (int, np.integer)) or not 0 <= int(channel) <= 255
        for channel in rgb
    ):
        raise ValueError(
            f"{field_name} must contain three integer channels within [0, 255]"
        )
