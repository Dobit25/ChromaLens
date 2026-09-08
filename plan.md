# ChromaLens AI — MVP Implementation Plan

Last updated: 2026-08-16  
Deadline: 2026-08-25  
Document role: Executable implementation plan and acceptance contract

## 1. Delivery objective

Build a reproducible laptop MVP that demonstrates this complete vertical slice:

```text
camera/video
→ AI garment mask
→ lighting correction and quality
→ original dominant color and name
→ selected CVD simulation
→ relational ΔE00 risk
→ selective assistive recolor
→ double outline + original-color tag + separate scores
→ optional rule-based clothing suggestion
```

The plan optimizes for a working two-minute competition demonstration by 24 August. Core implementation must not depend on work scheduled for 25 August.

## 2. Selected MVP stack

| Layer | Selected baseline | Upgrade/fallback policy |
| --- | --- | --- |
| Language | Python 3.10 | Change only for a proven dependency constraint. |
| Packaging/tests | `venv` or equivalent, pinned requirements, `pytest`, optional `ruff` | Keep installation reproducible on Windows. |
| Camera/video | OpenCV `VideoCapture` | Image and local video inputs are required for tests. No WebRTC in MVP. |
| Segmentation | Common `Segmenter` interface; MediaPipe clothes mask for fastest vertical slice | SCHP-ATR is the desired P1 backend for upper-clothes/pants/skirt/dress. Preserve MediaPipe as fallback. |
| Tracking/stability | Per-frame segmentation plus EMA/temporal hysteresis | Run segmentation every N frames and add optical flow only if profiling proves necessary. No ByteTrack/SAM 2. |
| Color constancy | OpenCV Gray-world white balance plus temporal EMA | Add clipping/quality guards; never claim true physical color recovery. |
| Color extraction | Eroded garment mask → CIELAB → robust median | Add deterministic K-means with `K=2` for simple multicolor garments after median path works. |
| Color naming | Van de Weijer 11 basic terms or a documented equivalent lookup | Vietnamese labels; retain raw Lab/RGB and best-vs-second margin. |
| CVD simulation | Machado via DaltonLens | Brettel may be a validation/reference option, not an MVP dependency. |
| Risk | CIEDE2000 before/after simulation | Compare retained garment clusters; P1 adds top-bottom and adjacent background. |
| Recolor | Selective LMS/daltonization or candidate-color optimization inside risk mask | Temporally stable LUT is a later optimization; never hard-code universal red→purple. |
| Outline/UI | OpenCV morphological gradient/contours, double black-white outline, custom overlay | UI starts as an OpenCV window; a web/mobile UI is out of scope. |
| Matching | CIELCH rule engine plus `assets/suggestions.csv` | Use original corrected colors only. Matching is after core assistive path. |
| Intel deployment | Correct PyTorch/MediaPipe baseline first | Export supported model to ONNX/OpenVINO only after output equivalence tests. |

Suggested dependency groups rather than one uncontrolled install:

- `base`: NumPy, OpenCV contrib, scientific/color utilities, pytest.
- `segment-mediapipe`: MediaPipe and its compatible dependency pins.
- `segment-schp`: PyTorch/Torchvision plus SCHP integration.
- `intel`: ONNX/OpenVINO tooling.

The agent must resolve and pin compatible versions in the actual environment. Do not place both `opencv-python` and `opencv-contrib-python` in the same environment unless a documented reason exists.

## 3. Repository target structure

```text
repository-root/
├── AGENTS.md
├── context.md
├── rubric.md
├── plan.md
├── knowledge_plan_discussion.md
├── codinglog.md
├── README.md
├── pyproject.toml or requirements files
├── src/
│   └── chromalens/
│       ├── __init__.py
│       ├── __main__.py
│       ├── app.py
│       ├── config.py
│       ├── contracts.py
│       ├── camera.py
│       ├── segmentation/
│       │   ├── base.py
│       │   ├── mediapipe_backend.py
│       │   └── schp_backend.py
│       ├── tracking.py
│       ├── white_balance.py
│       ├── color_extraction.py
│       ├── color_naming.py
│       ├── cvd_simulation.py
│       ├── risk_detection.py
│       ├── recolor.py
│       ├── matching.py
│       ├── renderer.py
│       ├── pipeline.py
│       └── metrics.py
├── assets/
│   ├── suggestions.csv
│   └── color_names/README.md
├── models/
│   └── README.md
├── tests/
│   ├── unit/
│   ├── integration/
│   └── samples/
├── evaluation/
│   ├── protocol.md
│   └── results/
└── scripts/
    ├── run_webcam.py
    ├── run_video.py
    └── benchmark.py
```

