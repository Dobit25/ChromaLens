# T07 rule-based color matching

`assets/suggestions.csv` is the data source for the deterministic T07
matching engine. The table and its Vietnamese explanations are authored by
the ChromaLens project under the repository's Apache-2.0 license. It does not
copy a fashion dataset or claim to encode objective taste.

## Schema

The loader requires the exact header order below and rejects missing columns,
invalid enums, non-finite or out-of-range numbers, duplicate rule IDs, empty
Vietnamese reasons/provenance, incompatible transformations, and missing
neutral/chromatic relationship coverage.

| Column | Meaning |
| --- | --- |
| `rule_id` | Unique lowercase ASCII slug. |
| `source_kind` | `neutral` or `chromatic`, decided from original corrected CIELCH chroma. |
| `harmony` | `neutral`, `analogous`, `complementary`, or `tone`. |
| `priority` | Deterministic presentation order only; never confidence. |
| `min_source_lightness`, `max_source_lightness` | Inclusive original L* applicability bounds. |
| `hue_offset_degrees` | Signed CIELCH hue rotation. |
| `lightness_strategy` | `neutral-contrast`, `preserve`, or `contrast-tone`. |
| `chroma_scale` | Scale applied to original CIELCH C*. |
| `reason_vi` | Vietnamese explanation fragment displayed with the suggestion. |
| `provenance` | Per-row origin required for auditability. |

The committed v1 rules use an opposite black/white neutral, a +30-degree
analogous rotation, a 180-degree complementary rotation, and a lighter/darker
same-hue tone. All generated colors are converted to displayable 8-bit sRGB
and then measured again after gamut clipping.

## Source and safety contract

`RuleBasedMatcher.suggest_from_original_cluster` accepts only T04's
`ColorCluster`. Its Lab/RGB fields represent the original corrected garment
color and are repeated in every suggestion for auditability. T06 assistive
display colors have no input field and must never be substituted.

An optional user-selected CVD profile/severity adds original and simulated
CIEDE2000 source-target separation. The default Delta-E threshold is an
uncalibrated heuristic for T09 evaluation, not a diagnosis, confidence,
accessibility guarantee, or universal safety threshold.

Missing input and names outside T04's documented 11-family vocabulary return
an empty result with a Vietnamese explanation. They never crash or invent a
high-confidence recommendation.

Every UI consumer must keep this notice visible with the result:

> Đây là gợi ý tham khảo, không phải quy tắc thời trang khách quan.

## Limitations

- CIELCH hue geometry is a simple explainable approximation, not a model of
  culture, context, material, trend, or individual preference.
- sRGB gamut clipping can alter requested lightness, chroma, and hue.
- The 11-name vocabulary and upstream camera/lighting/segmentation limitations
  directly limit the quality of the output.
- Rule wording, thresholds, and perceived usefulness require T09 user testing.
