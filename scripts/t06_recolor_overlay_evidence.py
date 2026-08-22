"""Generate deterministic offline T06 recolor/overlay evidence under artifacts/."""

from __future__ import annotations

import argparse
from dataclasses import asdict
import json
from pathlib import Path

import cv2
import numpy as np

from chromalens.color_extraction import ColorExtractionMode, DominantColorExtractor
from chromalens.config import CVDProfile
from chromalens.contracts import (
    FramePacket,
    GarmentRegion,
    LightingQuality,
    LightingQualityLevel,
)
from chromalens.cvd_simulation import MachadoSimulator
from chromalens.recolor import SelectiveRecolorer
from chromalens.renderer import (
    AssistiveOverlayData,
    OverlayView,
    build_assistive_overlay_lines,
    render_assistive_overlay,
    render_cvd_simulation_debug_overlay,
)
from chromalens.risk_detection import RelationalRiskDetector


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("artifacts/t06-recolor-overlay"),
    )
    args = parser.parse_args()
    args.output_dir.mkdir(parents=True, exist_ok=True)

    source_bgr, corrected_rgb, garment_mask = _build_scene()
    source_snapshot = source_bgr.copy()
    packet = FramePacket(
        frame_id=60,
        timestamp_ns=600,
        original_bgr=source_bgr,
        corrected_rgb=corrected_rgb,
        lighting_quality=LightingQuality(
            level=LightingQualityLevel.GOOD,
            dark_fraction=0.01,
            clipped_fraction=0.0,
            gain_extremity=0.05,
            temporal_gain_variation=0.01,
        ),
    )
    region = GarmentRegion(
        track_id=6,
        class_name="upper-clothes",
        mask=garment_mask,
        mask_confidence=0.93,
    )
    clusters = DominantColorExtractor().extract(
        packet,
        region,
        mode=ColorExtractionMode.KMEANS_2,
    )
    source_cluster = next(cluster for cluster in clusters if cluster.original_name == "red")
    comparison_cluster = next(cluster for cluster in clusters if cluster is not source_cluster)
    profile = CVDProfile.DEUTAN
    severity = 1.0
    risk = RelationalRiskDetector().assess_pair(
        source_cluster.rgb,
        comparison_cluster.rgb,
        source_id="track-6:red",
        comparison_id="track-6:comparison",
        profile=profile,
        severity=severity,
    )
    risk_mask = source_cluster.submask.copy()
    recolorer = SelectiveRecolorer()
    short_run = [
        recolorer.recolor(
            packet.original_bgr,
            garment_mask=region.mask,
            cluster=source_cluster,
            risk_mask=risk_mask,
            comparison_rgb=comparison_cluster.rgb,
            risk=risk,
            profile=profile,
            severity=severity,
            state_key="evidence:track-6:red",
        )
        for _ in range(20)
    ]
    result = short_run[-1]
    hard_intersection = region.mask & source_cluster.submask & risk_mask
    changed = np.any(result.assistive_bgr != packet.original_bgr, axis=2)
    outside_changed_count = int(np.count_nonzero(changed & ~result.recolor_mask))
    inside_changed_count = int(np.count_nonzero(changed & result.recolor_mask))
    if outside_changed_count != 0:
        raise RuntimeError("T06 containment failed: a pixel changed outside recolor_mask")
    if inside_changed_count == 0 or not result.debug.applied:
        raise RuntimeError("T06 evidence did not apply an eligible assistive transform")
    if not np.array_equal(result.recolor_mask, hard_intersection):
        raise RuntimeError("T06 recolor mask is not the exact declared intersection")
    if not np.array_equal(packet.original_bgr, source_snapshot):
        raise RuntimeError("T06 mutated the original source frame")

    overlay_data = _overlay_data(
        packet,
        result,
        source_cluster.color_margin,
        risk,
        profile,
        severity,
        view=OverlayView.ASSISTIVE,
    )
    assistive_overlay = render_assistive_overlay(
        result.assistive_bgr,
        garment_mask,
        overlay_data,
    )
    simulator = MachadoSimulator()
    source_rgb = cv2.cvtColor(source_bgr, cv2.COLOR_BGR2RGB)
    simulation_rgb = simulator.simulate_rgb(
        source_rgb,
        profile=profile,
        severity=severity,
    )
    simulation_bgr = cv2.cvtColor(simulation_rgb, cv2.COLOR_RGB2BGR)
    simulation_data = _overlay_data(
        packet,
        result,
        source_cluster.color_margin,
        risk,
        profile,
        severity,
        view=OverlayView.CVD_SIMULATION_DEBUG,
    )
    simulation_overlay = render_cvd_simulation_debug_overlay(
        simulation_bgr,
        garment_mask,
        simulation_data,
    )
    assistive_lines = build_assistive_overlay_lines(overlay_data)
    simulation_lines = build_assistive_overlay_lines(simulation_data)
    simulation_is_debug_only = (
        simulation_lines[0] == "VIEW: CVD SIMULATION (DEBUG ONLY)"
        and simulation_lines[0] != assistive_lines[0]
    )
    if not simulation_is_debug_only:
        raise RuntimeError("simulation evidence is not explicitly debug-only")

    source_lab = cv2.cvtColor(source_bgr.astype(np.float32) / 255.0, cv2.COLOR_BGR2LAB)
    result_lab = cv2.cvtColor(
        result.assistive_bgr.astype(np.float32) / 255.0,
        cv2.COLOR_BGR2LAB,
    )
    full_alpha = result.alpha_mask == 1.0
    maximum_full_alpha_lightness_delta = float(
        np.max(np.abs(result_lab[..., 0][full_alpha] - source_lab[..., 0][full_alpha]))
    )
    static_display_colors = {
        item.debug.assistive_display_rgb for item in short_run
    }
    static_switch_count = int(sum(item.debug.switched for item in short_run))
    if len(static_display_colors) != 1 or static_switch_count != 0:
        raise RuntimeError("static evidence switched assistive display color")

    light_dark_tag, tag_core_identical = _light_dark_tag_evidence(
        overlay_data,
        garment_mask.shape,
    )
    if not tag_core_identical:
        raise RuntimeError("opaque tag core differs between light and dark backgrounds")

    _write_image(args.output_dir / "original_camera_bgr.png", source_bgr)
    _write_image(
        args.output_dir / "assistive_before_overlay.png",
        result.assistive_bgr,
    )
    _write_image(args.output_dir / "assistive_overlay.png", assistive_overlay)
    _write_image(
        args.output_dir / "cvd_simulation_debug_only.png",
        simulation_overlay,
    )
    _write_image(
        args.output_dir / "mask_and_feather_debug.png",
        _mask_debug(garment_mask, source_cluster.submask, risk_mask, result.alpha_mask),
    )
    _write_image(args.output_dir / "tag_light_dark.png", light_dark_tag)

    debug_dict = asdict(result.debug)
    debug_dict["profile"] = result.debug.profile.value
    evidence = {
        "algorithm_backend": recolorer.backend_name,
        "simulation_backend": simulator.backend_name,
        "recolor_config": asdict(recolorer.config),
        "debug_data": debug_dict,
        "risk": asdict(risk),
        "hard_mask_pixel_count": int(np.count_nonzero(result.recolor_mask)),
        "hard_mask_is_exact_three_way_intersection": True,
        "inside_changed_pixel_count": inside_changed_count,
        "outside_changed_pixel_count_before_overlays": outside_changed_count,
        "alpha_outside_hard_mask_maximum": float(
            np.max(result.alpha_mask[~result.recolor_mask])
        ),
        "maximum_full_alpha_lightness_delta_lstar": maximum_full_alpha_lightness_delta,
        "static_frame_count": len(short_run),
        "static_unique_assistive_display_color_count": len(static_display_colors),
        "static_display_switch_count": static_switch_count,
        "assistive_view_label": assistive_lines[0],
        "simulation_view_label": simulation_lines[0],
        "simulation_is_debug_only": simulation_is_debug_only,
        "light_dark_opaque_tag_core_identical": tag_core_identical,
        "source_frame_unchanged": True,
        "limitations": [
            "Candidate scoring and risk thresholds are uncalibrated heuristics for T09 validation.",
            "Lightness is preserved before unavoidable sRGB gamut clipping and quantization.",
            "The selected CVD profile/severity is an assistive setting, not a diagnosis.",
            "This is deterministic offline evidence, not demo-hardware performance evidence.",
        ],
    }
    (args.output_dir / "evidence.json").write_text(
        json.dumps(evidence, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    print(
        json.dumps(
            {
                "outside_changed_pixel_count_before_overlays": outside_changed_count,
                "inside_changed_pixel_count": inside_changed_count,
                "original_corrected_rgb": result.debug.original_corrected_rgb,
                "assistive_display_rgb": result.debug.assistive_display_rgb,
                "static_display_switch_count": static_switch_count,
                "simulation_view_label": simulation_lines[0],
            },
            indent=2,
        )
    )
    print(f"Wrote T06 evidence to {args.output_dir}")
    return 0


def _build_scene() -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    height, width = 360, 640
    source_rgb = np.full((height, width, 3), (205, 205, 205), dtype=np.uint8)
    source_rgb[:, width // 2 :] = (45, 45, 45)
    garment_mask = np.zeros((height, width), dtype=np.bool_)
    garment_mask[75:330, 145:495] = True
    columns = np.indices((height, width))[1]
    source_rgb[garment_mask & (columns < 320)] = (220, 40, 40)
    source_rgb[garment_mask & (columns >= 320)] = (120, 120, 30)
    # Thin neutral lines provide deterministic texture/shading detail.
    for row in range(90, 325, 20):
        source_rgb[row : row + 2, 155:485] = np.clip(
            source_rgb[row : row + 2, 155:485].astype(np.int16) - 18,
            0,
            255,
        ).astype(np.uint8)
    return cv2.cvtColor(source_rgb, cv2.COLOR_RGB2BGR), source_rgb, garment_mask


def _overlay_data(
    packet: FramePacket,
    result,
    color_margin: float | None,
    risk,
    profile: CVDProfile,
    severity: float,
    *,
    view: OverlayView,
) -> AssistiveOverlayData:
    return AssistiveOverlayData(
        frame_id=packet.frame_id,
        original_color_name=result.debug.original_color_name,
        original_corrected_rgb=result.debug.original_corrected_rgb,
        assistive_display_rgb=result.debug.assistive_display_rgb,
        color_margin=color_margin,
        risk=risk,
        lighting_quality=packet.lighting_quality,
        profile=profile,
        severity=severity,
        backend_name="fixture-mask/cpu + chromalens-cielch-candidate-v1",
        recolor_applied=result.debug.applied,
        view=view,
    )


def _mask_debug(
    garment_mask: np.ndarray,
    cluster_mask: np.ndarray,
    risk_mask: np.ndarray,
    alpha_mask: np.ndarray,
) -> np.ndarray:
    panels = []
    for label, image in (
        ("garment", garment_mask.astype(np.uint8) * 255),
        ("cluster", cluster_mask.astype(np.uint8) * 255),
        ("risk", risk_mask.astype(np.uint8) * 255),
        ("inward alpha", np.rint(alpha_mask * 255.0).astype(np.uint8)),
    ):
        panel = cv2.cvtColor(image, cv2.COLOR_GRAY2BGR)
        cv2.rectangle(panel, (0, 0), (panel.shape[1] - 1, 34), (0, 0, 0), -1)
        cv2.putText(
            panel,
            label,
            (8, 24),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.6,
            (255, 255, 255),
            1,
            cv2.LINE_AA,
        )
        panels.append(panel)
    return np.concatenate(panels, axis=1)


def _light_dark_tag_evidence(
    data: AssistiveOverlayData,
    shape: tuple[int, int],
) -> tuple[np.ndarray, bool]:
    height, width = shape
    light = np.full((height, width, 3), 245, dtype=np.uint8)
    dark = np.full((height, width, 3), 10, dtype=np.uint8)
    mask = np.zeros((height, width), dtype=np.bool_)
    mask[220:330, 260:500] = True
    light_result = render_assistive_overlay(light, mask, data)
    dark_result = render_assistive_overlay(dark, mask, data)
    core_identical = bool(
        np.array_equal(
            light_result[12:156, 12:450],
            dark_result[12:156, 12:450],
        )
    )
    cv2.putText(
        light_result,
        "LIGHT BACKGROUND",
        (390, 345),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.55,
        (0, 0, 0),
        1,
        cv2.LINE_AA,
    )
    cv2.putText(
        dark_result,
        "DARK BACKGROUND",
        (390, 345),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.55,
        (255, 255, 255),
        1,
        cv2.LINE_AA,
    )
    return np.concatenate((light_result, dark_result), axis=1), core_identical


def _write_image(path: Path, image: np.ndarray) -> None:
    if not cv2.imwrite(str(path), image):
        raise RuntimeError(f"failed to write evidence image: {path}")


if __name__ == "__main__":
    raise SystemExit(main())
