# ChromaLens AI

ChromaLens AI is a local, explainable color-vision assistance prototype for
clothing. **T01** (webcam/video preview), the locked **T02** MediaPipe torso-
mask baseline, **T03** lighting correction, **T04** original-color
extraction/naming, **T05** CVD simulation/relational risk, **T06** selective
assistive recoloring/overlay, **T07** rule-based color matching, and **T08**
end-to-end live composition/controls are complete. **T09** evaluation is also
complete within its explicitly accepted evidence limitations. The repository
owner later reopened **T10**: the exact ATR checkpoint was acquired and
verified, a strict-load semantic SCHP backend was implemented, and an FP32
OpenVINO CPU conversion passed fixed-fixture equivalence gates. SCHP-ATR is now
the primary demo backend; the locked MediaPipe baseline remains an explicit
fallback. **T11** packages the competition handoff, reproducible offline
fallback, claims, credits, and demo shot list.

The MVP is assistive software, not a medical diagnosis tool. The user selects
their CVD profile and severity.

## Requirements

- Windows development environment used by the project.
- Conda.
- The committed Conda and pip lock files under `requirements/`.

Do not install project dependencies into the Anaconda base environment.

## Locked collaboration environment

All contributors and coding agents must create `lens` from the committed
Windows/Python 3.10 baseline. Do not use `pip freeze` as a replacement for the
lock file and do not install unrecorded packages manually.

From the repository root:

```powershell
conda create --name lens --file requirements/conda-win-64.lock
conda run --name lens python -m pip install --require-hashes --requirement requirements/segment-schp-py310-win64.lock
conda run --name lens python -m pip install --no-build-isolation --no-deps --editable ".[dev,segment-mediapipe,segment-schp]"
```

The explicit Conda lock pins every bootstrap artifact, build, URL, and MD5,
including Python 3.10.20 and pip 26.1.2. `environment.yml` is the concise,
human-readable declaration of the supported interpreter and bootstrap tools.
The combined hashed demo lock pins every approved base/development package,
the MediaPipe fallback, and the PyTorch/OpenVINO SCHP toolchain. The final
command installs only the local ChromaLens package; dependency resolution is
deliberately disabled. Model weights and generated IR are verified separately
and remain outside Git.

If `lens` already exists and matches the Conda lock, re-run the two pip
commands to apply the committed lock. Recreate the environment if Python,
pip, or any Conda package build differs from the lock.

Verify the environment:

```powershell
conda run --name lens python --version
conda run --name lens python -m pip check
conda run --name lens python -m chromalens --help
conda run --name lens python -m pytest -q
```

For a teammate starting from a fresh clone, the three install commands above
are the canonical package setup. Stage and export the ignored ATR model using
the T10 procedure below before the primary one-command live demo:

```powershell
conda run --name lens python -m chromalens --webcam
```

If the venue camera or lighting is unreliable, generate and run the licensed
offline fallback without a network or webcam:

```powershell
conda run --name lens python scripts/t11_prepare_handoff.py
conda run --name lens python -m chromalens --video artifacts/t11-handoff/fallback_mediapipe.avi
```

The generated video, screenshots, and checksum/provenance manifest remain
under ignored `artifacts/t11-handoff/`; they must not be forced into Git.

## Dependency change policy

`pyproject.toml` is the source of direct dependency intent. The lock file is
the source of the exact resolved install. Both must change in the same owner-
reviewed dependency commit.

Only the integration owner regenerates the shared lock. After an approved
direct dependency change:

```powershell
conda run --name lens python -m pip install --editable ".[lock]"
conda run --name lens pip-compile pyproject.toml --extra dev --generate-hashes --allow-unsafe --resolver backtracking --strip-extras --no-emit-index-url --no-emit-trusted-host --output-file requirements/py310-win64.lock
conda run --name lens pip-compile pyproject.toml --extra lock --generate-hashes --allow-unsafe --resolver backtracking --strip-extras --no-emit-index-url --no-emit-trusted-host --output-file requirements/lock-tools-py310-win64.lock
conda run --name lens pip-compile pyproject.toml --extra dev --extra segment-mediapipe --generate-hashes --allow-unsafe --resolver backtracking --strip-extras --no-emit-index-url --no-emit-trusted-host --output-file requirements/segment-mediapipe-py310-win64.lock
conda run --name lens pip-compile pyproject.toml --extra dev --extra segment-mediapipe --extra segment-schp --generate-hashes --allow-unsafe --resolver backtracking --strip-extras --no-emit-index-url --no-emit-trusted-host --output-file requirements/segment-schp-py310-win64.lock
conda list --explicit --md5 --name lens
```

Review the final command's output and save it as
`requirements/conda-win-64.lock`; never overwrite the committed lock without
reviewing every artifact URL, build, and checksum. Then repeat the locked
install and all verification commands. Task branches must not independently choose MediaPipe, DaltonLens, PyTorch,
SCHP, ONNX, or OpenVINO versions. Those dependencies are added to explicit
optional groups and the integration lock only when their owning task reaches
its dependency gate.

## Garment segmentation (T02)

Install the complete, hashed MediaPipe dependency closure before running
segmentation. Do not resolve the optional group directly:

```powershell
conda run --name lens python -m pip install --require-hashes --requirement requirements/segment-mediapipe-py310-win64.lock
conda run --name lens python -m pip install --no-build-isolation --no-deps --editable ".[dev,segment-mediapipe]"
```

This installs `mediapipe==0.10.21` and every transitive dependency at the
committed hashes. Model assets are bundled inside the MediaPipe wheel; no
manual download is required. See `models/README.md` for source, license
(Apache-2.0), and the deferred SCHP-ATR decision.

```python
from chromalens.segmentation import MediaPipeSegmenter

with MediaPipeSegmenter() as seg:
    regions = seg.segment(packet)   # returns tuple[GarmentRegion, ...]
```

Each `GarmentRegion` carries a boolean `H × W` mask, `class_name`, and
`mask_confidence`. Here confidence is the mean MediaPipe person-foreground
score inside the retained mask; it is a heuristic, not a calibrated garment
probability. The debug overlay draws mask fills and a text panel
onto a copy of the source frame:

```python
from chromalens.segmentation import draw_mask_overlay

debug_frame = draw_mask_overlay(
    packet.original_bgr, regions, backend_info=seg.device_info
)
```

Reproduce the five-scene, real-runtime evidence without a camera or network:

```powershell
conda run --name lens python scripts/t02_segmentation_evidence.py
```

The command writes five reviewable overlays plus `evidence.json` under the
ignored `artifacts/t02-segmentation/` directory. Fixture provenance, rights,
and checksums are recorded in `tests/samples/t02/README.md`.

## White balance and lighting quality (T03)

`GrayWorldWhiteBalancer` accepts an OpenCV `uint8 H × W × 3` BGR frame and
returns a new RGB frame. It estimates bounded Gray-world gains from pixels in
the configured brightness/saturation range, then applies per-stream EMA to
the gains. An optional aligned boolean mask may restrict only the estimation
region; correction and whole-frame lighting diagnostics remain global.

```python
from chromalens.white_balance import GrayWorldWhiteBalancer

white_balancer = GrayWorldWhiteBalancer()
result = white_balancer.process(packet, estimation_mask=garment_mask)

# packet.original_bgr is unchanged
corrected_rgb = packet.corrected_rgb
quality = packet.lighting_quality
```

Use one balancer instance per ordered camera/video stream and call `reset()`
before reusing it for an unrelated stream. `WhiteBalanceResult` exposes raw
and EMA-smoothed BGR gains, the valid-pixel fraction, and fallback use. If too
few eligible pixels exist, correction uses the previous gain (or identity for
the first frame) and reports `poor`; it never reports a fabricated successful
estimate.

The `good`/`medium`/`poor` label is a configurable heuristic over dark-pixel
fraction, highlight-clipped fraction, gain extremity, and temporal gain
variation. Raw values remain available in `LightingQuality`; the label is not
a calibrated probability or color-confidence score. Gray-world reduces a
global channel cast under its neutral-scene assumption, but does not recover
physical ground-truth garment color under arbitrary or mixed illumination.

Reproduce the deterministic T03 evidence without a camera, network, model, or
special hardware:

```powershell
conda run --name lens python scripts/t03_lighting_evidence.py
conda run --name lens python -m pytest -q tests/unit/test_t03_white_balance.py
```

The evidence command writes a before/after comparison and raw JSON metrics to
the ignored `artifacts/t03-lighting/` directory.

## Dominant original color and naming (T04)

`DominantColorExtractor` consumes only `FramePacket.corrected_rgb` from T03
and an aligned `GarmentRegion` from T02. It erodes the garment boundary,
rejects dark/highlight-clipped pixels, and optionally rejects pixels using an
aligned floating-point confidence map. The P0 path returns a robust median;
the P1 path returns up to two locally seeded deterministic K-means clusters
and filters clusters below the configured minimum area.

```python
from chromalens.color_extraction import (
    ColorExtractionMode,
    DominantColorExtractor,
)

extractor = DominantColorExtractor()
median_cluster = extractor.extract(packet, garment)[0]
two_colors = extractor.extract(
    packet,
    garment,
    mode=ColorExtractionMode.KMEANS_2,
)
```

Every retained `ColorCluster` includes conventional float CIELAB, displayable
original sRGB, ratio relative to all valid garment pixels, an aligned boolean
submask, canonical English name, all 11 normalized name scores, and the
best-versus-second score margin. Ratios of retained K-means clusters may sum to
less than one when a small cluster is deliberately filtered; they are not
renormalized to hide discarded area.

The supported terms are `black`, `blue`, `brown`, `grey`, `green`, `orange`,
`pink`, `purple`, `red`, `white`, and `yellow`, with explicit Vietnamese
labels. The vocabulary, W3C CSS sRGB anchor provenance/license, OpenCV float
Lab convention, and limitations are documented in
[`assets/color_names/README.md`](assets/color_names/README.md). Name scores and
margin are transparent heuristics, not calibrated probabilities.

Reproduce the controlled 11-family table and visual cluster evidence offline:

```powershell
conda run --name lens python scripts/t04_color_evidence.py
conda run --name lens python -m pytest -q tests/unit/test_t04_color_naming.py tests/unit/test_t04_color_extraction.py
```

The script writes `basic11_evaluation.csv`, `evidence.json`, a swatch grid,
and a synthetic two-cluster overlay under ignored `artifacts/t04-color/`.

## CVD simulation and relational risk (T05)

