# ChromaLens AI — Repository Instructions for Coding Agents

Last updated: 2026-08-16  
Status: Active execution contract

## 1. Purpose

This file defines how a coding agent must work in this repository. It does not replace the product requirements or technical explanation. Its job is to prevent scope drift, undocumented decisions, unverifiable claims, and changes that cannot be demonstrated before the competition deadline.

The immediate objective is to produce a stable, explainable laptop MVP for Intel® Vietnam AI Impact Festival 2026. The deadline is 25 August 2026. Correctness, demonstrability, and evidence for the judging rubric take priority over feature count.

## 2. Mandatory reading order

Before editing code, read these files completely in this order:

1. `AGENTS.md` — operating rules and source-of-truth precedence.
2. `context.md` — competition, user problem, product scope, and product requirements.
3. `rubric.md` — official judging criteria and evidence expected from this project.
4. `plan.md` — selected MVP stack, task order, dependencies, gates, and Definition of Done.
5. `knowledge_plan_discussion.md` — technical background, terminology, algorithms, alternatives, and rationale.
6. `codinglog.md` — current implementation state, evidence, blockers, and prior decisions.

Do not start implementation after reading only `plan.md`. The rubric and context determine why the plan exists.

## 3. Source-of-truth precedence

When documents appear to conflict, use this precedence:

1. Official competition requirements quoted and linked in `context.md` and `rubric.md`.
2. MVP scope, acceptance criteria, and cut rules in `plan.md`.
3. Technical rationale in `knowledge_plan_discussion.md`.
4. Historical entries in `codinglog.md`.
5. Comments in source code.

If a conflict remains, stop the affected task, record it as `BLOCKED` in `codinglog.md`, and ask the repository owner. Do not silently choose a new product direction.

## 4. Required execution protocol

For each task in `plan.md`:

1. Confirm all dependency tasks are `DONE` or that the plan explicitly permits a fallback.
2. Add or update the task entry in `codinglog.md` with status `IN_PROGRESS`.
3. State the smallest implementation that satisfies the task's Definition of Done.
4. Inspect existing files and preserve unrelated user changes.
5. Implement the task without adding unapproved product scope.
6. Run the listed tests and record the exact commands and outcomes.
7. Record measured values as measured values; label estimates and targets clearly.
8. Update documentation or configuration when behavior, interfaces, or assumptions changed.
9. Change status to `DONE` only when every required acceptance criterion has evidence.
10. If incomplete, use `BLOCKED`, `PARTIAL`, or `DEFERRED`; never report partial work as complete.

## 5. Scope rules

### Must preserve

- The original camera frame and original estimated garment colors must remain available throughout the pipeline.
- Color matching must use the corrected estimate of the original garment color, never the assistive recolored display value.
- CVD profile is a user-selected setting (`protan`, `deutan`, or `tritan` plus severity). The application must not claim to diagnose a medical condition.
- CVD simulation and assistive recoloring are separate operations.
- Recoloring must be restricted to a garment/risk mask. Background pixels must not be intentionally recolored.
- Risk score, segmentation confidence, color confidence, and lighting quality are separate concepts.
- Runtime operation must be local/offline for the MVP unless the repository owner explicitly changes this requirement.
- External models, algorithms, datasets, and code must receive attribution and license review.

### Prohibited without explicit approval

- Training a new segmentation or end-to-end recoloring model from scratch.
- Replacing the modular pipeline with a monolithic model.
- Adding accounts, databases, cloud backends, WebRTC, mobile apps, SAM 2, ByteTrack, RAG, agents, or generative AI merely to increase technical complexity.
- Collecting or uploading camera frames by default.
- Presenting heuristic confidence as a calibrated probability.
- Hard-coding a universal rule such as “red always becomes purple.”
- Optimizing or quantizing a model before a correct baseline is demonstrated and saved.
- Deleting fallback implementations when adding an optimized backend.

## 6. Engineering conventions

- Target Python: 3.10 unless the environment proves another version is required.
- Use a `src/` package layout and explicit module boundaries described in `plan.md`.
- Use type hints for public functions and dataclasses for cross-module contracts.
- A binary mask is a boolean array of shape `H × W` aligned with the source frame.
- OpenCV camera frames are BGR. Any RGB/Lab conversion must be explicit at module boundaries.
- Do not mutate the source frame in-place outside the renderer. Render onto a copy.
- Configuration values and thresholds belong in configuration, not scattered magic numbers.
- All per-frame data must carry a frame ID and monotonic timestamp.
- Bounded queues only. Live inference must prefer the newest frame and drop stale work instead of accumulating latency.
- Every model backend must implement a common interface and have a documented fallback/error path.
- Use deterministic seeds in K-means and tests.
- Do not commit model weights or datasets unless their license, size, and repository policy permit it.

## 7. Test and evidence rules

At minimum, changes must be checked with:

- Unit tests for deterministic color, CVD, risk, and mask operations.
- Smoke tests for camera/video input and end-to-end rendering.
- A declared evaluation set containing controlled images and short videos.
- Performance measurement on the declared demo laptop: processed FPS, capture-to-display latency p50/p95, memory trend, and backend/device.
- Visual artifacts for segmentation mask, corrected image, color clusters, CVD-risk mask, recolored mask, and final overlay.

If a test cannot be run, record `NOT RUN` and the reason. Do not infer that it passes.

## 8. Definition of Done for the repository

The repository is competition-demo ready only when:

- A fresh environment can be installed using documented commands.
- One command launches the webcam demo; another can run against a sample video.
- The user can select CVD profile and severity.
- A garment mask is produced by an AI segmentation backend or documented fallback.
- The pipeline corrects lighting, extracts and names original color, calculates CVD risk, selectively recolors risky regions, and renders an outline/tag.
- The UI separately shows original color confidence, CVD risk level, and lighting quality.
- A matching suggestion is generated from original corrected colors.
- No unbounded frame queue or continuously growing latency is observed in the demo run.
- Automated tests pass, or known failures are explicitly documented and accepted by the owner.
- Evaluation metrics, limitations, ethical considerations, privacy behavior, licenses, and attribution are documented.
- `codinglog.md` accurately reflects the final repository state.

## 9. Completion response expected from an agent

When handing off a task, report:

1. Task ID and final status.
2. Outcome visible to the user.
3. Files changed.
4. Commands/tests run and results.
5. Metrics or screenshots generated.
6. Assumptions, limitations, and remaining risks.
7. Exact next task from `plan.md`.

Do not end with only “implemented successfully.”
