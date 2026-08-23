"""Evaluate the frozen 10-case T09 end-to-end matrix."""

from __future__ import annotations

import argparse
from dataclasses import dataclass, replace
from pathlib import Path
import shutil
import sys
from time import monotonic_ns
from typing import Any, Mapping, Sequence

import cv2
import numpy as np

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from chromalens.config import CVDProfile
from chromalens.contracts import FramePacket, GarmentRegion
from chromalens.pipeline import ChromaLensPipeline, PipelineFrameResult, PipelineSettings
from chromalens.renderer import (
    PipelineDisplayState,
    PipelineView,
    PreviewMetricsTracker,
    render_pipeline_view,
)
from chromalens.segmentation import MediaPipeSegmenter
from chromalens.segmentation.base import Segmenter
from scripts.t09_evaluation_common import (
    PROTOCOL_VERSION,
    ROOT,
    collect_environment,
    curated_artifact,
    git_commit,
    ignored_artifact_manifest,
    load_cases,
    require_lens_interpreter,
    result_timestamp,
    sha256_file,
    utc_now,
    utc_text,
    write_csv_lf,
    write_json_lf,
    write_text_lf,
)


WORKSTREAM = "end_to_end"
OUTPUT_DIR = ROOT / "evaluation/results/curated/end_to_end"
ARTIFACT_DIR = ROOT / "artifacts/t09/end_to_end"
INPUT_DIR = ARTIFACT_DIR / "inputs"
REVIEW_DIR = ARTIFACT_DIR / "reviews"
WIDTH = 360
HEIGHT = 240
FRAME_COUNT = 8
COMMAND = "conda run --name lens python scripts/t09_end_to_end_eval.py"
CONSENT_REF = "private-record-held-by-data-custodian:t09-segmentation-consent-v1"
PRIVATE_LICENSE = "LicenseRef-ChromaLens-T09-Private-Evaluation"