`MachadoSimulator` accepts and returns `uint8 H x W x 3` gamma-encoded sRGB
in explicit **RGB** order. It maps the existing user-selected `CVDProfile` to
DaltonLens's Machado 2009 implementation. For non-zero severity, pinned
`daltonlens==0.1.5` performs sRGB decoding to linear RGB, the Machado transform,
gamut clipping, and sRGB encoding. Severity zero returns a byte-identical copy
without mutating or aliasing the input.

```python
from chromalens.config import CVDProfile
from chromalens.cvd_simulation import MachadoSimulator

simulator = MachadoSimulator()
simulated_rgb = simulator.simulate_rgb(
    corrected_rgb,
    profile=CVDProfile.DEUTAN,
    severity=0.8,
)
```

`RelationalRiskDetector` uses original corrected cluster RGB values only. It
computes CIEDE2000 before and after the selected simulation, retains both
distances, derives a numeric heuristic score, and maps the score to
`low`/`medium`/`high`. T05 P0 evaluates every unordered retained-color pair
inside one garment; it returns an empty tuple for fewer than two clusters and
does not fabricate top-bottom/background comparisons.

```python
from chromalens.risk_detection import RelationalRiskDetector

assessments = RelationalRiskDetector().assess_cluster_pairs(
    clusters,
    garment_id="track-4:upper-clothes",
    profile=CVDProfile.DEUTAN,
    severity=0.8,
)
```

The default heuristic uses `minimum_original_delta_e=5.0`,
`cvd_confusion_delta_e=20.0`, `medium_score_threshold=0.25`, and
`high_score_threshold=0.60`. These are validated configuration values, not
probabilities, medical thresholds, or universal perceptual truth. Formula,
papers, DaltonLens version/tag/license, gamma behavior, and limitations are
documented in [`assets/cvd/README.md`](assets/cvd/README.md); T09 must validate
the thresholds with declared conditions and users before competition claims.

Reproduce known-patch simulation and pair-risk evidence offline:

```powershell
conda run --name lens python scripts/t05_cvd_risk_evidence.py
conda run --name lens python -m pytest -q tests/unit/test_t05_cvd_simulation.py tests/unit/test_t05_risk_detection.py
```

The evidence script writes `known_patch_simulation.png`,
`pair_risk_evaluation.csv`, and `evidence.json` under the ignored
`artifacts/t05-cvd-risk/` directory. Simulation is an internal risk/debug view,
not the assistive recolored output that belongs to T06.

## Selective recolor and score overlay (T06)

`SelectiveRecolorer` consumes the unchanged camera/display BGR frame, one T04
original corrected cluster, its T05 relational assessment and comparison
color, plus explicit aligned garment/cluster/risk masks. Its hard mask is
exactly the three-way intersection. An inward distance-transform feather has
zero alpha outside that mask, so every outside pixel remains byte-identical
before outlines and text are added.

The project-authored candidate optimizer rotates/scales the original CIELCH
chroma while keeping representative lightness fixed, simulates each candidate
for the selected profile/severity, maximizes simulated CIEDE2000 separation,
and penalizes unnecessary departure from the original. It applies no universal
source-to-target color rule. Per-key selection uses three-frame hysteresis and
a 32-entry LRU bound by default.

```python
from chromalens.recolor import SelectiveRecolorer

result = SelectiveRecolorer().recolor(
    packet.original_bgr,
    garment_mask=region.mask,
    cluster=source_cluster,
    risk_mask=source_cluster.submask,
    comparison_rgb=comparison_cluster.rgb,
    risk=risk,
    profile=CVDProfile.DEUTAN,
    severity=1.0,
    state_key="video:track-4:cluster-red",
)
```

`result.debug.original_corrected_rgb` and
`result.debug.assistive_display_rgb` are deliberately separate. The first is
the T04 estimate used for analysis; the second is a representative display
target and must never feed color extraction or T07 matching.

`render_assistive_overlay` draws a thick black then thin white contour and an
opaque black/white score tag onto a copy. `AssistiveOverlayData` keeps original
color/margin, display color, risk, lighting quality, profile, severity, backend,
and frame ID explicit. `render_assistive_overlay` rejects simulation view data;
the separate `render_cvd_simulation_debug_overlay` requires
`OverlayView.CVD_SIMULATION_DEBUG`, emits `CVD SIMULATION (DEBUG ONLY)`, and
labels the assistive target as separate. The declared simulation path therefore
cannot silently masquerade as the assistive result.

Reproduce the controlled containment, lightness, temporal, label, contour, and
light/dark tag evidence offline:

```powershell
conda run --name lens python scripts/t06_recolor_overlay_evidence.py
conda run --name lens python -m pytest -q tests/unit/test_t06_recolor.py tests/unit/test_t06_renderer.py tests/integration/test_t06_assistive_slice.py
```

The command writes ignored PNG/JSON output under
`artifacts/t06-recolor-overlay/`. Algorithm details, defaults, RGB/BGR
boundaries, font behavior, and limitations are documented in
[`assets/recolor/README.md`](assets/recolor/README.md).

## Rule-based color matching (T07)

`RuleBasedMatcher` converts only T04's original corrected Lab value to CIELCH
and applies the validated project-authored table in `assets/suggestions.csv`.
Neutral sources receive an opposite black/white suggestion. Chromatic sources
receive neutral, +30-degree analogous, 180-degree complementary, and
lighter/darker same-hue tone guidance in deterministic priority order.

