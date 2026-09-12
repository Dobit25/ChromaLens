"""Bounded live SCHP keyframes with current-frame optical-flow propagation."""

from __future__ import annotations

from dataclasses import dataclass
import logging
from math import isfinite
from threading import Condition, Thread
from time import monotonic_ns

import cv2
import numpy as np
from numpy.typing import NDArray

from chromalens.contracts import BinaryMask, FramePacket, GarmentRegion
from chromalens.metrics import StageTimingName, StageTimingTracker
from chromalens.segmentation.base import (
    SegmentationFrameTelemetry,
    SegmentationMaskSource,
    Segmenter,
)

_logger = logging.getLogger(__name__)
FlowMap = NDArray[np.float32]


@dataclass(frozen=True, slots=True)
class AsyncKeyframeConfig:
    """Validated bounds for the single-worker live segmentation adapter."""

    maximum_mask_age_ms: float = 2_000.0
    flow_scale: float = 0.25
    minimum_area_ratio: float = 0.35
    maximum_area_ratio: float = 2.5
    minimum_region_pixels: int = 32
    inference_fps_ema_alpha: float = 0.25
    close_timeout_seconds: float = 10.0

    def __post_init__(self) -> None:
        if not isfinite(self.maximum_mask_age_ms) or self.maximum_mask_age_ms <= 0.0:
            raise ValueError("maximum_mask_age_ms must be finite and positive")
        if not isfinite(self.flow_scale) or not 0.0 < self.flow_scale <= 1.0:
            raise ValueError("flow_scale must be finite within (0, 1]")
        if not 0.0 < self.minimum_area_ratio <= 1.0:
            raise ValueError("minimum_area_ratio must be within (0, 1]")
        if not isfinite(self.maximum_area_ratio) or self.maximum_area_ratio < 1.0:
            raise ValueError("maximum_area_ratio must be finite and at least 1")
        if self.minimum_region_pixels <= 0:
            raise ValueError("minimum_region_pixels must be positive")
        if not 0.0 < self.inference_fps_ema_alpha <= 1.0:
            raise ValueError("inference_fps_ema_alpha must be within (0, 1]")
        if not isfinite(self.close_timeout_seconds) or self.close_timeout_seconds <= 0.0:
            raise ValueError("close_timeout_seconds must be finite and positive")


@dataclass(frozen=True, slots=True)
class _CompletedInference:
    packet: FramePacket
    regions: tuple[GarmentRegion, ...]
    completed_ns: int
    inference_latency_ms: float
    error: Exception | None = None


