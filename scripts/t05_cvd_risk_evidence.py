"""Generate deterministic, offline T05 CVD/risk evidence under artifacts/."""

from __future__ import annotations

import argparse
import csv
import json
from dataclasses import asdict
from importlib import metadata
from pathlib import Path

import cv2
import numpy as np

from chromalens.config import CVDProfile
from chromalens.cvd_simulation import MachadoSimulator
from chromalens.risk_detection import RelationalRiskConfig, RelationalRiskDetector


PATCHES: tuple[tuple[str, tuple[int, int, int]], ...] = (
    ("red", (255, 0, 0)),
    ("green", (0, 255, 0)),
    ("blue", (0, 0, 255)),
    ("white", (255, 255, 255)),
    ("black", (0, 0, 0)),
    ("yellow", (255, 255, 0)),
)

PAIR_CASES: tuple[
    tuple[str, CVDProfile, tuple[int, int, int], tuple[int, int, int]], ...
] = (
    ("protan-purple-blue", CVDProfile.PROTAN, (130, 60, 180), (40, 90, 220)),
    ("protan-control", CVDProfile.PROTAN, (40, 150, 60), (30, 190, 190)),
    ("deutan-red-olive", CVDProfile.DEUTAN, (220, 40, 40), (120, 120, 30)),
    ("deutan-control", CVDProfile.DEUTAN, (40, 90, 220), (235, 220, 40)),
    ("tritan-orange-pink", CVDProfile.TRITAN, (230, 130, 30), (230, 120, 170)),
    ("tritan-control", CVDProfile.TRITAN, (220, 40, 40), (40, 150, 60)),
)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("artifacts/t05-cvd-risk"),
    )
    args = parser.parse_args()
    args.output_dir.mkdir(parents=True, exist_ok=True)

    simulator = MachadoSimulator()
    config = RelationalRiskConfig()
    detector = RelationalRiskDetector(config, simulator=simulator)
    patch_image = np.asarray(
        [[rgb for _, rgb in PATCHES]],
        dtype=np.uint8,
    )
    profile_rows: list[dict[str, object]] = []
    simulated_patch_rows: dict[CVDProfile, np.ndarray] = {}
    for profile in CVDProfile:
        identity = simulator.simulate_rgb(
            patch_image,
            profile=profile,
            severity=0.0,
        )
        simulated = simulator.simulate_rgb(
            patch_image,
            profile=profile,
            severity=1.0,
        )
        identity_exact = bool(np.array_equal(identity, patch_image))
        if not identity_exact:
            raise RuntimeError(f"severity-zero identity failed for {profile.value}")
        simulated_patch_rows[profile] = simulated
        profile_rows.append(
            {
                "profile": profile.value,
                "severity_zero_identity_exact": identity_exact,
                "severity_one_rgb": simulated.tolist()[0],
            }
        )

    risk_rows: list[dict[str, object]] = []
    for case_name, profile, source_rgb, comparison_rgb in PAIR_CASES:
        result = detector.assess_pair(
            source_rgb,
            comparison_rgb,
            source_id=f"{case_name}:source",
            comparison_id=f"{case_name}:comparison",
            profile=profile,
            severity=1.0,
        )
        risk_rows.append(
            {
                "case": case_name,
                "profile": profile.value,
                "severity": 1.0,
                "source_rgb": list(source_rgb),
                "comparison_rgb": list(comparison_rgb),
                "simulated_source_rgb": list(
                    simulator.simulate_color(
                        source_rgb,
                        profile=profile,
                        severity=1.0,
                    )
                ),
                "simulated_comparison_rgb": list(
                    simulator.simulate_color(
                        comparison_rgb,
                        profile=profile,
                        severity=1.0,
                    )
                ),
                **asdict(result),
            }
        )

    confusing = next(row for row in risk_rows if row["case"] == "deutan-red-olive")
    control = next(row for row in risk_rows if row["case"] == "deutan-control")
    if float(confusing["risk_score"]) <= float(control["risk_score"]):
        raise RuntimeError("declared deutan confusing pair did not outrank control")

    _write_risk_csv(args.output_dir / "pair_risk_evaluation.csv", risk_rows)
    _write_swatch_grid(
        args.output_dir / "known_patch_simulation.png",
        patch_image,
        simulated_patch_rows,
    )
    evidence = {
        "backend": simulator.backend_name,
        "daltonlens_version": metadata.version("daltonlens"),
        "rgb_contract": "uint8 sRGB RGB channel order",
        "risk_config": asdict(config),
        "profiles": profile_rows,
        "risk_cases": risk_rows,
        "declared_dod_comparison": {
            "confusing_case": confusing["case"],
            "confusing_score": confusing["risk_score"],
            "control_case": control["case"],
            "control_score": control["risk_score"],
            "confusing_greater_than_control": True,
        },
        "limitations": [
            "Risk thresholds are uncalibrated heuristics requiring T09 user validation.",
            "Selected profile/severity are assistive settings, not medical diagnosis.",
            "Machado tritan simulation has a documented model limitation.",
        ],
    }
    (args.output_dir / "evidence.json").write_text(
        json.dumps(evidence, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    print(json.dumps(evidence["declared_dod_comparison"], indent=2))
    print(f"Wrote T05 evidence to {args.output_dir}")
    return 0


def _write_risk_csv(path: Path, rows: list[dict[str, object]]) -> None:
    fieldnames = (
        "case",
        "profile",
        "severity",
        "source_rgb",
        "comparison_rgb",
        "simulated_source_rgb",
        "simulated_comparison_rgb",
        "delta_e_original",
        "delta_e_cvd",
        "risk_score",
        "risk_level",
    )
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def _write_swatch_grid(
    path: Path,
    original: np.ndarray,
    simulated_rows: dict[CVDProfile, np.ndarray],
) -> None:
    cell_width = 120
    cell_height = 86
    label_width = 110
    rows = (("original", original),) + tuple(
        (profile.value, simulated_rows[profile]) for profile in CVDProfile
    )
    canvas = np.full(
        (len(rows) * cell_height, label_width + len(PATCHES) * cell_width, 3),
        245,
        dtype=np.uint8,
    )
    for row_index, (row_label, rgb_values) in enumerate(rows):
        top = row_index * cell_height
        cv2.putText(
            canvas,
            row_label,
            (5, top + 48),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.48,
            (20, 20, 20),
            1,
            cv2.LINE_AA,
        )
        for column, (patch_name, _) in enumerate(PATCHES):
            left = label_width + column * cell_width
            rgb = rgb_values[0, column]
            canvas[top : top + 58, left : left + cell_width] = rgb[::-1]
            cv2.putText(
                canvas,
                patch_name,
                (left + 5, top + 78),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.43,
                (20, 20, 20),
                1,
                cv2.LINE_AA,
            )
    if not cv2.imwrite(str(path), canvas):
        raise RuntimeError(f"failed to write evidence image: {path}")


if __name__ == "__main__":
    raise SystemExit(main())
