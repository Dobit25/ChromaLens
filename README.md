# ChromaLens AI

ChromaLens AI is a local, explainable color-vision assistance prototype for
clothing. **T01** (webcam/video preview), the locked **T02** MediaPipe torso-
mask baseline, and **T03** lighting correction are complete. Color extraction
begins in T04.

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

## T02/T03 handoff contracts

- `chromalens.camera.FrameSource` is the common webcam/video interface.
- Each successful read produces a `FramePacket` with a sequential frame ID,
  monotonic timestamp, and unchanged original BGR frame.
- Finite video EOF returns `None`; live-source read failures raise a specific,
  actionable exception.
- `chromalens.renderer.render_preview` draws only onto a copied frame.
- T02 can consume `FramePacket.original_bgr` for segmentation; T03 can produce
  corrected output without changing the source frame.

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
- T02/T03 contain segmentation and lighting correction only; color extraction,
  CVD-risk, recoloring, and performance-target claims belong to later tasks.
- Model weights, datasets, generated artifacts, and private footage are not
  included. See `models/README.md` for download policy.

## License

ChromaLens AI is licensed under the Apache License 2.0. Third-party model,
dataset, algorithm, and code attribution will be documented as each component
is integrated.
