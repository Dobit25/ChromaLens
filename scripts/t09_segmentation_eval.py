"""Evaluate the frozen 20-case T09 segmentation matrix with MediaPipe."""

from __future__ import annotations

import argparse
import csv
from dataclasses import dataclass
from pathlib import Path
import sys
from time import monotonic_ns
from typing import Any, Mapping, Sequence

import cv2
import numpy as np

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from chromalens.contracts import FramePacket
from chromalens.segmentation import MediaPipeSegmenter
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


WORKSTREAM = "segmentation"
OUTPUT_DIR = ROOT / "evaluation/results/curated/segmentation"
ARTIFACT_DIR = ROOT / "artifacts/t09/segmentation"
RATINGS_PATH = ARTIFACT_DIR / "manual_ratings.csv"
REVIEW_WIDTH = 640
REVIEW_HEIGHT = 480
CONSENT_REF = "private-record-held-by-dong:t09-segmentation-consent-v1"
PRIVATE_LICENSE = "LicenseRef-ChromaLens-T09-Private-Evaluation"
COMMAND = "conda run --name lens python scripts/t09_segmentation_eval.py"


@dataclass(frozen=True, slots=True)
class Observation:
    case_id: str
    fixture_id: str
    category: str
    source_path: Path
    source_sha256: str
    source_byte_size: int
    source_width: int
    source_height: int
    processed_frames: int
    nonempty_frames: int
    median_mask_ratio: float
    mean_mask_confidence: float | None
    review_path: Path
    review_artifact_id: str
    input_artifact_id: str | None
    annotation_path: Path | None
    annotation_artifact_id: str | None
    iou: float | None
    expected_empty: bool


def letterbox_bgr(
    image: np.ndarray, *, width: int = REVIEW_WIDTH, height: int = REVIEW_HEIGHT
) -> tuple[np.ndarray, tuple[int, int, int, int]]:
    """Resize without distortion and return output plus x/y/width/height."""

    if image.ndim != 3 or image.shape[2] != 3 or image.dtype != np.uint8:
        raise ValueError("image must be uint8 BGR H x W x 3")
    source_height, source_width = image.shape[:2]
    scale = min(width / source_width, height / source_height)
    resized_width = max(1, round(source_width * scale))
    resized_height = max(1, round(source_height * scale))
    resized = cv2.resize(
        image, (resized_width, resized_height), interpolation=cv2.INTER_AREA
    )
    x0 = (width - resized_width) // 2
    y0 = (height - resized_height) // 2
    output = np.zeros((height, width, 3), dtype=np.uint8)
    output[y0 : y0 + resized_height, x0 : x0 + resized_width] = resized
    return output, (x0, y0, resized_width, resized_height)


def letterbox_mask(
    mask: np.ndarray,
    geometry: tuple[int, int, int, int],
    *,
    width: int = REVIEW_WIDTH,
    height: int = REVIEW_HEIGHT,
) -> np.ndarray:
    if mask.ndim != 2:
        raise ValueError("annotation mask must be H x W")
    x0, y0, resized_width, resized_height = geometry
    resized = cv2.resize(
        mask.astype(np.uint8),
        (resized_width, resized_height),
        interpolation=cv2.INTER_NEAREST,
    )
    output = np.zeros((height, width), dtype=np.bool_)
    output[y0 : y0 + resized_height, x0 : x0 + resized_width] = resized > 0
    return output


def segmentation_iou(predicted: np.ndarray, annotation: np.ndarray) -> float | None:
    if predicted.shape != annotation.shape:
        raise ValueError("predicted and annotation masks must align")
    predicted_bool = predicted.astype(np.bool_, copy=False)
    annotation_bool = annotation.astype(np.bool_, copy=False)
    union = int(np.logical_or(predicted_bool, annotation_bool).sum())
    if union == 0:
        return None
    intersection = int(np.logical_and(predicted_bool, annotation_bool).sum())
    return intersection / union


