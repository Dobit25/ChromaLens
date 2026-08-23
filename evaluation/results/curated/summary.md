# T09 Cross-Workstream Summary

Protocol/schema/metric registry: `1.0.0`

Coordinator status: `DONE`

Host claim boundary: development-machine evidence only; no demo-hardware or
sensor-to-photon claim.

## Frozen matrix coverage

| Workstream | Result status | Frozen cases | Complete | Partial | Not run |
| --- | --- | ---: | ---: | ---: | ---: |
| Color science | `COMPLETE` | 50 | 17 | 0 | 33 |
| Segmentation | `COMPLETE` | 20 | 20 | 0 | 0 |
| End to end | `COMPLETE` | 10 | 10 | 0 | 0 |
| Performance and responsible AI | `COMPLETE` | 12 | 9 | 0 | 3 |
| **Total** | **`DONE`** | **92** | **56** | **0** | **36** |

Workstream `COMPLETE` means its T09 Definition of Done evidence is closed. A
case row remains `NOT_RUN` when no measurement exists; neither workstream
completion nor owner acceptance relabels it as measured. The protocol has no
calibrated aggregate segmentation or physical color-accuracy threshold.

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
- Performance: four locally regenerated 15-second-warm-up plus 120-second
  measurements are development-host observations. Processed FPS was
  19.73/14.01 for webcam GUI/headless and 15.94/24.17 for generated-video
  GUI/headless. GUI p50/p95 `source_read_to_display_submit_ms` was 47/78 ms;
  headless display-submit and every `sensor_to_photon_ms` row remain
  `NOT_MEASURED`.
- Responsible AI: runtime is local/offline, camera frames are not saved or
  uploaded by default, profile selection is not diagnosis, limitations and at
  least three concrete failures are documented, and private/raw media remains
  ignored with consent/provenance/license/checksum manifests.

## Accepted omissions and claim boundary

The repository owner accepted closure without acquiring the physical 11 x 3
color-lighting set. All 33 exact `COL-*` physical rows remain honestly
`NOT_RUN`; synthetic transformations cannot be relabeled as physical captures,
and no physical-camera color-accuracy claim is authorized.

The seven unrecoverable contributor artifacts are superseded, not recreated.
The active package is derived from four new raw benchmark JSON files and one
deterministically generated video; all five are present below the ignored
artifact root and strict checksum validation passes. Manual ROI timing,
external sensor-to-photon latency, energy use, and target-user validation remain
explicitly unmeasured. The host remains development-only.

## Next task

T09 is closed with the limitations above. The exact next plan task is T10,
SCHP/OpenVINO optimization gate; it must preserve the working MediaPipe
baseline and accept optimization only on saved-sample quality and measured
reliability/performance evidence.