Weights and large evaluation media should not be committed blindly. `models/README.md` must state source, license, checksum if practical, download/setup steps, and expected path.

## 4. Cross-module contracts

Implement these as typed dataclasses or equivalent. Field names may be refined once, in Task T00, and then treated as stable interfaces.

```python
@dataclass
class FramePacket:
    frame_id: int
    timestamp_ns: int
    original_bgr: np.ndarray
    corrected_rgb: np.ndarray | None
    lighting_quality: "LightingQuality | None"

@dataclass
class GarmentRegion:
    track_id: int | None
    class_name: str
    mask: np.ndarray          # bool, H x W
    mask_confidence: float | None

@dataclass
class ColorCluster:
    lab: tuple[float, float, float]
    rgb: tuple[int, int, int]
    ratio: float
    submask: np.ndarray       # bool, H x W
    original_name: str
    name_scores: dict[str, float]
    color_margin: float | None

@dataclass
class RiskAssessment:
    source_id: str
    comparison_id: str
    delta_e_original: float
    delta_e_cvd: float
    risk_score: float
    risk_level: str
```

Contract rules:

- All masks align to the original frame dimensions.
- All public color conversions state the source/target space explicitly.
- `severity` is validated within `[0, 1]`.
- Original and assistive display colors are never stored in the same ambiguous field.
- Risk score and confidence are separate fields.
- Renderer receives data and produces a copied output frame; it does not change analytical results.

## 5. Task plan

### T00 — Repository bootstrap and contracts

Priority: P0  
Dependencies: none  
Time box: 0.5 day

Work:

- Place the six instruction files at repository root.
- Create package/test/script structure.
- Add reproducible environment files and `.gitignore`.
- Define configuration and cross-module dataclasses/interfaces.
- Add CLI help and placeholder backends that fail clearly.
- Create `README.md` with install/run placeholders that become executable by T08.

Definition of Done:

- Fresh environment installation command is documented.
- `python -m chromalens --help` or equivalent exits successfully.
- `pytest` discovers and passes at least one smoke test.
- No model or large binary is committed unintentionally.
- `codinglog.md` contains the T00 entry with commands and results.

### T01 — Camera, video source, and base renderer

Priority: P0  
Dependencies: T00  
Time box: 0.5 day

Work:

- Implement webcam and local-video sources behind one interface.
- Attach frame ID and monotonic timestamp.
- Display source name, resolution, and basic FPS/latency placeholder.
- Implement clean exit, camera-open error, and end-of-video behavior.
- Use a bounded/latest-frame design or a simple loop that cannot accumulate an unbounded queue.

Definition of Done:

- Webcam preview runs for two minutes and exits cleanly.
- Sample video mode runs without a camera.
- Failure to open the source produces an actionable error.
- Memory/queue does not grow because old frames are being retained.

### T02 — Garment segmentation vertical slice

Priority: P0 baseline, P1 SCHP  
Dependencies: T01  
Time box: 1 day

Work:

- Implement `Segmenter` interface returning `GarmentRegion`.
- First obtain an end-to-end clothes mask using MediaPipe or the fastest verified backend.
- Implement mask resize/alignment, thresholding, small-component cleanup, and confidence extraction where available.
- Add debug overlay.
- Attempt SCHP-ATR backend behind the same interface only after the baseline mask works.

Decision gate:

- If SCHP dependency/model integration is not producing a valid aligned mask within four focused hours, preserve logs, mark SCHP `PARTIAL`, and continue the vertical slice with MediaPipe. Return to SCHP only after T08.

Definition of Done:

