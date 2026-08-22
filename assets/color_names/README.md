# ChromaLens basic 11 color families

## Runtime method

ChromaLens supports these canonical English terms and Vietnamese UI labels:

| English key | Vietnamese label |
| --- | --- |
| `black` | Đen |
| `blue` | Xanh dương |
| `brown` | Nâu |
| `grey` | Xám |
| `green` | Xanh lá |
| `orange` | Cam |
| `pink` | Hồng |
| `purple` | Tím |
| `red` | Đỏ |
| `white` | Trắng |
| `yellow` | Vàng |

The vocabulary follows the 11 basic English terms used in:

- Joost van de Weijer, Cordelia Schmid, Jakob Verbeek, and Diane Larlus,
  “Learning Color Names for Real-World Applications,” IEEE Transactions on
  Image Processing 18(7), 2009. The authors' project page is
  <https://lear.inrialpes.fr/people/vandeweijer/color_names.html>.

ChromaLens does **not** copy or redistribute the authors' learned RGB lookup
matrix because its download page does not state a redistribution license.
Instead, `chromalens.color_naming` implements a documented equivalent lookup:

1. Convert corrected uint8 sRGB to float32 CIELAB with OpenCV.
2. Measure CIE76 distance to a small set of standardized sRGB anchors for each
   family.
3. Use the minimum anchor distance per family.
4. Softmax negative distances into 11 normalized heuristic scores and expose
   the best-versus-second score margin.

The scores and margin are not calibrated probabilities.

## Anchor provenance and license

The exact anchor RGB values are named colors from the W3C
[CSS Color Module Level 4](https://www.w3.org/TR/css-color-4/#named-colors)
standardized sRGB table. The selection/grouping into 11 families and the
Vietnamese translations are authored for ChromaLens. CSS named colors are not
perceptually uniform, so this is a transparent MVP baseline rather than a
universal color-language model.

This software/document includes material copied from or derived from “CSS
Color Module Level 4” <https://www.w3.org/TR/css-color-4/>. Copyright © 2026
World Wide Web Consortium. The W3C Software and Document License applies to
that source material: <https://www.w3.org/copyright/software-license-2023/>.
The complete redistributed notice is in
[`W3C-SOFTWARE-DOCUMENT-LICENSE.md`](W3C-SOFTWARE-DOCUMENT-LICENSE.md).
ChromaLens-authored code and data remain under the repository's Apache-2.0
license. ChromaLens changes the W3C table by selecting and grouping a subset of
named sRGB values into the 11 project families.

## CIELAB convention

The module follows OpenCV's float conversion contract documented at
<https://docs.opencv.org/4.10.0/d8/d01/group__imgproc__color__conversions.html>:

- Input is explicitly RGB, not OpenCV BGR.
- `uint8 [0, 255]` is converted to `float32 [0, 1]` before the non-linear
  `COLOR_RGB2LAB` conversion.
- Output uses conventional CIELAB: `L*` in `[0, 100]`, signed `a*`, and signed
  `b*`. It is never stored in OpenCV's offset-packed uint8 Lab convention.

## Known limitations

- One or several prototypes cannot represent every shade, language, culture,
  material, shadow, highlight, or camera/display condition.
- CSS named colors are standardized implementation constants, not a balanced
  perceptual dataset.
- The controlled T04 set verifies deterministic coverage of all 11 contracts;
  it is not an accuracy benchmark. T09 owns broader evaluation and tuning.