```python
from chromalens.matching import RuleBasedMatcher

matcher = RuleBasedMatcher()
matching = matcher.suggest_from_original_cluster(
    source_cluster,
    profile=CVDProfile.DEUTAN,  # optional together with severity
    severity=1.0,
)
```

The method accepts `ColorCluster` or `None`; it has no assistive-display-color
parameter. Every suggestion echoes `source_original_lab` and
`source_original_rgb` from the T04 cluster. Missing input or an unknown name
returns an empty typed result with a safe Vietnamese explanation and never
invents confidence. `priority` is presentation order, not confidence.

When profile and severity are supplied together, each item includes original
and CVD-simulated CIEDE2000 source-target separation plus a configurable
heuristic threshold check. This is informational guidance, not a diagnosis,
accessibility guarantee, or calibrated probability. Every consumer must show:
"Đây là gợi ý tham khảo, không phải quy tắc thời trang khách quan."

Reproduce the controlled rule, fallback, source-contract, CVD-check, and
swatch evidence offline:

```powershell
conda run --name lens python scripts/t07_matching_evidence.py
conda run --name lens python -m pytest -q tests/unit/test_t07_matching.py tests/integration/test_t07_original_color_contract.py
```

The command writes ignored CSV/JSON/PNG output under
`artifacts/t07-matching/`. The exact schema, provenance, formulas, safety
contract, and limitations are documented in
[`assets/matching/README.md`](assets/matching/README.md).

## End-to-end webcam/video pipeline (T08)

The full default source path uses semantic `schp-atr` on CPU and prefers its
verified OpenVINO IR. For a webcam, one bounded worker produces authoritative
SCHP keyframes while optical flow aligns the newest accepted masks with current
display frames; T03-T07 then operate on those current-frame-aligned masks.
Finite videos remain synchronous and run SCHP on every ordered frame so saved
evaluation semantics do not change. Install
the combined lock and prepare the ignored model assets under **T10
SCHP/OpenVINO gate outcome** before using these commands. The earlier
MediaPipe person-derived torso backend remains selectable explicitly.

Launch the webcam demo using the default camera index:

```powershell
conda run --name lens python -m chromalens --webcam
```

The default `--ui-mode product` opens the user-facing Vietnamese presentation.
The camera viewport contains only the camera image, assistive recolor, and
garment outline. The header, result cards, and controls are composed on a
larger canvas outside that viewport, so status text never obscures the garment.
The camera pixels are not resized by the presentation layer and retain their
original aspect ratio.

For development, benchmark review, or a technical judging walkthrough, switch
to the separate presentation mode without changing the analytical pipeline:

```powershell
conda run --name lens python -m chromalens --webcam --ui-mode diagnostic
```

Choose the high-contrast background/card theme at launch, or press `t` while
the window is open:

```powershell
conda run --name lens python -m chromalens --webcam --theme dark
conda run --name lens python -m chromalens --webcam --theme light
```

Dark theme uses a dark shell with near-white information cards and dark card
text. Light theme uses a near-white shell with dark-grey information cards and
light card text. Header/footer text has a separate palette so both themes keep
strong contrast without changing camera, mask, colour, risk, or recolor data.

The Product UI shows only the named garment colour and swatch, a textual colour
confidence, an actionable distinguishability state, lighting guidance, matching
guidance, the selected CVD profile, and whether assistive recoloring is active.
Its cyan camera frame establishes the live image as the focal point; the main
colour card receives the strongest accent, secondary cards use quieter
surfaces, and the footer groups camera/AI/detection/assistance into a textual
status bar. Cards are informational and deliberately do not imitate clickable
controls.
The Diagnostic UI additionally shows backend/device, pipeline and SCHP
inference FPS, keyframe/propagation state, pre-render frame age, capture and
inference drops, raw RGB/margin, mask confidence, risk score, frame ID, and the
current degraded reason. Status is always expressed in text and card shapes;
colour is never the only carrier of meaning.

The webcam command requests the measured demo mode `480x360`; OpenCV/camera
drivers may select the nearest supported mode (the development camera returned
`640x360`). This changes only capture/output cost: SCHP preprocessing remains
the verified 512x512 graph.

Request a capture resolution or choose another camera when required:

```powershell
conda run --name lens python -m chromalens --webcam --camera-index 1 --width 1280 --height 720
```

Process a local sample video through the same analytical and rendering path
without opening a camera:

```powershell
conda run --name lens python -m chromalens --video C:\path\to\sample.mp4
```

Select a runtime or the fallback explicitly when diagnosing a venue machine:

```powershell
conda run --name lens python -m chromalens --webcam --schp-runtime openvino
conda run --name lens python -m chromalens --webcam --schp-runtime openvino --schp-live-mode sync
conda run --name lens python -m chromalens --webcam --schp-runtime pytorch
conda run --name lens python -m chromalens --webcam --backend mediapipe-selfie-torso
```

Press `q`, Escape, or close the window to exit. Automated/headless checks can
avoid GUI and bound execution explicitly:

```powershell
conda run --name lens python -m chromalens --video C:\path\to\sample.mp4 --no-display
conda run --name lens python -m chromalens --webcam --no-display --max-frames 120
conda run --name lens python -m chromalens --webcam --duration-seconds 120
```

