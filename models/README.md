# ChromaLens AI — Model Weights

This directory holds AI model weights used by ChromaLens inference backends.
Weights are **not committed to the repository** (see `.gitignore`).
Each backend documents its source, license, and setup steps below.

---

## MediaPipe Selfie Segmentation (T02 P0 baseline)

| Field | Value |
|---|---|
| Backend | `mediapipe-selfie-torso` (`MediaPipeSegmenter`) |
| Models | Selfie Segmentation `model_selection=1` (landscape) and Face Detection `model_selection=1` (full range) |
| Source | Bundled with the `mediapipe` Python package |
| License | Apache-2.0 — https://github.com/google/mediapipe/blob/master/LICENSE |
| Download | **Automatic** — no manual step required |
| Expected path | None; loaded by MediaPipe at runtime from its package data |

### Setup

```powershell
conda run --name lens python -m pip install --require-hashes --requirement requirements/segment-mediapipe-py310-win64.lock
conda run --name lens python -m pip install --no-build-isolation --no-deps --editable ".[dev,segment-mediapipe]"
```

### Notes

- The model assets are embedded inside the locked `mediapipe==0.10.21` wheel.
- Selfie Segmentation predicts a prominent-person mask. Face exclusion and
  vertical cleanup are ChromaLens heuristics; this is not semantic garment
  parsing and `mask_confidence` is not a calibrated garment probability.
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
| Expected path | To be assigned only if T10 approves the backend |
| File size | Not verified locally |
| Status | **DEFERRED TO T10** by the T02 four-hour decision gate; no runtime or weights installed |

### T10 re-evaluation procedure (only when approved by integration owner)

1. Confirm that T08 and the T09 protocol are complete and obtain integration-
   owner approval before downloading or adding PyTorch.
2. Use the ATR checkpoint linked from the
   [official upstream README](https://github.com/GoGoDuck912/Self-Correction-Human-Parsing#simple-out-of-box-extractor).
   Upstream distributes it through Google Drive, not GitHub Releases.
3. Review and lock a Python 3.10/Windows-compatible PyTorch closure separately.
4. Record the downloaded checkpoint's exact filename, byte size, and SHA-256
   before placing it at an approved ignored path.
5. Validate preprocessing, output geometry, class mapping, and masks against
   the frozen T09 samples before implementing a selectable backend.

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
