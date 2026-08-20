# T09 Color Science Workstream

Status: PARTIAL under frozen protocol 1.0.0.

The synthetic matrix covers 11 basic families x 3 deterministic lighting gains (33 cases). It is supplemental behavior evidence, not physical-camera accuracy. The frozen physical COL cases remain NOT_RUN because their assets are TO_BE_ACQUIRED.

## Lighting matrix

Synthetic evaluated cases: 33; name accuracy: 27/33.
Lighting stability rate: 0.545; protocol diagnostic target: >= 0.80.

| Family | Stable across all three conditions | Predicted names |
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

Confusion counts are in `color_confusion_table.csv`; rows with zero counts are retained.

## Plain and multicolor

The plain-garment matrix uses one dominant color per case. The separate multicolor case retained 2 K=2 clusters: red, blue. Cluster masks outside the garment: [0, 0].

## CVD risk sanity

Each row stores original and simulated CIEDE2000 values. Risk is a configured heuristic score, not a calibrated probability.

| Profile | Confusing score > control score |
| --- | ---: |
| protan | true |
| deutan | true |
| tritan | true |

## Limitations

- Synthetic lighting gains do not model a physical illuminant, camera ISP, exposure, glare, or display.
- The frozen physical matrix is NOT_RUN pending licensed/consented assets.
- No demographic, clinical, or population-level inference is supported.
- Existing color margins and CVD risk scores remain non-calibrated heuristics.
