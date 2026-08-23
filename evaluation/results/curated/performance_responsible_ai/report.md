# T09 Performance and Responsible-AI Workstream

Status: `COMPLETE` for the T09 Definition of Done with explicit optional/unmeasured boundaries.

The four performance runs were regenerated locally after the original contributor raw artifacts became unrecoverable. Lost bytes and old hashes are not cited as active evidence. Measurements remain development-host observations, never demo-hardware acceptance.

## Latency semantics

- `source_read_to_render_ms`: OpenCV read return to renderer completion.
- `source_read_to_display_submit_ms`: the same start to return from `cv2.imshow`; GUI only.
- `sensor_to_photon_ms`: `NOT_MEASURED`; no synchronized external apparatus.

## Fresh local performance observations

| Case | FPS | Render p50/p95 ms | Display-submit p50/p95 ms | RSS start/end/peak MiB | Degraded rate | RSS growth |
| --- | ---: | ---: | ---: | ---: | ---: | --- |
| PERF-WEBCAM-GUI-120 | 19.728 | 47.000 / 78.000 | 47.000 / 78.000 | 192.270 / 159.707 / 214.508 | 1.000000 | FAIL |
| PERF-WEBCAM-HEADLESS-120 | 14.013 | 62.000 / 187.000 | NOT_MEASURED | 194.797 / 168.621 / 214.398 | 0.685493 | PASS |
| PERF-VIDEO-GUI-120 | 15.944 | 47.000 / 78.000 | 47.000 / 78.000 | 133.859 / 112.230 / 139.570 | 1.000000 | PASS |
| PERF-VIDEO-HEADLESS-120 | 24.169 | 47.000 / 63.000 | NOT_MEASURED | 130.598 / 114.293 / 139.039 | 1.000000 | PASS |

Host: LENOVO 83DV; 13th Gen Intel(R) Core(TM) i5-13450HX; 15.78 GiB RAM; backend `mediapipe-selfie-torso/cpu` on CPU.

## Manual/non-AI baseline

The unrecoverable manual ROI timing is `NOT_MEASURED`; no human action or elapsed time was simulated. The retained baseline explanation is sufficient for AI necessity: fixed RGB thresholds neither identify which pixels are garments nor handle background, illuminant, pose, and material changes. AI supplies automatic per-pixel localization; deterministic color science remains appropriate after localization.

## Artifact integrity and supersession

The active package cites only four newly generated raw benchmark JSON files, the new deterministic video, and tracked curated CSV/Markdown. Every available byte is rehashed. The seven old contributor artifacts are superseded and intentionally absent from the active manifest; their values are not used by this result.

## Privacy, bias, environment, and licenses

- Webcam frames were processed locally and neither saved nor uploaded; raw JSON contains metrics/environment only.
- No private/raw artifact is tracked in Git. The generated video contains synthetic geometry and no person.
- Profile and severity are user-selected settings, not diagnosis.
- The evaluation convenience set does not establish demographic, garment, camera, or population accuracy.
- No training was performed; pretrained MediaPipe CPU inference was reused. RSS is measured; energy is not.
- User/accessibility validation is `NOT_MEASURED` and no participant is simulated.

### Attribution inventory

| Component | Version/status | License/evidence |
| --- | --- | --- |
| ChromaLens project | 0.1.0 | Apache-2.0; repository LICENSE |
| mediapipe | 0.10.21 | Apache-2.0; model/backend attribution in models/README.md; metadata=Apache 2.0 |
| daltonlens | 0.1.5 | MIT; bundled notice in assets/cvd/DALTONLENS-MIT-LICENSE.md; metadata=UNKNOWN |
| numpy | 1.26.4 | BSD-3-Clause; installed distribution metadata/project license; metadata=Copyright (c) 2005-2023, NumPy Developers. |
| opencv-contrib-python | 4.10.0.84 | Apache-2.0; installed distribution metadata/project license; metadata=Apache 2.0 |
| SCHP-ATR | DEFERRED | Not active in T09; license/weights review required by T10 gate |

SCHP is not active T09 runtime evidence. Its code/weights/license and OpenVINO deployment remain an explicit T10 gate rather than an inferred attribution pass.

## Known failures and limitations

1. Degraded-frame behavior remains visible and is reported per run.
2. Any fired RSS continuous-growth diagnostic remains an open risk.
3. The measured machine is development-only, not declared demo hardware.
4. Target-user validation and sensor-to-photon latency are not measured.