- At least one AI backend returns a boolean `H × W` clothes mask aligned to webcam/video frames.
- Debug view visibly overlays the mask on at least five sample scenes.
- Backend name and device are exposed in the UI/log.
- A missing optional backend falls back or fails clearly; it does not crash with an unexplained stack trace.
- Source/license/setup of weights are documented.

### T03 — White balance and lighting quality

Priority: P0  
Dependencies: T01; consumes mask optionally  
Time box: 0.5 day

Work:

- Implement Gray-world white balance with configurable valid saturation/brightness range.
- Implement EMA for gains.
- Compute lighting diagnostics: dark fraction, clipped fraction, gain extremity, and temporal gain variation.
- Map diagnostics to `good`, `medium`, or `poor` plus raw values.

Definition of Done:

- Unit test shows a synthetic channel cast moves closer to neutral gray.
- Severity of clipping/darkness changes the lighting-quality output as expected.
- Consecutive gain estimates are smoothed and do not cause obvious frame flicker in a short video.
- The original frame remains unchanged.

### T04 — Dominant color extraction and 11-name mapping

Priority: P0 median, P1 K-means  
Dependencies: T02, T03  
Time box: 1 day

Work:

- Erode garment mask and exclude invalid dark/clipped/low-confidence pixels.
- Convert corrected image to a clearly documented Lab convention.
- Implement robust median as the P0 dominant-color estimator.
- Add deterministic `K=2` clustering and minimum-area filtering as P1.
- Implement/document 11-color lookup, Vietnamese labels, score distribution or nearest-prototype score, and best-vs-second margin.
- Record source/license for color-name data.

Definition of Done:

- Unit tests cover mask erosion, invalid-pixel rejection, median robustness, and deterministic clustering.
- A controlled set with all 11 basic color families produces an evaluation table, not anecdotal claims.
- Each retained cluster includes Lab/RGB, ratio, submask, name, scores, and margin.
- No background pixel is intentionally included after mask alignment/erosion in synthetic tests.

### T05 — CVD simulation and relational risk

Priority: P0  
Dependencies: T04  
Time box: 1 day

Work:

- Define profile enum and validated severity.
- Integrate/document Machado simulation through DaltonLens or a verified implementation.
- Ensure sRGB linearization/gamma handling follows the selected library.
- Implement CIEDE2000 comparison before and after simulation.
- Create a configurable risk heuristic and `low/medium/high` display levels.
- Compare retained clusters inside a garment for P0; add top-bottom/background comparisons as P1.

Definition of Done:

- Severity `0` is identity within numerical tolerance.
- All profiles run without channel-order errors on known color patches.
- Unit tests show a known confusing pair receives greater risk than a clearly separated control pair for at least one declared profile.
- Output records both Delta-E values and risk; it does not expose only an unexplained label.
- Thresholds are configuration values and documented as heuristics requiring user validation.

### T06 — Selective recolor, outline, and score overlay

Priority: P0  
Dependencies: T02, T04, T05  
Time box: 1 day

Work:

- Implement a documented LMS/daltonization or candidate-color transform.
- Apply it only to the intersection of garment, retained color cluster, and risk masks.
- Preserve lightness/texture as practical and alpha-feather mask edges.
- Add temporal smoothing/hysteresis for chosen display color.
- Draw a double black-white contour/morphological-gradient outline.
- Display original color, color confidence/margin, risk, lighting quality, profile, severity, and backend.

Definition of Done:

- Synthetic test verifies pixels outside the recolor mask remain unchanged before overlays.
- Original color and assistive display color are labeled separately in debug data.
- A static scene does not switch display color repeatedly over a short run.
- Tag remains readable on light and dark backgrounds.
- Simulation view is debug-only and is not mislabeled as the assistive result.

### T07 — Rule-based color matching

Priority: P1  
Dependencies: T04; improved by SCHP in T02  
Time box: 0.5 day

Work:

- Define `suggestions.csv` schema, provenance, and validation.
- Convert original corrected Lab to CIELCH.
- Implement a small deterministic rule engine for neutral, analogous, complementary, and tone-based suggestions.
- Generate a Vietnamese explanation and optional CVD-separation check.