Runtime controls are reversible and remain user-selected settings, not a
medical diagnosis:

- `p`: cycle `protan` / `deutan` / `tritan`.
- `[` and `]`: decrease/increase severity by 0.1 within `[0, 1]`.
- `r`: enable or disable assistive recoloring without disabling analysis.
- `t`: switch the presentation palette between `dark` and `light`.
- `u`: switch the presentation shell between `product` and `diagnostic`.
- `v`: cycle views; keys `1`-`5` select `assistive`, `original`, `mask`,
  `risk`, and `diagnostic` directly.

The equivalent initial values are available as CLI flags, for example:

```powershell
conda run --name lens python -m chromalens --webcam --profile protan --severity 0.8 --disable-recolor --view original --ui-mode product
```

`--view` selects the camera content while `--ui-mode` selects the surrounding
presentation. They are intentionally independent: for example, the analytical
risk view can still be presented inside the uncluttered Product shell.

The external Diagnostic panel separately reports pipeline FPS, SCHP inference FPS, mask source
(`inferred`, `propagated`, `stale`, or `unavailable`), keyframe ID, mask age,
and capacity-one inference overwrites. This must not be described as SCHP
running at the display rate. A propagated mask is cleared after its configured
age limit or when flow validation fails. The panel also keeps original corrected color/margin, heuristic mask confidence,
CVD risk, and lighting quality as separate fields. Matching uses only the T04
original corrected cluster; the assistive display color never feeds analysis.
Every output is tied to the displayed `frame_id`. A missing or failed stage is
shown as `degraded`/`unavailable` for that current frame; prior masks, colors,
risks, or recolors are not presented as current results.

Live webcam capture and live SCHP scheduling each use an exact capacity-one
mailbox: capture and inference take the newest frame and count overwritten
stale frames instead of building latency.
Finite videos run sequentially through the same pipeline so evaluation frames
are not skipped. Runtime metrics use bounded buffers (10,000 samples per
latency series and at most 10,000 RSS samples). The T09-frozen names are:

- `source_read_to_render_ms`: starts at the monotonic timestamp created after
  `VideoCapture.read()` returns and ends after the renderer completes. It is
  available in GUI and headless runs.
- `source_read_to_display_submit_ms`: has the same start and ends immediately
  after `cv2.imshow()` returns. It is available only in GUI runs and measures
  software submission, not physical display emission.
- `sensor_to_photon_ms`: `NOT_MEASURED` unless an external synchronized
  apparatus is used.

The first two are software-timestamp/development-machine observations. They
must not be described as camera exposure-to-display, sensor-to-photon, or the
time at which the screen actually emits light. T09's frozen definitions,
formulae, thresholds, and result schema are in
[`evaluation/protocol.md`](evaluation/protocol.md).

The lightweight value drawn inside an overlay is labeled `pre-render age` (or
`frame age at overlay` in preview-only mode). It is sampled before the overlay
renderer runs and is a live diagnostic only; it is not a T09 latency metric.

The capture-only T01 diagnostic remains available explicitly and never loads a
segmentation backend:

```powershell
conda run --name lens python -m chromalens --video C:\path\to\sample.mp4 --preview-only
```

No command saves or uploads camera frames by default. Source-open failures,
missing backend dependencies/assets, and live read failures return actionable,
non-zero exits. Generate reviewable T08 fixture views, a local sample AVI, and
optional two-minute bounded-runtime metrics offline with:

```powershell
conda run --name lens python scripts/t08_pipeline_evidence.py
conda run --name lens python scripts/t08_pipeline_evidence.py --stability-seconds 120
conda run --name lens python -m chromalens --video artifacts/t08-pipeline/sample_mediapipe.avi --no-display
```

All generated output is under ignored `artifacts/t08-pipeline/`. The real
backend visual uses the repository's licensed/public-domain T02 fixture; the
stability source is generated and contains no private camera image.

## T09 evaluation and evidence

T09 is `DONE` under frozen protocol version `1.0.0`. The owner accepted the
absent 33-case physical color/lighting matrix as a declared limitation: every
physical row remains `NOT_RUN`, synthetic evidence is not relabeled, and no
physical-camera color-accuracy claim is made. The evaluation contract is:

- [`evaluation/protocol.md`](evaluation/protocol.md): procedure, hardware and
  resolution declarations, units, formulae, thresholds, latency semantics,
  claim limits, and evidence policy;
- [`evaluation/schema/t09-result.schema.json`](evaluation/schema/t09-result.schema.json)
  and [`evaluation/schema/metric_registry.json`](evaluation/schema/metric_registry.json):
  machine-readable result and metric contracts;
- [`evaluation/fixtures/test_cases.csv`](evaluation/fixtures/test_cases.csv):
  the frozen case matrix, including honest `TO_BE_ACQUIRED` slots;
- [`evaluation/OWNERSHIP.md`](evaluation/OWNERSHIP.md): non-overlapping branch,
  result, script, and test ownership.

The shared runtime instrumentation already supports the frozen 15-second
warm-up followed by a 120-second measured interval. `--duration-seconds`
counts the measured interval when a warm-up is set:

