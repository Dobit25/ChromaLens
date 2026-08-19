"""T02 demo: webcam + MediaPipe garment segmentation overlay.

Mo webcam, chay MediaPipeSegmenter moi frame,
ve debug overlay, hien len cua so.

Cach chay:
    python demo_t02_webcam.py
    python demo_t02_webcam.py --camera-index 1
    python demo_t02_webcam.py --save-snapshot

Phim:
    q / ESC  -> thoat
    s        -> luu anh snapshot vao thu muc hien tai
"""

from __future__ import annotations

import argparse
import os
import time
from pathlib import Path

import cv2
import numpy as np

from chromalens.contracts import FramePacket
from chromalens.segmentation.debug import draw_mask_overlay
from chromalens.segmentation.mediapipe_backend import (
    MediaPipeSegmenter,
    MediaPipeSegmenterConfig,
)
from chromalens.segmentation.schp_backend import SCHPSegmenter


def main() -> None:
    parser = argparse.ArgumentParser(description="ChromaLens T02 webcam demo")
    parser.add_argument("--camera-index", type=int, default=0)
    parser.add_argument(
        "--save-snapshot",
        action="store_true",
        help="Lưu frame và mask thành ảnh snapshot_XXXXX.png. Thoát khi đủ max-snapshots.",
    )
    parser.add_argument(
        "--backend",
        type=str,
        default="mediapipe",
        choices=["mediapipe", "schp-atr"],
        help="Backend segmentation sử dụng (mặc định: mediapipe)",
    )
    args = parser.parse_args()

    if args.backend == "schp-atr":
        seg = SCHPSegmenter()
    else:
        config = MediaPipeSegmenterConfig(
            model_selection=1,        # full-body model
            confidence_threshold=0.5,
            upper_body_ratio=0.75,
            min_area_ratio=0.005,
            morph_kernel_size=5,
        )
        seg = MediaPipeSegmenter(config)

    import threading

    class LatestFrameReader:
        def __init__(self, src=0):
            # Using DSHOW backend on Windows reduces internal buffering
            self.cap = cv2.VideoCapture(src, cv2.CAP_DSHOW) if os.name == 'nt' else cv2.VideoCapture(src)
            self.cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
            self.ret, self.frame = self.cap.read()
            self.lock = threading.Lock()
            self.running = True
            if self.cap.isOpened():
                self.thread = threading.Thread(target=self.update, args=())
                self.thread.daemon = True
                self.thread.start()

        def update(self):
            while self.running:
                if self.cap.isOpened():
                    ret, frame = self.cap.read()
                    if ret:
                        with self.lock:
                            self.ret = ret
                            self.frame = frame

        def read(self):
            with self.lock:
                if self.frame is not None:
                    return self.ret, self.frame.copy()
                return self.ret, None

        def isOpened(self):
            return self.cap.isOpened()
            
        def get(self, prop):
            return self.cap.get(prop)

        def release(self):
            self.running = False
            if hasattr(self, 'thread'):
                self.thread.join(timeout=1.0)
            self.cap.release()

    print(f"[ChromaLens T02] Mo camera index={args.camera_index} ...")
    cap = LatestFrameReader(args.camera_index)
    if not cap.isOpened():
        print("ERROR: Khong mo duoc camera! Thu --camera-index 1")
        return

    w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    print(f"[ChromaLens T02] Camera OK -- {w}x{h}")
    print("[ChromaLens T02] Nhan 'q' hoac ESC de thoat | 's' de luu anh")

    snapshot_count = 0
    max_snapshots = 5 if args.save_snapshot else 0
    frame_id = 0

    with seg:
        print(f"[ChromaLens T02] Backend: {seg.backend_name} | Device: {seg.device_info}")

        # FPS tracking
        fps_time = time.monotonic()
        fps_display = 0.0
        frame_counter = 0

        while True:
            ret, bgr = cap.read()
            if not ret:
                print("ERROR: Khong doc duoc frame tu camera")
                break

            frame_id += 1
            frame_counter += 1

            # Tạo FramePacket (contract T02)
            packet = FramePacket(
                frame_id=frame_id,
                timestamp_ns=time.monotonic_ns(),
                original_bgr=bgr,
            )

            # ─── Chạy segmentation ───
            regions = seg.segment(packet)

            # ─── Vẽ overlay ───
            overlay = draw_mask_overlay(
                bgr,
                regions,
                alpha=0.45,
                backend_info=f"{seg.device_info} | FPS:{fps_display:.1f}",
            )

            # ─── Thêm thông tin mask ───
            if regions:
                r = regions[0]
                pixel_count = int(r.mask.sum())
                total_pixels = h * w
                coverage = 100.0 * pixel_count / total_pixels
                conf_str = f"{r.mask_confidence:.2f}" if r.mask_confidence else "n/a"

                info_lines = [
                    f"class: {r.class_name}",
                    f"coverage: {coverage:.1f}%",
                    f"confidence: {conf_str}",
                    f"pixels: {pixel_count:,}",
                ]
                _draw_bottom_panel(overlay, info_lines)
            else:
                _draw_bottom_panel(overlay, ["no garment detected"])

            # ─── Tính FPS ───
            now = time.monotonic()
            elapsed = now - fps_time
            if elapsed >= 1.0:
                fps_display = frame_counter / elapsed
                fps_time = now
                frame_counter = 0

            # ─── Hiển thị ───
            cv2.imshow("ChromaLens T02 - Garment Segmentation", overlay)

            # ─── Tự động lưu snapshot ───
            if args.save_snapshot and snapshot_count < max_snapshots:
                fname = f"snapshot_{snapshot_count+1:02d}.png"
                cv2.imwrite(fname, overlay)
                print(f"[SAVED] {fname}")
                snapshot_count += 1
                if snapshot_count >= max_snapshots:
                    print(f"[DONE] Da luu du {max_snapshots} snapshot. Thoat.")
                    break

            # ─── Phím bấm ───
            key = cv2.waitKey(1) & 0xFF
            if key in (27, ord("q")):
                print("[EXIT]")
                break
            elif key == ord("s"):
                fname = f"snapshot_{frame_id:05d}.png"
                cv2.imwrite(fname, overlay)
                print(f"[SAVED] {Path(fname).resolve()}")

    cap.release()
    cv2.destroyAllWindows()


def _draw_bottom_panel(canvas: np.ndarray, lines: list[str]) -> None:
    """Vẽ panel thông tin ở góc dưới trái."""
    font = cv2.FONT_HERSHEY_SIMPLEX
    scale = 0.52
    thickness = 1
    pad = 6
    line_h = 20
    h, w = canvas.shape[:2]

    max_w = max(
        cv2.getTextSize(line, font, scale, thickness)[0][0] for line in lines
    )
    panel_h = line_h * len(lines) + pad * 2
    y0 = h - panel_h - 8

    # Nền tối
    panel = canvas[y0: y0 + panel_h, 8: 8 + max_w + pad * 2]
    if panel.size > 0:
        dark = np.zeros_like(panel)
        cv2.addWeighted(dark, 0.6, panel, 0.4, 0, panel)
        canvas[y0: y0 + panel_h, 8: 8 + max_w + pad * 2] = panel

    for i, line in enumerate(lines):
        y = y0 + pad + (i + 1) * line_h - 4
        cv2.putText(canvas, line, (9 + 1, y + 1), font, scale, (0, 0, 0), thickness + 1)
        cv2.putText(canvas, line, (9, y), font, scale, (0, 255, 180), thickness)


if __name__ == "__main__":
    main()