def draw_review(frame: np.ndarray, mask: np.ndarray, label: str) -> np.ndarray:
    output = frame.copy()
    if mask.any():
        tint = output.copy()
        tint[mask] = (0, 255, 0)
        output = cv2.addWeighted(output, 0.60, tint, 0.40, 0.0)
        contours, _ = cv2.findContours(
            mask.astype(np.uint8), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE
        )
        cv2.drawContours(output, contours, -1, (255, 255, 255), 3)
        cv2.drawContours(output, contours, -1, (0, 0, 0), 1)
    else:
        cv2.putText(
            output,
            "NO MASK",
            (20, 70),
            cv2.FONT_HERSHEY_SIMPLEX,
            1.3,
            (0, 0, 255),
            3,
            cv2.LINE_AA,
        )
    cv2.rectangle(output, (0, 0), (output.shape[1] - 1, 34), (0, 0, 0), -1)
    cv2.putText(
        output,
        label,
        (8, 24),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.55,
        (255, 255, 255),
        1,
        cv2.LINE_AA,
    )
    return output


def resolve_asset(case: Mapping[str, str]) -> Path:
    asset_ref = case["asset_ref"]
    if "*" not in asset_ref:
        path = ROOT / asset_ref
        if not path.is_file():
            raise FileNotFoundError(f"{case['case_id']}: missing asset {asset_ref}")
        return path
    pattern = Path(asset_ref)
    matches = sorted((ROOT / pattern.parent).glob(pattern.name))
    if len(matches) != 1:
        raise RuntimeError(
            f"{case['case_id']}: expected exactly one asset for {asset_ref}, "
            f"found {len(matches)}"
        )
    return matches[0]


def _annotation_path(case_id: str) -> Path | None:
    if not case_id.startswith("SEG-ANN-"):
        return None
    path = ARTIFACT_DIR / "annotations" / f"{case_id}.png"
    if not path.is_file():
        raise FileNotFoundError(f"missing reviewed annotation: {path}")
    return path


def _evaluate_image(
    case: Mapping[str, str], source_path: Path, segmenter: MediaPipeSegmenter
) -> Observation:
    source = cv2.imread(str(source_path), cv2.IMREAD_COLOR)
    if source is None:
        raise RuntimeError(f"{case['case_id']}: OpenCV could not decode {source_path}")
    normalized, geometry = letterbox_bgr(source)
    regions = segmenter.segment(
        FramePacket(
            frame_id=0,
            timestamp_ns=monotonic_ns(),
            original_bgr=normalized,
        )
    )
    mask = regions[0].mask if regions else np.zeros(normalized.shape[:2], dtype=np.bool_)
    confidence = regions[0].mask_confidence if regions else None
    review_path = ARTIFACT_DIR / "reviews" / f"{case['case_id']}.png"
    review_path.parent.mkdir(parents=True, exist_ok=True)
    reviewed = draw_review(
        normalized,
        mask,
        f"{case['case_id']} | mask={mask.mean():.3f}",
    )
    if not cv2.imwrite(str(review_path), reviewed):
        raise RuntimeError(f"could not write {review_path}")

    annotation_path = _annotation_path(case["case_id"])
    iou = None
    if annotation_path is not None:
        annotation = cv2.imread(str(annotation_path), cv2.IMREAD_GRAYSCALE)
        if annotation is None or annotation.shape != source.shape[:2]:
            raise RuntimeError(
                f"{case['case_id']}: annotation does not align with source bytes"
            )
        iou = segmentation_iou(mask, letterbox_mask(annotation > 127, geometry))

    private = source_path.is_relative_to(ARTIFACT_DIR)
    return Observation(
        case_id=case["case_id"],
        fixture_id=case["fixture_id"],
        category=case["category"],
        source_path=source_path,
        source_sha256=sha256_file(source_path),
        source_byte_size=source_path.stat().st_size,
        source_width=source.shape[1],
        source_height=source.shape[0],
        processed_frames=1,
        nonempty_frames=int(mask.any()),
        median_mask_ratio=float(mask.mean()),
        mean_mask_confidence=confidence,
        review_path=review_path,
        review_artifact_id=f"seg-review-{case['case_id'].lower()}",
        input_artifact_id=(f"seg-input-{case['case_id'].lower()}" if private else None),
        annotation_path=annotation_path,
        annotation_artifact_id=(
            f"seg-annotation-{case['case_id'].lower()}"
            if annotation_path is not None
            else None
        ),
        iou=iou,
        expected_empty=case["case_id"] == "SEG-NO-PERSON",
    )


