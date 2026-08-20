# T06 selective assistive recoloring

This directory documents the project-authored T06 candidate-color transform.
It contains no model weights, copied lookup table, dataset, or third-party
implementation. ChromaLens uses the already pinned NumPy, OpenCV, and
DaltonLens dependencies described elsewhere in the repository.

## Boundary and terminology

- Input display pixels are an explicit OpenCV `uint8` **BGR** frame.
- Candidate selection uses T04's original corrected `RGB`/CIELAB cluster and a
  T05 comparison color. It never uses a previously recolored display value as
  a new original estimate.
- The hard recolor mask is exactly `garment & retained cluster & risk mask`.
- `original_corrected_rgb` and `assistive_display_rgb` are different named
  debug fields. The latter is a representative transform target, not a new
  measurement of the garment.
- CVD simulation is an internal risk/debug view. It is not the assistive result
  and the renderer labels it `CVD SIMULATION (DEBUG ONLY)`.

## Candidate-color algorithm

The deterministic ChromaLens transform is an allowed `plan.md` candidate-color
path, not a rule such as “red always becomes purple.”

1. Convert the original corrected representative from sRGB to conventional
   CIELAB and CIELCH.
2. Generate configured hue rotations and chroma scales while keeping the
   representative L* fixed. Convert candidates through sRGB so gamut behavior
   is explicit.
3. Simulate every candidate and the comparison color for the user-selected
   `protan`, `deutan`, or `tritan` profile and severity using T05's pinned
   Machado/DaltonLens boundary.
4. Score each candidate as:

   `simulated CIEDE2000 separation - 0.18 × original-to-candidate CIEDE2000`

5. Apply a candidate only when risk is at least `0.25` and its simulated
   separation improves by at least `3.0` Delta-E00. These defaults are visible,
   configurable heuristics requiring T09 validation.
6. A different per-key target must exceed the retained target's objective by
   `2.0` for three consecutive frames. State uses LRU eviction and is capped at
   32 keys. T08 should reset state or include profile/track identity in the key
   when the user changes settings or tracking identity.

Candidate generation and tie breaking are deterministic. The selected target
can differ for the same original color when its comparison color, CVD profile,
or severity changes.

## Pixel transform and containment

The display frame is converted from normalized BGR to conventional CIELAB.
Only the selected target's `a*`/`b*` offset is applied; each pixel's source L*
is left untouched before conversion back to sRGB/BGR. This preserves texture
and shading as practical, although gamut clipping and 8-bit quantization can
still shift measured L* slightly.

Feathering is computed from an inward distance transform. Alpha is exactly
zero outside the hard mask, and assignment is restricted to the hard mask.
Therefore pixels outside it remain byte-identical before the renderer adds
outlines and text. T09 must repeat this containment check on the frozen
evaluation set.

## Overlay

`chromalens.renderer.render_assistive_overlay` draws onto a copy and rejects a
simulation view. The separate `render_cvd_simulation_debug_overlay` requires
the `CVD_SIMULATION_DEBUG` enum, so its `DEBUG ONLY` label cannot be omitted by
that path. Both render a thick black contour followed by a thinner white
contour and use an opaque black tag with white border/text. The tag reports
original corrected color and margin, separate assistive display color,
relational risk, lighting quality, profile, severity, backend, and frame ID.

OpenCV's Hershey font is ASCII-only. The current tag transliterates Vietnamese
labels (for example, `Đỏ` to `Do`) while the canonical accented label remains
available from `chromalens.color_naming.vietnamese_color_label`. T08/T11 can
adopt a bundled, license-reviewed Unicode font if the demo requires accented
on-frame text.

## Reproduce evidence

From the locked `lens` environment:

```powershell
conda run --name lens python scripts/t06_recolor_overlay_evidence.py
conda run --name lens python -m pytest -q tests/unit/test_t06_recolor.py tests/unit/test_t06_renderer.py tests/integration/test_t06_assistive_slice.py
```

The script writes ignored PNG/JSON artifacts under
`artifacts/t06-recolor-overlay/`. They are controlled synthetic evidence, not
user-perception, clinical, physical color-accuracy, or demo-hardware results.

## Known limitations

- Candidate and risk thresholds are not calibrated to an individual user.
- CIELAB, CIEDE2000, the display gamut, camera white balance, and Machado
  simulation are approximations; tritan simulation has an upstream caveat.
- Recolor quality depends on T02 mask adequacy and T04 cluster separation.
- Inward feathering avoids background changes but can leave a narrow strip of
  original garment color at uncertain mask edges.
- This module does not diagnose CVD, select a profile automatically, or claim
  universal fashion/accessibility correctness.
