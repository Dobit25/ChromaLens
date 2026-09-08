# ChromaLens Post-MVP Evaluation Protocol

Protocol version: `2.0.0`

Status: `FROZEN` for T12-T17

Product baseline: `d876e6acaa7373928bdfc796265051a36a80d680`

Schema: `evaluation/schema/post-mvp-result.schema.json`

Metric registry: `evaluation/schema/post-mvp-metric-registry.json`

Case registry: `evaluation/fixtures/post-mvp-cases.csv`

Ownership: `evaluation/OWNERSHIP-v2.md`

## 1. Purpose and change control

This is the Gate 0 contract for the owner-approved T12-T17 post-MVP phase. It
does not modify or reinterpret frozen T09 `evaluation/protocol.md` version
1.0.0 or its curated results. A result is a v2 result only when its protocol,
schema, metric registry, and exact fixture IDs all use version 2.0.0.

After the Gate commit, changing a case ID, metric name, unit, formula,
threshold, consent rule, or claim boundary requires an owner-approved protocol
revision. The change record must state compatibility impact and replacement
tests. Silent reinterpretation and editing historical result values are
prohibited.

Gate 0 freezes contracts and records a baseline. It does not implement any
T12-T17 product feature and does not claim the new acceptance targets pass.

## 2. Scope and dependency boundary

- T12: 11 stable level-one families, 29 allowed level-two labels, explicit
  uncertainty, and 30 physical samples in three lighting conditions.
- T13: 20 standalone garments and an explicitly manual ROI fallback.
- T14: windowed/fullscreen presentation at 1366x768 and 1920x1080 without
  changing processing resolution.
- T15: named-stage profiling, bounded optimization, and 300-second stability
  measurements.
- T16: five severity values for each user-selected profile plus experimental
  garment-bounded spatial gradient risk.
- T17: integrated release gate and feature freeze.

T12-T16 may be developed in parallel within `evaluation/OWNERSHIP-v2.md`.
T15 final measurements run after the integrated enabled feature set. T17 is
strictly last. T16 gradient risk remains disabled and visibly experimental if
its quality or performance gate does not pass.

## 3. Frozen color vocabulary and physical matrix

Level one remains exactly:

`black`, `blue`, `brown`, `grey`, `green`, `orange`, `pink`, `purple`, `red`,
`white`, and `yellow`.

Level two contains exactly 29 display labels:

| Basic family | Allowed level-two labels |
| --- | --- |
| black | black |
| blue | light_blue, blue, navy, teal |
| brown | beige, brown, dark_brown |
| grey | light_grey, grey, charcoal |
| green | mint, green, dark_green, olive |
| orange | peach, orange |
| pink | light_pink, pink |
| purple | lavender, purple, dark_purple |
| red | coral, red, dark_red |
| white | white, cream |
| yellow | light_yellow, yellow |

The registry includes one digital contract for each label and three explicit
uncertainty boundaries. It also locks 30 physical samples: the 29 labels plus
one boundary sample, each under `neutral`, `warm`, and `low` lighting, for 90
physical observations. Physical assets are not present at Gate 0 and remain
`TO_BE_ACQUIRED`/`NOT_RUN`; this is coverage planning, not an accuracy claim.

A result may expose a level-two label only when both conditions hold:

- `color_name_margin >= 0.10`; and
- lighting quality is not `poor`.

Otherwise the user-facing result is `uncertain` while the best level-one
family and raw heuristic scores remain available diagnostically. The margin is
not a calibrated probability. Physical accuracy has no frozen population claim
threshold. Digital contract accuracy must be 1.0; lighting stability target is
0.80 and is diagnostic until physical evidence exists.

## 4. Standalone-garment procedure

The registry freezes four variants for each of `top`, `trousers`, `skirt`,
`dress`, and `coat`: two simple-background and two complex-background cases.
Each case records automatic mask availability, a 0-3 adequacy rating, original
corrected dominant-color correctness, contamination/omission, and failure
reason. Annotation IoU is stored when a licensed annotation exists.

The current SCHP-ATR model is a human parser and standalone products are a
domain-shift evaluation. ATR exposes upper-clothes, skirt, pants, and dress;
it has no dedicated coat output in the current runtime contract. A coat may be
reported as an `upper-clothes` usefulness result but never as proven coat
classification.

Manual selection is a fallback, not AI inference. It requires an explicit
user action, visible `manual selection` provenance, cancel support, bounds
validation, and source-frame immutability. Automatic and manual results are
reported separately.

## 5. Fullscreen and presentation procedure