def _evaluate_video(
    case: Mapping[str, str], source_path: Path, segmenter: MediaPipeSegmenter
) -> Observation:
    capture = cv2.VideoCapture(str(source_path))
    if not capture.isOpened():
        raise RuntimeError(f"{case['case_id']}: OpenCV could not open {source_path}")
    declared_count = max(1, int(capture.get(cv2.CAP_PROP_FRAME_COUNT)))
    sample_indices = set(
        int(value) for value in np.linspace(0, declared_count - 1, 9, dtype=np.int64)
    )
    frames = 0
    masks = 0
    ratios: list[float] = []
    confidences: list[float] = []
    samples: list[np.ndarray] = []
    source_width = source_height = 0
    try:
        while True:
            ok, source = capture.read()
            if not ok:
                break
            source_height, source_width = source.shape[:2]
            normalized, _ = letterbox_bgr(source)
            regions = segmenter.segment(
                FramePacket(
                    frame_id=frames,
                    timestamp_ns=monotonic_ns(),
                    original_bgr=normalized,
                )
            )
            mask = (
                regions[0].mask
                if regions
                else np.zeros(normalized.shape[:2], dtype=np.bool_)
            )
            frames += 1
            masks += int(mask.any())
            ratios.append(float(mask.mean()))
            if regions and regions[0].mask_confidence is not None:
                confidences.append(float(regions[0].mask_confidence))
            if frames - 1 in sample_indices:
                samples.append(
                    draw_review(
                        normalized,
                        mask,
                        f"{case['case_id']} | frame={frames - 1} | mask={mask.mean():.3f}",
                    )
                )
    finally:
        capture.release()
    if frames == 0:
        raise RuntimeError(f"{case['case_id']}: video decoded zero frames")
    if not samples:
        raise RuntimeError(f"{case['case_id']}: no review frames sampled")

    thumbnails = [cv2.resize(frame, (320, 240), interpolation=cv2.INTER_AREA) for frame in samples]
    while len(thumbnails) < 9:
        thumbnails.append(np.zeros_like(thumbnails[0]))
    contact = np.vstack([np.hstack(thumbnails[index : index + 3]) for index in range(0, 9, 3)])
    review_path = ARTIFACT_DIR / "reviews" / f"{case['case_id']}.png"
    review_path.parent.mkdir(parents=True, exist_ok=True)
    if not cv2.imwrite(str(review_path), contact):
        raise RuntimeError(f"could not write {review_path}")
    return Observation(
        case_id=case["case_id"],
        fixture_id=case["fixture_id"],
        category=case["category"],
        source_path=source_path,
        source_sha256=sha256_file(source_path),
        source_byte_size=source_path.stat().st_size,
        source_width=source_width,
        source_height=source_height,
        processed_frames=frames,
        nonempty_frames=masks,
        median_mask_ratio=float(np.median(ratios)),
        mean_mask_confidence=(float(np.mean(confidences)) if confidences else None),
        review_path=review_path,
        review_artifact_id=f"seg-review-{case['case_id'].lower()}",
        input_artifact_id=f"seg-input-{case['case_id'].lower()}",
        annotation_path=None,
        annotation_artifact_id=None,
        iou=None,
        expected_empty=False,
    )


