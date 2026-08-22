# T09 Performance Evidence

Status: Performance evidence: `COMPLETE`. Responsible-AI audit execution: `COMPLETE`. License compliance: `GAPS_RECORDED` (not PASS).

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
| `artifacts/t09/performance_responsible_ai/t09-manual-roi-f59b5913-20260822t172922z.json` | BASELINE-MANUAL-ROI | 5307 | `a2392deae77829d358d86a22f9929d48b4e3c3d61f3cf943d8ab39c445a57d02` | false |
| `artifacts/t09/performance_responsible_ai/t09-responsible-ai-audit-63d6a1c9-20260822t185636z.json` | PERF-SENSOR-EXTERNAL; BASELINE-FIXED-RGB; RAI-ARTIFACT-INTEGRITY; RAI-PRIVACY; RAI-LICENSE; RAI-LIMITATIONS; RAI-USER-VALIDATION | 22107 | `cd703496b87dcb90ec438ff935f5100e7cfb7d313a489da3012ceec6e89244a5` | false |

## Manual ROI and Responsible-AI evidence

- Manual ROI evidence: `COMPLETE` at commit `c0e3e7a759e6ffeb8b2b903583b8cf05927b8416`; median completion time: `3.016` s.
- Manual ROI is a human non-AI baseline, not automatic garment localization. It records timing/hash metadata only; no image, ROI geometry, crop, screenshot, pixel array, or base64 data is included.
- Responsible-AI audit execution: `COMPLETE` at commit `3bd976bb09bdc4605bb3149089d9c00d4c11f470`. Sensor-to-photon remains `NOT_MEASURED`; user validation remains `NOT_MEASURED`.
- Unconsented tracked media count: `0 PASS`. Artifact checksum mismatch count: `0 PASS`.
- License compliance: `GAPS_RECORDED`, not PASS. Recorded gaps: `runtime-package-daltonlens`; `runtime-package-mediapipe`; `runtime-package-numpy`; `runtime-package-opencv-contrib-python`; `schp-atr-deferred`.
- Five public fixtures are not demographic validation. The product is not medically validated and does not make a medical diagnosis claim.

## Recorded limitations

- High degraded-frame rates were measured in all four performance cases; impact: reduced full-quality rendering; boundary: report values remain unmodified.
- RSS continuous-growth flag is FAIL in three of four cases; impact: potential long-run memory risk; mitigation: retain bounded-queue/RSS investigation as open work.
- Development host is not declared demo hardware; impact: no demo-threshold PASS claim; mitigation: repeat on declared demo hardware.
- sensor_to_photon_ms is NOT_MEASURED without external apparatus; impact: physical display latency is unknown; mitigation: acquire synchronized apparatus.
- Five public images are not demographic validation; impact: coverage gaps for segmentation, lighting, occlusion, backgrounds, and color similarity remain; mitigation: consented, reviewed evaluation expansion.
- The product is not a medical diagnosis and energy consumption is not measured; impact: no clinical or energy-use claim; mitigation: retain these boundaries.

## Scope boundary

This report consolidates measured development-host performance and the validated timing/hash-only Manual ROI and Responsible-AI audit summaries. It does not claim a demo-hardware threshold PASS, sensor-to-photon measurement, medical validation, or demographic validation.