Definition of Done:

- Unit tests cover at least neutral and chromatic examples.
- Suggestions are generated from original corrected colors only.
- Missing/unknown colors produce a safe explanation, not a crash or fabricated high confidence.
- Rules are explicitly described as guidance, not objective fashion truth.

### T08 — End-to-end live pipeline and controls

Priority: P0  
Dependencies: T01–T06; T07 optional  
Time box: 1 day

Work:

- Compose modules without duplicating conversions or mutating shared frames.
- Add profile/severity/recolor/debug controls.
- Use latest-frame or bounded queue behavior.
- Smooth analytical results at module boundaries.
- Add original, assistive, mask, risk, and diagnostic views as appropriate.
- Ensure webcam and local-video modes share the same pipeline.

Definition of Done:

- One command launches the webcam demo and another processes a sample video.
- End-to-end output shows a garment mask, original color, CVD risk, selective recolor when risk is triggered, outline, and separate scores.
- The user can change profile/severity and disable recoloring.
- Two-minute run has no continuously increasing lag or memory trend.
- A degraded/missing module is shown explicitly; stale results are not presented as current without indication.

### T09 — Evaluation, responsible AI, and evidence package

Priority: P0  
Dependencies: T08  
Time box: 1 day

Work:

- Freeze an evaluation protocol before reporting results.
- Build a small declared test matrix: all 11 basic colors, at least three lighting conditions, plain and simple multicolor garments, movement, and relevant CVD profiles.
- Measure color-name results, mask adequacy/IoU where annotation exists, risk sanity cases, processed FPS, latency p50/p95, and memory trend.
- Save representative intermediate artifacts.
- Document privacy, bias, limitations, failure cases, environmental consideration, licenses, and attribution.
- Add a non-AI/manual baseline explanation or small comparison for AI necessity.

Definition of Done:

- `evaluation/protocol.md` declares data, hardware, resolution, thresholds, and procedure.
- Machine-readable and human-readable results are saved.
- Performance values name backend/device and are not generalized beyond the test laptop.
- At least three failure examples and mitigations are documented.
- No unconsented personal footage is committed.

### T10 — SCHP/OpenVINO optimization gate

Priority: P1/stretch  
Dependencies: T08 baseline and T09 protocol  
Time box: 0.5–1 day maximum

Work:

- Return to SCHP-ATR if not completed in T02.
- Export only a supported stable model to ONNX/OpenVINO.
- Compare masks and performance against the saved baseline.
- Preserve the original backend and runtime selector.

Definition of Done:

- Conversion commands and versions are documented.
- At least a fixed sample set compares baseline and OpenVINO masks.
- Benchmark reports p50/p95 latency, FPS, precision, and exact Intel device.
- Optimization is accepted only if output remains adequate and startup/runtime is reliable.
- If conversion fails the time box, record it honestly and retain the working baseline.

### T11 — Competition handoff support

Priority: P0 for evidence, not new code  
Dependencies: T09  
Time box: 0.5 day

Work:

- Finalize README installation and one-command demo.
- Produce architecture graphic/source, screenshots, benchmark summary, licenses/credits, and known limitations.
- Prepare a two-minute demo shot list emphasizing user problem, live pipeline, AI necessity, impact, responsible AI, and measurements.
- Verify project name length, 150-word description, video length, consent, and live form requirements.

Definition of Done:

- A teammate unfamiliar with the code can install/run using README on the declared machine or a clean environment.
- Demo has a known offline fallback video if live camera conditions fail.
- All claims in the submission can be traced to code, a measured result, or a cited source.
- No core implementation remains scheduled for 25 August.

## 6. Calendar and cut line

| Date | Required outcome by end of day |
| --- | --- |
| 16 Aug | T00 complete; interfaces and scope frozen. |
| 17 Aug | T01–T02 baseline complete; live clothes mask visible. |
| 18 Aug | T03–T04 complete; corrected original color and name visible. |
| 19 Aug | T05 complete; profile simulation and relational risk tested. |
| 20 Aug | T06 complete; first full assistive vertical slice demonstrated. |
| 21 Aug | T07 optional and T08 integration complete. Feature freeze begins. |
| 22 Aug | T09 evaluation and failure analysis. |
| 23 Aug | T10 optimization only if baseline is safe; documentation. |
| 24 Aug | T11 video/form/package validation; no risky refactor. |
| 25 Aug | Submission and contingency only. |