class AsyncKeyframeSegmenter(Segmenter):
    """Run one backend worker and propagate its latest mask to current frames.

    Both the pending-input mailbox and completed-output mailbox have capacity
    one. The caller never waits for model inference, and producer overwrites are
    counted rather than accumulated. Returned regions are always aligned with
    the packet passed to :meth:`segment`; provenance identifies whether they
    were inferred for that exact frame or propagated from an older keyframe.
    """

    def __init__(
        self,
        backend: Segmenter,
        config: AsyncKeyframeConfig | None = None,
        *,
        stage_timing: StageTimingTracker | None = None,
    ) -> None:
        if not isinstance(backend, Segmenter):
            raise TypeError("backend must implement the Segmenter interface")
        self._backend = backend
        self.config = config or AsyncKeyframeConfig()
        self._stage_timing = stage_timing
        self._condition = Condition()
        self._pending: FramePacket | None = None
        self._completed: _CompletedInference | None = None
        self._stop = False
        self._closed = False
        self._dropped_pending_frames = 0
        self._last_completion_ns: int | None = None
        self._inference_fps_ema: float | None = None
        self._active_regions: tuple[GarmentRegion, ...] = ()
        self._active_frame_bgr: NDArray[np.uint8] | None = None
        self._keyframe_id: int | None = None
        self._keyframe_timestamp_ns: int | None = None
        self._latest_inference_latency_ms: float | None = None
        self._frame_telemetry: SegmentationFrameTelemetry | None = None
        self._worker = Thread(
            target=self._worker_loop,
            name=f"chromalens-segmentation:{backend.backend_name}",
            daemon=True,
        )
        self._worker.start()

    @property
    def backend_name(self) -> str:
        return self._backend.backend_name

    @property
    def device_info(self) -> str:
        return f"{self._backend.device_info} + async-keyframes/optical-flow"

    @property
    def frame_telemetry(self) -> SegmentationFrameTelemetry | None:
        return self._frame_telemetry

    @property
    def manages_stage_timing(self) -> bool:
        return True

    @property
    def dropped_pending_frames(self) -> int:
        with self._condition:
            return self._dropped_pending_frames

    @property
    def worker_alive(self) -> bool:
        return self._worker.is_alive()

    def segment(self, packet: FramePacket) -> tuple[GarmentRegion, ...]:
        if self._closed:
            raise RuntimeError("AsyncKeyframeSegmenter.segment() called after close()")

        completed = self._take_completed()
        self._submit_latest(packet)
        optical_flow_attempted = False

        source = SegmentationMaskSource.WARMING_UP
        message: str | None = "waiting for first SCHP keyframe"
        if completed is not None:
            self._latest_inference_latency_ms = completed.inference_latency_ms
            if completed.error is not None:
                self._clear_active()
                source = SegmentationMaskSource.UNAVAILABLE
                message = (
                    f"{completed.error.__class__.__name__}: "
                    f"{' '.join(str(completed.error).split()) or 'no detail provided'}"
                )
            else:
                self._keyframe_id = completed.packet.frame_id
                self._keyframe_timestamp_ns = completed.packet.timestamp_ns
                optical_flow_attempted = completed.packet.frame_id != packet.frame_id
                aligned = self._align_completed(completed, packet)
                if completed.regions and not aligned:
                    self._clear_active(keep_keyframe=True)
                    source = SegmentationMaskSource.UNAVAILABLE
                    message = "optical-flow validation rejected the SCHP keyframe"
                else:
                    self._active_regions = aligned
                    self._active_frame_bgr = packet.original_bgr.copy()
                    source = (
                        SegmentationMaskSource.INFERRED
                        if completed.packet.frame_id == packet.frame_id
                        else SegmentationMaskSource.PROPAGATED
                    )
                    message = None
        elif self._active_regions and self._active_frame_bgr is not None:
            optical_flow_attempted = True
            propagated = self._propagate(
                self._active_regions,
                self._active_frame_bgr,
                packet.original_bgr,
            )
            if propagated:
                self._active_regions = propagated
                self._active_frame_bgr = packet.original_bgr.copy()
                source = SegmentationMaskSource.PROPAGATED
                message = None
            else:
                self._clear_active(keep_keyframe=True)
                source = SegmentationMaskSource.UNAVAILABLE
                message = "optical-flow propagation failed validation"

        if self._stage_timing is not None and not optical_flow_attempted:
            self._stage_timing.skip(StageTimingName.OPTICAL_FLOW)

        age_ms = self._mask_age_ms(packet)
        if age_ms is not None and age_ms > self.config.maximum_mask_age_ms:
            self._clear_active(keep_keyframe=True)
            source = SegmentationMaskSource.STALE
            message = (
                f"mask age {age_ms:.0f} ms exceeds "
                f"{self.config.maximum_mask_age_ms:.0f} ms limit"
            )

        self._frame_telemetry = SegmentationFrameTelemetry(
            frame_id=packet.frame_id,
            mask_source=source,
            keyframe_id=self._keyframe_id,
            mask_age_ms=age_ms,
            inference_fps=self._inference_fps_ema,
            inference_latency_ms=self._latest_inference_latency_ms,
            dropped_pending_frames=self.dropped_pending_frames,
            message=message,
        )
        return tuple(self._copy_region(region) for region in self._active_regions)

    def close(self) -> None:
        if self._closed:
            return
        with self._condition:
            self._closed = True
            self._stop = True
            self._pending = None
            self._condition.notify_all()
        self._worker.join(timeout=self.config.close_timeout_seconds)
        if self._worker.is_alive():
            _logger.error(
                "segmentation worker did not stop within %.1f seconds; backend "
                "close deferred to avoid racing an in-flight inference",
                self.config.close_timeout_seconds,
            )
            return
        self._backend.close()
        self._clear_active()

    def _submit_latest(self, packet: FramePacket) -> None:
        # FramePacket.original_bgr is an immutable pipeline source by contract;
        # corrected analysis fields are deliberately omitted from the worker copy.
        worker_packet = FramePacket(
            frame_id=packet.frame_id,
            timestamp_ns=packet.timestamp_ns,
            original_bgr=packet.original_bgr,
        )
        with self._condition:
            if self._pending is not None:
                self._dropped_pending_frames += 1
            self._pending = worker_packet
            self._condition.notify()

    def _take_completed(self) -> _CompletedInference | None:
        with self._condition:
            completed = self._completed
            self._completed = None
            return completed

    def _worker_loop(self) -> None:
        while True:
            with self._condition:
                while self._pending is None and not self._stop:
                    self._condition.wait()
                if self._stop:
                    return
                packet = self._pending
                self._pending = None
            assert packet is not None
            started_ns = monotonic_ns()
            try:
                if self._stage_timing is None:
                    regions = self._backend.segment(packet)
                else:
                    with self._stage_timing.measure(
                        StageTimingName.SEGMENTATION_INFERENCE
                    ):
                        regions = self._backend.segment(packet)
                error: Exception | None = None
            except Exception as exc:  # reported on the main analysis boundary
                regions = ()
                error = exc
            completed_ns = monotonic_ns()
            self._observe_inference_completion(completed_ns)
            completed = _CompletedInference(
                packet=packet,
                regions=regions,
                completed_ns=completed_ns,
                inference_latency_ms=(completed_ns - started_ns) / 1_000_000.0,
                error=error,
            )
            with self._condition:
                self._completed = completed
                self._condition.notify_all()

    def _observe_inference_completion(self, completed_ns: int) -> None:
        previous = self._last_completion_ns
        if previous is not None and completed_ns > previous:
            instantaneous = 1_000_000_000.0 / (completed_ns - previous)
            if self._inference_fps_ema is None:
                self._inference_fps_ema = instantaneous
            else:
                alpha = self.config.inference_fps_ema_alpha
                self._inference_fps_ema = (
                    alpha * instantaneous
                    + (1.0 - alpha) * self._inference_fps_ema
                )
        self._last_completion_ns = completed_ns

    def _align_completed(
        self,
        completed: _CompletedInference,
        current: FramePacket,
    ) -> tuple[GarmentRegion, ...]:
        if not completed.regions:
            return ()
        if completed.packet.frame_id == current.frame_id:
            return tuple(self._copy_region(region) for region in completed.regions)
        return self._propagate(
            completed.regions,
            completed.packet.original_bgr,
            current.original_bgr,
        )

    def _propagate(
        self,
        regions: tuple[GarmentRegion, ...],
        source_bgr: NDArray[np.uint8],
        target_bgr: NDArray[np.uint8],
    ) -> tuple[GarmentRegion, ...]:
        if source_bgr.shape != target_bgr.shape or not regions:
            return ()
        try:
            if self._stage_timing is None:
                backward_flow = estimate_backward_flow(
                    source_bgr,
                    target_bgr,
                    scale=self.config.flow_scale,
                )
            else:
                with self._stage_timing.measure(StageTimingName.OPTICAL_FLOW):
                    backward_flow = estimate_backward_flow(
                        source_bgr,
                        target_bgr,
                        scale=self.config.flow_scale,
                    )
        except (cv2.error, ValueError):
            return ()
        propagated: list[GarmentRegion] = []
        for region in regions:
            mask = warp_mask_with_backward_flow(region.mask, backward_flow)
            source_area = int(np.count_nonzero(region.mask))
            target_area = int(np.count_nonzero(mask))
            if source_area <= 0 or target_area < self.config.minimum_region_pixels:
                continue
            area_ratio = target_area / source_area
            if not self.config.minimum_area_ratio <= area_ratio <= self.config.maximum_area_ratio:
                continue
            propagated.append(
                GarmentRegion(
                    track_id=region.track_id,
                    class_name=region.class_name,
                    mask=mask,
                    mask_confidence=region.mask_confidence,
                )
            )
        return tuple(propagated)

    def _mask_age_ms(self, packet: FramePacket) -> float | None:
        if self._keyframe_timestamp_ns is None:
            return None
        return max(0.0, (packet.timestamp_ns - self._keyframe_timestamp_ns) / 1_000_000.0)

    def _clear_active(self, *, keep_keyframe: bool = False) -> None:
        self._active_regions = ()
        self._active_frame_bgr = None
        if not keep_keyframe:
            self._keyframe_id = None
            self._keyframe_timestamp_ns = None

    @staticmethod
    def _copy_region(region: GarmentRegion) -> GarmentRegion:
        return GarmentRegion(
            track_id=region.track_id,
            class_name=region.class_name,
            mask=region.mask.copy(),
            mask_confidence=region.mask_confidence,
        )


