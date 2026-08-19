# ChromaLens AI — Model Weights

This directory holds AI model weights used by ChromaLens inference backends.
Weights are **not committed to the repository** (see `.gitignore`).
Each backend documents its source, license, and setup steps below.

---

## MediaPipe Selfie Segmentation (T02 P0 baseline)

| Field | Value |
|---|---|
| Backend | `mediapipe` (`MediaPipeSegmenter`) |
| Model | SelfieSegmentation `model_selection=1` (landscape / full-body) |
| Source | Bundled with the `mediapipe` Python package |
| License | Apache-2.0 — https://github.com/google/mediapipe/blob/master/LICENSE |
| Download | **Automatic** — no manual step required |
| Expected path | None; loaded by MediaPipe at runtime from its package data |

### Setup

```bash
pip install "chromalens-ai[segment-mediapipe]"
# mediapipe==0.10.21 — last version supporting Python 3.10 on Windows
```

### Notes

- The model weights are embedded inside the `mediapipe` wheel.
- No checkpoint file is written to this directory.
- Attribution: MediaPipe Authors, Google LLC (Apache-2.0).

---

## SCHP-ATR — Self-Correction for Human Parsing (T02 P1 / T10)

| Field | Value |
|---|---|
| Backend | `schp-atr` (`SCHPSegmenter`) |
| Model | SCHP trained on ATR dataset (~18 garment/body classes) |
| Source | https://github.com/GoGoDuck912/Self-Correction-Human-Parsing |
| License | MIT — see upstream repository |
| Reported accuracy | mIoU ≈ 82.29% on ATR test set (author benchmark, not validated here) |
| Expected path | `models/schp_atr.pth` |
| File size | ~195 MB |
| Status | **NOT DOWNLOADED** — placeholder only until T02 SCHP gate |

### Download steps (when approved by integration owner)

```bash
# 1. Confirm with Tung (integration owner) before downloading.
# 2. Download the ATR pretrained checkpoint from the upstream release page:
#    https://github.com/GoGoDuck912/Self-Correction-Human-Parsing/releases
# 3. Place the file at:
#    models/schp_atr.pth
# 4. Verify SHA-256 checksum (record here after download):
#    sha256sum models/schp_atr.pth
```

### ATR class index

| ID | Label | ID | Label |
|---|---|---|---|
| 0 | background | 9 | left-shoe |
| 1 | hat | 10 | right-shoe |
| 2 | hair | 11 | face |
| 3 | sunglasses | 12 | left-leg |
| 4 | **upper-clothes** | 13 | right-leg |
| 5 | **skirt** | 14 | left-arm |
| 6 | **pants** | 15 | right-arm |
| 7 | **dress** | 16 | bag |
| 8 | belt | 17 | scarf |

ChromaLens uses classes **4, 5, 6, 7** for garment masking.

---

## Policy

- Do **not** commit model weight files (`.pth`, `.onnx`, `.bin`, etc.).
- Do **not** commit dataset files.
- Record SHA-256 checksums here after each verified download.
- Any new model must have its license reviewed before use.
- Integration owner (Tùng) must approve new model assets before they are
  added to the project.
