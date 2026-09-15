# ChromaLens T12 Evaluation Protocol Revision

Protocol version: `2.1.0`

Status: `FROZEN` for T12

Product baseline: `8658ed1d3709969299c34374bc373bdc7654e469`

Schema: `evaluation/schema/post-mvp-result-v2.1.schema.json`

Metric registry: `evaluation/schema/post-mvp-metric-registry-v2.1.json`

Case registry: `evaluation/fixtures/post-mvp-cases-v2.1.csv`

Palette: `assets/color_names/extended_palette.csv`

Ownership: `evaluation/OWNERSHIP-v2.1.md`

## 1. Revision boundary

This owner-approved additive revision changes only T12. Frozen T09 protocol
1.0.0 and post-MVP protocol 2.0.0 files/results remain unchanged and valid.
Non-T12 case IDs and metric semantics are carried forward unchanged so future
integrated results can use one 2.1 registry without rewriting historical data.

## 2. Two-tier naming contract

- Level one is always one of the stable 11 families: `black`, `blue`, `brown`,
  `grey`, `green`, `orange`, `pink`, `purple`, `red`, `white`, `yellow`.
- Level two is the nearest of exactly 50 project-approved anchors in the
  palette CSV. Stable keys are machine-readable; Vietnamese labels are display
  copy.
- CIE76 distance and normalized softmax scores are deterministic heuristics,
  not calibrated probabilities.
- After the stable level-one family is selected, level-two scores are
  normalized across that family's allowed labels. `color_name_margin` is the
  highest such score minus the second-highest score. It passes the naming
  evidence gate at `>= 0.10`.
- Product output is `Không chắc chắn` when that margin is below `0.10` or the
  lighting level is `poor`. The nearest candidate remains available only in
  Diagnostic output for explainability.
- Poor lighting never changes the retained original corrected RGB/Lab value or
  level-one family; it only prevents a specific level-two label from being
  presented as reliable.

## 3. Frozen evaluation matrix

- 50 generated digital anchor cases, one per palette row.
- Three generated uncertainty-boundary cases: below margin, exact threshold,
  and poor lighting.
- 150 declared physical observations: each of the 50 labels under `neutral`,
  `warm`, and `low` lighting.
- Existing 54 non-T12 post-MVP cases are retained, giving 257 unique case IDs.

Digital anchor agreement proves implementation/registry consistency only. It
does not measure physical-camera accuracy. Missing physical captures must be
stored as `NOT_RUN` with a reason; they must never be synthesized or inferred.

## 4. Artifact and claim rules

The artifact, consent, license, privacy, checksum, raw-media, and Git tracking
rules from `evaluation/protocol-v2.md` apply unchanged. Curated JSON/CSV/Markdown
may be tracked. Raw photos/videos stay under ignored `artifacts/post_mvp/t12/`.
Every referenced artifact records provenance, consent classification, license,
byte size, and SHA-256. No `git add -f` bypass is permitted.

Changing any label, key, anchor, threshold, case ID, metric semantic, or
artifact rule requires another owner-approved revision.
