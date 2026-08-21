# T09 Performance Evidence

Status: `COMPLETE` for the four frozen performance cases. Responsible-AI evidence remains `PENDING` for the next Trinh work item.

These are development-host observations (`host_role=development`, `declared_demo_hardware=false`). No demo-floor or project-target PASS claim is made here.

## Provenance and environment

- Git commit: `7bc76d0526b34e7e366fe0cef730dc86680f5ef3`
- The following environment fields were validated identical across all four artifacts.
- Hardware: LENOVO 83JC; CPU AMD64 Family 25 Model 68 Stepping 1, AuthenticAMD; 4 physical / 8 logical cores; RAM 15.692100524902344 GiB; GPU NVIDIA GeForce RTX 3050 6GB Laptop GPU; NPU not detected.
- Operating system: Windows-10-10.0.26200-SP0
- Python: 3.10.20
- Backend/device: mediapipe-selfie-torso/cpu / cpu
- Lock SHA-256: `3abb7af836d5721db3bb3de753816f8b41994a2d20c71fd96c25d80e136a071a`
- Package versions: chromalens-ai 0.1.0; daltonlens 0.1.5; mediapipe 0.10.21; numpy 1.26.4; opencv-contrib-python 4.10.0.84

## Run records

| Case | Created UTC | Source | Resolution | Mode | Warm-up / measurement | Result |
| --- | --- | --- | --- | --- | --- | --- |
| PERF-WEBCAM-GUI-120 | 2026-08-21T16:53:24.455978Z | webcam:0 | 640x480 | gui | 15.0 s / 120.0 s | COMPLETE |
| PERF-WEBCAM-HEADLESS-120 | 2026-08-21T16:45:54.457154Z | webcam:0 | 640x480 | headless | 15.0 s / 120.0 s | COMPLETE |
| PERF-VIDEO-GUI-120 | 2026-08-21T17:03:51.436035Z | video:generated-360x240.avi | 360x240 | gui | 15.0 s / 120.0 s | COMPLETE |
| PERF-VIDEO-HEADLESS-120 | 2026-08-21T17:00:11.851923Z | video:generated-360x240.avi | 360x240 | headless | 15.0 s / 120.0 s | COMPLETE |

## Throughput and latency

`source_read_to_render_ms` ends after rendering. `source_read_to_display_submit_ms` ends after `cv2.imshow()` returns and is not sensor-to-photon latency. `NOT_MEASURED` is retained exactly where no measurement exists. Demo-threshold evaluation is `NOT_EVALUATED` for every case because this is development hardware; it is never interpreted as PASS.

| Case | FPS | Render p50 / p95 (ms) | Render slope (ms/min) | Display-submit p50 / p95 (ms) | Sensor-to-photon p50 / p95 (ms) | Processing p50 / p95 (ms) | Frames | Dropped capture frames | Degraded rate | Retained render / display samples |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- | ---: | ---: |
| PERF-WEBCAM-GUI-120 | 18.497687789026372 | 62.0 / 156.0 | -6.965429760462803 | 62.0 / 156.0 | NOT_MEASURED / NOT_MEASURED | 32.0 / 140.0 | 2220 | 1382 | 0.9355855855855856 | 2220 / 2220 |
| PERF-WEBCAM-HEADLESS-120 | 21.25 | 47.0 / 125.0 | 9.796190674127388 | NOT_MEASURED / NOT_MEASURED | NOT_MEASURED / NOT_MEASURED | 32.0 / 94.0 | 2550 | 1051 | 0.876078431372549 | 2550 / 0 |
| PERF-VIDEO-GUI-120 | 30.0 | 16.0 / 32.0 | -0.5640926120804822 | 16.0 / 32.0 | NOT_MEASURED / NOT_MEASURED | 16.0 / 32.0 | 3600 | NOT_APPLICABLE | 0.9833333333333333 | 3600 / 3600 |
| PERF-VIDEO-HEADLESS-120 | 48.95 | 16.0 / 32.0 | -0.023785868979778566 | NOT_MEASURED / NOT_MEASURED | NOT_MEASURED / NOT_MEASURED | 16.0 / 32.0 | 5874 | NOT_APPLICABLE | 0.9838270343888321 | 5874 / 0 |

## RSS and growth diagnostics

A `true [FAIL]` RSS growth flag is reported as a diagnostic failure, not suppressed or reinterpreted as success. High degraded-frame rates remain observations of the measured pipeline state.

| Case | RSS start / end / peak (MiB) | RSS delta (MiB) | RSS slope (MiB/min) | Render-latency growth flag | RSS growth flag |
| --- | ---: | ---: | ---: | --- | --- |
| PERF-WEBCAM-GUI-120 | 187.12890625 / 178.34765625 / 218.8671875 | -8.78125 | 6.900712044036851 | false [PASS] | true [FAIL] |
| PERF-WEBCAM-HEADLESS-120 | 191.671875 / 165.87109375 / 216.68359375 | -25.80078125 | 6.966297357784202 | false [PASS] | true [FAIL] |
| PERF-VIDEO-GUI-120 | 138.265625 / 120.1953125 / 148.99609375 | -18.0703125 | 3.6218831940234897 | false [PASS] | false [PASS] |
| PERF-VIDEO-HEADLESS-120 | 131.2578125 / 116.23828125 / 151.30078125 | -15.01953125 | 6.678754087905211 | false [PASS] | true [FAIL] |

## Ignored-artifact manifest

The following raw benchmark JSON and generated video remain under ignored `artifacts/t09/`; this report records only their byte sizes and SHA-256 digests. They are not added to Git.

| Artifact | Related case | Bytes | SHA-256 | Tracked in Git |
| --- | --- | ---: | --- | --- |
| `artifacts/t09/performance_responsible_ai/t09-performance-perf-webcam-gui-120-20260821t165324z.json` | PERF-WEBCAM-GUI-120 | 12901 | `f1576bfc3d1ff11f2c84bae4b8f15e52792a441dc2512de690f10b5d84f6d04b` | false |
| `artifacts/t09/performance_responsible_ai/t09-performance-perf-webcam-headless-120-20260821t164554z.json` | PERF-WEBCAM-HEADLESS-120 | 13102 | `f4b287d69cdcee658de57a4dda4ebf825fdc698cc6009cf2798bb51d95b73b37` | false |
| `artifacts/t09/performance_responsible_ai/t09-performance-perf-video-gui-120-20260821t170351z.json` | PERF-VIDEO-GUI-120 | 12544 | `e26674d85c7940ecd99e39259f5d6add6e643f089301f2c05cdd2ff0e3155a45` | false |
| `artifacts/t09/performance_responsible_ai/t09-performance-perf-video-headless-120-20260821t170011z.json` | PERF-VIDEO-HEADLESS-120 | 12758 | `9ec98841c1d3e3f6eee4cad4139001535391db516959e07a3d78c4d63ebfd517` | false |
| `artifacts/t09/performance_responsible_ai/inputs/generated-360x240.avi` | PERF-VIDEO-GUI-120; PERF-VIDEO-HEADLESS-120 | 1357144 | `3361444ba0a6c9119e10cc677fe5214f7035c2a2dda0e86c35be52a6d99d0244` | false |

## Scope boundary

This step consolidates measured performance and hardware evidence only. Responsible-AI evidence, including the full privacy, bias, limitations, license, and user-validation package, is `PENDING` for the next work item.