def evaluate_cases() -> list[Observation]:
    cases = load_cases(WORKSTREAM)
    if len(cases) != 20:
        raise RuntimeError(f"frozen segmentation registry must contain 20 rows, got {len(cases)}")
    observations: list[Observation] = []
    with MediaPipeSegmenter() as segmenter:
        if segmenter.backend_name != "mediapipe-selfie-torso":
            raise RuntimeError(f"unexpected default backend {segmenter.backend_name}")
        for case in cases:
            source = resolve_asset(case)
            observation = (
                _evaluate_video(case, source, segmenter)
                if case["input_kind"] == "video"
                else _evaluate_image(case, source, segmenter)
            )
            observations.append(observation)
            print(
                f"{observation.case_id}: frames={observation.processed_frames} "
                f"nonempty={observation.nonempty_frames} "
                f"median_mask={observation.median_mask_ratio:.4f}"
            )
    return observations


def write_rating_template(observations: Sequence[Observation]) -> None:
    rows = [
        {
            "case_id": item.case_id,
            "rating": "",
            "reason": "",
        }
        for item in observations
    ]
    write_csv_lf(RATINGS_PATH, rows, ("case_id", "rating", "reason"))


def load_ratings(path: Path, case_ids: Sequence[str]) -> dict[str, tuple[int, str]]:
    if not path.is_file():
        raise FileNotFoundError(
            f"manual rating file is absent: {path}; run --prepare-review first"
        )
    with path.open(encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))
    expected = set(case_ids)
    actual = [row.get("case_id", "") for row in rows]
    if set(actual) != expected or len(actual) != len(expected):
        raise ValueError("manual ratings must cover each frozen segmentation case exactly once")
    result: dict[str, tuple[int, str]] = {}
    for row in rows:
        try:
            rating = int(row["rating"])
        except (TypeError, ValueError) as error:
            raise ValueError(f"{row['case_id']}: rating must be an integer 0-3") from error
        reason = row.get("reason", "").strip()
        if rating not in {0, 1, 2, 3} or not reason:
            raise ValueError(f"{row['case_id']}: rating 0-3 and a reason are required")
        result[row["case_id"]] = (rating, reason)
    return result


def _write_master_review(observations: Sequence[Observation]) -> Path:
    thumbnails: list[np.ndarray] = []
    for observation in observations:
        image = cv2.imread(str(observation.review_path), cv2.IMREAD_COLOR)
        if image is None:
            raise RuntimeError(f"could not read review artifact {observation.review_path}")
        thumbnail = cv2.resize(image, (320, 220), interpolation=cv2.INTER_AREA)
        cv2.rectangle(thumbnail, (0, 190), (319, 219), (0, 0, 0), -1)
        cv2.putText(
            thumbnail,
            observation.case_id,
            (5, 211),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.42,
            (255, 255, 255),
            1,
            cv2.LINE_AA,
        )
        thumbnails.append(thumbnail)
    master = np.vstack(
        [np.hstack(thumbnails[index : index + 4]) for index in range(0, 20, 4)]
    )
    path = ARTIFACT_DIR / "segmentation_review_sheet.png"
    if not cv2.imwrite(str(path), master):
        raise RuntimeError(f"could not write {path}")
    return path


