"""Generate deterministic, hardware-independent T07 matching evidence."""

from __future__ import annotations

import csv
import json
from dataclasses import asdict
from pathlib import Path

import cv2
import numpy as np

from chromalens.color_naming import rgb_color_to_cielab
from chromalens.config import CVDProfile
from chromalens.contracts import ColorCluster
from chromalens.matching import HarmonyType, MatchingStatus, RuleBasedMatcher

OUTPUT_DIR = Path("artifacts/t07-matching")


def _cluster(rgb: tuple[int, int, int], name: str) -> ColorCluster:
    return ColorCluster(
        lab=rgb_color_to_cielab(rgb),
        rgb=rgb,
        ratio=1.0,
        submask=np.ones((8, 8), dtype=np.bool_),
        original_name=name,
        name_scores={name: 1.0},
        color_margin=1.0,
    )


def _draw_swatch_grid(results: list[tuple[str, object]]) -> np.ndarray:
    swatch_width = 150
    row_height = 105
    max_suggestions = 5
    canvas = np.full(
        (row_height * len(results), swatch_width * max_suggestions, 3),
        235,
        dtype=np.uint8,
    )
    for row_index, (label, result) in enumerate(results):
        source_rgb = result.source_original_rgb
        colors = [("SOURCE", source_rgb)] + [
            (item.harmony.value.upper(), item.target_rgb)
            for item in result.suggestions
        ]
        for column_index, (item_label, rgb) in enumerate(colors):
            x0 = column_index * swatch_width
            y0 = row_index * row_height
            if rgb is not None:
                bgr = (int(rgb[2]), int(rgb[1]), int(rgb[0]))
                canvas[y0 : y0 + 72, x0 : x0 + swatch_width] = bgr
            cv2.rectangle(
                canvas,
                (x0, y0),
                (x0 + swatch_width - 1, y0 + 72),
                (0, 0, 0),
                1,
            )
            cv2.putText(
                canvas,
                f"{label} {item_label}",
                (x0 + 5, y0 + 92),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.35,
                (0, 0, 0),
                1,
                cv2.LINE_AA,
            )
    return canvas


def main() -> None:
    matcher = RuleBasedMatcher()
    neutral = matcher.suggest_from_original_cluster(_cluster((128, 128, 128), "grey"))
    red = matcher.suggest_from_original_cluster(
        _cluster((218, 38, 38), "red"),
        profile=CVDProfile.DEUTAN,
        severity=1.0,
    )
    blue = matcher.suggest_from_original_cluster(
        _cluster((35, 80, 210), "blue"),
        profile=CVDProfile.TRITAN,
        severity=1.0,
    )
    missing = matcher.suggest_from_original_cluster(None)
    unknown = matcher.suggest_from_original_cluster(
        _cluster((12, 34, 56), "ultraviolet")
    )

    expected_chromatic = {
        HarmonyType.NEUTRAL,
        HarmonyType.ANALOGOUS,
        HarmonyType.COMPLEMENTARY,
        HarmonyType.TONE,
    }
    if neutral.status is not MatchingStatus.READY or len(neutral.suggestions) != 1:
        raise RuntimeError("neutral evidence did not produce exactly one safe rule")
    for result in (red, blue):
        if result.status is not MatchingStatus.READY:
            raise RuntimeError("chromatic evidence did not produce a ready result")
        if {item.harmony for item in result.suggestions} != expected_chromatic:
            raise RuntimeError("chromatic relationship coverage is incomplete")
        if any(
            item.source_original_lab != result.source_original_lab
            or item.source_original_rgb != result.source_original_rgb
            for item in result.suggestions
        ):
            raise RuntimeError("a suggestion lost the original-color contract")
    if missing.suggestions or unknown.suggestions:
        raise RuntimeError("missing/unknown evidence fabricated a suggestion")

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    records = []
    for source_label, result in (("grey", neutral), ("red", red), ("blue", blue)):
        for suggestion in result.suggestions:
            check = suggestion.cvd_separation
            records.append(
                {
                    "source": source_label,
                    "source_original_rgb": result.source_original_rgb,
                    "rule_id": suggestion.rule_id,
                    "harmony": suggestion.harmony.value,
                    "priority_not_confidence": suggestion.priority,
                    "target_name": suggestion.target_name,
                    "target_rgb": suggestion.target_rgb,
                    "cvd_delta_e": None if check is None else check.delta_e_cvd,
                    "cvd_meets_heuristic": None if check is None else check.meets_minimum,
                    "explanation_vi": suggestion.explanation_vi,
                    "provenance": suggestion.rule_provenance,
                }
            )
    with (OUTPUT_DIR / "suggestions.csv").open(
        "w", encoding="utf-8", newline=""
    ) as handle:
        writer = csv.DictWriter(handle, fieldnames=records[0].keys())
        writer.writeheader()
        writer.writerows(records)

    payload = {
        "evidence_scope": (
            "controlled deterministic contract evidence; not fashion-taste, "
            "clinical, accessibility, or user-validation evidence"
        ),
        "rule_count": len(matcher.rules),
        "neutral": asdict(neutral),
        "red": asdict(red),
        "blue": asdict(blue),
        "missing": asdict(missing),
        "unknown": asdict(unknown),
    }
    (OUTPUT_DIR / "evidence.json").write_text(
        json.dumps(payload, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    swatches = _draw_swatch_grid([("GREY", neutral), ("RED", red), ("BLUE", blue)])
    if not cv2.imwrite(str(OUTPUT_DIR / "suggestion_swatches.png"), swatches):
        raise RuntimeError("failed to write T07 swatch evidence")
    print(f"T07 evidence written to {OUTPUT_DIR}")
    print(f"rules={len(matcher.rules)} suggestions={len(records)}")


if __name__ == "__main__":
    main()