```powershell
conda run --name lens python -m chromalens --webcam --metrics-warmup-seconds 15 --duration-seconds 120
conda run --name lens python -m chromalens --webcam --no-display --metrics-warmup-seconds 15 --duration-seconds 120
```

The summary exposes the separately named latency percentiles, sample counts,
RSS values/slopes, and the frozen four-window continuous-growth diagnostics.
The benchmark workstream converts those observations to schema 1.0.0 results;
it does not redefine or re-instrument them.

After the Gate commit is pushed and CI is green, contributors update `mvp`,
verify its exact hash against the coordinator handoff, and create branches
from that commit:

```powershell
git switch mvp
git pull --ff-only origin mvp
git rev-parse HEAD
git switch -c eval/t09-segmentation-dong
# or: eval/t09-color-science-phong
# or: eval/t09-performance-rai-trinh
```

Do not branch from pre-gate T08 commit `f315fd7`. Small curated UTF-8
CSV/JSON/Markdown results belong under each assigned
`evaluation/results/curated/` namespace. Raw video, private footage, images,
arrays, and bulk evidence stay below ignored `artifacts/t09/`. Every report
artifact needs a manifest with provenance/consent, license, exact byte size,
and SHA-256. Never use `git add -f` to bypass the artifact policy.

### T09 curated evidence

The cross-workstream status and claim boundaries are in
[`evaluation/results/curated/summary.md`](evaluation/results/curated/summary.md).
The coordinator-regenerated packages are complete as evidence packages while
retaining unmeasured rows explicitly:

- color science accounts for all 50 frozen IDs: 11 digital contract and six
  CVD cases are complete, while the 33 physical color-lighting cases remain
  `NOT_RUN` under the owner-accepted limitation;
- the synthetic 11 x 3 lighting matrix, 121-cell confusion table, K=2
  containment diagnostic, and CVD sanity rows are retained as supplemental
  implementation evidence, not physical-camera accuracy;
- four new 15-second-warm-up plus 120-second performance observations are
  development-host evidence, never demo-hardware acceptance evidence;
- seven unrecoverable contributor artifacts are superseded by four new raw
  JSON files and one deterministic generated video. Their active manifests,
  provenance, licenses, byte sizes, and SHA-256 hashes validate strictly.

Regenerate the deterministic color result and reproduce the tracked
performance/RAI consolidation from the exact raw-generator commit, then
strictly validate schema, metric registry, case coverage, and checksums:

```powershell
conda run --name lens python scripts/t09_color_science_eval.py
conda run --name lens python scripts/t09_benchmark_report.py --raw-generator-commit f74227d2342dc81bc9fd66e71fc2b85c095065ef
conda run --name lens python scripts/t09_result_validation.py --require-untracked-artifacts
```

The segmentation evaluator requires Dong's consented inputs and annotations
to be materialized below ignored `artifacts/t09/segmentation/`. It runs the
exact 20-case registry with the locked default MediaPipe backend. First create
review artifacts and fill the ignored 0-3 rating CSV; then generate and
strictly validate the curated package:

```powershell
conda run --name lens python scripts/t09_segmentation_eval.py --prepare-review
conda run --name lens python scripts/t09_segmentation_eval.py
conda run --name lens python scripts/t09_result_validation.py --require-untracked-artifacts evaluation/results/curated/segmentation/result.json
```

The coordinator end-to-end evaluator runs all 10 frozen integration cases,
including locked MediaPipe on the licensed public fixture and the consented
moving sequence. It saves six controlled intermediate views plus failure and
temporal reviews only below ignored `artifacts/t09/end_to_end/`:

```powershell
conda run --name lens python scripts/t09_end_to_end_eval.py
conda run --name lens python scripts/t09_result_validation.py --require-untracked-artifacts evaluation/results/curated/end_to_end/result.json
```

The `t09_benchmark_report.py` command only consolidates raw observations; it
does not rerun or claim new measurements. Generate its deterministic no-person
video, then collect a new raw benchmark on the eventual declared demo machine
one
frozen case at a time; raw JSON remains ignored under `artifacts/t09/`:

```powershell
conda run --name lens python scripts/t09_benchmark_performance.py --prepare-video
conda run --name lens python scripts/t09_benchmark_performance.py --case PERF-WEBCAM-GUI-120
conda run --name lens python scripts/t09_benchmark_performance.py --case PERF-WEBCAM-HEADLESS-120
conda run --name lens python scripts/t09_benchmark_performance.py --case PERF-VIDEO-GUI-120 --video artifacts/t09/performance_responsible_ai/inputs/generated-360x240.avi
conda run --name lens python scripts/t09_benchmark_performance.py --case PERF-VIDEO-HEADLESS-120 --video artifacts/t09/performance_responsible_ai/inputs/generated-360x240.avi
```

The manual ROI timing command is interactive and saves timings/hashes only,
never selected geometry or image content:

```powershell
conda run --name lens python scripts/t09_responsible_ai_manual_roi.py
```

On a data-custodian checkout that contains every ignored artifact, require
strict raw-byte verification with:

```powershell
conda run --name lens python scripts/t09_result_validation.py --require-untracked-artifacts
```

## T11 competition handoff

The final handoff sources are intentionally small and reviewable:

- [`docs/competition-handoff.md`](docs/competition-handoff.md): submission
  copy, measured benchmark summary, claim boundaries, known limitations, live
  form/consent checklist, and exact remaining human actions;
