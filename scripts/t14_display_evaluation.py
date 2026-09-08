"""Generate frozen T14 offscreen evidence and optionally smoke a real GUI."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
from importlib import metadata
import json
from pathlib import Path
import platform
import subprocess
import sys
from typing import Sequence

import cv2
import numpy as np

from chromalens.config import CVDProfile
from chromalens.display import OpenCVDisplayController, fit_presentation_to_display
from chromalens.presentation import (
    PresentationData,
    PresentationMode,
    PresentationTheme,
    _product_card_rectangles,
    _product_card_regions,
    compose_presentation,
    layout_for_camera,
)


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUTPUT = ROOT / "artifacts/post_mvp/t14/display-evaluation-raw.json"
CASES = (
    (
        "PM-FULLSCREEN-1366X768-PRODUCT",
        "fullscreen-1366x768-product-dark",
        (1366, 768),
        PresentationMode.PRODUCT,
        PresentationTheme.DARK,
    ),
    (
        "PM-FULLSCREEN-1366X768-DIAGNOSTIC",
        "fullscreen-1366x768-diagnostic-light",
        (1366, 768),
        PresentationMode.DIAGNOSTIC,
        PresentationTheme.LIGHT,
    ),
    (
        "PM-FULLSCREEN-1920X1080-PRODUCT",
        "fullscreen-1920x1080-product-light",
        (1920, 1080),
        PresentationMode.PRODUCT,
        PresentationTheme.LIGHT,
    ),
    (
        "PM-FULLSCREEN-1920X1080-DIAGNOSTIC",
        "fullscreen-1920x1080-diagnostic-dark",
        (1920, 1080),
        PresentationMode.DIAGNOSTIC,
        PresentationTheme.DARK,
    ),
)


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument(
        "--gui-smoke",
        action="store_true",
        help="open a synthetic local window and exercise windowed/fullscreen/windowed",
    )
    parser.add_argument(
        "--gui-hold-seconds",
        type=float,
        default=0.35,
        help="event-pump duration for each GUI state (default: 0.35)",
    )
    return parser


def _data() -> PresentationData:
    return PresentationData(
        source_name="synthetic:t14-no-personal-data",
        profile=CVDProfile.DEUTAN,
        severity=1.0,
        recolor_enabled=True,
        view_name="assistive",
        original_color_label="Xám",
        original_color_rgb=(163, 168, 173),
        color_margin=0.294,
        risk_level="medium",
        lighting_level="good",
        matching_label="Trắng",
        matching_harmony="neutral",
        action_message="Đã tăng khả năng phân biệt màu.",
        diagnostic_lines=(
            "RGB=(163, 168, 173) | margin=0.294 | risk=medium 0.250",
            "backend=synthetic/no-inference | display evidence only",
            "processing resolution=640x360 | display scaling only",
            "sensor_to_photon_ms=NOT_MEASURED",
        ),
    )


def _camera() -> np.ndarray:
    y, x = np.indices((360, 640))
    frame = np.empty((360, 640, 3), dtype=np.uint8)
    frame[..., 0] = (x * 255 // 639).astype(np.uint8)
    frame[..., 1] = (y * 255 // 359).astype(np.uint8)
    frame[..., 2] = ((x + y) % 256).astype(np.uint8)
    return frame


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _package_versions() -> dict[str, str]:
    versions: dict[str, str] = {}
    for name in ("chromalens-ai", "numpy", "opencv-contrib-python", "Pillow"):
        try:
            versions[name] = metadata.version(name)
        except metadata.PackageNotFoundError:
            versions[name] = "NOT_INSTALLED"
    return versions


def _inside(inner: tuple[int, int, int, int], outer: tuple[int, int, int, int]) -> bool:
    return (
        outer[0] <= inner[0] < inner[2] <= outer[2]
        and outer[1] <= inner[1] < inner[3] <= outer[3]
    )


def _structural_overflow_count(mode: PresentationMode) -> int:
    layout = layout_for_camera(640, 360)
    canvas = (0, 0, layout.canvas_width, layout.canvas_height)
    violations = sum(
        not _inside(rect, canvas)
        for rect in (
            layout.header_rect,
            layout.camera_rect,
            layout.panel_rect,
            layout.footer_rect,
        )
    )
    if mode is PresentationMode.PRODUCT:
        for index, card in enumerate(_product_card_rectangles(layout)):
            violations += int(not _inside(card, layout.panel_rect))
            width, height = card[2] - card[0], card[3] - card[1]
            regions = _product_card_regions(width, height, has_swatch=index == 0)
            local_card = (0, 0, width, height)
            for region in (regions.title, regions.value, regions.detail):
                violations += int(not _inside(region, local_card))
            violations += int(regions.title[3] >= regions.value[1])
            violations += int(regions.value[3] >= regions.detail[1])
    return int(violations)


def _pump_events(seconds: float) -> None:
    deadline = cv2.getTickCount() / cv2.getTickFrequency() + seconds
    while cv2.getTickCount() / cv2.getTickFrequency() < deadline:
        cv2.waitKey(20)


def _gui_smoke(frame: np.ndarray, hold_seconds: float) -> dict[str, object]:
    if hold_seconds <= 0:
        raise ValueError("gui-hold-seconds must be positive")
    controller = OpenCVDisplayController("ChromaLens T14 GUI smoke")
    try:
        controller.submit(controller.prepare(frame))
        _pump_events(hold_seconds)
        controller.set_fullscreen(True)
        controller.submit(controller.prepare(frame))
        _pump_events(hold_seconds)
        fullscreen_property = cv2.getWindowProperty(
            controller.window_title, cv2.WND_PROP_FULLSCREEN
        )
        controller.set_fullscreen(False)
        controller.submit(controller.prepare(frame))
        _pump_events(hold_seconds)
        windowed_property = cv2.getWindowProperty(
            controller.window_title, cv2.WND_PROP_FULLSCREEN
        )
        return {
            "status": "COMPLETE",
            "fullscreen_property": fullscreen_property,
            "windowed_property": windowed_property,
            "toggle_success": bool(
                fullscreen_property >= 0.5 and windowed_property < 0.5
            ),
        }
    finally:
        controller.close()


def run(argv: Sequence[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    output = args.output.resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    camera = _camera()
    camera_before = camera.copy()
    case_results: list[dict[str, object]] = []
    artifacts: list[dict[str, object]] = []
    smoke_frame: np.ndarray | None = None

    for case_id, fixture_id, target_size, mode, theme in CASES:
        presentation = compose_presentation(camera, _data(), mode=mode, theme=theme)
        presentation_before = presentation.copy()
        layout = layout_for_camera(camera.shape[1], camera.shape[0])
        fitted = fit_presentation_to_display(presentation, target_size)
        image_path = output.parent / f"{fixture_id}.png"
        if not cv2.imwrite(str(image_path), fitted.frame_bgr):
            raise RuntimeError(f"could not write {image_path}")
        aspect_error = fitted.aspect_ratio_error(layout.camera_rect)
        processing_changed = not np.array_equal(camera, camera_before)
        source_canvas_changed = not np.array_equal(presentation, presentation_before)
        overflow_count = _structural_overflow_count(mode)
        case_results.append(
            {
                "case_id": case_id,
                "fixture_id": fixture_id,
                "mode": mode.value,
                "theme": theme.value,
                "display_width": target_size[0],
                "display_height": target_size[1],
                "processing_width": camera.shape[1],
                "processing_height": camera.shape[0],
                "content_rect": fitted.content_rect,
                "camera_rect": fitted.map_rect(layout.camera_rect),
                "viewport_aspect_ratio_error": aspect_error,
                "processing_resolution_changed_flag": processing_changed,
                "source_presentation_mutated_flag": source_canvas_changed,
                "text_overflow_count": overflow_count,
                "pass": bool(
                    aspect_error <= 0.005
                    and not processing_changed
                    and not source_canvas_changed
                    and overflow_count == 0
                ),
            }
        )
        artifacts.append(
            {
                "path": image_path.relative_to(ROOT).as_posix(),
                "bytes": image_path.stat().st_size,
                "sha256": _sha256(image_path),
                "provenance": "Project-generated synthetic gradient; no personal data",
                "consent": "NOT_APPLICABLE",
                "license": "Apache-2.0",
            }
        )
        smoke_frame = fitted.frame_bgr

    gui = {"status": "NOT_RUN", "toggle_success": False}
    if args.gui_smoke:
        assert smoke_frame is not None
        gui = _gui_smoke(smoke_frame, args.gui_hold_seconds)

    lock_path = ROOT / "requirements/segment-schp-py310-win64.lock"
    commit = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=True,
    ).stdout.strip()
    payload = {
        "format": "chromalens-t14-display-evaluation-1.0",
        "created_at_utc": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "git_commit": commit,
        "git_worktree_disclosure": (
            "Raw evaluation artifacts were generated from git_commit; unrelated "
            "owner presentation files remained uncommitted."
        ),
        "host_role": "development",
        "declared_demo_hardware": False,
        "platform": platform.platform(),
        "python_version": platform.python_version(),
        "python_executable": sys.executable,
        "package_versions": _package_versions(),
        "lock_path": lock_path.relative_to(ROOT).as_posix(),
        "lock_sha256": _sha256(lock_path),
        "processing_resolution": {"width": 640, "height": 360},
        "cases": case_results,
        "gui_smoke": gui,
        "artifacts": artifacts,
        "privacy": {
            "source": "deterministic project-generated synthetic gradient",
            "personal_data": False,
            "frames_uploaded": 0,
        },
        "sensor_to_photon_ms": "NOT_MEASURED",
    }
    output.write_text(
        json.dumps(payload, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    print(f"wrote {output}")
    print(
        f"cases={len(case_results)} passed={sum(bool(item['pass']) for item in case_results)} "
        f"gui_smoke={gui['status']} toggle_success={gui['toggle_success']}"
    )
    return 0 if all(bool(item["pass"]) for item in case_results) else 1


if __name__ == "__main__":
    raise SystemExit(run())
