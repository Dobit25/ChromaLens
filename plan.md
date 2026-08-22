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
