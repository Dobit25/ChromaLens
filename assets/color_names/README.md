# T04 Basic Color Prototype Provenance

## Implementation

`src/chromalens/color/naming.py` implements an explainable MVP
11-basic-color heuristic. It uses the following CSS named-color sRGB
prototypes:

- black
- white
- red
- green
- yellow
- blue
- brown
- purple
- pink
- orange
- gray

The Vietnamese labels are project translations:

- đen
- trắng
- đỏ
- xanh lá
- vàng
- xanh dương
- nâu
- tím
- hồng
- cam
- xám

## Source and attribution

The prototype RGB values come from the named-color table in:

- W3C, CSS Color Module Level 4:
  https://www.w3.org/TR/css-color-4/#named-colors
- W3C Document License:
  https://www.w3.org/copyright/document-license-2023/

Copyright © 2026 World Wide Web Consortium.
https://www.w3.org/copyright/document-license-2023/

The implementation does not copy or claim to implement the learned
Van de Weijer color-name distribution. It uses CSS named colors as the
documented equivalent lookup permitted by the T04 MVP plan.

## Algorithm and limitations

Input sRGB is converted to conventional floating-point CIE Lab using
OpenCV. The nearest prototype is selected using Euclidean Lab distance,
equivalent to Delta-E 1976 for this purpose.

Scores are produced using a temperature-scaled softmax over negative
prototype distances. These scores and their best-versus-second margin
are explainable heuristic values. They are not calibrated probabilities.

The prototypes are not perceptually uniform and cannot represent all
real-world shades, materials, lighting conditions, cameras, or cultural
color-name boundaries. For example, a dark red can be closer to the CSS
brown prototype than to pure CSS red.

## Controlled evaluation

The reproducible controlled input and generated result table are:

- `evaluation/t04_controlled_color_samples.csv`
- `evaluation/results/t04_color_naming_results.csv`
- `scripts/evaluate_t04_color_names.py`

The current controlled evaluation contains one synthetic uniform patch
for each of the 11 names. Values near absolute black and clipping were
adjusted to remain valid under T04 preprocessing.

A result of 11/11 on these synthetic patches demonstrates deterministic
pipeline behavior only. It is not a claim of 100% accuracy on real
garments or unconstrained camera images. Real-world evaluation is
deferred to T09.