Cut rules:

- If no full vertical slice exists by 20 August: drop matching, optical flow, SCHP retry, and OpenVINO optimization until the slice works.
- If the pipeline is unstable on 21 August: feature freeze immediately; fix only demo blockers and evidence gaps.
- After 23 August: no dependency upgrades, model swaps, broad refactors, or new UI framework.
- Always preserve a known-good tag/commit before optional optimization.

## 7. Minimum evaluation matrix

| Area | Minimum evidence |
| --- | --- |
| Color naming | Controlled samples spanning all 11 names; confusion matrix or per-class table. |
| Lighting | Same garments under at least daylight/neutral indoor/warm or low light; show quality warning and color stability. |
| Segmentation | At least 20 representative frames or several short clips; manual adequacy rating and IoU on any annotated subset. |
| CVD risk | Synthetic/reference color pairs for each profile; report both original and simulated ΔE00. |
| Recolor containment | Automated outside-mask invariance test before overlays. |
| Temporal behavior | Static and moving clips; color/transform switch count and visible flicker review. |
| Performance | p50/p95 capture-to-display latency, processed FPS, memory trend, resolution, backend, and exact device. |
| Usability | Short structured feedback from target users or accessibility stakeholders if obtainable ethically; otherwise label as not yet validated. |

## 8. Global Definition of Done

The MVP is complete only when all P0 tasks are `DONE`, all test/results evidence is stored, and the repository satisfies the Definition of Done in `AGENTS.md`. A visually appealing demo without evaluation and responsible-AI evidence is not complete; a technically sophisticated collection of modules without a stable end-to-end demo is also not complete.

## 9. Owner-approved post-MVP phase: T12-T17

Approval date: 2026-09-08
Status: Approved scope; implementation begins only after Post-MVP Gate 0 is
`DONE`.
Purpose: Incorporate the dated 09-17 September review feedback without
rewriting the completed T00-T11 MVP history or the frozen T09 protocol/results.

The T00-T11 plan and its August evidence remain historical. The following
tasks are an additive post-MVP phase. They preserve the modular local/offline
pipeline, original corrected color, user-selected non-diagnostic CVD profile,
separate risk/confidence/lighting concepts, bounded newest-frame processing,
and explicit MediaPipe fallback.

### Post-MVP Gate 0 — Scope and evaluation-contract freeze

Dependencies: T00-T11 `DONE`
Priority: Required before T12-T17 feature implementation

Work:

- Freeze protocol version 2.0.0, machine-readable result schema, metric
  registry, fixture IDs, artifact/consent/license/checksum rules, and file
  ownership.
- Record the current development-host benchmark baseline without describing it
  as demo-hardware or sensor-to-photon evidence.
- Keep `evaluation/protocol.md` and T09 schema/results frozen at 1.0.0; use
  separate v2 paths.
- Preserve unrelated local work and do not include it in the Gate commit.

Definition of Done:

- T12-T17 scope, dependency rules, and task DoD are recorded in this plan.
- Protocol, schema, metric registry, fixture registry, and ownership all state
  version 2.0.0 and pass automated cross-validation.
- A fresh current-product baseline records the exact host role, source,
  backend/device, resolution, duration, metric semantics, and target comparison.
- Every baseline artifact records provenance, consent/privacy classification,
  license, byte size, and SHA-256; raw media/traces stay ignored.
- Focused Gate tests and the complete existing test suite pass in the isolated
  Python 3.10 `lens` environment.
- No T12-T17 feature behavior is implemented by the Gate.

### T12 — Extended color vocabulary and uncertainty

Priority: Post-MVP product quality
Dependencies: Post-MVP Gate 0; T04
Can run in parallel with: T13, T14, T15 baseline instrumentation, and the
severity-only portion of T16

