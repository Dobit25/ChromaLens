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
| Source | https://github.com/GoGoDuck912/Self-Correction-Human-Parsing at `eb84c432cc697f494d99662a05f2335eb2f26095` |
| Source-code license | MIT — upstream `LICENSE` SHA-256 `4b6f33d1127bad303130ad839fd79541e4390c43a4c4de3e9ebbdd90978df941` |
| Checkpoint license | **Not separately stated by the official download page; unresolved for redistribution** |
| Reported accuracy | mIoU ≈ 82.29% on ATR test set (author benchmark, not validated here) |
| Expected ignored path | `models/schp/exp-schp-201908301523-atr.pth` |
| Expected file size | `267445237` bytes (verified local object and mirror metadata) |
| Expected SHA-256 | `e9d7c91ce3b4e7133df56b599fc817b533e3439c5e8d282a59126d2fda339a2a` (three independent fixed mirror records; not published by upstream) |
| Status | **T10 ACCEPTED after owner reopen** on 2026-08-24; SCHP is primary, OpenVINO is preferred, MediaPipe is explicit fallback |

### Setup after owner approval

1. Install the combined hashed collaboration closure:
   `requirements/segment-schp-py310-win64.lock`, then install the editable
   package with extras `dev,segment-mediapipe,segment-schp` and `--no-deps`.
2. Obtain the ATR checkpoint linked from the
   [official upstream README](https://github.com/GoGoDuck912/Self-Correction-Human-Parsing#simple-out-of-box-extractor).
   Upstream distributes it through Google Drive, not GitHub Releases.
3. Place it at `models/schp/exp-schp-201908301523-atr.pth`; confirm the exact
   size and SHA-256 in the table above. A mismatch fails fast and must never be
   bypassed.
4. Run `python scripts/t10_export_schp_openvino.py`. The command strict-loads
   all checkpoint keys and creates ignored `.xml`, `.bin`, and
   `.manifest.json` files under `models/schp/openvino/`.
5. Run `python -m pytest -q tests/integration/test_t10_schp_integration.py`,
   then launch the default demo. Use `--backend mediapipe-selfie-torso` only as
   the explicit fallback.

### T10 accepted gate evidence (2026-08-24)

The earlier transfer failure was resolved by resuming the frozen Git-LFS object
through its CDN. The final local file is exactly `267445237` bytes and matches
SHA-256 `e9d7...9a2a`. The hash is a transport/object integrity record from
fixed mirrors, not an upstream-published checksum and not proof of checkpoint
redistribution rights. The checkpoint and derived IR remain ignored.

The approved Windows/Python 3.10 closure pins `torch==2.5.1` and
`openvino==2025.4.1` together with the existing MediaPipe fallback. Direct
PyTorch-to-OpenVINO conversion made an intermediate ONNX package unnecessary. The
portable graph is adapted from pinned MIT upstream source and replaces only
the historical custom InPlaceABNSync extension with state-dict-compatible
PyTorch BatchNorm plus the same activation. Strict loading reports every key
matched.

The runtime preserves the upstream ATR contract: 18 classes, 512x512 input,
affine whole-frame preprocessing, BGR tensor normalization with mean
`[0.406, 0.456, 0.485]` and standard deviation
`[0.225, 0.224, 0.229]`, fusion-logit interpolation, and inverse-affine logits.
On five fixed licensed/public fixtures, FP32 OpenVINO and PyTorch per-class
garment masks have IoU at least `0.999`. The current development Intel Core
i5-13450HX full pipeline remains slow at about `0.91 FPS` in one 20-frame
640x480 headless observation; this conversion-fidelity gate is not a broad
accuracy or official demo-hardware claim.

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
