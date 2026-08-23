# T09 Cross-Workstream Summary

Protocol/schema/metric registry: `1.0.0`

Coordinator status: `PARTIAL`

Host claim boundary: development-machine evidence only; no demo-hardware or
sensor-to-photon claim.

## Frozen matrix coverage

| Workstream | Result status | Frozen cases | Complete | Partial | Not run |
| --- | --- | ---: | ---: | ---: | ---: |
| Color science | `PARTIAL` | 50 | 17 | 0 | 33 |
| Segmentation | `COMPLETE` | 20 | 20 | 0 | 0 |
| End to end | `COMPLETE` | 10 | 10 | 0 | 0 |
| Performance and responsible AI | `PARTIAL` | 12 | 8 | 2 | 2 |
| **Total** | **`PARTIAL`** | **92** | **55** | **2** | **35** |

`COMPLETE` describes execution/coverage of a frozen case, not proof that its
quality passed an unapproved threshold. The protocol deliberately has no
calibrated aggregate segmentation or physical color accuracy threshold.

## Key evidence

- Color: the deterministic 11-name contract is 11/11 and all six frozen CVD
  sanity cases ran. The supplemental synthetic 11 x 3 lighting diagnostic
  covered 27/33 combinations and produced 6/11 stable color families (0.545),
  but it is not a substitute for physical-camera observations.
- Segmentation: the locked `mediapipe-selfie-torso/cpu` backend ran all 20
  cases. Manual adequacy was 9/20 (0.45). Annotated IoU observations were
  0.383 for plain upper, 0.370 for plain lower, and 0.881 for multicolor upper.
- End to end: all 10 integration cases ran. Current-frame mismatch count and
  pre-overlay changes outside the hard recolor mask were zero. The eight-frame
  static sequence had zero assistive-target switches. The consented moving
  sequence processed 292 frames, with 31 degraded frames (0.106) and 218
  observed target switches; no static threshold is applied to moving footage.
- Performance: Trinh's four 120-second measurements remain development-host
  observations. Recorded processed FPS was 18.50/21.25 for webcam GUI/headless
  and 30.00/48.95 for generated-video GUI/headless. Software latency is named
  `source_read_to_render_ms` and `source_read_to_display_submit_ms` exactly;
  `sensor_to_photon_ms` remains `NOT_MEASURED`.
- Responsible AI: runtime is local/offline, camera frames are not saved or
  uploaded by default, profile selection is not diagnosis, limitations and at
  least three concrete failures are documented, and private/raw media remains
  ignored with consent/provenance/license/checksum manifests.

## Why T09 is not `DONE`

The frozen minimum matrix requires physical observations for every one of the
11 color names under daylight, warm/low, and cool/harsh lighting. No compliant
physical 11 x 3 asset set exists in this checkout, so all 33 exact `COL-*`
physical cases remain honestly `NOT_RUN`. Synthetic transformations cannot be
relabeled as physical captures.

Seven raw artifacts underlying the imported performance/responsible-AI
package also are not available on this coordinator checkout. Their manifests
record provenance, byte size, and SHA-256, while tracked curated bytes validate;
strict raw-byte verification of that package remains unavailable until the
original artifacts are recovered or the four sessions/manual audit are rerun.
The host remains development-only, external sensor-to-photon apparatus was not
used, and user validation remains `NOT_MEASURED`.

## Exact completion action

Acquire or capture the 33 registry-matching physical color/lighting assets
with documented consent/provenance/license, keep them under ignored
`artifacts/t09/color_science/`, run the frozen evaluator without changing case
IDs or thresholds, and regenerate the color result. Recover and checksum the
seven performance/RAI raw artifacts or rerun their frozen procedures on a
fully declared host. Then rerun strict result validation and the full test/CI
gate before changing T09 to `DONE` or starting T10.