- [`docs/submission.json`](docs/submission.json): locked project name,
  description, public limits, 120-second shot registry, and claim-to-evidence
  paths;
- [`docs/architecture.md`](docs/architecture.md): Mermaid architecture graphic
  and its source;
- [`docs/demo-shot-list.md`](docs/demo-shot-list.md): timed two-minute script,
  recording procedure, fallback command, and final-duration check;
- [`THIRD_PARTY_NOTICES.md`](THIRD_PARTY_NOTICES.md): default runtime,
  algorithms, public fixtures, credits, licenses, and deferred-asset gaps.

Prepare the ignored demo package through the real locked MediaPipe backend:

```powershell
conda run --name lens python scripts/t11_prepare_handoff.py
```

The command verifies the public NASA fixture checksum, overlays declared BGR
patches derived from the frozen T05 deutan red/olive sanity pair and adjusted
so the complete pipeline exercises risk/recolour, writes a 15-second 640x480
MJPG/AVI fallback, renders all five pipeline views, and writes actual byte
sizes and SHA-256 values to
`artifacts/t11-handoff/manifest.json`. It does
not download a model, open a webcam, or use private footage. The visibly
engineered fallback exercises risk/recolour through real MediaPipe inference;
it is operational safety input, not evaluation or physical colour-accuracy
evidence.

The public competition page was checked on 24 August 2026. The linked live
Google Form returned HTTP 401 from this development machine, so the owner must
sign in and verify any form-only fields/video criteria before submission. This
human confirmation, signed-consent custody, final video export review, and a
dry run on the actual venue laptop are the only scheduled 25 August actions;
no core implementation remains scheduled.

## Verification

These commands require no webcam, network access at runtime, model weights, or
special inference hardware:

```powershell
conda run --name lens python -m chromalens --help
conda run --name lens python -m pytest -q
```

The console entry point is equivalent:

```powershell
conda run --name lens chromalens --help
```

## T10 SCHP/OpenVINO gate outcome

The owner reopened T10 after the preserved `t11-demo-v1` baseline. Place the
ATR checkpoint linked by the official SCHP README at
`models/schp/exp-schp-201908301523-atr.pth`; it must be exactly `267445237`
bytes with SHA-256
`e9d7c91ce3b4e7133df56b599fc817b533e3439c5e8d282a59126d2fda339a2a`.
That object identity comes from fixed mirror metadata because upstream does
not publish a checksum, and the checkpoint has no separately stated
redistribution license. Do not commit or redistribute it.

Verify and export a checksummed FP32 OpenVINO IR:

```powershell
conda run --name lens powershell -NoProfile -Command "(Get-Item 'models/schp/exp-schp-201908301523-atr.pth').Length; (Get-FileHash -Algorithm SHA256 'models/schp/exp-schp-201908301523-atr.pth').Hash.ToLowerInvariant()"
conda run --name lens python scripts/t10_export_schp_openvino.py
conda run --name lens python -m pytest -q tests/integration/test_t10_schp_integration.py
```

The exporter strict-loads every checkpoint key into the pinned MIT SCHP graph,
uses a portable activated-BatchNorm implementation, converts with
`torch==2.5.1` and `openvino==2025.4.1`, and writes `.xml`, `.bin`, and a
checksum/provenance manifest under ignored `models/schp/openvino/`. `auto`
prefers that verified IR and falls back only to the SCHP PyTorch runtime, never
silently to MediaPipe. Missing or altered assets fail with an actionable exit;
use the explicit `--backend mediapipe-selfie-torso` fallback when needed.

On the current development Intel Core i5-13450HX, the accepted FP32 OpenVINO
conversion matched PyTorch garment masks on all five fixed public fixtures
(per-class IoU at least `0.999`) and reduced model/runtime cost, but a 20-frame
640x480 full-pipeline headless observation was still only `0.89 FPS`, with
render-complete latency p50/p95 `1195.00/1411.65 ms`. This is development-host
evidence, not sensor-to-photon latency or an official demo-laptop benchmark.

The owner-approved asynchronous corrective pass retained FP32/512 SCHP as the
authoritative parser and measured a 15-second 640x480 webcam headless run after
a 3-second warm-up at `11.82` pipeline FPS, `2.21` SCHP keyframes/second,
source-read-to-render p50/p95 `110.00/171.15 ms`, and processing-to-render
p50/p95 `78.00/110.00 ms`. These are development-machine software timings;
GUI-submit and sensor-to-photon were not measured in that run. The speedup also
includes a deterministic bounded K-means fit whose final cluster assignment
still covers every valid garment pixel.

Two production GUI runs requesting `480x360` (actual camera mode `640x360`)
measured `10.75` and `13.75` pipeline FPS. The final default-command run
reported GUI-submit p50/p95 `110.00/156.00 ms` over an 8-second window after
3 seconds of warm-up. An explicit `320x240` request
measured `18.71` FPS and p50/p95 `32.00/63.00 ms`; it is available as a venue
fallback, not the default quality setting. Sensor-to-photon remains unmeasured.

