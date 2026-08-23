# T09 Color Science Workstream

Status: `COMPLETE` under frozen protocol `1.0.0`, with the physical matrix retained as an owner-accepted limitation.

This is a coordinator regeneration of the useful logic from Phong's commit `82ce430d2f7157d8e26254ed2cfd9f69ad82eeb4`. It reports the exact frozen case registry. Synthetic gain transforms remain supplemental and never replace physical camera observations. `COMPLETE` means the required evidence package is closed with the repository owner's explicit acceptance; it is not a physical color-accuracy claim.

## Frozen case coverage

- 33 physical color-lighting cases: `NOT_RUN` because the exact assets remain `TO_BE_ACQUIRED`; this limitation is explicitly accepted by the repository owner.
- 11 tracked digital contract cases: `11/11` correct.
- Six frozen CVD-risk sanity cases: complete.

## Supplemental synthetic lighting diagnostic

The 11 families x three deterministic RGB gains produced 27/33 matching names. This is implementation behavior, not physical color accuracy.
Stability was `0.545`, below the diagnostic target `0.80`.

| Family | Stable | Predicted names |
| --- | ---: | --- |
| black | true | black |
| blue | false | blue, grey |
| brown | true | brown |
| grey | true | grey |
| green | true | green |
| orange | true | orange |
| pink | false | brown, pink |
| purple | true | purple |
| red | false | brown, red |
| white | false | white, yellow |
| yellow | false | orange, yellow |

The complete 121-cell confusion table retains zero-count cells in `color_confusion_table.csv`.

## Plain and multicolor diagnostic

The deterministic two-panel garment retained 2 clusters (red, blue). Changed/assigned cluster pixels outside the garment mask: [0, 0].

## CVD relational-risk sanity

Each CSV row stores original and simulated CIEDE2000 plus the heuristic risk score. The confusing pair outranked its control for:

| Profile | Sanity order |
| --- | ---: |
| protan | PASS |
| deutan | PASS |
| tritan | PASS |

## Limitations

- No physical-camera color/lighting case has run yet.
- Synthetic RGB gains omit illuminant spectra, exposure, ISP, material, glare, camera, and display effects.
- Stability below target is retained as a failure observation, not tuned away.
- Color margins and CVD risk scores are uncalibrated heuristics.
- No clinical, demographic, usability, or population claim is made.