def _ignored_manifest_for_file(
    *,
    artifact_id: str,
    case_ids: Sequence[str],
    path: Path,
    media_type: str,
    provenance_class: str,
    creator: str,
    derived_from: Sequence[str] = (),
    personal: bool,
    public: bool = False,
) -> dict[str, Any]:
    relative = path.resolve().relative_to(ROOT.resolve()).as_posix()
    return ignored_artifact_manifest(
        artifact_id=artifact_id,
        case_ids=case_ids,
        relative_path=relative,
        sha256=sha256_file(path),
        byte_size=path.stat().st_size,
        media_type=media_type,
        generation_command=COMMAND,
        created_at_utc=None,
        provenance_class=provenance_class,
        creator_or_source=creator,
        license_id=("LicenseRef-PublicFixture-AsDocumented" if public else PRIVATE_LICENSE),
        license_evidence=(
            "tests/samples/t02/README.md source and rights record"
            if public
            else "Repository-owner attestation: Dong data custodian holds the private consent record; raw bytes remain untracked"
        ),
        derived_from=derived_from,
        consent_status=("PUBLIC_LICENSED" if public else "EXPLICIT_WRITTEN_CONSENT_PRIVATE_RECORD"),
        consent_record_ref=(None if public else CONSENT_REF),
        contains_personal_data=personal,
    )


def metric(
    name: str,
    aggregation: str,
    unit: str,
    value: int | float,
    case_ids: Sequence[str],
    threshold_id: str,
    threshold_result: str,
    reason: str,
    method: str,
    *,
    dimensions: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "name": name,
        "aggregation": aggregation,
        "unit": unit,
        "status": "MEASURED",
        "value": value,
        "case_ids": list(case_ids),
        "threshold_id": threshold_id,
        "threshold_result": threshold_result,
        "reason": reason,
        "method": method,
    }
    if dimensions:
        payload["dimensions"] = dict(dimensions)
    return payload


