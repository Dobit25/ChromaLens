"""Generate deterministic T04 evaluation tables and cluster visual evidence."""

from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path

import cv2
import numpy as np

from chromalens.color_extraction import (
    ColorExtractionMode,
    DominantColorExtractor,
)
from chromalens.color_naming import (
    BASIC_COLOR_NAMES,
    name_cielab_color,
    rgb_color_to_cielab,
)
from chromalens.contracts import FramePacket, GarmentRegion

CONTROLLED_SET = Path("tests/samples/t04/basic11_controlled.csv")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("artifacts/t04-color"),
        help="ignored output directory (default: artifacts/t04-color)",
    )
    args = parser.parse_args()
    args.output_dir.mkdir(parents=True, exist_ok=True)

    evaluation_rows = _evaluate_controlled_set(CONTROLLED_SET)
    table_path = args.output_dir / "basic11_evaluation.csv"
    _write_evaluation_table(table_path, evaluation_rows)
    _write_image(
        args.output_dir / "basic11_swatch_grid.png",
        _render_swatch_grid(evaluation_rows),
    )

    cluster_evidence, cluster_overlay = _extract_synthetic_clusters()
    _write_image(args.output_dir / "synthetic_cluster_overlay.png", cluster_overlay)

    correct_count = sum(row["correct"] == "true" for row in evaluation_rows)
    summary = {
        "method": "float CIELAB nearest W3C sRGB family anchors",
        "controlled_set": str(CONTROLLED_SET),
        "family_order": BASIC_COLOR_NAMES,
        "correct": correct_count,
        "total": len(evaluation_rows),
        "controlled_accuracy": correct_count / len(evaluation_rows),
        "cluster_evidence": cluster_evidence,
        "limitations": (
            "Controlled contract smoke evidence only; not a physical or "
            "population-level color-name accuracy claim."
        ),
    }
    (args.output_dir / "evidence.json").write_text(
        json.dumps(summary, indent=2, sort_keys=True),
        encoding="utf-8",
    )

    print("expected,predicted,best_score,margin,nearest_distance,correct")
    for row in evaluation_rows:
        print(
            f"{row['expected_name']},{row['predicted_name']},"
            f"{row['best_score']},{row['margin']},"
            f"{row['nearest_distance']},{row['correct']}"
        )
    print(f"Controlled basic-11 result: {correct_count}/{len(evaluation_rows)}")
    print(f"Wrote T04 evidence to {args.output_dir.resolve()}")
    return 0 if correct_count == len(evaluation_rows) else 1


