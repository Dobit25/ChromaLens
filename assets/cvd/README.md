# T05 CVD simulation and relational-risk provenance

## DaltonLens / Machado simulation

ChromaLens pins
[`daltonlens==0.1.5`](https://pypi.org/project/daltonlens/0.1.5/) and uses
`daltonlens.simulate.Simulator_Machado2009`. The matching upstream tag resolves
to commit `3c41b9457aeda18cc3780aaff3052d53d34a9293` in
[`DaltonLens/DaltonLens-Python`](https://github.com/DaltonLens/DaltonLens-Python/tree/v0.1.5).
DaltonLens is Copyright 2021 DaltonLens and distributed under the MIT License;
the notice is reproduced in `DALTONLENS-MIT-LICENSE.md`.

The model originates from:

- Gustavo M. Machado, Manuel M. Oliveira, and Leandro A. F. Fernandes,
  “A Physiologically-based Model for Simulation of Color Vision Deficiency,”
  IEEE TVCG 15(6), 2009. DOI:
  [`10.1109/TVCG.2009.113`](https://doi.org/10.1109/TVCG.2009.113).

The public ChromaLens boundary accepts and returns `uint8 H x W x 3` sRGB in
**RGB** channel order. For every non-zero severity, DaltonLens converts
gamma-encoded sRGB to linear RGB using the standard piecewise sRGB transfer
function, applies the selected Machado matrix in linear RGB, clips, reapplies
the sRGB transfer function, and returns uint8 sRGB. ChromaLens returns an exact
copy at severity zero because DaltonLens 0.1.5's otherwise-correct float/uint8
round trip maps full-scale channel value 255 to 254.

The user selects `protan`, `deutan`, or `tritan` and severity `[0, 1]`.
Selection is an assistive preference, not a diagnosis or a calibrated measure
of an individual's vision. DaltonLens itself notes that the Machado model is
less suitable for tritanopia than for red-green deficiencies; T09 must retain
this limitation during user/evaluation review.

## CIEDE2000

`chromalens.risk_detection.ciede2000` follows:

- Gaurav Sharma, Wencheng Wu, and Edul N. Dalal, “The CIEDE2000
  Color-Difference Formula: Implementation Notes, Supplementary Test Data, and
  Mathematical Observations,” Color Research & Application 30(1), 2005. DOI:
  [`10.1002/col.20070`](https://doi.org/10.1002/col.20070).
- The authors' reference note and supplemental test material are available
  from the
  [University of Rochester CIEDE2000 page](https://www.ece.rochester.edu/~gsharma/ciede2000/).

Tests use conventional CIELAB (`L* [0,100]`, signed `a*`/`b*`) and published
reference values. They do not use OpenCV's offset-packed uint8 Lab form.

## Relational-risk heuristic

For a pair of retained original corrected colors:

```text
relative_loss = clip((DeltaE_original - DeltaE_CVD) / DeltaE_original, 0, 1)
simulated_closeness = clip(1 - DeltaE_CVD / cvd_confusion_delta_e, 0, 1)
risk_score = relative_loss * simulated_closeness
```

If `DeltaE_original` is below `minimum_original_delta_e`, the score is zero:
the colors were already close and ChromaLens does not label that as a
CVD-created loss. Default configuration is:

| Setting | Default |
| --- | ---: |
| `minimum_original_delta_e` | 5.0 |
| `cvd_confusion_delta_e` | 20.0 |
| `medium_score_threshold` | 0.25 |
| `high_score_threshold` | 0.60 |

Scores below the medium threshold display as `low`; scores at/above the medium
threshold and below high display as `medium`; scores at/above high display as
`high`. Both Delta-E values and the numeric score remain in every
`RiskAssessment` so the level is never the only explanation.

These defaults are transparent engineering heuristics, not calibrated
probabilities, universal just-noticeable-difference thresholds, medical
claims, or validated user-confusion rates. They require the declared T09
evaluation with relevant CVD profiles, displays, lighting, garments, and user
feedback before competition claims are made.

T05 P0 compares unordered retained-color pairs inside one garment. It does not
invent top-bottom or garment-background relationships when those regions are
unavailable. Simulation is an internal risk/debug representation and must not
be presented as the T06 assistive recolored result.
