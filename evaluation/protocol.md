# T09 Evaluation Protocol

Protocol version: `1.0.0`

Status: `FROZEN` for T09 Wave 4

Frozen from implementation baseline: `f315fd766f01c231c3265c3f91522e1c5e50af9e`

Schema: `evaluation/schema/t09-result.schema.json`

Metric registry: `evaluation/schema/metric_registry.json`

Case registry: `evaluation/fixtures/test_cases.csv`

## 1. Purpose and change control

This file is the Gate 0 contract for T09. Results created against another
definition are not T09 results. The three collaborator branches must be
created from the Gate 0 commit containing this protocol, not directly from
the pre-gate T08 commit shown above.

Protocol, schema, metric registry, case registry, shared instrumentation,
dependency locks, and final summary are coordinator-owned. Contributors must
not edit them on task branches. A required change is proposed to the
coordinators with the affected case/metric, reason, compatibility impact, and
replacement test. Accepted semantic changes increment the protocol and schema
version and invalidate incompatible results; silent reinterpretation is
prohibited.

This gate freezes definitions and collaboration boundaries. It does not claim
that T09 evaluation is complete and it does not create measured quality or
performance results.

## 2. Workstreams

| Workstream key | Owner | Scope |
| --- | --- | --- |
| `end_to_end` | Repository owner + Codex | Pipeline integration failures, latency instrumentation/semantics, stale-frame and containment checks, final coordination. |
| `segmentation` | Dong | Real-backend mask adequacy, annotated-subset IoU, and declared failure scenes. |
| `color_science` | Phong | 11-name matrix, lighting stability, and CVD-risk sanity cases. |
| `performance_responsible_ai` | Trinh | Execute the frozen benchmark; record p50/p95/FPS/RSS, artifact manifests, privacy, bias, limitations, environmental notes, and a workstream report. |

File-level ownership is normative in `evaluation/OWNERSHIP.md`. Contributors
write only to their namespaces. The coordinators merge workstreams in the
order needed to preserve schema and protocol compatibility.

## 3. Evaluation inputs and frozen case list

The case registry is `evaluation/fixtures/test_cases.csv`. Its `case_id` values
and rows are frozen for protocol 1.0.0. It contains:

- all 11 basic color terms under `daylight`, `neutral_indoor`, and
  `warm_low` lighting;
- the 11 existing deterministic digital contract patches;
- at least 20 segmentation scenes/frames including the five licensed T02
  fixtures, plain and multicolor clothing, movement, pose, occlusion,
  background similarity, no-person, and multi-person cases;
- confusing/control synthetic color pairs for `protan`, `deutan`, and
  `tritan` at severity 1.0;
- end-to-end success, degradation, controls, containment, temporal, and stale
  analysis cases;
- GUI/headless performance runs and a manual/non-AI baseline record.

`gate_asset_status=TO_BE_ACQUIRED` is an honest acquisition slot, not evidence.
A case remains `NOT_RUN` until its exact asset has a manifest and checksum.
Unavailable cases must remain visible in results; they cannot be replaced
silently by an easier input. Synthetic/generated cases state their generator
and seed or deterministic construction. Public fixtures retain their recorded
source, rights statement, and SHA-256.

The matrix is small and declared, not statistically representative. It does
not support demographic, cultural, clinical, or population-level claims.

## 4. Hardware, software, and resolution declaration

Every result document must record:

- full 40-character Git commit and protocol/schema version;
- operator role and UTC creation timestamp;
- host role: `development` or owner-declared `demo`;
- manufacturer/model, OS/version/build, CPU, logical/physical cores, RAM GiB;
- GPU/NPU names and whether each was used;
- camera or video source identifier without a personal device serial;
- Python, NumPy, OpenCV, MediaPipe, DaltonLens, and ChromaLens versions;
- exact segmentation backend name and execution device;
- source resolution, rendered resolution, GUI/headless mode, and source kind;
- CVD profile/severity, configuration thresholds, and lock-file SHA-256.

Gate host reference, detected on 2026-08-20, is a development machine only:

| Field | Value |
| --- | --- |
| Host | Lenovo model `83DV` |
| OS | Windows 11 Home Single Language `10.0.26200` build `26200` |
| CPU | 13th Gen Intel Core i5-13450HX; 10 cores / 16 logical processors |
| RAM | 16,944,848,896 bytes (approximately 15.78 GiB) |
| Discrete GPU | NVIDIA GeForce RTX 4050 Laptop GPU; not used by the locked MediaPipe CPU backend |
| Camera | Integrated Camera; no serial/instance ID is stored |
| Python | 3.10.20 in the isolated `lens` environment |

This host is not declared competition demo hardware. Measurements on it must
be labeled development-machine observations. A collaborator's different host
is allowed only when fully recorded in that result; values must not be pooled
or generalized across hosts. The owner must explicitly set
`declared_demo_hardware=true` before demo-hardware acceptance claims are made.

Frozen performance resolutions are:

- webcam GUI: request `640x480`; record the actual delivered resolution;
- webcam headless diagnostic: request `640x480`; record actual delivery;
- fixed generated-video comparison: `360x240`, sequential finite-video mode;
- another resolution may be reported as an additional run but cannot replace
  these rows or be compared without a separate result ID.

## 5. Common execution procedure

1. Start from the Gate 0 commit or a descendant and verify a clean worktree.
2. Install only from the committed Conda/pip locks into `lens`; run
   `python --version`, `pip check`, CLI help, and the full test suite.
3. Verify every input asset against its manifest SHA-256 before processing.
4. Record exact configuration and environment before the first measurement.
5. Run deterministic fixture cases with their fixed seed/settings.
6. For a performance session, complete 15 seconds of warm-up, reset metric
   state, then measure 120 continuous seconds. Do not include setup/model-load
   time in per-frame latency; record startup separately if measured.
7. Keep all samples from the 120-second measurement window. Bounded storage
   must be configured large enough; a truncated series is `INVALID`, not an
   approximate percentile.
8. Save raw images/video/traces only under ignored `artifacts/t09/`. Generate
   curated result tables and reports under the owning tracked namespace.
9. Validate the result against the JSON Schema, verify artifact checksums, run
   automated tests, and record commands plus exit codes.
10. Record failures and missing cases explicitly. Never convert `NOT_RUN`,
    `NOT_MEASURED`, or a degraded frame into success.

Network access must not be required during runtime evaluation. Camera frames
are neither uploaded nor saved by default. Evaluation capture is an explicit
action governed by Section 10.

The shared CLI implements this boundary with
`--metrics-warmup-seconds 15 --duration-seconds 120`; with a warm-up configured
the duration is the measured interval rather than total process wall time.

## 6. Frozen latency semantics

### `source_read_to_render_ms`

Start: `FramePacket.timestamp_ns`, created immediately after OpenCV
`VideoCapture.read()` has returned a valid frame.

End: monotonic timestamp immediately after `render_pipeline_view()` returns.

Modes: GUI and headless.

Includes: newest-frame mailbox residence, pipeline processing, and rendering.

Excludes: sensor exposure/readout before `VideoCapture.read()` returns,
`cv2.imshow`, GUI queueing, scan-out, display response, and emitted light.

This is the exact name for the T08 value formerly labeled loosely as
capture-to-render. Human-readable phrase:
`capture-return-to-render-complete latency`.

### `source_read_to_display_submit_ms`

Start: the same `FramePacket.timestamp_ns`.

End: monotonic timestamp immediately after `cv2.imshow()` returns.

Mode: GUI only; headless results use status `NOT_MEASURED` with reason
`headless run has no OpenCV GUI submission`.

It is a software submission measurement. It does not prove that the frame was
painted, scanned out, or visible to a human.

### `sensor_to_photon_ms`

This metric is `NOT_MEASURED` unless a synchronized external apparatus such as
a photodiode/high-speed camera plus a documented stimulus and synchronization
method is used. Software timestamps alone can never set it to `MEASURED`.

None of the first two metrics may be called sensor-to-photon latency, camera
exposure-to-display latency, or time until the screen physically emits light.

## 7. Aggregation, formulae, and units

The machine-readable registry is normative. The following rules aid review:

