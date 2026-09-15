# Post-MVP Fixture Registry 2.1

Protocol version: `2.1.0`
Registry: `post-mvp-cases-v2.1.csv`
Status: `FROZEN`

The registry contains 257 unique case IDs: 203 T12 cases (50 digital anchors,
three uncertainty boundaries, and 150 physical observations) plus the 54
unchanged non-T12 cases carried forward from protocol 2.0.0.

Each physical palette label has exactly one observation for each `neutral`,
`warm`, and `low` lighting condition. `TO_BE_ACQUIRED` means the consented,
licensed, checksummed physical input is unavailable and therefore must be
reported as `NOT_RUN`, never treated as a pass.

The palette keys and expected labels are normative. Digital fixtures are
deterministic implementation contracts, not physical-camera accuracy evidence.