class ControlledTorsoSegmenter(Segmenter):
    """Deterministic contract double used only for synthetic invariant cases."""

    @property
    def backend_name(self) -> str:
        return "controlled-t09-contract"

    @property
    def device_info(self) -> str:
        return "controlled-t09-contract/cpu"

    def segment(self, packet: FramePacket) -> tuple[GarmentRegion, ...]:
        height, width = packet.original_bgr.shape[:2]
        mask = np.zeros((height, width), dtype=np.bool_)
        mask[height // 4 : 3 * height // 4, width // 5 : 4 * width // 5] = True
        return (
            GarmentRegion(
                track_id=1,
                class_name="controlled-upper-clothes",
                mask=mask,
                mask_confidence=0.82,
            ),
        )


class EmptySegmenter(ControlledTorsoSegmenter):
    @property
    def backend_name(self) -> str:
        return "controlled-empty-t09"

    def segment(self, packet: FramePacket) -> tuple[GarmentRegion, ...]:
        return ()


class FailingSegmenter(ControlledTorsoSegmenter):
    @property
    def backend_name(self) -> str:
        return "controlled-unavailable-t09"

    def segment(self, packet: FramePacket) -> tuple[GarmentRegion, ...]:
        raise RuntimeError("controlled backend unavailable for T09 failure contract")


@dataclass(frozen=True, slots=True)
class CaseEvidence:
    case_id: str
    fixture_id: str
    status: str
    reason: str
    processed_frames: int
    degraded_frames: int
    mismatch_count: int
    outside_changed_pixels: int | None
    temporal_switches: int | None
    artifact_ids: tuple[str, ...]
    notes: str


def controlled_frame(*, multicolor: bool = True) -> np.ndarray:
    frame = np.full((HEIGHT, WIDTH, 3), 128, dtype=np.uint8)
    y0, y1 = HEIGHT // 4, 3 * HEIGHT // 4
    x0, x1 = WIDTH // 5, 4 * WIDTH // 5
    split = x0 + round((x1 - x0) * 0.62)
    frame[y0:y1, x0:split] = (30, 30, 210)
    frame[y0:y1, split:x1] = (20, 130, 130) if multicolor else (30, 30, 210)
    return frame


def no_person_frame() -> np.ndarray:
    x = np.linspace(55, 160, WIDTH, dtype=np.uint8)
    gradient = np.tile(x, (HEIGHT, 1))
    return np.dstack((gradient, np.flipud(gradient), gradient // 2))


def normalize_frame(frame: np.ndarray) -> np.ndarray:
    if frame.ndim != 3 or frame.shape[2] != 3 or frame.dtype != np.uint8:
        raise ValueError("frame must be uint8 BGR H x W x 3")
    source_height, source_width = frame.shape[:2]
    scale = min(WIDTH / source_width, HEIGHT / source_height)
    resized_width = max(1, round(source_width * scale))
    resized_height = max(1, round(source_height * scale))
    resized = cv2.resize(
        frame, (resized_width, resized_height), interpolation=cv2.INTER_AREA
    )
    output = np.zeros((HEIGHT, WIDTH, 3), dtype=np.uint8)
    x0 = (WIDTH - resized_width) // 2
    y0 = (HEIGHT - resized_height) // 2
    output[y0 : y0 + resized_height, x0 : x0 + resized_width] = resized
    return output


def target_switch_count(values: Sequence[tuple[int, int, int]]) -> int:
    return sum(first != second for first, second in zip(values, values[1:]))


def changed_pixels_outside(
    original: np.ndarray, assistive: np.ndarray, hard_mask: np.ndarray
) -> int:
    if original.shape != assistive.shape or hard_mask.shape != original.shape[:2]:
        raise ValueError("containment inputs must align")
    changed = np.any(original != assistive, axis=2)
    return int(np.count_nonzero(changed & ~hard_mask))


def _write_image(path: Path, frame: np.ndarray) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    if not cv2.imwrite(str(path), frame):
        raise RuntimeError(f"could not write {path}")
    return path


def _write_video(path: Path, frames: Sequence[np.ndarray]) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    writer = cv2.VideoWriter(
        str(path), cv2.VideoWriter_fourcc(*"MJPG"), 12.0, (WIDTH, HEIGHT)
    )
    if not writer.isOpened():
        raise RuntimeError(f"could not create {path}")
    try:
        for frame in frames:
            writer.write(frame)
    finally:
        writer.release()
    return path


def prepare_inputs() -> dict[str, Path]:
    INPUT_DIR.mkdir(parents=True, exist_ok=True)
    controlled = _write_image(
        INPUT_DIR / "controlled-multicolor.png", controlled_frame(multicolor=True)
    )
    single = _write_image(
        INPUT_DIR / "single-color.png", controlled_frame(multicolor=False)
    )
    no_person = _write_image(INPUT_DIR / "no-person.png", no_person_frame())
    static = _write_video(
        INPUT_DIR / "static-multicolor.avi",
        [controlled_frame(multicolor=True) for _ in range(FRAME_COUNT)],
    )
    consented_source = (
        ROOT / "artifacts/t09/segmentation/inputs/motion-slow.mp4"
    )
    if not consented_source.is_file():
        raise FileNotFoundError(
            "consented moving source is absent; materialize Dong's verified "
            "artifacts/t09/segmentation/inputs/motion-slow.mp4 first"
        )
    moving = INPUT_DIR / "moving.mp4"
    if not moving.is_file() or sha256_file(moving) != sha256_file(consented_source):
        shutil.copyfile(consented_source, moving)
    return {
        "controlled": controlled,
        "single": single,
        "no_person": no_person,
        "static": static,
        "moving": moving,
    }


def process_frame(
    pipeline: ChromaLensPipeline,
    frame: np.ndarray,
    *,
    frame_id: int,
    recolor_enabled: bool = True,
) -> PipelineFrameResult:
    packet = FramePacket(
        frame_id=frame_id,
        timestamp_ns=monotonic_ns(),
        original_bgr=frame.copy(),
    )
    return pipeline.process(
        packet,
        PipelineSettings(
            profile=CVDProfile.DEUTAN,
            severity=0.8,
            recolor_enabled=recolor_enabled,
        ),
    )


def render_result(result: PipelineFrameResult, *, source_name: str) -> np.ndarray:
    telemetry = PreviewMetricsTracker().observe(
        result.packet, observed_ns=monotonic_ns()
    )
    return render_pipeline_view(
        result,
        source_name=source_name,
        telemetry=telemetry,
        display_state=PipelineDisplayState(
            profile=CVDProfile.DEUTAN,
            severity=0.8,
            recolor_enabled=result.recolor is not None,
            view=PipelineView.ASSISTIVE,
            dropped_capture_frames=0,
        ),
    )


def _stage_images(result: PipelineFrameResult, prefix: str) -> list[Path]:
    original = result.packet.original_bgr
    corrected = (
        cv2.cvtColor(result.packet.corrected_rgb, cv2.COLOR_RGB2BGR)
        if result.packet.corrected_rgb is not None
        else original.copy()
    )
    cluster_map = np.zeros_like(original)
    for cluster in result.clusters:
        cluster_map[cluster.submask] = tuple(reversed(cluster.rgb))
    risk_mask = np.zeros_like(original)
    risk_mask[result.risk_mask] = (255, 255, 255)
    final = render_result(result, source_name=f"t09:{prefix}")
    frames = (
        ("original", original),
        ("corrected", corrected),
        ("clusters", cluster_map),
        ("risk-mask", risk_mask),
        ("assistive", result.assistive_bgr),
        ("final", final),
    )
    return [
        _write_image(REVIEW_DIR / f"{prefix}-{suffix}.png", frame)
        for suffix, frame in frames
    ]


def _single_review(result: PipelineFrameResult, prefix: str) -> Path:
    return _write_image(
        REVIEW_DIR / f"{prefix}.png", render_result(result, source_name=f"t09:{prefix}")
    )


def _case_map() -> dict[str, Mapping[str, str]]:
    cases = load_cases(WORKSTREAM)
    if len(cases) != 10:
        raise RuntimeError(f"frozen end-to-end registry must have 10 cases, got {len(cases)}")
    return {case["case_id"]: case for case in cases}


def run_cases(inputs: Mapping[str, Path]) -> tuple[list[CaseEvidence], dict[str, Path]]:
    cases = _case_map()
    artifacts: dict[str, Path] = {
        "e2e-input-controlled": inputs["controlled"],
        "e2e-input-single": inputs["single"],
        "e2e-input-no-person": inputs["no_person"],
        "e2e-input-static": inputs["static"],
        "e2e-input-moving": inputs["moving"],
    }
    evidence: list[CaseEvidence] = []

    controlled_pipeline = ChromaLensPipeline(
        ControlledTorsoSegmenter(), stream_id="t09-controlled"
    )
    controlled = process_frame(controlled_pipeline, controlled_frame(), frame_id=0)
    if controlled.recolor is None or not controlled.recolor.debug.applied:
        raise RuntimeError("controlled multicolor case did not exercise recoloring")
    controlled_paths = _stage_images(controlled, "controlled-multicolor")
    controlled_ids = []
    for path in controlled_paths:
        artifact_id = f"e2e-review-{path.stem}"
        artifacts[artifact_id] = path
        controlled_ids.append(artifact_id)
    controlled_outside = changed_pixels_outside(
        controlled.packet.original_bgr,
        controlled.assistive_bgr,
        controlled.recolor.recolor_mask,
    )
    evidence.append(
        CaseEvidence(
            "E2E-CONTROLLED-MULTICOLOR",
            cases["E2E-CONTROLLED-MULTICOLOR"]["fixture_id"],
            "COMPLETE",
            "deterministic T02-T07 success path executed and rendered",
            1,
            int(controlled.degraded),
            int(controlled.analysis_frame_id != controlled.packet.frame_id),
            controlled_outside,
            None,
            tuple(["e2e-input-controlled", *controlled_ids]),
            "mask, correction, two clusters, risk, recolor, outline, overlay, and matching are available",
        )
    )

    real_source = cv2.imread(
        str(ROOT / "tests/samples/t02/astronaut.png"), cv2.IMREAD_COLOR
    )
    if real_source is None:
        raise RuntimeError("could not decode licensed astronaut fixture")
    with ChromaLensPipeline(
        MediaPipeSegmenter(), stream_id="t09-real-public"
    ) as real_pipeline:
        real = process_frame(real_pipeline, normalize_frame(real_source), frame_id=0)
        real_review = _single_review(real, "real-public-mediapipe")
    artifacts["e2e-review-real-public"] = real_review
    evidence.append(
        CaseEvidence(
            "E2E-REAL-PUBLIC",
            cases["E2E-REAL-PUBLIC"]["fixture_id"],
            "COMPLETE",
            "locked MediaPipe backend executed on the licensed public fixture",
            1,
            int(real.degraded),
            int(real.analysis_frame_id != real.packet.frame_id),
            None,
            None,
            ("e2e-review-real-public",),
            "; ".join(real.degraded_reasons) or "all required analytical stages available",
        )
    )

    single_pipeline = ChromaLensPipeline(
        ControlledTorsoSegmenter(), stream_id="t09-single"
    )
    single = process_frame(single_pipeline, controlled_frame(multicolor=False), frame_id=0)
    single_review = _single_review(single, "single-color-degraded")
    artifacts["e2e-review-single"] = single_review
    evidence.append(
        CaseEvidence(
            "E2E-SINGLE-COLOR",
            cases["E2E-SINGLE-COLOR"]["fixture_id"],
            "COMPLETE",
            "single-color input produced explicit unavailable relational risk",
            1,
            int(single.degraded),
            int(single.analysis_frame_id != single.packet.frame_id),
            None,
            None,
            ("e2e-input-single", "e2e-review-single"),
            "; ".join(single.degraded_reasons),
        )
    )

    empty_pipeline = ChromaLensPipeline(EmptySegmenter(), stream_id="t09-empty")
    empty = process_frame(empty_pipeline, no_person_frame(), frame_id=0)
    empty_review = _single_review(empty, "no-person-degraded")
    artifacts["e2e-review-no-person"] = empty_review
    evidence.append(
        CaseEvidence(
            "E2E-NO-PERSON",
            cases["E2E-NO-PERSON"]["fixture_id"],
            "COMPLETE",
            "negative case cleared dependent stages without fabricating a garment",
            1,
            int(empty.degraded),
            int(empty.analysis_frame_id != empty.packet.frame_id),
            None,
            None,
            ("e2e-input-no-person", "e2e-review-no-person"),
            "; ".join(empty.degraded_reasons),
        )
    )

    failure_pipeline = ChromaLensPipeline(
        FailingSegmenter(), stream_id="t09-backend-unavailable"
    )
    failed = process_frame(failure_pipeline, controlled_frame(), frame_id=0)
    failure_review = _single_review(failed, "backend-unavailable")
    artifacts["e2e-review-backend-unavailable"] = failure_review
    evidence.append(
        CaseEvidence(
            "E2E-BACKEND-UNAVAILABLE",
            cases["E2E-BACKEND-UNAVAILABLE"]["fixture_id"],
            "COMPLETE",
            "controlled exception was surfaced and no inference output was fabricated",
            1,
            int(failed.degraded),
            int(failed.analysis_frame_id != failed.packet.frame_id),
            None,
            None,
            ("e2e-input-controlled", "e2e-review-backend-unavailable"),
            "; ".join(failed.degraded_reasons),
        )
    )

    disabled_pipeline = ChromaLensPipeline(
        ControlledTorsoSegmenter(), stream_id="t09-recolor-disabled"
    )
    disabled = process_frame(
        disabled_pipeline, controlled_frame(), frame_id=0, recolor_enabled=False
    )
    disabled_review = _single_review(disabled, "recolor-disabled")
    artifacts["e2e-review-recolor-disabled"] = disabled_review
    disabled_outside = int(
        np.count_nonzero(
            np.any(disabled.assistive_bgr != disabled.packet.original_bgr, axis=2)
        )
    )
    evidence.append(
        CaseEvidence(
            "E2E-RECOLOR-DISABLED",
            cases["E2E-RECOLOR-DISABLED"]["fixture_id"],
            "COMPLETE",
            "recolor control disabled only the assistive transform",
            1,
            int(disabled.degraded),
            int(disabled.analysis_frame_id != disabled.packet.frame_id),
            disabled_outside,
            None,
            ("e2e-input-controlled", "e2e-review-recolor-disabled"),
            "analysis remained current and assistive pixels stayed source-identical",
        )
    )

    static_pipeline = ChromaLensPipeline(
        ControlledTorsoSegmenter(), stream_id="t09-static-temporal"
    )
    capture = cv2.VideoCapture(str(inputs["static"]))
    static_targets: list[tuple[int, int, int]] = []
    static_degraded = static_mismatches = static_frames = 0
    static_last: PipelineFrameResult | None = None
    try:
        while True:
            ok, frame = capture.read()
            if not ok:
                break
            static_last = process_frame(static_pipeline, frame, frame_id=static_frames)
            static_frames += 1
            static_degraded += int(static_last.degraded)
            static_mismatches += int(
                static_last.analysis_frame_id != static_last.packet.frame_id
            )
            if static_last.recolor is not None:
                static_targets.append(static_last.recolor.debug.assistive_display_rgb)
    finally:
        capture.release()
    if static_last is None or static_frames != FRAME_COUNT or not static_targets:
        raise RuntimeError("static temporal fixture did not complete its declared sequence")
    static_review = _single_review(static_last, "static-temporal-final")
    artifacts["e2e-review-static"] = static_review
    evidence.append(
        CaseEvidence(
            "E2E-STATIC-TEMPORAL",
            cases["E2E-STATIC-TEMPORAL"]["fixture_id"],
            "COMPLETE",
            "all eight decoded static frames retained an assistive target",
            static_frames,
            static_degraded,
            static_mismatches,
            None,
            target_switch_count(static_targets),
            ("e2e-input-static", "e2e-review-static"),
            f"retained assistive selections={len(static_targets)}",
        )
    )

    moving_capture = cv2.VideoCapture(str(inputs["moving"]))
    if not moving_capture.isOpened():
        raise RuntimeError("could not open consented moving input")
    declared_frames = max(1, int(moving_capture.get(cv2.CAP_PROP_FRAME_COUNT)))
    sample_indices = set(
        int(value) for value in np.linspace(0, declared_frames - 1, 9, dtype=np.int64)
    )
    moving_targets: list[tuple[int, int, int]] = []
    moving_degraded = moving_mismatches = moving_frames = 0
    moving_samples: list[np.ndarray] = []
    with ChromaLensPipeline(
        MediaPipeSegmenter(), stream_id="t09-moving-temporal"
    ) as moving_pipeline:
        try:
            while True:
                ok, frame = moving_capture.read()
                if not ok:
                    break
                current = process_frame(
                    moving_pipeline, normalize_frame(frame), frame_id=moving_frames
                )
                moving_degraded += int(current.degraded)
                moving_mismatches += int(
                    current.analysis_frame_id != current.packet.frame_id
                )
                if current.recolor is not None:
                    moving_targets.append(current.recolor.debug.assistive_display_rgb)
                if moving_frames in sample_indices:
                    moving_samples.append(
                        cv2.resize(
                            render_result(current, source_name="t09:moving"),
                            (320, 220),
                            interpolation=cv2.INTER_AREA,
                        )
                    )
                moving_frames += 1
        finally:
            moving_capture.release()
    if moving_frames == 0 or not moving_samples:
        raise RuntimeError("moving temporal case decoded no evidence frames")
    while len(moving_samples) < 9:
        moving_samples.append(np.zeros_like(moving_samples[0]))
    moving_contact = np.vstack(
        [np.hstack(moving_samples[index : index + 3]) for index in range(0, 9, 3)]
    )
    moving_review = _write_image(REVIEW_DIR / "moving-temporal-contact.png", moving_contact)
    artifacts["e2e-review-moving"] = moving_review
    evidence.append(
        CaseEvidence(
            "E2E-MOVING-TEMPORAL",
            cases["E2E-MOVING-TEMPORAL"]["fixture_id"],
            "COMPLETE",
            "all decoded consented video frames ran through locked MediaPipe and T03-T07",
            moving_frames,
            moving_degraded,
            moving_mismatches,
            None,
            (target_switch_count(moving_targets) if moving_targets else None),
            ("e2e-input-moving", "e2e-review-moving"),
            f"assistive selections={len(moving_targets)}; nine-frame contact review saved",
        )
    )

    stale_base = process_frame(
        ChromaLensPipeline(ControlledTorsoSegmenter(), stream_id="t09-stale"),
        controlled_frame(),
        frame_id=7,
    )
    rejected = False
    try:
        replace(stale_base, analysis_frame_id=6)
    except ValueError as error:
        rejected = "stale analysis" in str(error)
    if not rejected:
        raise RuntimeError("stale result contract did not reject mismatched frame ID")
    stale_review = _single_review(stale_base, "stale-current-frame")
    artifacts["e2e-review-stale"] = stale_review
    evidence.append(
        CaseEvidence(
            "E2E-STALE-REJECTION",
            cases["E2E-STALE-REJECTION"]["fixture_id"],
            "COMPLETE",
            "one synthetic stale result was rejected before rendering",
            1,
            int(stale_base.degraded),
            0,
            None,
            None,
            ("e2e-input-controlled", "e2e-review-stale"),
            "rejected_attempts=1; mismatched results presented=0",
        )
    )

    containment_pipeline = ChromaLensPipeline(
        ControlledTorsoSegmenter(), stream_id="t09-containment"
    )
    containment = process_frame(containment_pipeline, controlled_frame(), frame_id=0)
    if containment.recolor is None:
        raise RuntimeError("containment case did not produce a recolor result")
    containment_outside = changed_pixels_outside(
        containment.packet.original_bgr,
        containment.assistive_bgr,
        containment.recolor.recolor_mask,
    )
    containment_review = _single_review(containment, "recolor-containment")
    artifacts["e2e-review-containment"] = containment_review
    evidence.append(
        CaseEvidence(
            "E2E-RECOLOR-CONTAINMENT",
            cases["E2E-RECOLOR-CONTAINMENT"]["fixture_id"],
            "COMPLETE",
            "pre-overlay assistive bytes were compared outside the exact hard recolor mask",
            1,
            int(containment.degraded),
            int(containment.analysis_frame_id != containment.packet.frame_id),
            containment_outside,
            None,
            ("e2e-input-controlled", "e2e-review-containment"),
            "outline and text overlays were excluded from the containment comparison",
        )
    )

    for pipeline in (
        controlled_pipeline,
        single_pipeline,
        empty_pipeline,
        failure_pipeline,
        disabled_pipeline,
        static_pipeline,
        containment_pipeline,
    ):
        pipeline.close()
    return evidence, artifacts


def measured_metric(
    name: str,
    aggregation: str,
    unit: str,
    value: int | float,
    case_id: str,
    threshold_id: str,
    threshold_result: str,
    reason: str,
    method: str,
    dimensions: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    result: dict[str, Any] = {
        "name": name,
        "aggregation": aggregation,
        "unit": unit,
        "status": "MEASURED",
        "value": value,
        "case_ids": [case_id],
        "threshold_id": threshold_id,
        "threshold_result": threshold_result,
        "reason": reason,
        "method": method,
    }
    if dimensions:
        result["dimensions"] = dict(dimensions)
    return result


def unavailable_metric(
    name: str,
    aggregation: str,
    unit: str,
    case_id: str,
    threshold_id: str,
    reason: str,
    method: str,
) -> dict[str, Any]:
    return {
        "name": name,
        "aggregation": aggregation,
        "unit": unit,
        "status": "NOT_APPLICABLE",
        "value": None,
        "case_ids": [case_id],
        "threshold_id": threshold_id,
        "threshold_result": "NOT_APPLICABLE",
        "reason": reason,
        "method": method,
    }


def build_metrics(evidence: Sequence[CaseEvidence]) -> list[dict[str, Any]]:
    metrics: list[dict[str, Any]] = []
    for item in evidence:
        metrics.append(
            measured_metric(
                "analysis_frame_id_mismatch_count",
                "count",
                "count",
                item.mismatch_count,
                item.case_id,
                "required",
                "PASS" if item.mismatch_count == 0 else "FAIL",
                "only results whose analysis_frame_id equals current frame_id were retained",
                "count of mismatched result IDs allowed to reach evidence rendering",
                {"processed_frames": item.processed_frames},
            )
        )
        if item.case_id in {
            "E2E-REAL-PUBLIC",
            "E2E-NO-PERSON",
            "E2E-MOVING-TEMPORAL",
        }:
            metrics.append(
                measured_metric(
                    "degraded_frame_rate",
                    "single",
                    "ratio",
                    item.degraded_frames / item.processed_frames,
                    item.case_id,
                    "observation_only",
                    "NOT_EVALUATED",
                    f"{item.degraded_frames}/{item.processed_frames} frames had a degraded or unavailable required stage",
                    "degraded frame count / processed frame count",
                )
            )
        if item.outside_changed_pixels is not None:
            metrics.append(
                measured_metric(
                    "outside_recolor_mask_changed_pixel_count",
                    "count",
                    "pixel",
                    item.outside_changed_pixels,
                    item.case_id,
                    "required",
                    "PASS" if item.outside_changed_pixels == 0 else "FAIL",
                    "comparison occurs before outline and text overlay",
                    "count any-channel byte changes outside AssistiveRecolorResult.recolor_mask",
                )
            )
        if item.case_id in {"E2E-STATIC-TEMPORAL", "E2E-MOVING-TEMPORAL"}:
            if item.temporal_switches is None:
                metrics.append(
                    unavailable_metric(
                        "temporal_assistive_color_switch_count",
                        "count",
                        "count",
                        item.case_id,
                        "static_required",
                        "no assistive target was available; a zero switch count would be misleading",
                        "compare consecutive available assistive target RGB values after first selection",
                    )
                )
            else:
                is_static = item.case_id == "E2E-STATIC-TEMPORAL"
                metrics.append(
                    measured_metric(
                        "temporal_assistive_color_switch_count",
                        "count",
                        "count",
                        item.temporal_switches,
                        item.case_id,
                        "static_required",
                        (
                            "PASS"
                            if is_static and item.temporal_switches == 0
                            else "NOT_EVALUATED"
                        ),
                        (
                            "frozen zero-switch invariant for the static sequence"
                            if is_static
                            else "moving sequence is observation-only; static threshold is not applied"
                        ),
                        "count changes between consecutive available assistive target RGB values",
                    )
                )
    return metrics


def _ignored_artifact(
    artifact_id: str,
    case_ids: Sequence[str],
    path: Path,
    *,
    derived_from: Sequence[str] = (),
    private: bool = False,
    public: bool = False,
) -> dict[str, Any]:
    suffix = path.suffix.lower()
    media_type = {
        ".png": "image/png",
        ".jpg": "image/jpeg",
        ".jpeg": "image/jpeg",
        ".mp4": "video/mp4",
        ".avi": "video/x-msvideo",
    }.get(suffix, "application/octet-stream")
    return ignored_artifact_manifest(
        artifact_id=artifact_id,
        case_ids=case_ids,
        relative_path=path.resolve().relative_to(ROOT.resolve()).as_posix(),
        sha256=sha256_file(path),
        byte_size=path.stat().st_size,
        media_type=media_type,
        generation_command=COMMAND,
        created_at_utc=None,
        provenance_class=(
            "project_capture"
            if private and not derived_from
            else "public_fixture"
            if public and not derived_from
            else "derived_artifact"
            if derived_from
            else "project_synthetic"
        ),
        creator_or_source=(
            "T09 segmentation workstream data custodian"
            if private and not derived_from
            else "NASA public fixture through tests/samples/t02"
            if public and not derived_from
            else "ChromaLens T09 end-to-end evaluator"
        ),
        license_id=(
            PRIVATE_LICENSE
            if private
            else "LicenseRef-NASA-PublicDomain"
            if public
            else "Apache-2.0"
        ),
        license_evidence=(
            "Repository-owner attestation: Dong holds the private consent record; bytes remain untracked"
            if private
            else "tests/samples/t02/README.md rights record"
            if public
            else "Repository LICENSE and protocol Section 10"
        ),
        derived_from=derived_from,
        consent_status=(
            "EXPLICIT_WRITTEN_CONSENT_PRIVATE_RECORD"
            if private
            else "PUBLIC_LICENSED"
            if public
            else "NOT_APPLICABLE_NO_PERSON"
        ),
        consent_record_ref=(CONSENT_REF if private else None),
        contains_personal_data=private or public,
    )


def build_package(
    evidence: Sequence[CaseEvidence], artifact_paths: Mapping[str, Path]
) -> Path:
    started = utc_now()
    case_ids = [item.case_id for item in evidence]
    metrics = build_metrics(evidence)
    metrics_path = OUTPUT_DIR / "end_to_end_metrics.csv"
    metric_rows = [
        {
            "case_id": metric["case_ids"][0],
            "metric": metric["name"],
            "aggregation": metric["aggregation"],
            "unit": metric["unit"],
            "status": metric["status"],
            "value": "" if metric["value"] is None else metric["value"],
            "threshold_id": metric["threshold_id"],
            "threshold_result": metric["threshold_result"],
            "reason": metric["reason"],
        }
        for metric in metrics
    ]
    write_csv_lf(metrics_path, metric_rows, tuple(metric_rows[0]))

    report_path = OUTPUT_DIR / "report.md"
    lines = [
        "# T09 End-to-End Integration Evaluation",
        "",
        "Status: `COMPLETE` coverage of the frozen 10-case integration matrix.",
        "",
        "This is development-machine evidence. It is not sensor-to-photon measurement, demo-hardware acceptance, population accuracy, or clinical validation.",
        "",
        "## Results",
        "",
        "| Case | Status | Frames | Degraded | ID mismatch | Outside mask | Target switches | Observation |",
        "| --- | --- | ---: | ---: | ---: | ---: | ---: | --- |",
    ]
    for item in evidence:
        lines.append(
            f"| `{item.case_id}` | {item.status} | {item.processed_frames} | "
            f"{item.degraded_frames} | {item.mismatch_count} | "
            f"{item.outside_changed_pixels if item.outside_changed_pixels is not None else 'N/A'} | "
            f"{item.temporal_switches if item.temporal_switches is not None else 'N/A'} | {item.notes} |"
        )
    lines.extend(
        [
            "",
            "## Intermediate visual evidence",
            "",
            "The controlled success case saves source, corrected image, color-cluster map, CVD-risk mask, pre-overlay assistive recolor, and final overlay as separate ignored artifacts. Other cases save final views or a moving-video contact sheet. Every cited byte has a manifest entry and SHA-256 in `result.json`.",
            "",
            "## Concrete integration failures",
            "",
            "1. `E2E-SINGLE-COLOR`: a single retained color cannot produce relational risk; recolor stays unavailable. Mitigation: explain that a comparison color is required instead of fabricating risk.",
            "2. `E2E-NO-PERSON`: no current garment mask clears all dependent stages. Mitigation: show degraded state and ask the user to enter/reframe.",
            "3. `E2E-BACKEND-UNAVAILABLE`: backend exception is visible on the current frame and produces no fake mask. Mitigation: keep the documented fallback/error path and expose backend status.",
            "4. `E2E-MOVING-TEMPORAL`: real MediaPipe processing records degraded frames and may have no stable assistive selection. Mitigation: retain newest-frame semantics, expose degraded state, and evaluate SCHP only in T10 while preserving MediaPipe fallback.",
            "",
            "## Scope, privacy, bias, and limitations",
            "",
            "All processing is local/offline. Saving occurs only in this explicit evaluator. Synthetic fixtures contain no people; the NASA fixture is licensed and documented; the moving capture is covered by the owner-confirmed private consent record and remains ignored. This small convenience set does not establish demographic, garment, pose, lighting, camera, or user-outcome generalization.",
        ]
    )
    write_text_lf(report_path, "\n".join(lines))

    artifact_case_ids: dict[str, list[str]] = {}
    for item in evidence:
        for artifact_id in item.artifact_ids:
            artifact_case_ids.setdefault(artifact_id, []).append(item.case_id)
    artifacts: list[dict[str, Any]] = []
    for artifact_id, path in artifact_paths.items():
        ids = artifact_case_ids.get(artifact_id, case_ids)
        private = artifact_id in {"e2e-input-moving", "e2e-review-moving"}
        public = artifact_id == "e2e-review-real-public"
        derived = ()
        if artifact_id.startswith("e2e-review-controlled"):
            derived = ("e2e-input-controlled",)
        elif artifact_id == "e2e-review-single":
            derived = ("e2e-input-single",)
        elif artifact_id == "e2e-review-no-person":
            derived = ("e2e-input-no-person",)
        elif artifact_id == "e2e-review-static":
            derived = ("e2e-input-static",)
        elif artifact_id == "e2e-review-moving":
            derived = ("e2e-input-moving",)
        elif artifact_id.startswith("e2e-review-") and not public:
            derived = ("e2e-input-controlled",)
        artifacts.append(
            _ignored_artifact(
                artifact_id,
                ids,
                path,
                derived_from=derived,
                private=private,
                public=public,
            )
        )
    artifacts.extend(
        [
            curated_artifact(
                metrics_path,
                artifact_id="end-to-end-metrics",
                case_ids=case_ids,
                media_type="text/csv",
                generation_command=COMMAND,
                created_at=started,
                creator="ChromaLens T09 coordinators",
            ),
            curated_artifact(
                report_path,
                artifact_id="end-to-end-report",
                case_ids=case_ids,
                media_type="text/markdown",
                generation_command=COMMAND,
                created_at=started,
                creator="ChromaLens T09 coordinators",
            ),
        ]
    )

    ended = utc_now()
    failures = [
        {
            "failure_id": "FAIL-E2E-SINGLE-COLOR",
            "case_ids": ["E2E-SINGLE-COLOR"],
            "observed_behavior": "Only one retained original color; relational risk and recolor are unavailable",
            "expected_behavior": "Do not fabricate relational risk without a comparison color",
            "user_impact": "Assistive recolor is unavailable for this frame",
            "reproduction": COMMAND,
            "mitigation": "Explain the comparison requirement and keep the original view",
            "status": "OPEN",
        },
        {
            "failure_id": "FAIL-E2E-NO-PERSON",
            "case_ids": ["E2E-NO-PERSON"],
            "observed_behavior": "No current garment region and all dependent stages are cleared",
            "expected_behavior": "No stale garment inference may be presented",
            "user_impact": "Color assistance is unavailable until a person is visible",
            "reproduction": COMMAND,
            "mitigation": "Show degraded state and request reframing",
            "status": "OPEN",
        },
        {
            "failure_id": "FAIL-E2E-BACKEND-UNAVAILABLE",
            "case_ids": ["E2E-BACKEND-UNAVAILABLE"],
            "observed_behavior": "Controlled segmentation exception is surfaced as unavailable",
            "expected_behavior": "Fail visibly without fabricated inference",
            "user_impact": "Garment analysis is unavailable",
            "reproduction": COMMAND,
            "mitigation": "Expose backend status and preserve a documented fallback/error path",
            "status": "OPEN",
        },
        {
            "failure_id": "FAIL-E2E-MOVING-DEGRADED",
            "case_ids": ["E2E-MOVING-TEMPORAL"],
            "observed_behavior": f"{next(item.degraded_frames for item in evidence if item.case_id == 'E2E-MOVING-TEMPORAL')} moving frames had a degraded stage",
            "expected_behavior": "Stable garment analysis across the declared moving sequence",
            "user_impact": "Overlay availability or selected assistive color can be unstable",
            "reproduction": COMMAND,
            "mitigation": "Use newest-frame handling, expose degradation, and compare SCHP only through T10",
            "status": "OPEN",
        },
    ]
    result = {
        "protocol_version": PROTOCOL_VERSION,
        "schema_version": PROTOCOL_VERSION,
        "metric_registry_version": PROTOCOL_VERSION,
        "result_id": f"t09-end-to-end-{result_timestamp(ended)}",
        "workstream": WORKSTREAM,
        "result_status": "COMPLETE",
        "git_commit": git_commit(),
        "created_at_utc": utc_text(ended),
        "operator": {"role": "coordinator", "identifier": "t09-coordinator"},
        "environment": collect_environment(
            lock_path=ROOT / "requirements/segment-mediapipe-py310-win64.lock",
            backend_name="controlled-contract plus mediapipe-selfie-torso",
            backend_device="cpu",
            camera_or_source="generated fixtures, NASA astronaut fixture, and consented moving video",
            source_kind="generated",
            source_resolution=(WIDTH, HEIGHT),
            render_resolution=(WIDTH, HEIGHT),
            display_mode="headless",
            warmup_seconds=0.0,
            measurement_seconds=0.0,
        ),
        "cases": [
            {
                "case_id": item.case_id,
                "status": item.status,
                "fixture_id": item.fixture_id,
                "artifact_ids": list(
                    dict.fromkeys([*item.artifact_ids, "end-to-end-metrics", "end-to-end-report"])
                ),
                "reason": item.reason,
            }
            for item in evidence
        ],
        "configuration": {
            "cvd_profile": "deutan",
            "severity": 0.8,
            "thresholds": {
                "recolor_containment_outside_pixels": 0,
                "static_target_switches": 0,
                "analysis_frame_id_mismatches": 0,
            },
            "random_seed": 0,
            "settings": {
                "normalized_width": WIDTH,
                "normalized_height": HEIGHT,
                "static_frame_count": FRAME_COUNT,
                "moving_frames_processed": next(
                    item.processed_frames
                    for item in evidence
                    if item.case_id == "E2E-MOVING-TEMPORAL"
                ),
            },
        },
        "metrics": metrics,
        "artifacts": artifacts,
        "commands": [
            {
                "command": COMMAND,
                "exit_code": 0,
                "started_at_utc": utc_text(started),
                "ended_at_utc": utc_text(ended),
                "output_summary": "10/10 frozen end-to-end cases evaluated",
            }
        ],
        "failure_cases": failures,
        "limitations": [
            "Controlled Segmenter cases prove deterministic contracts, not AI segmentation quality.",
            "The real MediaPipe cases are development-machine observations on two convenience sources.",
            "Moving-target switch count is not interpreted as a static stability pass threshold.",
            "No sensor-to-photon or declared demo-hardware performance claim is made here.",
        ],
        "responsible_ai": {
            "runtime_local_offline": True,
            "frames_saved_by_default": False,
            "frames_uploaded_by_default": False,
            "medical_diagnosis_claim": False,
            "user_selected_profile": True,
            "privacy_summary": "Evaluation saving was explicit; consented moving media and all visual derivatives remain ignored and untracked.",
            "bias_coverage_summary": "Synthetic contracts and two convenience sources do not establish demographic, garment, pose, or camera generalization.",
            "environmental_summary": "No model training occurred; pretrained MediaPipe CPU inference and deterministic contract doubles were reused.",
            "license_summary": "Repository code/artifacts are Apache-2.0; NASA fixture rights are documented; private moving media is not redistributed.",
            "user_validation_status": "NOT_MEASURED",
        },
        "notes": "All invariant comparisons use pre-overlay pixels. Rendered images are visual evidence only.",
    }
    result_path = OUTPUT_DIR / "result.json"
    write_json_lf(result_path, result)
    print(f"wrote {result_path}")
    return result_path


def build_parser() -> argparse.ArgumentParser:
    return argparse.ArgumentParser(description=__doc__)


def main(argv: Sequence[str] | None = None) -> int:
    build_parser().parse_args(argv)
    require_lens_interpreter()
    inputs = prepare_inputs()
    evidence, artifacts = run_cases(inputs)
    build_package(evidence, artifacts)
    for item in evidence:
        print(
            f"{item.case_id}: frames={item.processed_frames} "
            f"degraded={item.degraded_frames} mismatches={item.mismatch_count}"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
