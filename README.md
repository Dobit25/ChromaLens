# ChromaLens AI

ChromaLens AI is a local, explainable color-vision assistance prototype for
clothing. **T01** (webcam/video preview), the locked **T02** MediaPipe torso-
mask baseline, **T03** lighting correction, **T04** original-color
extraction/naming, and **T05** CVD simulation/relational risk are complete.

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
conda run --name lens python -m pip install --require-hashes --requirement requirements/py310-win64.lock
conda run --name lens python -m pip install --no-build-isolation --no-deps --editable ".[dev]"
```

The explicit Conda lock pins every bootstrap artifact, build, URL, and MD5,
including Python 3.10.20 and pip 26.1.2. `environment.yml` is the concise,
human-readable declaration of the supported interpreter and bootstrap tools.
The hashed pip lock pins every currently approved base/development Python
package and transitive dependency. The final command installs only the local
ChromaLens package; dependency resolution is deliberately disabled.

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

## Camera and local-video preview

Run the webcam preview using the default camera index:

```powershell
conda run --name lens python -m chromalens --webcam
```

Request a capture resolution or choose another camera when required:

```powershell
conda run --name lens python -m chromalens --webcam --camera-index 1 --width 1280 --height 720
```

Run a local video without opening a camera:

```powershell
conda run --name lens python -m chromalens --video C:\path\to\sample.mp4
```

Press `q`, Escape, or close the window to exit. Automated/headless checks can
avoid GUI and bound execution explicitly:

```powershell
conda run --name lens python -m chromalens --video C:\path\to\sample.mp4 --no-display
conda run --name lens python -m chromalens --webcam --no-display --max-frames 120
conda run --name lens python -m chromalens --webcam --duration-seconds 120
```

The overlay reports source name, observed resolution, frame ID, processed FPS,
and basic pipeline latency. At T01, pipeline latency is measured from the
monotonic timestamp assigned immediately after OpenCV returns a frame to the
start of rendering; it is not yet a sensor-to-photon benchmark.

The capture loop reads, renders, displays, and discards one frame at a time.
There is no application queue or frame history in T01. A webcam disconnect is
reported as an error, while local-video end-of-file is a successful exit. No
frame is saved or uploaded. OpenCV is asked for a one-frame webcam buffer, but
backend support for that hint varies; T08 will introduce latest-frame behavior
if inference becomes slower than capture.

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

The T01 suite generates short MJPG/AVI files under pytest's temporary directory
and deletes them with the test workspace. It does not commit or download sample
media and verifies that video mode never opens a webcam.

## T02–T05 handoff contracts

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

## Current limitations

- MediaPipe Selfie Segmentation predicts prominent humans, not semantic
  garment classes. T02 combines it with face exclusion and vertical cleanup to
  approximate a torso/upper-clothes mask. Hands, carried objects, or background
  attached to the person silhouette can remain.
- SCHP-ATR was not validated within the T02 time box and is explicitly
  `DEFERRED` to T10; its dependencies and weights are not installed.
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
- T02–T05 contain segmentation, lighting correction, original-color
  extraction, simulation, and relational risk only; recoloring, live pipeline
  composition, and performance-target claims belong to later tasks.
- Model weights, datasets, generated artifacts, and private footage are not
  included. See `models/README.md` for download policy.

## License

ChromaLens AI is licensed under the Apache License 2.0. Third-party model,
dataset, algorithm, and code attribution will be documented as each component
is integrated.
