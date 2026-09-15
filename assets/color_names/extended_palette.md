# ChromaLens 50-anchor palette

Protocol version: `2.1.0`
Status: `FROZEN` for T12

The CSV contains the owner-approved Vietnamese display vocabulary. RGB values
are W3C CSS named-color anchors; family grouping, stable keys, and Vietnamese
display labels are project-authored mappings. They are deterministic reference
points, not a trained classifier and not evidence of camera accuracy.

The 50 contributor labels and RGB anchors are preserved. Level-one ownership
is assigned by the frozen T04 11-family classifier, so nine boundary anchors
belong to a different stable family than in the contributor prototype. This
prevents T12 from silently changing historical T04/T09 level-one behavior.

`ash_grey` uses CSS `silver` bytes `(192, 192, 192)` while the project display
label is `Xám tro`; `silver` uses CSS `darkgray` bytes `(169, 169, 169)` while
the display label is `Bạc`. The explicit `css_anchor_name` column records this
provenance without pretending those Vietnamese labels are literal W3C names.

Do not change a key, label, family, or RGB value without an owner-approved
protocol revision and replacement contract tests.
