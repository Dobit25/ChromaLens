"""Bounded temporal smoothing for current-frame garment masks.

The smoother never emits pixels outside the current segmentation mask.  Prior
state may suppress a newly appearing edge for one frame, but it cannot paint a
stale garment region after the current backend has rejected that pixel.
"""

from __future__ import annotations

from collections import OrderedDict
from dataclasses import dataclass

import numpy as np
from numpy.typing import NDArray

from chromalens.contracts import GarmentRegion

ProbabilityMask = NDArray[np.float32]


@dataclass(frozen=True, slots=True)
class MaskSmoothingConfig:
    """Validated EMA settings for a small bounded set of garment regions."""

    current_frame_weight: float = 0.45
    threshold: float = 0.50
    max_state_entries: int = 8

    def __post_init__(self) -> None:
        if not 0.0 < self.current_frame_weight <= 1.0:
            raise ValueError("current_frame_weight must be within (0, 1]")
        if not 0.0 < self.threshold <= 1.0:
            raise ValueError("threshold must be within (0, 1]")
        if not isinstance(self.max_state_entries, int) or isinstance(
            self.max_state_entries, bool
        ):
            raise ValueError("max_state_entries must be a positive integer")
        if self.max_state_entries <= 0:
            raise ValueError("max_state_entries must be a positive integer")


class TemporalMaskSmoother:
    """Smooth aligned masks without retaining a stale result as current."""

    def __init__(self, config: MaskSmoothingConfig | None = None) -> None:
        self.config = config or MaskSmoothingConfig()
        self._states: OrderedDict[str, ProbabilityMask] = OrderedDict()

    @property
    def state_count(self) -> int:
        """Return the bounded number of current temporal records."""

        return len(self._states)

    def reset(self, state_key: str | None = None) -> None:
        """Clear one record or every record when no key is supplied."""

        if state_key is None:
            self._states.clear()
        else:
            self._states.pop(state_key, None)

    def smooth(
        self,
        regions: tuple[GarmentRegion, ...],
        *,
        stream_id: str,
        frame_shape: tuple[int, int],
    ) -> tuple[GarmentRegion, ...]:
        """Return current-frame-contained masks and update bounded EMA state."""

        if not stream_id.strip():
            raise ValueError("stream_id must not be empty")
        height, width = frame_shape
        if height <= 0 or width <= 0:
            raise ValueError("frame_shape dimensions must be positive")
        if not regions:
            # An empty current result must stay empty rather than displaying a
            # previous mask without a stale warning.
            self.reset()
            return ()

        active_keys: set[str] = set()
        smoothed_regions: list[GarmentRegion] = []
        for index, region in enumerate(regions):
            if region.mask.shape != frame_shape:
                raise ValueError("every garment mask must align with frame_shape")
            identity = (
                f"track:{region.track_id}"
                if region.track_id is not None
                else f"class:{region.class_name}:index:{index}"
            )
            state_key = f"{stream_id}:{identity}"
            active_keys.add(state_key)
            current = region.mask.astype(np.float32)
            previous = self._states.get(state_key)
            if previous is None or previous.shape != current.shape:
                ema = current
            else:
                alpha = self.config.current_frame_weight
                ema = alpha * current + (1.0 - alpha) * previous

            # Containment in the current mask is intentional: history can
            # stabilize acceptance, never resurrect rejected/stale pixels.
            smoothed_mask = (ema >= self.config.threshold) & region.mask
            if not np.any(smoothed_mask):
                smoothed_mask = region.mask.copy()
            self._states[state_key] = ema.astype(np.float32, copy=False)
            self._states.move_to_end(state_key)
            smoothed_regions.append(
                GarmentRegion(
                    track_id=region.track_id,
                    class_name=region.class_name,
                    mask=smoothed_mask.astype(np.bool_, copy=False),
                    mask_confidence=region.mask_confidence,
                )
            )

        for stale_key in tuple(self._states):
            if stale_key.startswith(f"{stream_id}:") and stale_key not in active_keys:
                self._states.pop(stale_key, None)
        while len(self._states) > self.config.max_state_entries:
            self._states.popitem(last=False)
        return tuple(smoothed_regions)
