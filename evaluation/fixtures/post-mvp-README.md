# Post-MVP Fixture Registry

Protocol version: `2.0.0`
Registry: `post-mvp-cases.csv`
Status: `FROZEN`

The registry contains 176 unique case IDs:

- 29 extended-color digital contracts;
- three explicit uncertainty-boundary contracts;
- 90 physical observations: 30 samples x neutral/warm/low lighting;
- 20 standalone garments: five garment types x two backgrounds x two variants;
- four fullscreen/presentation cases;
- one fresh Gate 0 performance-baseline snapshot;
- four final 300-second backend/mode performance cases;
- 15 severity cases and three experimental large-gradient cases;
- seven integrated T17 release cases.

`TO_BE_ACQUIRED` means the exact consented/licensed/checksummed input does not
exist at Gate 0. It cannot be treated as tested. `GENERATED_AT_RUN` requires a
deterministic construction or an explicitly recorded runtime capture.
`AVAILABLE_IGNORED` identifies a local asset that remains outside Git.

The semicolon-separated `required_metrics` values must exist in
`evaluation/schema/post-mvp-metric-registry.json`. Case IDs, task IDs, expected
observations, and ownership are normative. Changing them requires a protocol
revision; adding an easier replacement case under the same ID is prohibited.

Physical color label references are evaluation targets, not a claim that a
camera recovers physical color in every environment. Standalone coat cases do
not imply that ATR has a coat class. Manual selection results must remain
separate from automatic inference results.