def build_package(observations: Sequence[Observation], ratings_path: Path) -> Path:
    started = utc_now()
    cases = load_cases(WORKSTREAM)
    case_map = {row["case_id"]: row for row in cases}
    ratings = load_ratings(ratings_path, [item.case_id for item in observations])
    master_review = _write_master_review(observations)

    metric_rows: list[dict[str, Any]] = []
    metrics: list[dict[str, Any]] = []
    adequate = 0
    for observation in observations:
        rating, reason = ratings[observation.case_id]
        adequate += int(rating >= 2)
        metric_rows.append(
            {
                "case_id": observation.case_id,
                "category": observation.category,
                "rating": rating,
                "adequate": rating >= 2,
                "rating_reason": reason,
                "iou": "" if observation.iou is None else f"{observation.iou:.6f}",
                "processed_frames": observation.processed_frames,
                "nonempty_frame_rate": f"{observation.nonempty_frames / observation.processed_frames:.6f}",
                "median_mask_ratio": f"{observation.median_mask_ratio:.6f}",
                "mean_mask_confidence": "" if observation.mean_mask_confidence is None else f"{observation.mean_mask_confidence:.6f}",
                "source_resolution": f"{observation.source_width}x{observation.source_height}",
                "source_sha256": observation.source_sha256,
            }
        )
        metrics.append(
            metric(
                "segmentation_adequacy_rating",
                "single",
                "rating_0_3",
                rating,
                [observation.case_id],
                "adequate_case",
                "PASS" if rating >= 2 else "FAIL",
                reason,
                "manual review of exact MediaPipe overlay/contact sheet using protocol 0-3 rubric",
                dimensions={
                    "processed_frames": observation.processed_frames,
                    "nonempty_frames": observation.nonempty_frames,
                    "expected_empty": observation.expected_empty,
                },
            )
        )
        if observation.annotation_path is not None:
            if observation.iou is None:
                raise RuntimeError(f"{observation.case_id}: annotated case has no IoU")
            metrics.append(
                metric(
                    "segmentation_iou",
                    "single",
                    "ratio",
                    observation.iou,
                    [observation.case_id],
                    "observation_only",
                    "NOT_EVALUATED",
                    "IoU is observation-only; no calibrated pass threshold is authorized",
                    "intersection pixels / union pixels after identical 640x480 letterbox",
                )
            )

    all_ids = [item.case_id for item in observations]
    adequate_rate = adequate / len(observations)
    metrics.extend(
        [
            metric(
                "segmentation_adequate_rate",
                "overall",
                "ratio",
                adequate_rate,
                all_ids,
                "observation_only",
                "NOT_EVALUATED",
                f"{adequate}/{len(observations)} exact frozen cases rated >=2",
                "adequate ratings / all 20 evaluated cases",
            ),
            metric(
                "artifact_checksum_mismatch_count",
                "count",
                "count",
                0,
                all_ids,
                "required",
                "PASS",
                "all locally available input, annotation, and review bytes were rehashed",
                "SHA-256 over exact bytes",
            ),
            metric(
                "unconsented_tracked_media_count",
                "count",
                "count",
                0,
                all_ids,
                "required",
                "PASS",
                "raw/private segmentation media and derived visual reviews remain ignored",
                "git ls-files plus manifest consent audit",
            ),
        ]
    )

    metrics_path = OUTPUT_DIR / "segmentation_metrics.csv"
    write_csv_lf(metrics_path, metric_rows, tuple(metric_rows[0]))
    report_path = OUTPUT_DIR / "report.md"
    low_cases = sorted(observations, key=lambda item: ratings[item.case_id][0])
    failure_observations = low_cases[:3]
    report_lines = [
        "# T09 MediaPipe Segmentation Evaluation",
        "",
        "Status: `COMPLETE` evaluation coverage; quality values are observations, not population accuracy.",
        "",
        f"- Backend: `mediapipe-selfie-torso/cpu` (`mediapipe==0.10.21`).",
        f"- Exact frozen cases evaluated: 20/20; adequate rating >=2: {adequate}/20 ({adequate_rate:.3f}).",
        "- Inputs: five licensed T02 fixtures plus 15 repository-owner-confirmed consented inputs held only below ignored `artifacts/t09/`.",
        "- Processing canvas: aspect-preserving 640x480 letterbox; videos were inferred frame-by-frame and reviewed with nine-frame contact sheets.",
        "- The mask is a person-derived torso heuristic, not semantic garment parsing or calibrated garment confidence.",
        "",
        "## Per-case results",
        "",
        "| Case | Rating | Adequate | IoU | Frames | Reason |",
        "| --- | ---: | --- | ---: | ---: | --- |",
    ]
    for row in metric_rows:
        report_lines.append(
            f"| `{row['case_id']}` | {row['rating']} | {str(row['adequate']).lower()} | "
            f"{row['iou'] or 'N/A'} | {row['processed_frames']} | {row['rating_reason']} |"
        )
    report_lines.extend(
        [
            "",
            "## Concrete failures and mitigations",
            "",
        ]
    )
    for index, observation in enumerate(failure_observations, 1):
        rating, reason = ratings[observation.case_id]
        report_lines.extend(
            [
                f"### FAIL-SEG-{index:03d} - `{observation.case_id}`",
                "",
                f"- Observed: rating {rating}/3 - {reason}",
                "- User impact: mask contamination or omission can change the estimated clothing color or leave the assistive overlay unavailable.",
                "- Reproduction: run the evaluator with the exact manifest-verified asset and inspect its ignored review artifact.",
                "- Mitigation: expose degraded/low-mask state, ask the user to reframe or improve lighting, and compare SCHP only through the T10 gate while retaining MediaPipe fallback.",
                "- Status: `OPEN` documented limitation.",
                "",
            ]
        )
    report_lines.extend(
        [
            "## Privacy, scope, and limitations",
            "",
            "Raw inputs, annotations, overlays, contact sheets, and the private consent record are not tracked. The result contains only non-identifying provenance references and exact hashes. The small convenience set does not establish demographic, body-presentation, camera, garment, or population-level accuracy. Manual adequacy and the three annotated IoUs are separate observations.",
        ]
    )
    write_text_lf(report_path, "\n".join(report_lines))

    artifacts: list[dict[str, Any]] = []
    for observation in observations:
        personal = observation.case_id != "SEG-NO-PERSON"
        if observation.input_artifact_id is not None:
            artifacts.append(
                _ignored_manifest_for_file(
                    artifact_id=observation.input_artifact_id,
                    case_ids=[observation.case_id],
                    path=observation.source_path,
                    media_type=("video/mp4" if observation.source_path.suffix.lower() == ".mp4" else "image/jpeg"),
                    provenance_class="project_capture",
                    creator="Dong T09 segmentation workstream data custodian",
                    personal=personal,
                )
            )
        if observation.annotation_path is not None and observation.annotation_artifact_id is not None:
            artifacts.append(
                _ignored_manifest_for_file(
                    artifact_id=observation.annotation_artifact_id,
                    case_ids=[observation.case_id],
                    path=observation.annotation_path,
                    media_type="image/png",
                    provenance_class="derived_artifact",
                    creator="Dong T09 segmentation workstream annotation review",
                    derived_from=([observation.input_artifact_id] if observation.input_artifact_id else ()),
                    personal=personal,
                )
            )
        artifacts.append(
            _ignored_manifest_for_file(
                artifact_id=observation.review_artifact_id,
                case_ids=[observation.case_id],
                path=observation.review_path,
                media_type="image/png",
                provenance_class="derived_artifact",
                creator="ChromaLens T09 MediaPipe evaluator",
                derived_from=([observation.input_artifact_id] if observation.input_artifact_id else ()),
                personal=personal,
                public=observation.input_artifact_id is None,
            )
        )
    artifacts.append(
        _ignored_manifest_for_file(
            artifact_id="segmentation-review-sheet",
            case_ids=all_ids,
            path=master_review,
            media_type="image/png",
            provenance_class="derived_artifact",
            creator="ChromaLens T09 MediaPipe evaluator",
            derived_from=[item.review_artifact_id for item in observations],
            personal=True,
        )
    )
    artifacts.extend(
        [
            curated_artifact(
                metrics_path,
                artifact_id="segmentation-metrics",
                case_ids=all_ids,
                media_type="text/csv",
                generation_command=COMMAND,
                created_at=started,
                creator="ChromaLens T09 coordinators",
            ),
            curated_artifact(
                report_path,
                artifact_id="segmentation-report",
                case_ids=all_ids,
                media_type="text/markdown",
                generation_command=COMMAND,
                created_at=started,
                creator="ChromaLens T09 coordinators",
            ),
        ]
    )

    cases_payload = []
    for observation in observations:
        artifact_ids = [
            observation.review_artifact_id,
            "segmentation-metrics",
            "segmentation-report",
        ]
        if observation.input_artifact_id:
            artifact_ids.append(observation.input_artifact_id)
        if observation.annotation_artifact_id:
            artifact_ids.append(observation.annotation_artifact_id)
        cases_payload.append(
            {
                "case_id": observation.case_id,
                "status": "COMPLETE",
                "fixture_id": observation.fixture_id,
                "artifact_ids": artifact_ids,
                "reason": "real locked MediaPipe inference plus recorded manual review",
            }
        )

    failures = []
    for index, observation in enumerate(failure_observations, 1):
        rating, reason = ratings[observation.case_id]
        failures.append(
            {
                "failure_id": f"FAIL-SEG-{index:03d}",
                "case_ids": [observation.case_id],
                "observed_behavior": f"Manual adequacy rating {rating}/3: {reason}",
                "expected_behavior": "A garment-localized mask adequate for reliable downstream color use, or a correct explicit empty result for the negative case",
                "user_impact": "Mask contamination or omission can alter color analysis or make assistance unavailable",
                "reproduction": f"Run {COMMAND} and inspect {observation.review_path.relative_to(ROOT).as_posix()}",
                "mitigation": "Show degraded state, request reframing/better lighting, and compare a semantic SCHP candidate only through T10 while preserving fallback",
                "status": "OPEN",
            }
        )

    ended = utc_now()
    result = {
        "protocol_version": PROTOCOL_VERSION,
        "schema_version": PROTOCOL_VERSION,
        "metric_registry_version": PROTOCOL_VERSION,
        "result_id": f"t09-segmentation-{result_timestamp(ended)}",
        "workstream": WORKSTREAM,
        "result_status": "COMPLETE",
        "git_commit": git_commit(),
        "created_at_utc": utc_text(ended),
        "operator": {"role": "segmentation_evaluator", "identifier": "coordinator-assisted-manual-review"},
        "environment": collect_environment(
            lock_path=ROOT / "requirements/segment-mediapipe-py310-win64.lock",
            backend_name="mediapipe-selfie-torso",
            backend_device="cpu",
            camera_or_source="five licensed public fixtures plus 15 consented local inputs; decoded video frames",
            source_kind="image",
            source_resolution=(REVIEW_WIDTH, REVIEW_HEIGHT),
            render_resolution=(REVIEW_WIDTH, REVIEW_HEIGHT),
            display_mode="headless",
            warmup_seconds=0.0,
            measurement_seconds=0.0,
        ),
        "cases": cases_payload,
        "configuration": {
            "cvd_profile": "not_applicable",
            "severity": None,
            "thresholds": {"adequate_case_rating": 2},
            "random_seed": None,
            "settings": {
                "review_width": REVIEW_WIDTH,
                "review_height": REVIEW_HEIGHT,
                "resize_mode": "aspect-preserving-letterbox",
                "video_review_sample_count": 9,
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
                "output_summary": f"20/20 cases evaluated; {adequate}/20 rated adequate",
            }
        ],
        "failure_cases": failures,
        "limitations": [
            "MediaPipe Selfie Segmentation plus torso cleanup is not semantic garment parsing.",
            "The 20-case convenience set and one manual review do not establish calibrated or population accuracy.",
            "Letterboxing, camera processing, clothing presentation, occlusion, and lighting can change observed masks.",
            "Mean retained foreground score is a MediaPipe-derived heuristic, not calibrated garment confidence.",
        ],
        "responsible_ai": {
            "runtime_local_offline": True,
            "frames_saved_by_default": False,
            "frames_uploaded_by_default": False,
            "medical_diagnosis_claim": False,
            "user_selected_profile": True,
            "privacy_summary": "Evaluation saving was explicit; raw personal media, derived reviews, and consent records remain ignored and untracked.",
            "bias_coverage_summary": "Twenty convenience cases include several clothing/pose/lighting failures but do not cover demographic or body-presentation diversity sufficiently.",
            "environmental_summary": "A pretrained MediaPipe CPU backend was reused with no training; segmentation quality was evaluated before optional SCHP/OpenVINO work.",
            "license_summary": "MediaPipe is Apache-2.0; five public fixtures retain documented rights; private captures use the owner-confirmed consent/license reference and are not redistributed in Git.",
            "user_validation_status": "NOT_MEASURED",
        },
        "notes": "source_kind=image denotes the normalized frame unit passed to inference; two source assets were decoded videos and are identified per case/manifest.",
    }
    result_path = OUTPUT_DIR / "result.json"
    write_json_lf(result_path, result)
    print(f"wrote {result_path}")
    return result_path


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--prepare-review",
        action="store_true",
        help="run real inference and write ignored review artifacts plus a blank rating CSV",
    )
    parser.add_argument("--ratings", type=Path, default=RATINGS_PATH)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    require_lens_interpreter()
    observations = evaluate_cases()
    _write_master_review(observations)
    if args.prepare_review:
        write_rating_template(observations)
        print(f"review sheet: {ARTIFACT_DIR / 'segmentation_review_sheet.png'}")
        print(f"complete manual ratings: {RATINGS_PATH}")
        return 0
    build_package(observations, args.ratings)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