Two local NNCF 3.2.0 INT8 post-training quantization experiments were rejected.
They improved fixed-fixture mean runtime by `1.65x` (performance preset) and
`1.57x` (mixed preset), but both lost the `skirt` class on `nasa_shepard` and
had minimum per-class IoU `0.0`; their manifests remain ignored and marked
`REJECTED`. Runtime manifest validation refuses an INT8 artifact unless its
acceptance decision is `ACCEPTED`. NNCF and its temporary packages were removed
after the experiment, so the locked production dependency closure is unchanged.

The T01/T08 suites generate short MJPG/AVI files under pytest's temporary directory
and deletes them with the test workspace. It does not commit or download sample
media and verifies that video mode never opens a webcam.

## T02-T08 handoff contracts

- `chromalens.camera.FrameSource` is the common webcam/video interface.
- Each successful read produces a `FramePacket` with a sequential frame ID,
  monotonic timestamp, and unchanged original BGR frame.
- Finite video EOF returns `None`; live-source read failures raise a specific,
  actionable exception.
- `chromalens.renderer.render_preview` draws only onto a copied frame.
- T02 can consume `FramePacket.original_bgr` for segmentation; T03 can produce
  corrected output without changing the source frame.
- T04 consumes only `corrected_rgb` plus an aligned garment mask and returns
  original-color `ColorCluster` values; assistive display colors do not exist
  yet and cannot contaminate extraction.
- T05 simulates those original cluster RGB values under a user-selected
  profile/severity and returns relational `RiskAssessment` values containing
  both Delta-E measurements, numeric risk score, and display level.
- T06 selects a representative assistive color from T04/T05 data, but assigns
  pixels only inside the exact hard intersection and preserves the source frame.
  Its original corrected and assistive display colors remain separate fields.
- T06's overlay renderer copies its input and marks simulation as debug-only.
- T07 accepts only T04's original corrected `ColorCluster`, never T06's
  assistive display value. It returns deterministic guidance plus an optional
  CVD-separation diagnostic; neither priority nor separation is confidence.
  T08 presents that guidance but does not change its source contract.
- `chromalens.pipeline.ChromaLensPipeline` is the sole T08 composition
  boundary. It emits typed current-frame stage reports and resets recolor state
  when profile, severity, or recolor context changes.
- `LatestFrameReader` has a one-packet live mailbox; video deliberately remains
  sequential. `TemporalMaskSmoother` intersects history with the current mask,
  so temporal state cannot resurrect rejected pixels.

## Current limitations

- MediaPipe Selfie Segmentation predicts prominent humans, not semantic
  garment classes. T02 combines it with face exclusion and vertical cleanup to
  approximate a torso/upper-clothes mask. Hands, carried objects, or background
  attached to the person silhouette can remain.
- SCHP-ATR is semantic parsing and improves class specificity, but its
  512x512 ResNet-101 graph is materially slower than the MediaPipe fallback on
  this development CPU. The checkpoint's separate redistribution license is
  unstated, so every demo machine needs an owner-reviewed ignored local copy.
  The five-fixture equivalence gate proves conversion fidelity, not broad
  segmentation accuracy or superiority on all scenes.
- Face detection and the upper-body cutoff (`upper_body_ratio=0.80`) are
  heuristics and can clip clothing or retain non-clothing pixels, especially
  with occlusion, multiple people, unusual poses, or an undetected face.
- T03 uses the Gray-world neutral-scene assumption and heuristic lighting
  thresholds. Mixed illuminants, strongly single-colored scenes, or very few
  eligible pixels can limit correction; `used_fallback` and `valid_fraction`
  expose the latter case.
- T04's CSS-anchor lookup is transparent and deterministic but cannot represent
  every shade, language, material, camera, display, or lighting condition. Its
  11-patch controlled result is contract evidence, not a real-world accuracy
  claim; broader evaluation and threshold tuning belong to T09.
- T05's CVD profile and severity are user-selected settings, not diagnosis.
  Machado/DaltonLens simulation and the risk formula approximate perception;
  DaltonLens documents an additional tritan limitation. Delta-E thresholds and
  risk levels are uncalibrated heuristics requiring T09 evaluation.
- T06's candidate score, risk activation, feathering, and hysteresis defaults
  are explainable but uncalibrated. Gamut clipping can slightly shift L*, and
  mask/cluster errors directly limit containment quality. The OpenCV tag
  used by the standalone T06 evidence renderer transliterates accented
  Vietnamese because its bundled Hershey font is ASCII-only. The main T08
  Product/Diagnostic presentation uses locked Pillow and an available system
  Unicode font (with Pillow's embedded fallback), so its Vietnamese UI retains
  accents without redistributing an operating-system font.
- T07's CIELCH geometry and five-row project-authored table are simple
  guidance. They do not model culture, material, occasion, trend, or individual
  taste; their wording and usefulness require T09 user testing.
- T08/T09 development measurements are not an official hardware benchmark.
  The current live path runs all analytical modules on every consumed frame
  and can drop capture frames under load. T09 declares its development host,
  footage, conditions, protocol, thresholds, failures, and unmeasured cases;
  those observations cannot be generalized to the eventual demo laptop.
- Model weights, datasets, generated artifacts, and private footage are not
  included. See `models/README.md` for download policy.

## License

ChromaLens AI is licensed under the Apache License 2.0. Third-party model,
fixture, algorithm, and code attribution is consolidated in
[`THIRD_PARTY_NOTICES.md`](THIRD_PARTY_NOTICES.md).