Work:

- Preserve the 11 basic color families as the stable level-one output.
- Add the frozen 29-label level-two vocabulary from protocol v2 using light,
  dark, and selected common shade names.
- Return an explicit `uncertain` state when naming evidence is below the frozen
  margin/lighting criteria instead of forcing a specific display label.
- Evaluate at least 30 declared physical samples under neutral, warm, and low
  lighting. The frozen registry treats this as 30 samples x 3 conditions = 90
  observations; unavailable captures remain `NOT_RUN`.

Definition of Done:

- Every output retains a level-one basic family; a confident output may also
  expose one allowed level-two label.
- Low-evidence cases display `Uncertain`/`Không chắc chắn` and do not present a
  forced label as reliable.
- The 29-label digital contract and uncertainty-boundary tests pass.
- All 90 physical observation IDs are reported with confusion/stability tables,
  including explicit `NOT_RUN` rows and failure causes.
- Naming scores/margins remain documented heuristics, not calibrated
  probabilities.

### T13 — Standalone-garment evaluation and manual ROI fallback

Priority: Post-MVP reliability
Dependencies: Post-MVP Gate 0; T02-T04
Can run in parallel with: T12, T14, and T15 instrumentation

Work:

- Evaluate exactly 20 frozen standalone products: tops, trousers, skirts,
  dresses, and coats across simple and complex backgrounds.
- Record mask quality, original corrected color result, and failure reason.
- If automatic human parsing does not return a usable standalone-garment mask,
  provide an explicit user-selected rectangular/polygonal ROI fallback.
- Do not replace the segmentation model or claim that manual selection is AI
  detection. ATR has no dedicated coat label; coat observations measure mask
  usefulness and may map visibly to `upper-clothes`.

Definition of Done:

- All 20 IDs have automatic-backend results or explicit `NOT_RUN` reasons,
  adequacy ratings, and color observations.
- Manual selection is optional, visibly labeled `manual selection`, bounded to
  the source frame, reversible, and never reported as automatic inference.
- Automated tests cover cancel/invalid/out-of-bounds selection and prove source
  frame immutability.
- Fixture provenance, consent, license, checksums, failures, and mitigations are
  recorded.

### T14 — Fullscreen and resolution-independent presentation

Priority: Post-MVP demo usability
Dependencies: Post-MVP Gate 0; completed T11 presentation compositor
Can run in parallel with: T12, T13, and T15 instrumentation after display
ownership is frozen

Work:

- Add a reversible windowed/fullscreen control with a visible keyboard escape
  path.
- Preserve camera aspect ratio with letterbox/pillarbox as needed and scale
  typography, labels, and outlines for the display canvas.
- Scale only presentation output; do not increase capture/model processing
  resolution implicitly.
- Test the frozen 1366x768 and 1920x1080 cases in Product and Diagnostic modes.

Definition of Done:

- Fullscreen toggles without restarting inference; `Esc` leaves fullscreen and
  `q` exits clearly.
- Viewport aspect-ratio error is within the frozen tolerance, processing
  resolution does not change, and no text/card overflow is detected.
- Product and Diagnostic modes pass offscreen tests at both required display
  resolutions and a manual GUI smoke test is recorded.
- Camera masks, color analysis, recolor containment, and source pixels are
  unchanged by presentation scaling.

### T15 — Bottleneck measurement and bounded performance optimization

Priority: Post-MVP performance
Dependencies: Post-MVP Gate 0; final acceptance benchmark runs after T12-T14
integration and any enabled T16 path
Can run in parallel with: T12-T14 during instrumentation/baseline only

Work:

- Instrument named pipeline stages before optimizing them.
- Preserve bounded newest-frame capture/inference, SCHP keyframes, optical-flow
  propagation, stale-mask clearing, and explicit mask provenance.
- Profile model input resolution/cadence, array copies, color analysis,
  renderer, compositor, and GUI submission. Optimize only measured bottlenecks.
- Do not promote the previously rejected INT8 model without a new representative
  calibration/equivalence gate.
- Run five-minute GUI and headless measurements with exact hardware/backend/
  resolution declarations.