def estimate_backward_flow(
    source_bgr: NDArray[np.uint8],
    target_bgr: NDArray[np.uint8],
    *,
    scale: float = 0.5,
) -> FlowMap:
    """Estimate a target-to-source flow map for current-frame resampling."""

    if source_bgr.dtype != np.uint8 or source_bgr.ndim != 3 or source_bgr.shape[2] != 3:
        raise ValueError("source_bgr must be a uint8 H x W x 3 frame")
    if target_bgr.dtype != np.uint8 or target_bgr.shape != source_bgr.shape:
        raise ValueError("target_bgr must match source_bgr shape and dtype")
    if not isfinite(scale) or not 0.0 < scale <= 1.0:
        raise ValueError("scale must be finite within (0, 1]")

    height, width = source_bgr.shape[:2]
    small_width = max(16, round(width * scale))
    small_height = max(16, round(height * scale))
    source_gray = cv2.cvtColor(source_bgr, cv2.COLOR_BGR2GRAY)
    target_gray = cv2.cvtColor(target_bgr, cv2.COLOR_BGR2GRAY)
    if (small_width, small_height) != (width, height):
        source_gray = cv2.resize(source_gray, (small_width, small_height), interpolation=cv2.INTER_AREA)
        target_gray = cv2.resize(target_gray, (small_width, small_height), interpolation=cv2.INTER_AREA)

    small_flow = cv2.calcOpticalFlowFarneback(
        target_gray,
        source_gray,
        None,
        0.5,
        3,
        15,
        3,
        5,
        1.2,
        0,
    )
    if small_flow is None or not np.all(np.isfinite(small_flow)):
        raise ValueError("optical flow returned non-finite data")
    if (small_width, small_height) == (width, height):
        return small_flow.astype(np.float32, copy=False)
    flow = cv2.resize(small_flow, (width, height), interpolation=cv2.INTER_LINEAR)
    flow[..., 0] *= width / small_width
    flow[..., 1] *= height / small_height
    return flow.astype(np.float32, copy=False)


def warp_mask_with_backward_flow(mask: BinaryMask, backward_flow: FlowMap) -> BinaryMask:
    """Warp one source mask using a target-to-source dense flow field."""

    if mask.dtype != np.bool_ or mask.ndim != 2:
        raise ValueError("mask must be a boolean H x W array")
    if (
        backward_flow.dtype != np.float32
        or backward_flow.shape != (*mask.shape, 2)
        or not np.all(np.isfinite(backward_flow))
    ):
        raise ValueError("backward_flow must be a finite float32 H x W x 2 array")
    height, width = mask.shape
    grid_x, grid_y = np.meshgrid(
        np.arange(width, dtype=np.float32),
        np.arange(height, dtype=np.float32),
    )
    remapped = cv2.remap(
        mask.astype(np.uint8),
        grid_x + backward_flow[..., 0],
        grid_y + backward_flow[..., 1],
        cv2.INTER_NEAREST,
        borderMode=cv2.BORDER_CONSTANT,
        borderValue=0,
    )
    return remapped.astype(np.bool_)