def _evaluate_controlled_set(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8", newline="") as handle:
        source_rows = list(csv.DictReader(handle))
    rows: list[dict[str, str]] = []
    for source in source_rows:
        rgb = (int(source["r"]), int(source["g"]), int(source["b"]))
        lab = rgb_color_to_cielab(rgb)
        result = name_cielab_color(lab)
        runner_up = sorted(
            result.name_scores,
            key=result.name_scores.get,  # type: ignore[arg-type]
            reverse=True,
        )[1]
        rows.append(
            {
                **source,
                "lab_l": f"{lab[0]:.6f}",
                "lab_a": f"{lab[1]:.6f}",
                "lab_b": f"{lab[2]:.6f}",
                "predicted_name": result.name,
                "predicted_label_vi": result.label_vi,
                "best_score": f"{result.name_scores[result.name]:.6f}",
                "runner_up": runner_up,
                "runner_up_score": f"{result.name_scores[runner_up]:.6f}",
                "margin": f"{result.margin:.6f}",
                "nearest_distance": f"{result.nearest_distance:.6f}",
                "correct": str(result.name == source["expected_name"]).lower(),
            }
        )
    return rows


def _write_evaluation_table(path: Path, rows: list[dict[str, str]]) -> None:
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def _render_swatch_grid(rows: list[dict[str, str]]) -> np.ndarray:
    cell_width, cell_height = 220, 120
    columns = 4
    row_count = (len(rows) + columns - 1) // columns
    canvas = np.full(
        (row_count * cell_height, columns * cell_width, 3),
        245,
        dtype=np.uint8,
    )
    for index, row in enumerate(rows):
        grid_y, grid_x = divmod(index, columns)
        x0, y0 = grid_x * cell_width, grid_y * cell_height
        rgb = (int(row["r"]), int(row["g"]), int(row["b"]))
        bgr = (rgb[2], rgb[1], rgb[0])
        canvas[y0 : y0 + 76, x0 : x0 + cell_width] = bgr
        text_color = (255, 255, 255) if sum(rgb) < 330 else (20, 20, 20)
        cv2.putText(
            canvas,
            f"expected: {row['expected_name']}",
            (x0 + 7, y0 + 24),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.52,
            text_color,
            1,
            cv2.LINE_AA,
        )
        cv2.putText(
            canvas,
            f"predicted: {row['predicted_name']}",
            (x0 + 7, y0 + 51),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.52,
            text_color,
            1,
            cv2.LINE_AA,
        )
        cv2.putText(
            canvas,
            (
                f"score {float(row['best_score']):.3f} | "
                f"margin {float(row['margin']):.3f}"
            ),
            (x0 + 7, y0 + 100),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.42,
            (20, 20, 20),
            1,
            cv2.LINE_AA,
        )
        cv2.rectangle(
            canvas,
            (x0, y0),
            (x0 + cell_width - 1, y0 + cell_height - 1),
            (60, 60, 60),
            1,
        )
    return canvas


def _extract_synthetic_clusters() -> tuple[dict[str, object], np.ndarray]:
    corrected_rgb = np.full((240, 320, 3), (70, 110, 70), dtype=np.uint8)
    garment_mask = np.zeros((240, 320), dtype=np.bool_)
    garment_mask[35:215, 60:260] = True
    corrected_rgb[garment_mask] = (210, 40, 40)
    corrected_rgb[35:215, 180:260] = (30, 80, 220)
    original_bgr = cv2.cvtColor(corrected_rgb, cv2.COLOR_RGB2BGR)
    packet = FramePacket(
        frame_id=0,
        timestamp_ns=1,
        original_bgr=original_bgr,
        corrected_rgb=corrected_rgb,
    )
    region = GarmentRegion(
        track_id=1,
        class_name="upper-clothes",
        mask=garment_mask,
        mask_confidence=0.9,
    )
    clusters = DominantColorExtractor().extract(
        packet,
        region,
        mode=ColorExtractionMode.KMEANS_2,
    )
    overlay = original_bgr.copy()
    palette = ((255, 255, 255), (0, 255, 255))
    cluster_rows: list[dict[str, object]] = []
    for index, cluster in enumerate(clusters):
        if np.any(cluster.submask & ~garment_mask):
            raise RuntimeError("cluster submask escaped the synthetic garment mask")
        contours, _ = cv2.findContours(
            cluster.submask.astype(np.uint8),
            cv2.RETR_EXTERNAL,
            cv2.CHAIN_APPROX_SIMPLE,
        )
        cv2.drawContours(overlay, contours, -1, palette[index], 2)
        cluster_rows.append(
            {
                "name": cluster.original_name,
                "rgb": cluster.rgb,
                "lab": cluster.lab,
                "ratio": cluster.ratio,
                "margin": cluster.color_margin,
                "pixel_count": int(np.count_nonzero(cluster.submask)),
                "outside_garment_pixels": int(
                    np.count_nonzero(cluster.submask & ~garment_mask)
                ),
            }
        )
    cv2.putText(
        overlay,
        "K=2 clusters retained inside mask",
        (8, 24),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.55,
        (255, 255, 255),
        1,
        cv2.LINE_AA,
    )
    return {"clusters": cluster_rows}, overlay


def _write_image(path: Path, image: np.ndarray) -> None:
    if not cv2.imwrite(str(path), image):
        raise RuntimeError(f"OpenCV could not write evidence image: {path}")


if __name__ == "__main__":
    raise SystemExit(main())
