"""T08 composition boundary for the local ChromaLens analytical pipeline."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
import logging
from time import monotonic_ns

import numpy as np

from chromalens.color_extraction import (
    ColorExtractionError,
    ColorExtractionMode,
    DominantColorExtractor,
)
from chromalens.config import CVDProfile
from chromalens.contracts import (
    BinaryMask,
    ColorCluster,
    ColorFrame,
    FramePacket,
    GarmentRegion,
    RiskAssessment,
)
from chromalens.cvd_simulation import validate_severity
from chromalens.matching import MatchingResult, RuleBasedMatcher
from chromalens.recolor import AssistiveRecolorResult, SelectiveRecolorer
from chromalens.risk_detection import RelationalRiskDetector
from chromalens.segmentation.base import Segmenter
from chromalens.tracking import TemporalMaskSmoother
from chromalens.white_balance import GrayWorldWhiteBalancer, WhiteBalanceResult

_logger = logging.getLogger(__name__)


class PipelineStage(str, Enum):
    """Stable stage identifiers for UI, evidence, and failure reports."""

    SEGMENTATION = "segmentation"
    WHITE_BALANCE = "white-balance"
    COLOR = "color"
    RISK = "risk"
    RECOLOR = "recolor"
    MATCHING = "matching"


class StageStatus(str, Enum):
    """A stage outcome that does not conflate confidence or risk."""

    OK = "ok"
    DEGRADED = "degraded"
    UNAVAILABLE = "unavailable"
    SKIPPED = "skipped"


@dataclass(frozen=True, slots=True)
class StageReport:
    """One explicit pipeline-stage outcome for the current frame."""

    stage: PipelineStage
    status: StageStatus
    message: str

    def __post_init__(self) -> None:
        if not self.message.strip():
            raise ValueError("stage report message must not be empty")


@dataclass(frozen=True, slots=True)
class PipelineSettings:
    """User-selected analytical settings, independent of display view."""

    profile: CVDProfile = CVDProfile.DEUTAN
    severity: float = 1.0
    recolor_enabled: bool = True

    def __post_init__(self) -> None:
        if not isinstance(self.profile, CVDProfile):
            raise TypeError("profile must be a CVDProfile selected by the user")
        validate_severity(self.severity)
        if not isinstance(self.recolor_enabled, bool):
            raise TypeError("recolor_enabled must be boolean")


@dataclass(frozen=True, slots=True)
class PipelineConfig:
    """T08 composition choices; thresholds remain owned by stage configs."""

    extraction_mode: ColorExtractionMode = ColorExtractionMode.KMEANS_2
    matching_enabled: bool = True

    def __post_init__(self) -> None:
        if not isinstance(self.extraction_mode, ColorExtractionMode):
            raise TypeError("extraction_mode must be a ColorExtractionMode")
        if not isinstance(self.matching_enabled, bool):
            raise TypeError("matching_enabled must be boolean")


@dataclass(frozen=True, slots=True)
class PipelineFrameResult:
    """All current-frame analysis needed by T08 views and evidence."""

    packet: FramePacket
    analysis_frame_id: int
    completed_timestamp_ns: int
    backend_name: str
    regions: tuple[GarmentRegion, ...]
    primary_region: GarmentRegion | None
    clusters: tuple[ColorCluster, ...]
    primary_cluster: ColorCluster | None
    comparison_cluster: ColorCluster | None
    risk: RiskAssessment | None
    risk_mask: BinaryMask
    recolor: AssistiveRecolorResult | None
    matching: MatchingResult | None
    white_balance: WhiteBalanceResult | None
    stage_reports: tuple[StageReport, ...]

    def __post_init__(self) -> None:
        if self.analysis_frame_id != self.packet.frame_id:
            raise ValueError(
                "analysis_frame_id must equal packet.frame_id; stale analysis "
                "cannot be presented as current"
            )
        if self.completed_timestamp_ns < self.packet.timestamp_ns:
            raise ValueError("completed timestamp must not precede capture timestamp")
        if not self.backend_name.strip():
            raise ValueError("backend_name must not be empty")
        if (
            self.risk_mask.dtype != np.bool_
            or self.risk_mask.ndim != 2
            or self.risk_mask.shape != self.packet.original_bgr.shape[:2]
        ):
            raise ValueError("risk_mask must be an aligned boolean H x W mask")
        if self.primary_region is not None and all(
            self.primary_region is not region for region in self.regions
        ):
            raise ValueError("primary_region must belong to regions")
        if self.primary_cluster is not None and all(
            self.primary_cluster is not cluster for cluster in self.clusters
        ):
            raise ValueError("primary_cluster must belong to clusters")
        if self.comparison_cluster is not None and all(
            self.comparison_cluster is not cluster for cluster in self.clusters
        ):
            raise ValueError("comparison_cluster must belong to clusters")
        if not self.stage_reports:
            raise ValueError("stage_reports must not be empty")

    @property
    def assistive_bgr(self) -> ColorFrame:
        """Return a copy of the current assistive or unchanged display frame."""

        if self.recolor is not None:
            return self.recolor.assistive_bgr.copy()
        return self.packet.original_bgr.copy()

    @property
    def degraded(self) -> bool:
        """Whether any required/current stage reported a degraded condition."""

        return any(
            report.status in (StageStatus.DEGRADED, StageStatus.UNAVAILABLE)
            for report in self.stage_reports
        )

    @property
    def degraded_reasons(self) -> tuple[str, ...]:
        """Return concise current-frame degraded/unavailable messages."""

        return tuple(
            f"{report.stage.value}: {report.message}"
            for report in self.stage_reports
            if report.status in (StageStatus.DEGRADED, StageStatus.UNAVAILABLE)
        )


class ChromaLensPipeline:
    """Compose T02-T07 without caching a prior result as the current frame."""

    def __init__(
        self,
        segmenter: Segmenter,
        *,
        stream_id: str,
        config: PipelineConfig | None = None,
        mask_smoother: TemporalMaskSmoother | None = None,
        white_balancer: GrayWorldWhiteBalancer | None = None,
        color_extractor: DominantColorExtractor | None = None,
        risk_detector: RelationalRiskDetector | None = None,
        recolorer: SelectiveRecolorer | None = None,
        matcher: RuleBasedMatcher | None = None,
    ) -> None:
        if not isinstance(segmenter, Segmenter):
            raise TypeError("segmenter must implement the Segmenter interface")
        if not stream_id.strip():
            raise ValueError("stream_id must not be empty")
        self.segmenter = segmenter
        self.stream_id = stream_id
        self.config = config or PipelineConfig()
        self.mask_smoother = mask_smoother or TemporalMaskSmoother()
        self.white_balancer = white_balancer or GrayWorldWhiteBalancer()
        self.color_extractor = color_extractor or DominantColorExtractor()
        self.risk_detector = risk_detector or RelationalRiskDetector()
        self.recolorer = recolorer or SelectiveRecolorer()
        self.matcher = matcher or RuleBasedMatcher()
        self._last_cvd_context: tuple[CVDProfile, float, bool] | None = None
        self._closed = False

    @property
    def backend_name(self) -> str:
        """Expose backend/device identity used by the live UI and metrics."""

        return self.segmenter.device_info

    def process(
        self,
        packet: FramePacket,
        settings: PipelineSettings,
    ) -> PipelineFrameResult:
        """Analyze exactly ``packet.frame_id`` and return no previous result."""

        if self._closed:
            raise RuntimeError("pipeline is closed")
        if not isinstance(settings, PipelineSettings):
            raise TypeError("settings must be PipelineSettings")
        context = (settings.profile, float(settings.severity), settings.recolor_enabled)
        if self._last_cvd_context is not None and context != self._last_cvd_context:
            self.recolorer.reset()
        self._last_cvd_context = context

        reports: list[StageReport] = []
        frame_shape = packet.original_bgr.shape[:2]
        regions: tuple[GarmentRegion, ...] = ()
        try:
            raw_regions = self.segmenter.segment(packet)
            regions = self.mask_smoother.smooth(
                raw_regions,
                stream_id=self.stream_id,
                frame_shape=frame_shape,
            )
            if regions:
                reports.append(
                    StageReport(
                        PipelineStage.SEGMENTATION,
                        StageStatus.OK,
                        f"{len(regions)} current-frame region(s)",
                    )
                )
            else:
                reports.append(
                    StageReport(
                        PipelineStage.SEGMENTATION,
                        StageStatus.DEGRADED,
                        "no current garment region; prior masks cleared",
                    )
                )
        except Exception as exc:  # explicit recoverable backend boundary
            _logger.exception("frame_id=%d segmentation failed", packet.frame_id)
            self.mask_smoother.reset()
            reports.append(_stage_failure(PipelineStage.SEGMENTATION, exc))

        primary_region = (
            max(regions, key=lambda region: int(np.count_nonzero(region.mask)))
            if regions
            else None
        )
        white_balance: WhiteBalanceResult | None = None
        estimation_mask = None
        if primary_region is not None:
            background_mask = ~primary_region.mask
            if np.any(background_mask):
                estimation_mask = background_mask
        try:
            white_balance = self.white_balancer.process(
                packet,
                estimation_mask=estimation_mask,
            )
            reports.append(
                StageReport(
                    PipelineStage.WHITE_BALANCE,
                    (
                        StageStatus.DEGRADED
                        if white_balance.used_fallback
                        else StageStatus.OK
                    ),
                    (
                        "insufficient valid pixels; previous/identity gains used"
                        if white_balance.used_fallback
                        else f"lighting={white_balance.lighting_quality.level.value}"
                    ),
                )
            )
        except Exception as exc:
            _logger.exception("frame_id=%d white balance failed", packet.frame_id)
            reports.append(_stage_failure(PipelineStage.WHITE_BALANCE, exc))

        clusters: tuple[ColorCluster, ...] = ()
        if primary_region is None:
            reports.append(
                StageReport(
                    PipelineStage.COLOR,
                    StageStatus.SKIPPED,
                    "no current garment region",
                )
            )
        elif white_balance is None:
            reports.append(
                StageReport(
                    PipelineStage.COLOR,
                    StageStatus.SKIPPED,
                    "corrected RGB unavailable",
                )
            )
        else:
            try:
                clusters = self.color_extractor.extract(
                    packet,
                    primary_region,
                    mode=self.config.extraction_mode,
                )
                reports.append(
                    StageReport(
                        PipelineStage.COLOR,
                        StageStatus.OK,
                        f"{len(clusters)} original corrected cluster(s)",
                    )
                )
            except (ColorExtractionError, ValueError) as exc:
                _logger.info(
                    "frame_id=%d color extraction degraded: %s",
                    packet.frame_id,
                    exc,
                )
                reports.append(
                    StageReport(
                        PipelineStage.COLOR,
                        StageStatus.DEGRADED,
                        _exception_message(exc),
                    )
                )

        primary_cluster = clusters[0] if clusters else None
        comparison_cluster = clusters[1] if len(clusters) >= 2 else None
        risk: RiskAssessment | None = None
        if primary_cluster is None or comparison_cluster is None:
            reports.append(
                StageReport(
                    PipelineStage.RISK,
                    StageStatus.DEGRADED,
                    "two retained original-color clusters are required",
                )
            )
        else:
            try:
                risk = self.risk_detector.assess_pair(
                    primary_cluster.rgb,
                    comparison_cluster.rgb,
                    source_id=(
                        f"{self.stream_id}:frame:{packet.frame_id}:cluster:0:"
                        f"{primary_cluster.original_name}"
                    ),
                    comparison_id=(
                        f"{self.stream_id}:frame:{packet.frame_id}:cluster:1:"
                        f"{comparison_cluster.original_name}"
                    ),
                    profile=settings.profile,
                    severity=settings.severity,
                )
                reports.append(
                    StageReport(
                        PipelineStage.RISK,
                        StageStatus.OK,
                        f"{risk.risk_level} score={risk.risk_score:.3f}",
                    )
                )
            except Exception as exc:
                _logger.exception("frame_id=%d risk stage failed", packet.frame_id)
                reports.append(_stage_failure(PipelineStage.RISK, exc))

        risk_mask = np.zeros(frame_shape, dtype=np.bool_)
        if (
            risk is not None
            and primary_cluster is not None
            and risk.risk_score >= self.recolorer.config.minimum_risk_score
        ):
            risk_mask = primary_cluster.submask.copy()

        recolor: AssistiveRecolorResult | None = None
        if not settings.recolor_enabled:
            self.recolorer.reset()
            reports.append(
                StageReport(
                    PipelineStage.RECOLOR,
                    StageStatus.SKIPPED,
                    "disabled by user",
                )
            )
        elif (
            primary_region is None
            or primary_cluster is None
            or comparison_cluster is None
            or risk is None
        ):
            reports.append(
                StageReport(
                    PipelineStage.RECOLOR,
                    StageStatus.SKIPPED,
                    "current relational risk context unavailable",
                )
            )
        else:
            try:
                recolor = self.recolorer.recolor(
                    packet.original_bgr,
                    garment_mask=primary_region.mask,
                    cluster=primary_cluster,
                    risk_mask=(
                        primary_cluster.submask
                        if risk.risk_score >= self.recolorer.config.minimum_risk_score
                        else risk_mask
                    ),
                    comparison_rgb=comparison_cluster.rgb,
                    risk=risk,
                    profile=settings.profile,
                    severity=settings.severity,
                    state_key=(
                        f"{self.stream_id}:{settings.profile.value}:"
                        f"{settings.severity:.2f}:cluster:0"
                    ),
                )
                reports.append(
                    StageReport(
                        PipelineStage.RECOLOR,
                        StageStatus.OK,
                        (
                            "selective assistive transform applied"
                            if recolor.debug.applied
                            else f"unchanged: {recolor.debug.decision_reason}"
                        ),
                    )
                )
            except Exception as exc:
                _logger.exception("frame_id=%d recolor failed", packet.frame_id)
                reports.append(_stage_failure(PipelineStage.RECOLOR, exc))

        matching: MatchingResult | None = None
        if not self.config.matching_enabled:
            reports.append(
                StageReport(
                    PipelineStage.MATCHING,
                    StageStatus.SKIPPED,
                    "disabled by pipeline configuration",
                )
            )
        elif primary_cluster is None:
            reports.append(
                StageReport(
                    PipelineStage.MATCHING,
                    StageStatus.SKIPPED,
                    "original corrected color unavailable",
                )
            )
        else:
            try:
                matching = self.matcher.suggest_from_original_cluster(
                    primary_cluster,
                    profile=settings.profile,
                    severity=settings.severity,
                )
                reports.append(
                    StageReport(
                        PipelineStage.MATCHING,
                        (
                            StageStatus.OK
                            if matching.suggestions
                            else StageStatus.DEGRADED
                        ),
                        matching.explanation_vi,
                    )
                )
            except Exception as exc:
                _logger.exception("frame_id=%d matching failed", packet.frame_id)
                reports.append(_stage_failure(PipelineStage.MATCHING, exc))

        return PipelineFrameResult(
            packet=packet,
            analysis_frame_id=packet.frame_id,
            completed_timestamp_ns=monotonic_ns(),
            backend_name=self.backend_name,
            regions=regions,
            primary_region=primary_region,
            clusters=clusters,
            primary_cluster=primary_cluster,
            comparison_cluster=comparison_cluster,
            risk=risk,
            risk_mask=risk_mask,
            recolor=recolor,
            matching=matching,
            white_balance=white_balance,
            stage_reports=tuple(reports),
        )

    def reset_temporal_state(self) -> None:
        """Clear all stream analysis state without changing configuration."""

        self.mask_smoother.reset()
        self.white_balancer.reset()
        self.recolorer.reset()
        self._last_cvd_context = None

    def close(self) -> None:
        """Release the AI backend and bounded temporal records once."""

        if self._closed:
            return
        try:
            self.segmenter.close()
        finally:
            self.reset_temporal_state()
            self._closed = True

    def __enter__(self) -> "ChromaLensPipeline":
        return self

    def __exit__(self, *_exc_info: object) -> None:
        self.close()


def _stage_failure(stage: PipelineStage, error: Exception) -> StageReport:
    return StageReport(stage, StageStatus.UNAVAILABLE, _exception_message(error))


def _exception_message(error: Exception) -> str:
    detail = " ".join(str(error).split())
    return f"{error.__class__.__name__}: {detail or 'no detail provided'}"
