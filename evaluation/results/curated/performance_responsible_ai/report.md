# T09 Performance and Responsible-AI Workstream

Status: `PARTIAL`. Performance runs and the manual ROI observation are retained; demo-hardware acceptance, raw-artifact coordinator re-verification, external sensor latency, license closure, and user validation are incomplete.

Source: Trinh branch tip `b5da1c0e4975f3f4b07f08cec83bf0ada457bf2e`. Performance measurement commit `7bc76d0526b34e7e366fe0cef730dc86680f5ef3`; manual ROI commit `c0e3e7a759e6ffeb8b2b903583b8cf05927b8416`; responsible-AI audit commit `3bd976bb09bdc4605bb3149089d9c00d4c11f470`.

## Claim boundary

All numbers are development-host observations for LENOVO 83JC, AMD64 Family 25 Model 68, 4 physical/8 logical cores, 15.69 GiB RAM, MediaPipe CPU. They are not generalized to the undeclared demo machine.

- `source_read_to_render_ms`: capture-read return to renderer completion.
- `source_read_to_display_submit_ms`: capture-read return to return from `cv2.imshow`; GUI only.
- `sensor_to_photon_ms`: `NOT_MEASURED`; no external synchronized apparatus.

## Performance observations

| Case | FPS | Render p50/p95 ms | Display-submit p50/p95 ms | RSS start/end/peak MiB | Degraded rate | RSS growth |
| --- | ---: | ---: | ---: | ---: | ---: | --- |
| PERF-WEBCAM-GUI-120 | 18.497687789026372 | 62.0 / 156.0 | 62.0 / 156.0 | 187.12890625 / 178.34765625 / 218.8671875 | 0.935586 | FAIL |
| PERF-WEBCAM-HEADLESS-120 | 21.25 | 47.0 / 125.0 | NOT_MEASURED | 191.671875 / 165.87109375 / 216.68359375 | 0.876078 | FAIL |
| PERF-VIDEO-GUI-120 | 30.0 | 16.0 / 32.0 | 16.0 / 32.0 | 138.265625 / 120.1953125 / 148.99609375 | 0.983333 | PASS |
| PERF-VIDEO-HEADLESS-120 | 48.95 | 16.0 / 32.0 | NOT_MEASURED | 131.2578125 / 116.23828125 / 151.30078125 | 0.983827 | FAIL |

Every render-latency continuous-growth flag was false. RSS growth was true in three of four runs and remains an open diagnostic failure.

## Manual/non-AI baseline

Five public-fixture manual ROI trials had median completion time `3.016 s`. This measures human selection effort; it does not automatically locate garments in moving/unconstrained scenes. Fixed RGB thresholding also cannot determine garment location independently of background, illumination, pose, and material. AI is needed for automatic per-pixel localization; deterministic color science remains appropriate after localization.

## Artifact integrity

The machine result contains complete size/SHA-256/provenance manifests for the four raw benchmark JSON files, generated video, manual ROI JSON, and RAI audit JSON. Those ignored files were present for Trinh's report generation but are absent in this coordinator checkout. Their recorded hashes are preserved, not falsely reported as independently reverified. Tracked `report.md` and `performance_metrics.csv` are rehashed and tested from exact LF bytes.

## Privacy, bias, environmental impact, and license gaps

- Local/offline runtime; camera frames are neither saved nor uploaded by default.
- No private/raw T09 media is tracked. Evaluation capture remains explicit opt-in.
- The product is assistive and non-diagnostic; profile/severity are user selected.
- Five public fixtures are not demographic validation. Coverage gaps include skin tone, body presentation, garment type/material/pattern, lighting, occlusion, camera, and display.
- Pretrained MediaPipe CPU inference avoids training from scratch. FPS/RSS are reported; energy consumption is not measured.
- License status is `GAPS_RECORDED`, not PASS. Open items: DaltonLens, MediaPipe, NumPy, OpenCV package evidence and deferred SCHP-ATR attribution/weights review.
- User/accessibility validation is `NOT_MEASURED`; no participant is simulated.

## Known failures

1. Degraded-frame rates are high in every run.
2. RSS continuous-growth diagnostic fails in three runs.
3. The measured host is not declared demo hardware.
4. Ignored raw bytes are unavailable for coordinator-side independent rehash.
