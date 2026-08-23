# T09 End-to-End Integration Evaluation

Status: `COMPLETE` coverage of the frozen 10-case integration matrix.

This is development-machine evidence. It is not sensor-to-photon measurement, demo-hardware acceptance, population accuracy, or clinical validation.

## Results

| Case | Status | Frames | Degraded | ID mismatch | Outside mask | Target switches | Observation |
| --- | --- | ---: | ---: | ---: | ---: | ---: | --- |
| `E2E-CONTROLLED-MULTICOLOR` | COMPLETE | 1 | 0 | 0 | 0 | N/A | mask, correction, two clusters, risk, recolor, outline, overlay, and matching are available |
| `E2E-REAL-PUBLIC` | COMPLETE | 1 | 0 | 0 | N/A | N/A | all required analytical stages available |
| `E2E-SINGLE-COLOR` | COMPLETE | 1 | 1 | 0 | N/A | N/A | risk: two retained original-color clusters are required |
| `E2E-NO-PERSON` | COMPLETE | 1 | 1 | 0 | N/A | N/A | segmentation: no current garment region; prior masks cleared; risk: two retained original-color clusters are required |
| `E2E-BACKEND-UNAVAILABLE` | COMPLETE | 1 | 1 | 0 | N/A | N/A | segmentation: RuntimeError: controlled backend unavailable for T09 failure contract; risk: two retained original-color clusters are required |
| `E2E-RECOLOR-DISABLED` | COMPLETE | 1 | 0 | 0 | 0 | N/A | analysis remained current and assistive pixels stayed source-identical |
| `E2E-STATIC-TEMPORAL` | COMPLETE | 8 | 0 | 0 | N/A | 0 | retained assistive selections=8 |
| `E2E-MOVING-TEMPORAL` | COMPLETE | 292 | 31 | 0 | N/A | 218 | assistive selections=261; nine-frame contact review saved |
| `E2E-STALE-REJECTION` | COMPLETE | 1 | 0 | 0 | N/A | N/A | rejected_attempts=1; mismatched results presented=0 |
| `E2E-RECOLOR-CONTAINMENT` | COMPLETE | 1 | 0 | 0 | 0 | N/A | outline and text overlays were excluded from the containment comparison |

## Intermediate visual evidence

The controlled success case saves source, corrected image, color-cluster map, CVD-risk mask, pre-overlay assistive recolor, and final overlay as separate ignored artifacts. Other cases save final views or a moving-video contact sheet. Every cited byte has a manifest entry and SHA-256 in `result.json`.

## Concrete integration failures

1. `E2E-SINGLE-COLOR`: a single retained color cannot produce relational risk; recolor stays unavailable. Mitigation: explain that a comparison color is required instead of fabricating risk.
2. `E2E-NO-PERSON`: no current garment mask clears all dependent stages. Mitigation: show degraded state and ask the user to enter/reframe.
3. `E2E-BACKEND-UNAVAILABLE`: backend exception is visible on the current frame and produces no fake mask. Mitigation: keep the documented fallback/error path and expose backend status.
4. `E2E-MOVING-TEMPORAL`: real MediaPipe processing records degraded frames and may have no stable assistive selection. Mitigation: retain newest-frame semantics, expose degraded state, and evaluate SCHP only in T10 while preserving MediaPipe fallback.

## Scope, privacy, bias, and limitations

All processing is local/offline. Saving occurs only in this explicit evaluator. Synthetic fixtures contain no people; the NASA fixture is licensed and documented; the moving capture is covered by the owner-confirmed private consent record and remains ignored. This small convenience set does not establish demographic, garment, pose, lighting, camera, or user-outcome generalization.