- time: milliseconds (`ms`), monotonic clock only;
- throughput: frames per second (`frames/s`);
- memory: mebibytes (`MiB = bytes / 2^20`);
- memory slope: ordinary least-squares slope in `MiB/min`;
- color distance: CIEDE2000 (`delta_e_00`);
- ratios and heuristic scores: real values in `[0,1]`;
- counts: non-negative integers;
- p50/p95: NumPy linear percentile over every valid measurement-window sample
  (`numpy.percentile(..., method="linear")` semantics);
- processed FPS: processed frames divided by measured elapsed seconds;
- IoU: intersection pixel count divided by union pixel count; empty/empty is
  `NOT_APPLICABLE`, not one;
- color-name accuracy: correct cases divided by evaluated cases; missing cases
  stay outside the denominator and are reported separately;
- adequate segmentation: manual rating at least 2 on the frozen 0-3 rubric;
- risk sanity: the declared confusing-pair score must exceed its same-profile
  control-pair score and both Delta-E00 values plus risk score are stored;
- recolor containment: count of changed pixels outside the hard recolor mask
  before outline/tag overlays;
- static switch count: number of changes between consecutive assistive target
  RGB values after the first selected value.

The 0-3 segmentation adequacy rubric is:

| Rating | Meaning |
| ---: | --- |
| 0 | No usable target mask or mask is predominantly wrong. |
| 1 | Target is recognizable but contamination/omission blocks reliable color use. |
| 2 | Usable for dominant-color assistance despite visible boundary or small-region errors. |
| 3 | Target garment is well covered with only minor non-blocking error. |

The rater records a reason. Where annotation exists, IoU is also measured;
manual adequacy is not renamed as IoU or accuracy.

## 8. Frozen thresholds and claim rules

| Area | Threshold or rule | Claim class |
| --- | --- | --- |
| Performance floor | On owner-declared demo hardware in GUI mode: `processed_fps >= 5` and p50 `source_read_to_display_submit_ms <= 350`; otherwise report the limitation. | MVP engineering floor from `context.md`, not organizer claim. |
| Performance target | `processed_fps >= 10` and GUI p50 `source_read_to_display_submit_ms <= 200`. | Project target only. |
| Duration | 15 s warm-up plus 120 s measured session. | Required for live trend claim. |
| Latency growth flag | Four consecutive 30 s window medians strictly increase and Q4-Q1 exceeds `max(20 ms, 10% of Q1)`. Flag must be false. | Project diagnostic; not proof of real-time guarantees. |
| RSS growth flag | Four consecutive 30 s window medians strictly increase and Q4-Q1 exceeds `max(8 MiB, 5% of Q1)`. Flag must be false. | Project diagnostic; not proof of leak freedom. |
| Digital 11-name contract | 11/11 expected labels. | Deterministic implementation gate only. |
| Physical color/lighting matrix | Per-class table and confusion matrix required; no calibrated pass threshold is authorized. Stability target is at least 0.80 and is reported as a diagnostic target. | Observation only; no population accuracy claim. |
| Segmentation adequacy | Per-case rating `>=2` is adequate; aggregate and IoU have no authorized pass threshold. All 20 rows must be reported or visibly `NOT_RUN`. | Observation/failure analysis. |
| CVD risk | Existing heuristic: medium `>=0.25`, high `>=0.60`; every declared confusing pair must outrank its same-profile control. | Sanity check, not medical/perceptual validation. |
| Recolor containment | Changed pixels outside hard mask before overlay `==0`. | Required invariant. |
| Static temporal selection | Assistive target switch count `==0` over the declared static sequence. | Required deterministic invariant. |
| Stale analysis | Frame-ID mismatch count `==0`. | Required safety invariant. |
| Artifact integrity | SHA-256 mismatch count `==0`. | Required evidence invariant. |
| Consent/privacy | Unconsented tracked media count `==0`; private/raw media tracked in Git `==0`. | Required privacy invariant. |

Absence of an authorized aggregate quality threshold is a frozen decision, not
permission to omit results. It prevents a small convenience set from being
misrepresented as calibrated product accuracy.

## 9. Results and failure reporting