Definition of Done:

- Per-stage timing identifies the dominant bottlenecks with reproducible raw
  evidence.
- Internal target on the declared test configuration is at least 20 processed
  frames/s and p95 `source_read_to_display_submit_ms <= 120 ms` for GUI, or p95
  `source_read_to_render_ms <= 120 ms` for headless.
- No continuously increasing software latency or RSS trend is detected during
  each 300-second measured interval; missed targets are reported, not hidden.
- `sensor_to_photon_ms` remains `NOT_MEASURED` without synchronized external
  apparatus.
- Mask fidelity, semantic labels, recolor containment, and fallback reliability
  remain at or above their pre-optimization gates.

### T16 — Severity coverage and experimental spatial gradient risk

Priority: Severity support required; spatial gradient risk experimental
Dependencies: Post-MVP Gate 0; T05-T06. T12 is optional for the algorithm but
required before final Product-copy integration.
Can run in parallel with: T12-T15 while isolated behind configuration

Work:

- Keep CVD profile and severity user-selected and explicitly non-diagnostic.
- Evaluate severity values 0.00, 0.25, 0.50, 0.75, and 1.00 for protan, deutan,
  and tritan using frozen sanity fixtures.
- Expose understandable support-intensity presets in Product mode while keeping
  the exact numeric severity in Diagnostic mode.
- Prototype a tiled/region-based CIELAB spatial risk map inside the garment
  mask for large gradients, with zero risk pixels outside that mask.
- Keep spatial gradient risk behind an explicit experimental flag unless its
  frozen validation gate passes.

Definition of Done:

- Severity 0 remains identity and all 15 profile/severity contract cases store
  Delta-E00/risk/recolor behavior without medical claims.
- Severity presets map exactly and reversibly to documented numeric values.
- Protan, deutan, and tritan each have a large-gradient evaluation row.
- Spatial-risk output is aligned to the source mask, bounded to `[0,1]`, and
  zero outside the garment; performance cost is measured.
- If the experimental quality/performance gate fails, severity support ships
  independently and gradient risk remains disabled and labeled experimental.

### T17 — Integration, release gate, and demo freeze

Priority: Required final task
Dependencies: T12-T16 have terminal statuses (`DONE`, or owner-accepted
`PARTIAL`/`DEFERRED` with explicit claim cuts)
Can run in parallel with: none

Work:

- Integrate only validated T12-T16 outputs into one stable Product/Diagnostic
  application.
- Run all existing tests (302 collected at Gate start) plus every new test; the
  exact collected count replaces the stale feedback reference to 193 tests.
- Exercise webcam, deterministic video, fullscreen at both required display
  sizes, standalone and multicolor garments, severity, privacy defaults, and a
  five-minute performance/stability session.
- Record all failures, licenses, consent/provenance, limitations, and release
  claims. Freeze features after acceptance; fixes after freeze are limited to
  release blockers.

Definition of Done:

- All automated tests pass, or each failure has explicit owner acceptance and
  a corresponding claim cut; no test is silently skipped to obtain green CI.
- Required manual/demo checks and schema-valid machine/human-readable results
  are stored with checksums and exact commands.
- Camera frames remain local and unsaved by default; no private/raw/bulk media
  is tracked.
- README, architecture, attribution, limitations, benchmark summary, and demo
  commands match the release behavior.
- A known-good release commit/tag is identified and no core implementation
  remains after feature freeze.

## 10. Post-MVP dependency and integration order

```text
Post-MVP Gate 0
  +-- T12 extended naming -----------+
  +-- T13 standalone garments -------+
  +-- T14 fullscreen ----------------+--> T15 final benchmark --+
  +-- T15 instrumentation/baseline --+                         |
  +-- T16 severity/experimental gradient ----------------------+--> T17
```

T12-T16 may be developed in parallel only within the ownership map frozen by
protocol v2. Coordinator-owned integration surfaces (`app.py`, `pipeline.py`,
`presentation.py`, configuration/contracts, dependencies, CI, plan, and coding
log) are merged deliberately. T15's final acceptance benchmark is rerun after
the integrated feature set; T17 is always last.
