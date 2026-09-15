# T14 Fullscreen and Resolution-Independent Presentation

Status: `COMPLETE`

Protocol/schema/metric registry: `2.0.0`

Implementation commit under evaluation: `c4cd008b7d9e22fdce146d5a995d6eb07f0a681e`

T14 adds a reversible OpenCV fullscreen boundary around the existing
presentation compositor. It scales only the completed canvas, so the frozen
640x360 analytical source, SCHP input, masks, colors, risk, and recolor outputs
are not recomputed or resized when the window state changes.

## Frozen cases

| Case | Mode/theme | Display | Aspect error | Processing changed | Overflow | Result |
| --- | --- | ---: | ---: | --- | ---: | --- |
| PM-FULLSCREEN-1366X768-PRODUCT | Product/dark | 1366x768 | 0.0022007 | false | 0 | PASS |
| PM-FULLSCREEN-1366X768-DIAGNOSTIC | Diagnostic/light | 1366x768 | 0.0022007 | false | 0 | PASS |
| PM-FULLSCREEN-1920X1080-PRODUCT | Product/light | 1920x1080 | 0.0006250 | false | 0 | PASS |
| PM-FULLSCREEN-1920X1080-DIAGNOSTIC | Diagnostic/dark | 1920x1080 | 0.0006250 | false | 0 | PASS |

The worst viewport aspect-ratio error is `0.0022007`, below the frozen
`0.005` maximum. A real development-host OpenCV window completed
windowed/fullscreen/windowed transitions and reported the requested
`WND_PROP_FULLSCREEN` states. Deterministic integration coverage confirms
`f`, `Esc`, and `q` operate across three frames with one pipeline and one
segmenter instance.

## Controls and evidence

- Start fullscreen with `python -m chromalens --webcam --fullscreen`.
- Press `f` to toggle fullscreen without restarting inference.
- Press `Esc` to leave fullscreen; press `q` to exit.
- Regenerate ignored raw JSON/PNGs with
  `python scripts/t14_display_evaluation.py --gui-smoke --gui-hold-seconds 0.4`.
- Strict machine-readable values, provenance, consent, license, byte sizes,
  checksums, and limitations are in `result.json`.

This is display correctness evidence on the development host. It is not a
latency/FPS result, not segmentation evidence, and not a declaration of final
demo hardware. Sensor-to-photon latency remains `NOT_MEASURED`.
