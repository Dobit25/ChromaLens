# T09 MediaPipe Segmentation Evaluation

Status: `COMPLETE` evaluation coverage; quality values are observations, not population accuracy.

- Backend: `mediapipe-selfie-torso/cpu` (`mediapipe==0.10.21`).
- Exact frozen cases evaluated: 20/20; adequate rating >=2: 9/20 (0.450).
- Inputs: five licensed T02 fixtures plus 15 repository-owner-confirmed consented inputs held only below ignored `artifacts/t09/`.
- Processing canvas: aspect-preserving 640x480 letterbox; videos were inferred frame-by-frame and reviewed with nine-frame contact sheets.
- The mask is a person-derived torso heuristic, not semantic garment parsing or calibrated garment confidence.

## Per-case results

| Case | Rating | Adequate | IoU | Frames | Reason |
| --- | ---: | --- | ---: | ---: | --- |
| `SEG-PUB-ASTRONAUT` | 3 | true | N/A | 1 | Upper garment is well covered with only small boundary spill. |
| `SEG-PUB-CC0-WOMAN` | 0 | false | N/A | 1 | No target mask was returned. |
| `SEG-PUB-LOC-LINCOLN` | 0 | false | N/A | 1 | No target mask was returned. |
| `SEG-PUB-LOC-MAN` | 0 | false | N/A | 1 | No target mask was returned. |
| `SEG-PUB-NASA-SHEPARD` | 0 | false | N/A | 1 | Only a thin non-garment strip was retained. |
| `SEG-ANN-PLAIN-UPPER` | 2 | true | 0.382858 | 1 | Upper garment is usable but hair and torso-boundary error remain. |
| `SEG-ANN-PLAIN-LOWER` | 1 | false | 0.370076 | 1 | Upper-body contamination blocks reliable lower-garment color use. |
| `SEG-ANN-MULTICOLOR-UPPER` | 3 | true | 0.881396 | 1 | The patterned upper garment is well covered with minor edge error. |
| `SEG-MULTICOLOR-DRESS` | 2 | true | N/A | 1 | Dress torso is usable but lower-garment coverage is incomplete. |
| `SEG-LOW-LIGHT` | 2 | true | N/A | 1 | Main garment remains usable despite boundary loss in dim lighting. |
| `SEG-WARM-LIGHT` | 1 | false | N/A | 1 | Held certificate and adjacent regions contaminate the garment mask. |
| `SEG-MOTION-SLOW` | 2 | true | N/A | 292 | Most sampled frames are usable but startup and distant frames lose coverage. |
| `SEG-MOTION-FAST` | 1 | false | N/A | 113 | Motion causes severe vegetation and trailing-background contamination. |
| `SEG-OCCLUSION` | 1 | false | N/A | 1 | Occluding laptop and nearby people contaminate the retained region. |
| `SEG-CARRIED-OBJECT` | 1 | false | N/A | 1 | The carried certificate is included and blocks reliable clothing color use. |
| `SEG-SIMILAR-BACKGROUND` | 2 | true | N/A | 1 | The visible upper garment remains usable with limited edge error. |
| `SEG-POSE-SEATED` | 2 | true | N/A | 1 | Seated upper garment is usable despite lower-body omission. |
| `SEG-CLOSE-CROP` | 1 | false | N/A | 1 | Large foreground object and crop contamination dominate the retained mask. |
| `SEG-MULTI-PERSON` | 1 | false | N/A | 1 | People and held object are merged so garment ownership is ambiguous. |
| `SEG-NO-PERSON` | 3 | true | N/A | 1 | Correctly returned no garment mask for the negative scene. |

## Concrete failures and mitigations

### FAIL-SEG-001 - `SEG-PUB-CC0-WOMAN`

- Observed: rating 0/3 - No target mask was returned.
- User impact: mask contamination or omission can change the estimated clothing color or leave the assistive overlay unavailable.
- Reproduction: run the evaluator with the exact manifest-verified asset and inspect its ignored review artifact.
- Mitigation: expose degraded/low-mask state, ask the user to reframe or improve lighting, and compare SCHP only through the T10 gate while retaining MediaPipe fallback.
- Status: `OPEN` documented limitation.

### FAIL-SEG-002 - `SEG-PUB-LOC-LINCOLN`

- Observed: rating 0/3 - No target mask was returned.
- User impact: mask contamination or omission can change the estimated clothing color or leave the assistive overlay unavailable.
- Reproduction: run the evaluator with the exact manifest-verified asset and inspect its ignored review artifact.
- Mitigation: expose degraded/low-mask state, ask the user to reframe or improve lighting, and compare SCHP only through the T10 gate while retaining MediaPipe fallback.
- Status: `OPEN` documented limitation.

### FAIL-SEG-003 - `SEG-PUB-LOC-MAN`

- Observed: rating 0/3 - No target mask was returned.
- User impact: mask contamination or omission can change the estimated clothing color or leave the assistive overlay unavailable.
- Reproduction: run the evaluator with the exact manifest-verified asset and inspect its ignored review artifact.
- Mitigation: expose degraded/low-mask state, ask the user to reframe or improve lighting, and compare SCHP only through the T10 gate while retaining MediaPipe fallback.
- Status: `OPEN` documented limitation.

## Privacy, scope, and limitations

Raw inputs, annotations, overlays, contact sheets, and the private consent record are not tracked. The result contains only non-identifying provenance references and exact hashes. The small convenience set does not establish demographic, body-presentation, camera, garment, or population-level accuracy. Manual adequacy and the three annotated IoUs are separate observations.