Each workstream saves at least one JSON result conforming to
`t09-result.schema.json` and one Markdown or CSV human-readable result in its
tracked namespace. A result identifies every case as completed, partial,
invalid, or not run and stores exact commands/exit codes.

The final coordinated package must include at least three concrete failure
examples with case IDs, observed behavior, user impact, reproduction steps,
mitigation, and status. Expected inherited limitations include the
person-derived torso heuristic, Gray-world assumptions, color-name anchor
coverage, uncalibrated CVD/risk/recolor thresholds, multicolor requirement for
relational risk, dropped live capture frames, ASCII-only overlay text, and no
sensor-to-photon measurement.

Manual/non-AI baseline evidence must explain or demonstrate that fixed RGB
thresholds or manual region selection do not automatically locate garments in
unconstrained motion/backgrounds. It must not claim that deterministic color
science modules should be replaced by AI.

Usability or accessibility feedback is optional only when ethically
obtainable. Without appropriate participants/consent, record
`NOT_MEASURED`/`not yet user validated`; do not simulate a participant.

## 10. Artifact, provenance, consent, license, and checksum policy

Tracked results:

- only small UTF-8 `.csv`, `.json`, and `.md` files below
  `evaluation/results/curated/<workstream>/`;
- at most 1 MiB per curated file; no base64, raw arrays, embedded media,
  private identifiers, signed consent forms, or secrets;
- JSON results must conform to the frozen schema.

Ignored evidence:

- raw video, private footage, images, NumPy arrays, profiler traces, and bulk
  output live below `artifacts/t09/<workstream>/`;
- these files are never added with `git add -f`;
- only their manifest records are committed.

Every artifact cited by a result/report requires a manifest entry containing:

- stable artifact ID and related case IDs;
- repository-relative path, media type, byte size, and SHA-256 of exact bytes;
- creator/source URL or capture origin and UTC capture/generation time;
- provenance class and SPDX license ID or documented `LicenseRef-*`;
- consent status, private consent-record reference when applicable, and
  whether personal data is present;
- whether the file is tracked in Git and the generation command/version.

Allowed consent statuses are `NOT_APPLICABLE_NO_PERSON`, `PUBLIC_LICENSED`, and
`EXPLICIT_WRITTEN_CONSENT_PRIVATE_RECORD`. `UNKNOWN` or `WITHDRAWN` artifacts
cannot be used in a report. Signed forms and identifying consent records stay
outside Git; a non-identifying private record reference may be committed.
Withdrawal invalidates all affected result/artifact references and requires
local deletion by the data custodian.

All manifests are verified by recomputing SHA-256 before merge. A transformed
artifact has its own checksum and a `derived_from` link; it does not inherit
the source checksum. License/consent evidence must cover both use and
redistribution. Public-domain and permissively licensed material remains
attributed. ChromaLens-authored synthetic data uses `Apache-2.0`.

## 11. Responsible-AI and environmental reporting

The final human-readable report must state:

- local/offline runtime and no default frame storage/upload;
- explicit opt-in artifact capture and withdrawal handling;
- assistive, non-diagnostic CVD profile selection;
- separate confidence, lighting quality, and risk semantics;
- expected demographic, body-presentation, clothing, lighting, camera, and
  display coverage gaps;
- at least three failures and mitigations;
- pretrained-model reuse, no training from scratch, exact backend/device, and
  the measured performance/memory proxy rather than unsupported energy claims;
- model/data/algorithm/code licenses and attribution;
- human oversight: visible degraded state and ability to disable recoloring.

## 12. Gate acceptance and branch point

Gate 0 is accepted only when:

- protocol/schema/registry/case list/ownership files pass their tests;
- instrumentation exposes the two software latency series separately and GUI
  submission is never populated for headless runs;
- `sensor_to_photon_ms` remains explicitly unmeasured without external gear;
- curated text paths are not ignored, while raw T09 media paths are ignored;
- full tests, dependency checks, CLI help, whitespace, and repository artifact
  policy pass;
- the atomic commit is pushed to `origin/mvp` and required CI jobs are green.

Only then may Dong, Phong, and Trinh create their branches from that exact
commit. T09 remains `IN_PROGRESS` until the complete Definition of Done in
`plan.md` has measured machine-readable and human-readable evidence.