The frozen cases cover Product and Diagnostic modes at 1366x768 and
1920x1080. The viewport is fit with letterbox/pillarbox and the aspect-ratio
error must be at most 0.005. Text overflow count must be zero. Entering
fullscreen must not change capture resolution, SCHP input size, analytical
mask coordinates, or color/recolor outputs. `Esc` leaves fullscreen and `q`
exits. A manual GUI observation supplements deterministic offscreen tests.

## 6. Performance procedure and exact timing semantics

Every acceptance session uses 15 seconds warm-up followed by a 300-second
measured interval. Store every valid sample or mark the result `INVALID`.
Report exact host role, hardware, backend/device, source, requested and actual
resolution, UI/theme, profile/severity, model precision, and lock checksum.

`source_read_to_render_ms` starts at `FramePacket.timestamp_ns`, created
immediately after `VideoCapture.read()` returns a valid frame, and ends after
the analytical renderer plus presentation compositor return. It is available
for GUI and headless runs.

`source_read_to_display_submit_ms` has the same start and ends immediately
after `cv2.imshow()` returns. It is GUI-only and measures software submission,
not physical visibility.

`sensor_to_photon_ms` is `NOT_MEASURED` unless synchronized external apparatus
measures sensor stimulus to emitted display light. No software timestamp may
be relabeled as sensor-to-photon, exposure-to-display, or photon latency.

Percentiles use NumPy linear interpolation. The internal target is:

- processed FPS at least 20 frames/s;
- GUI p95 `source_read_to_display_submit_ms <= 120 ms`, or headless p95
  `source_read_to_render_ms <= 120 ms`;
- `latency_continuous_growth_flag == false` and
  `rss_continuous_growth_flag == false` over the full 300 seconds.

Growth uses six consecutive 50-second window medians and the formulae in the
metric registry. These are internal engineering targets, not organizer facts.
Missing targets are honest failures/limitations, never grounds to delete data.

Named stage timing uses the dimension values `segmentation_inference`,
`optical_flow`, `white_balance`, `color_extraction`, `risk`, `recolor_render`,
`presentation`, and `display_submit`. Instrumentation must not change the
analytical result.

## 7. Severity and spatial-risk procedure

The user selects `protan`, `deutan`, or `tritan`; ChromaLens does not diagnose
a condition. Each profile is evaluated at severity 0.00, 0.25, 0.50, 0.75,
and 1.00. Severity zero must retain the existing identity contract. Exact
Delta-E00 values, risk score, and recolor decision are recorded. Product
presets, if added, must map reversibly to numeric values; Diagnostic mode keeps
the number visible.

The three large-gradient cases evaluate an experimental tiled/region-based
CIELAB risk map for each profile. Values must be finite and in `[0,1]`, aligned
to the source garment mask, and exactly zero outside it. Runtime cost and
failure modes are recorded. No clinical sensitivity/specificity claim is
allowed.

## 8. Artifacts, privacy, consent, licenses, and checksums

Small curated `.json`, `.csv`, and `.md` results are tracked only under
`evaluation/results/curated/post_mvp/`. Raw videos, private footage, large
images, traces, model files, and bulk output live under ignored
`artifacts/post_mvp/`. `git add -f` is prohibited.

Every artifact referenced by a result has one manifest entry containing:

- stable artifact ID and exact repository-relative path;
- tracked-curated or ignored-raw classification and media kind;
- whether it contains personal data;
- source/provenance and creation command;
- consent state (`NOT_APPLICABLE`, `OWNER_CONFIRMED`, or
  `DOCUMENTED_PRIVATE` for usable artifacts);
- license/rights statement;
- exact byte size and lowercase SHA-256 over actual file bytes;
- availability.

`NOT_AUTHORIZED` media must not be used or tracked. If ignored raw bytes are
absent on another checkout, validation reports them unavailable rather than
pretending to verify them. All present bytes must match. Default camera/video
operation stores and uploads no frames. Evaluation capture is explicit opt-in.

## 9. Result and baseline rules

Every v2 result validates structurally against the schema and semantically
against the metric and case registries. Case IDs and metric units cannot be
invented in result files. A command stores its exact invocation, purpose, and
observed exit code. A result identifies the exact 40-character code commit it
measures; a dirty worktree must be disclosed.

Gate baseline evidence is a current-product observation on the development
host, not the final T15 benchmark and not official demo-hardware evidence. It
may fail the new targets. The baseline raw log remains ignored, while a small
curated JSON/Markdown summary and its raw-log manifest are tracked.

## 10. Gate 0 completion

Gate 0 is complete only when the plan addendum and all v2 contracts agree,
fixture IDs are unique, every required metric exists, a current baseline is
recorded, present artifact bytes pass SHA-256 validation, focused tests pass,
and the complete pre-feature test suite passes in `lens`. No T12-T17 feature
implementation belongs in the Gate commit.
