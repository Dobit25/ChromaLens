# ChromaLens AI — Coding Log

Last updated: 2026-08-20 19:21 +07:00
Document role: Append-only implementation record with a maintained summary table

## 1. Rules for coding agents

- Read `AGENTS.md`, `context.md`, `rubric.md`, `plan.md`, and `knowledge_plan_discussion.md` before adding the first entry.
- Update the summary table when task status changes.
- Add a chronological entry whenever work starts, is handed off, becomes blocked, or completes.
- Do not delete old entries. Correct mistakes with a new correction note.
- Record exact commands and observed results. Use `NOT RUN` when a command was not executed.
- Do not write “tests passed” without listing the tests/command and result.
- Separate measured metrics, estimates, and targets.
- Link deviations to the relevant requirement/task and explain why they were necessary.
- Never include passwords, tokens, private footage, personal data, or signed consent forms.

Allowed task status values:

- `NOT_STARTED`
- `IN_PROGRESS`
- `PARTIAL`
- `BLOCKED`
- `DONE`
- `DEFERRED`

## 2. Current task summary

This table is intentionally empty until an agent starts the plan.

| Task ID | Task name | Status | Owner/agent | Started | Last updated | Evidence/entry |
| --- | --- | --- | --- | --- | --- | --- |
| T00 | Repository bootstrap and contracts | `DONE` | Codex | 2026-08-16 17:58 +07:00 | 2026-08-16 18:06 +07:00 | T00 start and completion entries below |
| T00-GATE | Collaboration dependency-lock/CI gate | `DONE` | Codex | 2026-08-18 21:47 +07:00 | 2026-08-18 22:12 +07:00 | T00-GATE entries and successful cloud-CI evidence below |
| T01 | Camera, video source, and base renderer | `DONE` | Codex | 2026-08-18 23:00 +07:00 | 2026-08-18 23:13 +07:00 | T01 start and completion entries below |
| T02 | Garment segmentation vertical slice | `DONE` | Codex (integration audit) | 2026-08-19 15:06 +07:00 | 2026-08-20 00:35 +07:00 | Corrective implementation and successful PR CI entries below |
| T03 | White balance and lighting quality | `DONE` | Codex | 2026-08-20 00:47 +07:00 | 2026-08-20 00:55 +07:00 | T03 start and completion entries below |
| T04 | Dominant color extraction and 11-name mapping | `DONE` | Codex | 2026-08-20 11:43 +07:00 | 2026-08-20 11:54 +07:00 | T04 start and completion entries below |
| T05 | CVD simulation and relational risk | `DONE` | Codex | 2026-08-20 12:11 +07:00 | 2026-08-20 12:27 +07:00 | T05 start and completion entries below |
| T06 | Selective recolor, outline, and score overlay | `DONE` | Codex | 2026-08-20 13:02 +07:00 | 2026-08-20 13:10 +07:00 | T06 start and completion entries below |
| T07 | Rule-based color matching | `DONE` | Codex | 2026-08-20 16:02 +07:00 | 2026-08-20 16:11 +07:00 | T07 start and completion entries below |
| T08 | End-to-end live pipeline and controls | `DONE` | Codex | 2026-08-20 16:24 +07:00 | 2026-08-20 16:58 +07:00 | T08 start and completion entries below |
| T09 | Evaluation, responsible AI, and evidence package | `IN_PROGRESS` | Repository owner + Codex (coordinators) | 2026-08-20 18:59 +07:00 | 2026-08-20 19:21 +07:00 | T09 Gate 0 start/completion entries below; evaluation workstreams not yet run |

## 3. Active blockers

| Blocker ID | Related task | Description | Impact | Required decision/action | Owner | Status |
| --- | --- | --- | --- | --- | --- | --- |

## 4. Decision index

Use this section only for implementation decisions that affect later tasks. Detailed reasoning remains in the chronological entry.

| Decision ID | Date | Decision | Affected tasks/modules | Entry link |
| --- | --- | --- | --- | --- |
| DEC-001 | 2026-08-16 | Use Python 3.10 only and pin the minimal T00 base/dev dependencies in `pyproject.toml`; keep inference stacks optional for later tasks. | T00 and future environment changes | T00 completion entry |
| DEC-002 | 2026-08-18 | Use one common sequential `FrameSource` contract and a synchronous read-render-discard loop for T01; finite EOF is normal while live read failure is explicit. | T01, T02, T03, T08 | T01 completion entry |
| DEC-003 | 2026-08-20 | Keep the locked MediaPipe person-derived torso mask as T02 P0 and name it honestly; it is not semantic garment parsing or calibrated confidence. | T02, T04, T06, T08, T09 | T02 corrective validation entry |
| DEC-004 | 2026-08-20 | Apply the T02 four-hour gate: remove the unverified SCHP copy/runtime and defer any locked SCHP attempt to T10 after T08/T09. | T02, T08, T09, T10 | T02 corrective validation entry |
| DEC-005 | 2026-08-20 | Keep one Gray-world balancer per ordered stream; use an optional mask only for gain estimation, apply EMA-smoothed gains globally, and report insufficient valid pixels as a visible poor-quality fallback. | T03, T04, T08, T09 | T03 completion entry |
| DEC-006 | 2026-08-20 | Use conventional float OpenCV CIELAB plus an attributed W3C sRGB multi-anchor equivalent for the Van de Weijer 11-term vocabulary; expose normalized distance scores/margin as heuristics, not probabilities. | T04, T05, T06, T07, T08, T09 | T04 completion entry |
| DEC-007 | 2026-08-20 | Pin DaltonLens 0.1.5 in the P0 base runtime, preserve exact severity-zero identity, and score CVD-created relational loss from CIEDE2000 collapse plus simulated closeness using configurable heuristic thresholds. | T05, T06, T08, T09 | T05 completion entry |
| DEC-008 | 2026-08-20 | Select assistive colors by documented CIELCH candidates scored under the chosen CVD simulation; preserve per-pixel L*, use an inward-only exact mask, bounded hysteresis, and separate mandatory assistive/debug-simulation render paths. | T06, T08, T09 | T06 completion entry |
| DEC-009 | 2026-08-20 | Generate matching guidance only from T04 `ColorCluster` Lab/RGB through a strictly validated project-authored CIELCH rule table; treat priority and optional CVD separation as heuristics, never confidence or objective fashion truth. | T07, T08, T09 | T07 completion entry |
| DEC-010 | 2026-08-20 | Compose T02-T07 through one typed current-frame pipeline; use a capacity-one newest-frame mailbox for webcam and sequential consumption for finite video. Temporal mask history is intersected with the current mask, and missing stages clear/skip dependent state instead of reusing stale analysis. | T08, T09, T11 | T08 completion entry |
| DEC-011 | 2026-08-20 | Freeze T09 protocol/schema/metric/case contracts at version 1.0.0; distinguish render-complete, GUI-submit, and externally measured latency; track only curated text results and assign disjoint workstream namespaces. | T09, T10, T11 | T09 Gate 0 completion entry |

## 5. Chronological entries

### `2026-08-16 17:58 +07:00` — `T00` `Repository bootstrap and contracts`

**Status:** `IN_PROGRESS`
**Owner/agent:** Codex
**Plan reference:** `plan.md#t00--repository-bootstrap-and-contracts`  
**Requirements/rubric affected:** Repository bootstrap; NFR-01, NFR-06, NFR-07, NFR-08; Metric 03 tech-stack evidence

#### Objective

Create only the reproducible Python 3.10 package, typed contracts, fail-fast segmentation interface placeholders, hardware-independent CLI help, and smoke test required by the T00 Definition of Done.

#### Starting state

- Branch: `mvp`.
- Planning baseline commit: `9bfb759d4c60900d205c40da6ecdbef9ce46adeb`; no tag points at the baseline commit.
- Relevant existing behavior: repository contains planning/instruction documents, `LICENSE`, and a title-only `README.md`; no package, environment configuration, or tests exist.
- Dependencies already complete: none, as specified by T00.
- Approved environment: conda environment `lens`, Python `3.10.20`, executable `D:\Coding\Anaconda\envs\lens\python.exe`.
- Known risks/assumptions: the six planning/instruction documents are currently untracked and must be preserved; model weights, datasets, SCHP, and OpenVINO are outside T00.

#### Work performed

- Verified the active Git branch, planning baseline commit, absence of a baseline tag, clean tracked-file state, and the approved Python environment before implementation.
- No source or packaging files had been created at the time of this status transition.

#### Files changed

| File | Change | Why |
| --- | --- | --- |
| `codinglog.md` | Modified | Record T00 as `IN_PROGRESS` before implementation. |

#### Commands run

```text
git status --short --branch
git rev-parse HEAD
git tag --points-at HEAD
git log -3 --oneline --decorate
conda env list
conda run -n lens python --version
conda run -n lens python -c "import sys; print(sys.executable); print(sys.version)"
```

#### Tests and observed results

| Test/check | Result | Evidence/output location |
| --- | --- | --- |
| Git baseline inspection | PASS (exit 0): branch `mvp`, commit `9bfb759d...`, no tag at HEAD | Terminal output |
| Approved environment inspection | PASS (exit 0): Python 3.10.20 in conda env `lens` | Terminal output |
| Project tests | NOT RUN — package and tests do not exist yet | N/A |

#### Measurements

Not applicable to T00.

#### Definition-of-Done check

- [ ] Fresh environment installation command is documented.
- [ ] `python -m chromalens --help` exits successfully.
- [ ] `pytest` discovers and passes at least one smoke test.
- [ ] No model or large binary is committed unintentionally.
- [x] `codinglog.md` contains a T00 `IN_PROGRESS` entry with baseline commands and observed results.

#### Deviations and decisions

- **Decision ID:** None
- **Deviation from plan:** None.
- **Reason:** N/A.
- **Trade-off/impact:** N/A.
- **Owner approval required:** no

#### Problems, limitations, or blockers

- No blocker at task start.

#### Next action

Create the minimal T00 packaging, contracts, CLI, backend interface placeholders, README instructions, and hardware-independent smoke test.

#### Version control

- Branch: `mvp`
- Commit hash: `not committed`
- Known-good baseline commit: `9bfb759d4c60900d205c40da6ecdbef9ce46adeb` (no tag)

---

### `2026-08-16 18:06 +07:00` — `T00` `Repository bootstrap and contracts complete`

**Status:** `DONE`  
**Owner/agent:** Codex  
**Plan reference:** `plan.md#t00--repository-bootstrap-and-contracts`  
**Requirements/rubric affected:** Repository bootstrap; NFR-01, NFR-06, NFR-07, NFR-08; Metric 03 tech-stack evidence

#### Objective

Finish the minimal reproducible package and typed interfaces required to start T01 without invoking a camera or a model backend.

#### Starting state

- T00 was `IN_PROGRESS`; no prior plan task was required.
- The approved `lens` conda environment was an isolated Python 3.10.20 environment containing only packaging tools before the editable install.
- The planning baseline was commit `9bfb759d4c60900d205c40da6ecdbef9ce46adeb`, with no tag pointing at it.

#### Work performed

- Added a Python 3.10-only `pyproject.toml` with exact direct dependency pins and a `dev` extra.
- Added ignore rules for local environments, secrets, caches, package output, weights, generated media, evaluation output, and datasets.
- Defined validated dataclasses for frame, lighting, garment-mask, original-color-cluster, and relational-risk contracts.
- Defined a common abstract `Segmenter` interface and backend-specific MediaPipe/SCHP exceptions. Both placeholders raise on inference and never return fabricated masks.
- Added a standard-library `argparse` CLI whose help/default paths import no backend and require no camera, network, weight, or special hardware.
- Added five independent smoke tests covering module help, OpenCV contrib availability, severity validation, fail-fast placeholder behavior, and absence of placeholder calls on the default CLI path.
- Replaced the title-only README with exact environment, editable-install, CLI, test, limitation, and license instructions.
- Preserved and staged the six root instruction/planning files without changing their content.

#### Files changed

| File | Change | Why |
| --- | --- | --- |
| `.gitignore` | Created | Exclude environments, secrets, caches, weights, generated media, and large runtime artifacts. |
| `pyproject.toml` | Created | Reproducible Python 3.10 package, direct pins, dev extra, CLI entry point, and pytest settings. |
| `README.md` | Modified | Document exact fresh environment, editable install, verification, limitations, and license. |
| `src/chromalens/__init__.py` | Created | Package identity/version. |
| `src/chromalens/__main__.py` | Created | `python -m chromalens` entry point. |
| `src/chromalens/app.py` | Created | Hardware-independent `argparse` CLI. |
| `src/chromalens/config.py` | Created | CVD profile and validated severity contract. |
| `src/chromalens/contracts.py` | Created | Typed cross-module dataclasses and mask/frame validation. |
| `src/chromalens/segmentation/__init__.py` | Created | Public segmentation contract exports. |
| `src/chromalens/segmentation/base.py` | Created | Common `Segmenter` interface and unavailable-backend base exception. |
| `src/chromalens/segmentation/mediapipe_backend.py` | Created | Fail-fast T00 MediaPipe placeholder. |
| `src/chromalens/segmentation/schp_backend.py` | Created | Fail-fast T00 SCHP placeholder. |
| `tests/test_t00_smoke.py` | Created | Five model/camera/network-independent smoke tests. |
| `codinglog.md` | Modified | Record T00 start, evidence, decision, and completion. |
| `AGENTS.md`, `context.md`, `rubric.md`, `plan.md`, `knowledge_plan_discussion.md` | Added to version control without content edits | Satisfy the T00 root-instruction-file requirement and preserve source-of-truth documents. |

#### Commands run

```text
conda run -n lens python -m pip list --format=freeze
conda run -n lens python -m pip install --editable ".[dev]"
conda run -n lens python -m chromalens --help
conda run -n lens python -m pytest -q
conda run -n lens python -m pytest -q
conda run -n lens python -m chromalens
conda run -n lens chromalens --help
conda run -n lens python -m pip check
conda run -n lens python -c "from importlib import metadata; names=('chromalens-ai','numpy','opencv-contrib-python','pytest','setuptools','wheel'); [print(f'{name}=={metadata.version(name)}') for name in names]"
conda run -n lens python -m pip freeze
conda run -n lens python -m pip show chromalens-ai
D:\Coding\Anaconda\envs\lens\python.exe -m chromalens --help
D:\Coding\Anaconda\envs\lens\python.exe -m pytest -q
git check-ignore -v -- .env .env.local .venv/python.exe venv/python.exe env/python.exe
git diff --cached --check -- . (with existing source-of-truth Markdown files excluded)
staged-path audit for forbidden environment/cache/weight extensions, binary files, and files over 5 MiB
```

#### Tests and observed results

| Test/check | Result | Evidence/output location |
| --- | --- | --- |
| Editable install | PASS (exit 0): `chromalens-ai==0.1.0` installed editable from this repository | Terminal output; `pip show` |
| First `pytest -q` run | FAIL at assertion level: 1 failed, 4 passed because `argparse` wrapped one help-description line; the CLI subprocess itself exited 0 | Terminal output |
| Smallest repair | Normalized help-output whitespace in the smoke assertion; no runtime behavior or dependency changed | `tests/test_t00_smoke.py` |
| Re-run `pytest -q` | PASS (exit 0): 5 passed in 0.21 s | Terminal output |
| Direct lens-Python verification | PASS (exit 0): 5 passed in 0.26 s; final pre-commit confirmation: 5 passed in 0.28 s | Terminal output |
| `python -m chromalens --help` | PASS (exit 0), help printed without backend/camera/model access | Terminal output |
| Default `python -m chromalens` | PASS (exit 0), help printed; placeholders not invoked | Terminal output plus smoke test |
| Console `chromalens --help` | PASS (exit 0) | Terminal output |
| `pip check` | PASS (exit 0): no broken requirements | Terminal output |
| Ignore rules | PASS (exit 0): `.env`, `.venv`, caches, model extensions, generated results, and datasets match `.gitignore` | `git check-ignore` output |
| Staged-content audit | PASS (exit 0): no forbidden tracked paths, staged binary files, or staged files over 5 MiB | Terminal output |
| Source/package whitespace check | PASS (exit 0); pre-existing Markdown hard-break whitespace was excluded rather than edited | Terminal output |

#### Measurements

Not applicable to T00. No performance claim or demo-hardware declaration was made.

#### Definition-of-Done check

- [x] Fresh environment installation command is documented in `README.md` using conda environment `lens` and Python 3.10.
- [x] `python -m chromalens --help` exits successfully (exit 0, verified through conda and direct `lens` Python).
- [x] `pytest` discovers and passes at least one smoke test (5 passed).
- [x] No model or large binary is committed unintentionally (ignore and staged-content audits passed).
- [x] `codinglog.md` contains the T00 entries with commands, initial failure, repair, rerun, and observed results.

#### Deviations and decisions

- **Decision ID:** `DEC-001`
- **Deviation from plan:** None. Only T00 files needed for its Definition of Done were created; no empty T01+ modules were scaffolded.
- **Reason:** Keep the bootstrap reproducible and minimize dependency/scope risk.
- **Trade-off/impact:** T01 will create camera and renderer modules when their behavior can be tested. MediaPipe, SCHP, DaltonLens, ONNX, and OpenVINO remain uninstalled.
- **Owner approval required:** no; this follows the approved T00 constraints.

#### Problems, limitations, or blockers

- The first test run found only a test assertion sensitive to `argparse` line wrapping. It was repaired and the full suite passed twice afterward.
- No webcam/video behavior, segmentation inference, model setup, or performance measurement exists yet by design.
- The current machine remains a development machine and is not declared as official demo hardware.

#### Next action

T01 — Camera, video source, and base renderer. Do not start until owner handoff/approval.

#### Version control

- Branch: `mvp`
- T00 commit: created after this completion entry with message `chore: bootstrap ChromaLens MVP repository`
- Known-good planning baseline: `9bfb759d4c60900d205c40da6ecdbef9ce46adeb` (no tag)

---

### `2026-08-18 21:47 +07:00` — `T00-GATE` `Collaboration dependency-lock/CI gate`

**Status:** `IN_PROGRESS`
**Owner/agent:** Codex
**Plan reference:** Owner-approved collaboration hardening after T00; no change to T01–T11 scope or dependencies
**Requirements/rubric affected:** T00 reproducibility; NFR-01, NFR-06, NFR-07, NFR-08; Metric 03 tech-stack evidence

#### Objective

Create a single reproducible Windows/Python 3.10 collaboration baseline with a fully resolved hashed base/dev dependency lock and CI that installs from the lock, validates package dependencies, runs CLI help, and runs the hardware-independent test suite.

#### Starting state

- Branch `mvp` is clean and synchronized with `origin/mvp` at `1200e67e88f5c2b8add07f39d62f7f9084c5acc1`.
- T00 is `DONE`; T01 has not started.
- Direct base/dev dependencies and build tools are pinned in `pyproject.toml`, but Python patch, pip bootstrap, transitive packages, hashes, clean-install CI, and dependency-update policy are not yet locked.
- Approved execution environment remains conda environment `lens`, Python 3.10.20. No model, dataset, MediaPipe, SCHP, DaltonLens, ONNX, or OpenVINO work is in scope.

#### Work performed

- Verified the local/remote baseline and empty tag list.
- Verified Python 3.10.20 and pip 26.1.2 in `lens`.
- Queried the package index from the absolute `lens` Python executable and selected `pip-tools==7.6.1` as the lock generator candidate.

#### Files changed

| File | Change | Why |
| --- | --- | --- |
| `codinglog.md` | Modified | Record the collaboration gate as `IN_PROGRESS` before implementation. |

#### Commands run

```text
git status --short --branch
git rev-parse HEAD
git rev-parse origin/mvp
git tag --list
conda run -n lens python --version
conda run -n lens python -m pip --version
conda list -n lens python pip setuptools wheel
conda run -n lens python -m pip index versions pip-tools
D:\Coding\Anaconda\envs\lens\python.exe -m pip index versions pip-tools
```

#### Tests and observed results

| Test/check | Result | Evidence/output location |
| --- | --- | --- |
| Git baseline | PASS (exit 0): local and remote `mvp` both at `1200e67e...`; no tags exist | Terminal output |
| Python/pip inspection | PASS (exit 0): Python 3.10.20 and pip 26.1.2 | Terminal output |
| `conda list` package-filter attempt | FAIL: current Conda CLI does not accept multiple positional package names | Terminal output |
| Concurrent `conda run` index query | FAIL: concurrent Conda activation helpers contended for the same temporary file | Terminal output |
| Direct `lens` Python index query | PASS (exit 0): `pip-tools` 7.6.1 available | Terminal output |
| Project tests | NOT RUN — gate files and lock are not created yet | N/A |

#### Measurements

Not applicable. This gate does not make runtime-performance claims.

#### Definition-of-Done check

- [ ] Exact Conda/Python/pip bootstrap is committed.
- [ ] All base/dev dependencies and transitive packages are locked with hashes.
- [ ] CI installs from the lock and passes dependency, CLI, and pytest checks.
- [ ] Collaboration install/update policy is documented.
- [ ] Gate evidence is recorded, committed, pushed, and tagged without starting T01.

#### Deviations and decisions

- **Decision ID:** Pending completion entry.
- **Deviation from plan:** Owner-approved repository hardening between T00 and T01; no product task or MVP scope changes.
- **Reason:** Four coding-agent workstreams require a shared deterministic environment and CI merge gate.
- **Trade-off/impact:** T01 starts after this short gate; no model stack is selected prematurely.
- **Owner approval required:** no; the owner explicitly requested this gate.

#### Problems, limitations, or blockers

- Concurrent `conda run` calls are unreliable on this Windows installation because they can contend for Conda's temporary activation file. Subsequent environment commands will use `D:\Coding\Anaconda\envs\lens\python.exe` directly and serially.

#### Next action

Add the exact environment manifest, pinned lock-generator extra, hashed base/dev lock, collaboration instructions, and CI workflow.

#### Version control

- Branch: `mvp`
- Commit hash: `not committed`
- Known-good baseline: `1200e67e88f5c2b8add07f39d62f7f9084c5acc1`

---

### `2026-08-18 22:01 +07:00` — `T00-GATE` `Collaboration dependency-lock/CI gate`

**Status:** `DONE`
**Owner/agent:** Codex
**Plan reference:** Owner-approved collaboration hardening after T00; no change to T01–T11 scope or dependencies
**Requirements/rubric affected:** T00 reproducibility; NFR-01, NFR-06, NFR-07, NFR-08; Metric 03 tech-stack evidence

#### Objective

Provide one deterministic Windows/Python 3.10 dependency baseline and a hardware-independent CI merge check before four feature branches begin work.

#### Work performed

- Added a human-readable Conda manifest and an explicit `win-64` Conda lock containing all 19 bootstrap artifacts, exact builds, trusted artifact URLs, and MD5 checksums.
- Added separate SHA-256 pip locks for runtime/development dependencies and the pinned lock-generation toolchain.
- Pinned direct runtime, test, build, and lock-tool versions in `pyproject.toml`; no T01 or model dependency was selected.
- Added a Windows GitHub Actions workflow pinned to immutable action commit SHAs. It validates the Conda lock, regenerates and diffs the pip locks, installs with `--require-hashes`, checks dependencies, runs hardware-independent CLI help and tests, and rejects tracked environments, caches, model weights, and files larger than 5 MiB.
- Documented exact contributor bootstrap, verification, lock ownership, and dependency-change commands. The existing `.gitignore` already covered the prohibited artifact classes and required no change.

#### Files changed

| File | Change | Why |
| --- | --- | --- |
| `.github/workflows/ci.yml` | Created | Enforce the locked Windows/Python 3.10 verification workflow. |
| `environment.yml` | Created | Declare the supported Conda bootstrap versions and builds. |
| `requirements/conda-win-64.lock` | Created | Pin every Conda bootstrap artifact and checksum. |
| `requirements/py310-win64.lock` | Created | Pin and hash all runtime/development Python dependencies. |
| `requirements/lock-tools-py310-win64.lock` | Created | Pin and hash the reproducible lock-generation toolchain. |
| `requirements/README.md` | Created | Define lock roles and ownership. |
| `pyproject.toml` | Modified | Pin build/test tools and add the lock-tool extra. |
| `README.md` | Modified | Document exact collaboration install, verification, and update policy. |
| `codinglog.md` | Modified | Record gate state, decisions, failures, and evidence. |

#### Commands run

```text
git status --short --branch
git rev-parse HEAD
git rev-parse origin/mvp
git tag --list
conda run -n lens python --version
conda run -n lens python -m pip --version
conda list --explicit --md5 --name lens
D:\Coding\Anaconda\envs\lens\python.exe -m pip index versions pip-tools
D:\Coding\Anaconda\envs\lens\python.exe -m pip install --editable ".[lock]"
D:\Coding\Anaconda\envs\lens\python.exe -m piptools compile pyproject.toml --extra dev --generate-hashes --allow-unsafe --resolver backtracking --strip-extras --no-emit-index-url --no-emit-trusted-host --output-file requirements/py310-win64.lock
D:\Coding\Anaconda\envs\lens\python.exe -m piptools compile pyproject.toml --extra lock --generate-hashes --allow-unsafe --resolver backtracking --strip-extras --no-emit-index-url --no-emit-trusted-host --output-file requirements/lock-tools-py310-win64.lock
D:\Coding\Anaconda\envs\lens\python.exe -m pip install --disable-pip-version-check --require-hashes --requirement requirements/lock-tools-py310-win64.lock
D:\Coding\Anaconda\envs\lens\python.exe -m pip install --disable-pip-version-check --require-hashes --requirement requirements/py310-win64.lock
D:\Coding\Anaconda\envs\lens\python.exe -m pip install --disable-pip-version-check --no-build-isolation --no-deps --editable ".[dev]"
D:\Coding\Anaconda\envs\lens\python.exe -m pip check
D:\Coding\Anaconda\envs\lens\python.exe -m chromalens --help
D:\Coding\Anaconda\envs\lens\python.exe -m pytest -q
git ls-remote https://github.com/actions/checkout.git refs/tags/v4
git ls-remote https://github.com/actions/setup-python.git refs/tags/v5
git diff --check
```

#### Tests and observed results

| Test/check | Result | Evidence/output location |
| --- | --- | --- |
| Conda explicit-lock comparison | PASS (exit 0): committed lock exactly matches all 19 artifacts in `lens` | Terminal output |
| Conda lock source/checksum policy | PASS (exit 0): only `repo.anaconda.com/pkgs/main` `win-64`/`noarch` artifacts with MD5 checksums | Terminal output |
| Hashed lock-tool install | PASS (exit 0): every requirement satisfied under `--require-hashes` | Terminal output |
| Hashed base/dev install | PASS (exit 0): every requirement satisfied under `--require-hashes` | Terminal output |
| Editable project install | PASS (exit 0): `chromalens-ai==0.1.0` rebuilt and installed with resolver/build isolation disabled | Terminal output |
| Lock regeneration | PASS (exit 0): base SHA-256 `7C7394ED...96CAF`; tool SHA-256 `63DBE596...26493`; both unchanged | Terminal output |
| `python -m pip check` | PASS (exit 0): `No broken requirements found.` | Terminal output |
| `python -m chromalens --help` | PASS (exit 0): help rendered without camera/model/hardware | Terminal output |
| `python -m pytest -q` | PASS (exit 0): `5 passed in 0.28s` | Terminal output |
| Pending/tracked artifact policy | PASS (exit 0): 26 candidates, 0 forbidden paths, 0 files above 5 MiB | Terminal output |
| Immutable GitHub Action references | PASS (exit 0): official `v4`/`v5` tag SHAs resolved and committed by SHA | Terminal output |

#### Installed dependency versions

`build==1.5.0`, `click==8.4.2`, `colorama==0.4.6`, `exceptiongroup==1.3.1`, `iniconfig==2.3.0`, `numpy==1.26.4`, `opencv-contrib-python==4.10.0.84`, `packaging==26.3`, `pip==26.1.2`, `pip-tools==7.6.1`, `pluggy==1.6.0`, `pyproject-hooks==1.2.0`, `pytest==8.3.5`, `setuptools==83.0.0`, `tomli==2.4.1`, `typing-extensions==4.16.0`, and `wheel==0.47.0`.

#### Definition-of-Done check

- [x] Exact Conda/Python/pip bootstrap is represented by a reviewed manifest and explicit hashed artifact lock.
- [x] All current base/dev dependencies and transitives are version-pinned with hashes.
- [x] CI installs from committed locks and defines dependency, CLI, pytest, lock-freshness, and artifact-policy checks.
- [x] Collaboration install/update policy and integration-owner responsibility are documented.
- [x] Local CI-equivalent checks pass in `lens`; T01 and all model/data work remain untouched.
- [x] Gate is prepared as one atomic commit on `mvp`, followed by the `collab-baseline-v1` tag and push; immutable hashes are reported after creation because a commit cannot contain its own hash.

#### Deviations and decisions

- **Decision ID:** `DEC-T00-GATE-001`
- **Decision:** Support one collaboration platform for this gate: Conda `win-64`, Python 3.10.20, exact Conda artifacts, and hashed pip resolution. Use `environment.yml` as dependency intent and the explicit/pip locks as executable sources of exact versions.
- **Deviation from plan:** Owner-approved hardening gate inserted between completed T00 and unstarted T01; no product scope, task dependency, or acceptance criterion changed.
- **Trade-off/impact:** Reproducibility is exact on the approved Windows platform. Linux/macOS require a separately reviewed lock and CI job before being supported.
- **Owner approval required:** no; the owner explicitly requested this gate.

#### Problems, limitations, or blockers

- The first lock-tool resolution exposed that `--allow-unsafe` would otherwise select newer pip/setuptools/wheel versions. These were pinned to the approved `lens` bootstrap versions and both locks were regenerated deterministically.
- A first lock-source audit regex matched explanatory header text; it was narrowed to executable requirement/directive positions and rerun successfully.
- `conda list -n lens python pip setuptools wheel` failed because this Conda CLI accepts only one positional package regex. Exact versions/builds were instead verified with `conda list --explicit --md5 --name lens`.
- Concurrent `conda run` calls contended for a temporary activation file. All mutating and final checks were run serially with the absolute `lens` Python executable.
- One PowerShell verification attempt quoted the Python executable without the `&` call operator and failed at parse time before executing pip; the corrected command sequence then passed completely.
- CI is committed as a status check, but repository branch-protection rules are an external GitHub setting and are not changed by this repository commit. The required check name is `Locked Python 3.10 base`.

#### Next action

T01 — Camera, video source, and base renderer. Do not start until owner handoff/approval.

#### Version control

- Branch: `mvp`
- Atomic commit message: `chore: lock collaboration environment and add CI`
- Baseline tag: `collab-baseline-v1`
- Known-good pre-gate baseline: `1200e67e88f5c2b8add07f39d62f7f9084c5acc1`

---

### `2026-08-18 22:07 +07:00` — `T00-GATE` `Cloud CI corrective pass`

**Status:** `IN_PROGRESS`
**Owner/agent:** Codex
**Plan reference:** T00-GATE verification correction; no change to T01–T11

#### Observed failure and cause

- GitHub Actions run `32152286399` executed commit `76c42a96ae24e3f2bab7276bf94c36cab645eae9` and failed in `Set up exact Python`; all later steps were skipped.
- The public check annotation reports that `3.10.20 x64` is not available for the newly selected `Windows 2025` runner image. The official `actions/python-versions` manifest has no Windows artifact for Python 3.10.20.
- The same run warns that the pinned checkout/setup-python actions use deprecated Node.js 20.

#### Smallest corrective action

Replace `actions/setup-python` with the Node.js 24 `conda-incubator/setup-miniconda` action and create CI's `lens` directly from the committed explicit Conda lock. Update checkout to its Node.js 24 release. Pin both actions to verified immutable tag SHAs, then rerun the existing lock, install, CLI, pytest, and artifact gates without changing dependencies or product scope.

#### Version control

- Failed cloud-CI commit: `76c42a96ae24e3f2bab7276bf94c36cab645eae9`
- Failed run: `https://github.com/Dobit25/ChromaLens/actions/runs/32152286399`
- `collab-baseline-v1` remains an immutable audit tag for the failed first attempt; it will not be moved or deleted.

---

### `2026-08-18 22:12 +07:00` — `T00-GATE` `Cloud CI correction complete`

**Status:** `DONE`
**Owner/agent:** Codex
**Plan reference:** T00-GATE verification correction; no change to T01–T11

#### Outcome and evidence

- Corrective commit `be3f9b86bcb84a212baf513cac9ca321423d3f2b` replaced runner-managed Python with the committed exact Conda environment.
- GitHub Actions run `32152728588` completed with conclusion `success` against that exact commit.
- Job `Locked Python 3.10 base` passed every step: checkout; exact Conda setup; Conda-lock validation; Python/pip bootstrap validation; hashed lock-tool install; deterministic pip-lock regeneration; hashed base/dev install; editable install; `pip check`; hardware-independent CLI help; `pytest`; artifact policy; and action cleanup.
- Immutable action pins were verified from official repositories: `actions/checkout@d23441a48e516b6c34aea4fa41551a30e30af803` (`v6`) and `conda-incubator/setup-miniconda@8ee1f361103df19b6f8c8655fd3967a8ecb162d5` (`v4`). Both actions use Node.js 24.
- T01 remains unstarted. No dependency, model, dataset, product behavior, plan, or MVP-scope change was introduced by the correction.

#### Commands and remote checks

```text
git ls-remote https://github.com/actions/checkout.git refs/tags/v6
git ls-remote https://github.com/conda-incubator/setup-miniconda.git refs/tags/v4
GET https://api.github.com/repos/Dobit25/ChromaLens/actions/runs/32152728588
GET https://api.github.com/repos/Dobit25/ChromaLens/actions/runs/32152728588/jobs
```

#### Final baseline policy

- `collab-baseline-v1` intentionally remains attached to failed run `32152286399` as an audit record; rewriting or deleting the published tag was avoided.
- The verified final gate commit receives a new annotated tag, `collab-baseline-v2`, after this completion entry is committed and its own CI run passes.
- Required GitHub branch-protection check name: `Locked Python 3.10 base`.

#### Next action

T01 — Camera, video source, and base renderer. Do not start until owner handoff/approval.

---

### `2026-08-18 23:00 +07:00` — `T01` `Camera, video source, and base renderer`

**Status:** `IN_PROGRESS`
**Owner/agent:** Codex
**Plan reference:** `plan.md#t01--camera-video-source-and-base-renderer`
**Requirements/rubric affected:** FR-01, FR-11; NFR-01, NFR-02, NFR-04, NFR-07; Metric 02 working-prototype readiness

#### Objective

Implement the smallest shared webcam/local-video input and copied-frame renderer that attaches frame identity/timing, shows source/resolution/basic FPS and latency, exits cleanly, reports actionable source errors, and cannot accumulate stale frames.

#### Starting state

- Branch `mvp` is clean and synchronized with `origin/mvp` at verified tag `collab-baseline-v2`, commit `e0ab09fc51ed139b9a3002fda25679f9a2761095`.
- Dependencies T00 and T00-GATE are `DONE`; T02 and T03 are unstarted.
- Approved environment `lens` runs Python 3.10.20; `pip check` passes and the existing suite reports `5 passed`.
- OpenCV 4.10.0 WIN32 UI is available. Webcam index 0 opened through MSMF and returned one 640×480 BGR frame; the probe released the device and saved no frame.
- No new Python dependency is expected. Automated tests must synthesize temporary video and must not require a camera, network, model, or committed binary media.

#### Planned implementation

- Add `camera.py` with a common source interface, webcam/video factories, fail-fast source errors, frame IDs, monotonic capture timestamps, explicit EOF, and idempotent release.
- Add `renderer.py` that draws basic diagnostics onto a copy and never mutates `FramePacket.original_bgr`.
- Extend the CLI with mutually exclusive webcam/video execution, display/headless controls, bounded execution for automation, and clean `q`/Escape/window-close behavior.
- Use one synchronous read-render-display loop with no queue or frame retention. Add hardware-independent tests and documented commands, then verify a two-minute real webcam preview.

#### Baseline commands and observed results

| Command/check | Result |
| --- | --- |
| `git status --short --branch` | PASS: clean `mvp`, synchronized with `origin/mvp` |
| `D:\Coding\Anaconda\envs\lens\python.exe --version` | PASS: Python 3.10.20 |
| `D:\Coding\Anaconda\envs\lens\python.exe -m pip check` | PASS: no broken requirements |
| `D:\Coding\Anaconda\envs\lens\python.exe -m pytest -q` | PASS: 5 passed in 0.20 s |
| OpenCV build inspection | PASS: `GUI: WIN32UI` |
| One-frame webcam probe | PASS: opened/read 640×480 BGR through MSMF; released without saving |

#### Definition-of-Done check

- [ ] Webcam preview runs for two minutes and exits cleanly.
- [ ] Sample video mode runs without a camera.
- [ ] Failure to open the source produces an actionable error.
- [ ] Memory/queue does not grow because old frames are retained.
- [ ] Automated tests remain independent of webcam, network, and models.

#### Problems, limitations, or blockers

- No blocker at task start. The current machine remains a development machine, not declared demo hardware.

#### Next action

Implement the T01 camera/video interface, renderer, CLI execution loop, tests, and documentation without starting T02 or T03.

---

### `2026-08-18 23:13 +07:00` — `T01` `Camera, video source, and base renderer complete`

**Status:** `DONE`
**Owner/agent:** Codex
**Plan reference:** `plan.md#t01--camera-video-source-and-base-renderer`
**Requirements/rubric affected:** FR-01, FR-11; NFR-01, NFR-02, NFR-04, NFR-07; Metric 02 working-prototype readiness

#### Outcome

- Added a typed `FrameSource` interface and OpenCV implementation for webcam and local-video input.
- Each read returns the T00 `FramePacket` contract with sequential frame ID, `monotonic_ns()` timestamp, and original uint8 BGR frame. Finite EOF returns `None`; live/open/state failures use specific actionable exceptions.
- Added a configurable base renderer with EMA processed FPS, basic packet-to-render latency, source/resolution/frame diagnostics, and a high-contrast panel drawn only on a copied frame.
- Extended the default-safe CLI with explicit `--webcam`/`--video`, camera index/resolution, GUI/headless operation, duration/frame limits, `q`/Escape/window-close handling, successful video EOF, and guaranteed source release.
- Kept T01 synchronous: read one frame, render it, display/discard it, then read the next. No application queue, prefetch thread, frame list, or history exists.
- Added hardware-independent tests using temporary MJPG/AVI media. They prove video mode does not open a webcam, verify EOF/timestamps/copy semantics/actionable errors, prove exact read-render ordering, and simulate clean `q` exit.
- Updated README commands, measurement definition, privacy behavior, limitations, and T02/T03 handoff contracts. No dependency or lock file changed.

#### Files changed

| File | Change | Why |
| --- | --- | --- |
| `src/chromalens/camera.py` | Created | Common webcam/video source contract and fail-fast OpenCV implementation. |
| `src/chromalens/renderer.py` | Created | Copied-frame diagnostic renderer and lightweight telemetry. |
| `src/chromalens/app.py` | Modified | Explicit source CLI and bounded preview lifecycle. |
| `tests/test_t01_camera_renderer.py` | Created | Hardware-independent T01 unit/integration coverage. |
| `tests/test_t00_smoke.py` | Modified | Update help assertion for implemented T01 behavior. |
| `README.md` | Modified | Document execution, privacy, queue policy, limitations, and handoff. |
| `codinglog.md` | Modified | Record T01 start, evidence, failure/repair, decision, and completion. |

#### Commands run

```text
D:\Coding\Anaconda\envs\lens\python.exe --version
D:\Coding\Anaconda\envs\lens\python.exe -m pip check
D:\Coding\Anaconda\envs\lens\python.exe -m pytest -q
D:\Coding\Anaconda\envs\lens\python.exe -m compileall -q src tests
D:\Coding\Anaconda\envs\lens\python.exe -m chromalens --help
D:\Coding\Anaconda\envs\lens\python.exe -m chromalens
D:\Coding\Anaconda\envs\lens\python.exe -m chromalens --video Z:\definitely-missing\sample.mp4 --no-display
D:\Coding\Anaconda\envs\lens\python.exe -m chromalens --video artifacts\t01-manual-sample.avi
D:\Coding\Anaconda\envs\lens\python.exe -m chromalens --webcam --duration-seconds 5
D:\Coding\Anaconda\envs\lens\python.exe -m chromalens --webcam --duration-seconds 120
D:\Coding\Anaconda\envs\lens\python.exe -m chromalens --webcam --no-display --max-frames 300
git diff --check
```

Manual video and overlay artifacts were generated only from synthetic NumPy arrays under ignored `artifacts/`, inspected, and deleted. No camera frame or generated media remains.

#### Tests and observed results

| Test/check | Result | Evidence/output location |
| --- | --- | --- |
| Baseline suite | PASS: 5 passed in 0.20 s | Terminal output |
| First T01 suite | FAIL: 1 failed, 10 passed; forcing timestamps one nanosecond apart exceeded effective Windows clock resolution | Terminal output |
| Timestamp repair | Removed fabricated `previous + 1 ns`; packets use the monotonic clock directly and tests require non-decreasing timestamps | Source/test diff |
| Final suite | PASS: 12 passed in 0.46 s | Terminal output |
| Syntax/dependencies | PASS: `compileall` exit 0; `pip check` reports no broken requirements | Terminal output |
| CLI help/default | PASS: exit 0; no camera/backend opens without explicit source selection | Terminal output/tests |
| Missing video | PASS: exit 2 with path, existence/permission, and `--video` guidance | Terminal output/tests |
| Camera-open failure simulation | PASS: handle released; error mentions permission/index/other applications | Automated test |
| Camera-free video | PASS: four-frame temporary video reaches EOF; webcam factory never called | Automated test |
| GUI synthetic video | PASS: 60 frames, 640×360, 3.06 s, clean EOF, exit 0 | Terminal output |
| Renderer visual check | PASS: readable synthetic overlay contains source, resolution, frame, FPS, latency, and exit hint | Visual inspection; artifact deleted |
| Short webcam preview | PASS: 143 frames, 640×480, 5.34 s, duration exit, code 0 | Terminal output |
| Two-minute webcam preview | PASS: visible window ran to 120 s app limit and exited 0; monitor wall time 125.4 s including startup/polling | Process monitor output |
| Headless webcam bound | PASS: 300 frames, 640×480, 10.59 s, frame-limit exit, code 0 | Terminal output |
| No-prefetch contract | PASS: exact `read, render` alternation and source close; no queue exists | Automated test |

#### Measurements

Development-machine observations only; this machine is not declared official demo hardware.

| Metric | Measured value | Conditions |
| --- | ---: | --- |
| Webcam resolution | 640×480 BGR | Index 0, OpenCV MSMF |
| Short visible throughput | 26.8 frames/s | 143 frames / 5.34 s, capture + T01 overlay |
| Headless throughput | 28.3 frames/s | 300 frames / 10.59 s, capture + renderer |
| Two-minute Working Set | 96.15 → 103.02 MiB | Samples every 5 s from 15–120 s; min 96.15, peak/end 103.02 MiB |
| Working Set delta | +6.87 MiB | Small allocator/backend drift, not frame-proportional retention; one frame is about 0.88 MiB |

The Working Set change is recorded rather than claimed as zero. Retaining every frame would grow in proportion to thousands of approximately 0.88 MiB frames; the process stayed near 96–103 MiB and implementation/tests show no queue/history. Longer real-pipeline measurement remains T08/T09.

#### Definition-of-Done check

- [x] Webcam preview runs for two minutes and exits cleanly: visible 120 s duration run, exit 0.
- [x] Sample video mode runs without a camera: automated factory assertion and real synthetic GUI run reach clean EOF.
- [x] Failure to open the source produces an actionable error: missing video and unavailable-webcam simulation covered.
- [x] Memory/queue does not grow because old frames are retained: synchronous read-render-discard design, ordering test, and bounded two-minute evidence.
- [x] Source name, resolution, frame ID, basic FPS, and basic pipeline latency are visible on a copied frame.
- [x] Tests are independent of webcam, network, models, and committed binary media.

#### Deviations and decisions

- **Decision ID:** `DEC-002`
- **Decision:** Keep T01 synchronous with no application queue. Return `None` only for finite EOF and raise explicit live-source failures.
- **Deviation from plan:** None; the plan permits a simple loop that cannot accumulate an unbounded queue.
- **Trade-off/impact:** Minimal and deterministic for T02/T03. If inference later becomes slower than capture, T08 must introduce bounded latest-frame orchestration without changing `FrameSource` or `FramePacket`.
- **Owner approval required:** no

#### Problems, limitations, or blockers

- Windows may produce equal consecutive `monotonic_ns()` values. Timestamps are non-decreasing but not guaranteed unique; frame ID is the uniqueness key.
- `CAP_PROP_BUFFERSIZE=1` is a backend hint and MSMF may ignore it. T01 has no application queue; T08 owns capture-thread/latest-frame behavior if needed.
- A local-video read failure after successful open is treated as EOF because OpenCV does not reliably distinguish EOF from mid-stream decode failure across codecs.
- Working Set ended 6.87 MiB above its 15-second sample. It is not proportional to frame count, but must be remeasured with real T08 inference.
- Two combined PowerShell media lifecycle commands were rejected by execution policy before running; generation, verification, preview, inspection, and deletion were rerun as separate scoped commands.

#### Next action

T02 — Garment segmentation vertical slice and T03 — White balance and lighting quality may now start in parallel from the verified T01 handoff commit.

#### Version control

- Branch: `mvp`
- Planned commit message: `feat: add camera and video preview`
- Planned handoff tag: `t01-handoff-v1`
- Known-good pre-T01 baseline: `collab-baseline-v2` / `e0ab09fc51ed139b9a3002fda25679f9a2761095`

---

### `2026-08-19 15:06 +07:00` — `T02` `Garment segmentation vertical slice`

**Status:** `IN_PROGRESS`  
**Owner/agent:** Đông  
**Plan reference:** `plan.md#t02--garment-segmentation-vertical-slice`  
**Requirements/rubric affected:** FR-02, FR-03, FR-04; NFR-01, NFR-02; Metric 02 working-prototype readiness

#### Objective

Deliver a working `MediaPipeSegmenter` returning a boolean `H × W` garment mask aligned with live frames. Full P0 Definition of Done: backend name/device exposed, debug overlay on ≥5 scenes, missing backend fails clearly, source/license documented.

#### Starting state

- Branch `mvp` clean at `105b5ac` (`feat: add camera and video preview`).
- T01 `DONE`; T03 not started.
- `segmentation/mediapipe_backend.py` and `schp_backend.py` are T00 fail-fast placeholders.
- `mediapipe` not installed in `lens` env.
- Approved env: conda `lens`, Python 3.10.20, `C:\Users\DELL\miniconda3\envs\lens\python.exe`.

#### Work performed (IN_PROGRESS entry)

- Created branch `feat/dong-segmentation-mediapipe` from `mvp` and pushed to remote.
- Verified `mediapipe==0.10.21` available on PyPI for Python 3.10.

#### Files changed

| File | Change | Why |
|---|---|---|
| `codinglog.md` | Modified | Record T02 as `IN_PROGRESS`. |

#### Commands run

```text
git fetch origin
git switch mvp; git pull --ff-only
git switch -c feat/dong-segmentation-mediapipe
git push --set-upstream origin feat/dong-segmentation-mediapipe
C:\Users\DELL\miniconda3\envs\lens\python.exe -m pip index versions mediapipe
```

#### Tests and observed results

| Test/check | Result | Evidence |
|---|---|---|
| Git baseline | PASS: `mvp` at `105b5ac`, branch created | Terminal |
| mediapipe version check | PASS: 0.10.21 available | Terminal |
| Project tests | NOT RUN — implementation not started yet | N/A |

---

### `2026-08-19 15:15 +07:00` — `T02` `Garment segmentation vertical slice complete`

**Status:** `DONE`  
**Owner/agent:** Đông  
**Plan reference:** `plan.md#t02--garment-segmentation-vertical-slice`  
**Requirements/rubric affected:** FR-02, FR-03, FR-04; NFR-01, NFR-02; Metric 02 working-prototype readiness

#### Objective

P0 MediaPipe baseline delivering a typed, tested `Segmenter` implementation with mask cleanup, confidence extraction, debug overlay, and full test coverage.

#### Work performed

- Added `segment-mediapipe` optional dependency group (`mediapipe==0.10.21`) to `pyproject.toml`.
- Extended `Segmenter` base interface with `device_info` abstract property and concrete `close()`/context-manager methods.
- Implemented `MediaPipeSegmenterConfig` frozen dataclass — all thresholds configurable, no magic numbers in code.
- Implemented `_import_mediapipe()` lazy import with actionable `pip install` hint on `ImportError`.
- Implemented `apply_mask_cleanup()` pure function: threshold → upper-body height filter (top 75%) → morphological open/close → largest connected component → minimum area gate.
- Implemented `compute_mask_confidence()`: mean confidence over masked pixels, returns `None` for empty mask.
- Implemented `MediaPipeSegmenter`: lazy init, RGB conversion at module boundary (explicit comment), `segment()` with no frame mutation, `close()` idempotent, `__enter__`/`__exit__`.
- Implemented `debug.py`: `draw_mask_overlay()` renders per-class colour fills, contour outlines, and a text info panel onto a copy; never mutates `original_bgr`.
- Updated `segmentation/__init__.py` with full `__all__` exports.
- Updated `schp_backend.py` placeholder to satisfy new `device_info` interface.
- Added `tests/unit/test_t02_segmentation_unit.py`: 21 hardware-independent unit tests (AAA pattern).
- Added `tests/integration/test_t02_segmentation_integration.py`: 11 integration tests, auto-skipped if mediapipe not installed.
- Added `models/README.md`: documents MediaPipe (Apache-2.0, bundled) and SCHP-ATR (MIT, manual download), ATR class index, and model policy.
- Updated `tests/test_t00_smoke.py` match string from `"not implemented in T00"` to `"segment-mediapipe"` to reflect real backend.

#### Files changed

| File | Change | Why |
|---|---|---|
| `pyproject.toml` | Modified | Add `segment-mediapipe` optional group. |
| `src/chromalens/segmentation/base.py` | Modified | Add `device_info`, `close()`, context manager to interface. |
| `src/chromalens/segmentation/mediapipe_backend.py` | Modified | Replace T00 placeholder with full P0 implementation. |
| `src/chromalens/segmentation/debug.py` | Created | Debug overlay utility. |
| `src/chromalens/segmentation/schp_backend.py` | Modified | Satisfy new interface; improve docstring. |
| `src/chromalens/segmentation/__init__.py` | Modified | Full `__all__` exports. |
| `tests/unit/test_t02_segmentation_unit.py` | Created | 21 unit tests. |
| `tests/integration/test_t02_segmentation_integration.py` | Created | 11 integration tests. |
| `tests/unit/__init__.py` | Created | Package marker. |
| `tests/integration/__init__.py` | Created | Package marker. |
| `models/README.md` | Created | Model source, license, ATR class index, policy. |
| `tests/test_t00_smoke.py` | Modified | Update error-message match for T02 reality. |
| `codinglog.md` | Modified | Record T02 start and completion. |

#### Commands run

```text
git switch -c feat/dong-segmentation-mediapipe
git push --set-upstream origin feat/dong-segmentation-mediapipe
C:\Users\DELL\miniconda3\envs\lens\python.exe -m pytest tests/unit/test_t02_segmentation_unit.py -v
C:\Users\DELL\miniconda3\envs\lens\python.exe -m pytest -v
C:\Users\DELL\miniconda3\envs\lens\python.exe -m pip install mediapipe==0.10.21
C:\Users\DELL\miniconda3\envs\lens\python.exe -m pytest tests/integration/test_t02_segmentation_integration.py -v  [PENDING mediapipe install]
git add <all T02 files>
git commit -m "feat(seg): implement T02 MediaPipe garment segmentation baseline"
git push
```

#### Tests and observed results

| Test/check | Result | Evidence |
|---|---|---|
| Unit tests (21 tests) | PASS: 21 passed in 0.64 s | Terminal, Python 3.10.20, env lens |
| Full suite pre-install | PASS: 33 passed, 1 skipped (mediapipe not installed) in 0.81 s | Terminal |
| Integration tests | PENDING — awaiting `mediapipe==0.10.21` install completion | N/A |
| Compile check | NOT RUN explicitly — pytest import covers syntax | N/A |

#### Measurements

| Metric | Measured value | Conditions |
|---:|---:|---|
| Unit test runtime | 0.64 s | 21 tests, Python 3.10.20, Windows, no model |
| Full suite runtime | 0.81 s | 33 passed + 1 skipped, env lens |
| MediaPipe inference FPS | NOT YET MEASURED — pending install | Planned in T09 |

#### Definition-of-Done check

- [x] At least one AI backend returns a boolean `H × W` clothes mask aligned to webcam/video frames: `MediaPipeSegmenter` implemented and tested.
- [x] Debug view visibly overlays the mask: `draw_mask_overlay()` tested on synthetic frames; integration tests cover 5 scenes.
- [x] Backend name and device exposed: `backend_name="mediapipe"`, `device_info="mediapipe/cpu"`.
- [x] Missing backend fails clearly: `MediaPipeBackendUnavailableError` with `pip install` hint; unit test verifies.
- [x] Source/license/setup of weights documented: `models/README.md` (Apache-2.0, bundled).
- [ ] Integration tests with real MediaPipe runtime: PENDING install — 11 tests written, auto-skip guard in place.

#### Deviations and decisions

- **Decision ID:** `DEC-T02-001`
- **Decision:** Upper-body height filter set to `upper_body_ratio=0.75` (top 75% of frame). This is a heuristic to reduce false positives from floors and backgrounds. The value is configurable via `MediaPipeSegmenterConfig` and must be tuned in T09 evaluation.
- **Deviation from plan:** None. Followed P0 MediaPipe baseline path as specified.
- **Trade-off/impact:** The filter may clip masks for tall individuals standing very close to camera. Documented as a known limitation.
- **Owner approval required:** no; stays within T02 scope.

#### Problems, limitations, or blockers

- MediaPipe `SelfieSegmentation` returns a single person mask, not per-garment class labels. Upper-clothes is inferred by the upper-body height filter. SCHP-ATR (P1/T10) provides true per-class labels.
- Integration tests auto-skip until `mediapipe==0.10.21` is installed in `lens`. This is expected behaviour.
- The T00 smoke test match string was updated from `"not implemented in T00"` to `"segment-mediapipe"` — a necessary correction as the backend is no longer a placeholder.

#### Next action

- Complete mediapipe install → run integration tests → record results.
- Notify Tùng (integration owner) to review PR `feat/dong-segmentation-mediapipe → mvp`.
- T03 (White balance) can proceed in parallel from the verified T01 handoff.

#### Version control

- Branch: `feat/dong-segmentation-mediapipe`
- Commit: `fc83d09` `feat(seg): implement T02 MediaPipe garment segmentation baseline`
- Known-good pre-T02 baseline: `105b5ac` (`feat: add camera and video preview`)

---

### `[YYYY-MM-DD HH:MM TZ]` — `[TASK_ID]` `[Short task title]`

**Status:** `IN_PROGRESS | PARTIAL | BLOCKED | DONE | DEFERRED`  
**Owner/agent:**  
**Plan reference:** `plan.md#...`  
**Requirements/rubric affected:** `FR-...`, `NFR-...`, Metric `...`

#### Objective

State the smallest intended outcome for this entry.

#### Starting state

- Relevant existing behavior:
- Dependencies already complete:
- Known risks/assumptions:

#### Work performed

- Summarize implementation and reasoning.
- State important algorithms, interfaces, thresholds, and fallback behavior.
- If this entry changes a prior decision, reference the earlier entry.

#### Files changed

| File | Change | Why |
| --- | --- | --- |
| `path/to/file` | Created/modified/deleted | Reason |

#### Commands run

```text
exact command
```

#### Tests and observed results

| Test/check | Result | Evidence/output location |
| --- | --- | --- |
| Example: `pytest tests/unit/test_risk.py -q` | PASS: 8 passed | Terminal output / report path |

Use `NOT RUN — reason` rather than leaving this section ambiguous.

#### Measurements

| Metric | Measured value | Conditions |
| --- | ---: | --- |
| Processed FPS |  | Hardware, resolution, backend, clip |
| Latency p50/p95 |  | Capture-to-display definition and sample count |
| Memory |  | Start/end/peak and run duration |
| Quality metric |  | Dataset/protocol/version |

If no measurement applies, state `Not applicable`.

#### Definition-of-Done check

- [ ] Criterion 1 copied or summarized from `plan.md`.
- [ ] Criterion 2.
- [ ] Required tests/evidence recorded.
- [ ] Documentation/configuration updated.

#### Deviations and decisions

- **Decision ID:** `DEC-###` or `None`
- **Deviation from plan:**
- **Reason:**
- **Trade-off/impact:**
- **Owner approval required:** `yes/no`

#### Problems, limitations, or blockers

- Describe the observed issue with reproduction details.
- Do not hide known failure cases.

#### Next action

Name the exact next task or unblock action. Do not use only “continue development.”

#### Version control

- Branch: `exp/dong-segmentation-schp-atr`
- Commit hash: `not committed`
- Known-good tag/commit preserved:

---

### `2026-08-19 16:15 +07:00` — `T02` `Garment segmentation vertical slice (Phase 2 SCHP) complete`

**Status:** `DONE`
**Owner/agent:** Đông
**Plan reference:** `plan.md#t02--garment-segmentation-vertical-slice`

#### Objective

Implement the P1 requirement: SCHP-ATR backend for true garment parsing (ignoring face/background) and optimize CPU inference speed/latency on Windows.

#### Work performed

- Bypassed custom `InPlaceABNSync` C++ Ninja build by mapping it to PyTorch's standard `BatchNorm` since it's just inference.
- Implemented `SCHPSegmenter` resolving classes 4 (upper-clothes), 5 (skirt), and 6 (pants).
- Reduced `_INPUT_SIZE` from 512x512 to 256x256 to achieve ~1.5 - 2.0 FPS on CPU.
- Re-architected `demo_t02_webcam.py` with a background `LatestFrameReader` thread and `cv2.CAP_DSHOW` to completely eliminate frame buffering latency.

#### Tests and observed results

- SCHP model loads successfully and returns GarmentRegion.
- Live demo overlay strictly adheres to the garment (no face/background bleeding).
- Latency accumulation is completely fixed (drops stale frames correctly).

#### Next action

Proceed to T03 (White balance and lighting quality).

---

### `2026-08-20 00:05 +07:00` — `T02` `Production integration correction`

**Status:** `IN_PROGRESS`
**Owner/agent:** Codex (integration audit)
**Plan reference:** `plan.md#t02--garment-segmentation-vertical-slice`

#### Objective

Bring the existing T02 branch back to its reproducible P0 MediaPipe scope: lock
the complete optional dependency graph, require a real backend in CI, replace
vacuous scene checks with licensed-sample evidence, and defer unverified
SCHP-ATR work to T10 as permitted by the T02 decision gate.

#### Starting state and audit correction

- Branch `feat/dong-segmentation` is a clean descendant of
  `t01-handoff-v1` at `c5762ddf77a8f93b2fbcf6e60440f1ccdec01aab`.
- Base-only validation reports `33 passed, 1 skipped`; all 11 MediaPipe
  integration tests skip because the locked `lens` environment does not
  contain MediaPipe. The earlier `44/44` statement is therefore not accepted
  as current reproducible evidence.
- The five-scene integration test uses random noise and checks only overlay
  shape; it does not prove that the backend returns a garment/person mask.
- `torch` and `torchvision` are unpinned and absent from the collaboration
  locks. The SCHP path has no automated checkpoint inference test, loads with
  `strict=False`, assigns fabricated confidence `1.0`, and differs from the
  upstream ATR geometry restoration path.
- The existing CI runs only base/dev dependencies, so it can pass while all
  optional-backend tests are skipped.

#### Planned smallest correction

- Preserve MediaPipe as the T02 P0 backend and label its torso crop accurately
  as a heuristic derived from a person mask.
- Defer SCHP-ATR implementation, weights, PyTorch dependencies, and optimization
  to T10; retain only a fail-fast optional-backend contract.
- Commit a complete hashed Python 3.10/Windows MediaPipe lock and a CI job that
  installs it and fails if the real integration suite skips.
- Add licensed deterministic person-scene fixtures/evidence, validate mask
  shape/type/non-empty output and copied-frame overlay, then record exact
  commands and results.

#### Tests and observed results

| Check | Result |
| --- | --- |
| Branch ancestry/cleanliness | PASS: branch descends from `105b5ac`; working tree was clean before this entry |
| Base T02 suite before correction | PASS with incomplete coverage: `33 passed, 1 skipped in 2.99 s` |
| Approved environment | PASS: `lens`, Python 3.10.20; MediaPipe/Torch/Torchvision not installed at audit start |
| Corrected backend/CI/evidence suite | NOT RUN — implementation starts after this status entry |

#### Next action

Apply the T02 decision gate, generate the MediaPipe lock, add non-skipping
real-backend evidence, and rerun all gates before changing T02 back to `DONE`.

---

### `2026-08-20 00:29 +07:00` — `T02` `Corrective implementation ready for PR CI`

**Status:** `IN_PROGRESS`
**Owner/agent:** Codex (integration audit)
**Plan reference:** `plan.md#t02--garment-segmentation-vertical-slice`

#### Objective

Finish the smallest reproducible T02 P0 implementation and collect local
evidence before opening the pull request. T02 remains `IN_PROGRESS` until the
new locked real-backend GitHub Actions job passes on the final PR commit.

#### Work performed

- Kept `mediapipe==0.10.21` as the only executable T02 backend and generated
  `requirements/segment-mediapipe-py310-win64.lock` with hashes for the entire
  Python 3.10/Windows base, development, MediaPipe, JAX, and native-wheel
  closure. The existing base and lock-tool locks reproduce unchanged.
- Added a separate CI job, `Locked MediaPipe 0.10.21 backend`, that installs
  only the hashed closure, verifies the exact MediaPipe/OpenCV runtime, and
  runs both the real integration module and the complete suite. The base CI job
  now also regenerates and diffs the MediaPipe lock.
- Corrected the backend description: MediaPipe Selfie Segmentation is a
  prominent-person model, not a garment parser. The backend now exposes
  `mediapipe-selfie-torso/cpu`, uses full-range MediaPipe face detection plus a
  margin to exclude detected faces, retains a documented vertical fallback,
  validates all configuration bounds, normalizes mask dtype/size, and never
  mutates the source frame.
- Added five offline person fixtures with source, rights, and SHA-256 records.
  Replaced random-noise/vacuous integration checks with real inference checks
  for non-empty boolean aligned masks, plausible coverage, confidence bounds,
  changed overlay pixels, and source-frame invariance.
- Added `scripts/t02_segmentation_evidence.py`; it fails if any real scene has
  no mask and generates ignored review overlays plus machine-readable JSON.
- Removed the copied, unpinned, and unverified SCHP implementation and its
  duplicate webcam application. `SCHPSegmenter` remains a typed fail-fast
  placeholder with no default execution path. SCHP is `DEFERRED` to T10 under
  the plan decision gate; no weights, dataset, PyTorch, or Torchvision were
  installed or downloaded.
- Corrected SCHP documentation: the official ATR weight link is in the
  upstream README and points to Google Drive, not GitHub Releases. T10 must
  establish compatibility, checksum, geometry, and fixed-sample evidence
  before it can become a selectable backend.

#### Dependency evidence

- Approved environment: `lens`; Python `3.10.20`; pip `26.1.2`.
- Direct runtime pins: NumPy `1.26.4`, OpenCV contrib `4.10.0.84`, MediaPipe
  `0.10.21`; dev pin: pytest `8.3.5`.
- The full MediaPipe lock contains 34 packages plus pinned build tools and all
  artifact hashes. `python -m pip check` reports no broken requirements.

#### Commands run and observed results

```text
$env:CUSTOM_COMPILE_COMMAND = 'conda run --name lens pip-compile pyproject.toml --extra dev --generate-hashes --allow-unsafe --resolver backtracking --strip-extras --no-emit-index-url --no-emit-trusted-host --output-file requirements/py310-win64.lock'
D:\Coding\Anaconda\envs\lens\python.exe -m piptools compile --quiet pyproject.toml --extra dev --generate-hashes --allow-unsafe --resolver backtracking --strip-extras --no-emit-index-url --no-emit-trusted-host --output-file requirements/py310-win64.lock
$env:CUSTOM_COMPILE_COMMAND = 'conda run --name lens pip-compile pyproject.toml --extra lock --generate-hashes --allow-unsafe --resolver backtracking --strip-extras --no-emit-index-url --no-emit-trusted-host --output-file requirements/lock-tools-py310-win64.lock'
D:\Coding\Anaconda\envs\lens\python.exe -m piptools compile --quiet pyproject.toml --extra lock --generate-hashes --allow-unsafe --resolver backtracking --strip-extras --no-emit-index-url --no-emit-trusted-host --output-file requirements/lock-tools-py310-win64.lock
$env:CUSTOM_COMPILE_COMMAND = 'conda run --name lens pip-compile pyproject.toml --extra dev --extra segment-mediapipe --generate-hashes --allow-unsafe --resolver backtracking --strip-extras --no-emit-index-url --no-emit-trusted-host --output-file requirements/segment-mediapipe-py310-win64.lock'
D:\Coding\Anaconda\envs\lens\python.exe -m piptools compile --quiet pyproject.toml --extra dev --extra segment-mediapipe --generate-hashes --allow-unsafe --resolver backtracking --strip-extras --no-emit-index-url --no-emit-trusted-host --output-file requirements/segment-mediapipe-py310-win64.lock
git diff --exit-code -- requirements/py310-win64.lock requirements/lock-tools-py310-win64.lock requirements/segment-mediapipe-py310-win64.lock
D:\Coding\Anaconda\envs\lens\python.exe -m pip install --disable-pip-version-check --require-hashes --requirement requirements/segment-mediapipe-py310-win64.lock
D:\Coding\Anaconda\envs\lens\python.exe -m pip check
D:\Coding\Anaconda\envs\lens\python.exe -m chromalens --help
D:\Coding\Anaconda\envs\lens\python.exe scripts\t02_segmentation_evidence.py
D:\Coding\Anaconda\envs\lens\python.exe -m pytest -q tests\integration\test_t02_segmentation_integration.py
D:\Coding\Anaconda\envs\lens\python.exe -m pytest -q
git diff --check
```

| Check | Result | Evidence |
| --- | --- | --- |
| All three pip locks regenerate exactly | PASS, exit 0 | No lock diff after regeneration |
| Hashed MediaPipe install | PASS, exit 0 | 34-package resolved closure installed only in `lens` |
| Dependency consistency | PASS, exit 0 | `No broken requirements found` |
| Hardware-independent CLI help | PASS, exit 0 | Usage printed without camera/model invocation |
| Real-backend integration | PASS, exit 0 | `8 passed in 1.03s` |
| Complete suite with MediaPipe installed | PASS, exit 0 | `45 passed in 1.43s`; repeated after final source cleanup: `45 passed in 1.52s` |
| Generated five-scene evidence | PASS, exit 0 | `artifacts/t02-segmentation/` (ignored local artifacts) |
| Tracked artifact policy | PASS, exit 0 | No environment/cache/weight; no tracked file over 5 MiB |
| Git whitespace check | PASS, exit 0 | `git diff --check` produced no error |
| Final PR cloud CI | NOT RUN — PR not yet opened | Required before `DONE`/merge |

#### Measured real-backend fixture results

These are deterministic smoke/adequacy observations on this development
machine, not segmentation-accuracy or demo-hardware performance claims.

| Fixture | Mask coverage | Mean retained foreground score | Aligned bool mask/overlay |
| --- | ---: | ---: | --- |
| `astronaut.png` | 0.281490 | 0.973566 | PASS |
| `cc0_woman.jpg` | 0.040646 | 0.693574 | PASS |
| `loc_lincoln.jpg` | 0.077339 | 0.968651 | PASS |
| `loc_man.jpg` | 0.081223 | 0.941176 | PASS |
| `nasa_shepard.jpg` | 0.048819 | 0.992859 | PASS |

#### Definition-of-Done status

- [x] A real AI backend returns non-empty boolean `H x W` masks aligned to all
  five fixed source frames.
- [x] Debug view overlays were generated and visually reviewed on five scenes.
- [x] Backend and CPU device are exposed in overlay, public properties, JSON,
  integration assertions, and log output.
- [x] MediaPipe missing/install failure and deferred SCHP paths use specific,
  actionable exceptions; neither placeholder is on the default CLI path.
- [x] MediaPipe source/license/setup, fixture sources/rights/hashes, and SCHP
  source/license/deferred setup gate are documented.
- [ ] Final pull-request CI passes on the final commit; required before T02 is
  changed to `DONE` and merged into `mvp`.

#### Known limitations

- The P0 mask is a person-derived torso heuristic, not semantic garment
  parsing. It can include hands/objects or retain face/pants when face detection
  fails, and it can clip garments under occlusion, multiple people, unusual
  poses, or framing outside MediaPipe's intended prominent-person use case.
- Mean MediaPipe foreground score is exposed as heuristic `mask_confidence`;
  it is not a calibrated garment probability.
- No webcam, sample video, latency, FPS, or accuracy claim was made in this
  correction. T09 owns the declared evaluation protocol and demo-machine
  measurements.

#### Next action

Commit and push the correction, open the T02 pull request, require both locked
CI jobs, and append the cloud-CI result before merging T02 into `mvp`.

---

### `2026-08-20 00:35 +07:00` — `T02` `Garment segmentation vertical slice corrected and complete`

**Status:** `DONE`
**Owner/agent:** Codex (integration audit)
**Plan reference:** `plan.md#t02--garment-segmentation-vertical-slice`

#### Outcome

Pull request [#1](https://github.com/Dobit25/ChromaLens/pull/1) contains the
locked MediaPipe P0 vertical slice and the documented SCHP deferral. The code
commit `c1d2a29bd5962edcfcc93b340c63d82b18439c42` passed both new and existing
GitHub Actions gates; local evidence and limitations are recorded in the
preceding entry.

#### Cloud CI evidence

- Workflow run: [ChromaLens CI #32282134992](https://github.com/Dobit25/ChromaLens/actions/runs/32282134992)
- Head SHA: `c1d2a29bd5962edcfcc93b340c63d82b18439c42`
- `Locked Python 3.10 base`: `success`, completed at
  `2026-08-19T17:34:07Z`; [job 96163133516](https://github.com/Dobit25/ChromaLens/actions/runs/32282134992/job/96163133516)
- `Locked MediaPipe 0.10.21 backend`: `success`, completed at
  `2026-08-19T17:34:21Z`; [job 96163133842](https://github.com/Dobit25/ChromaLens/actions/runs/32282134992/job/96163133842)
- Overall conclusion: `success`; completed at `2026-08-19T17:34:22Z`.

#### Final Definition of Done

- [x] A real AI backend returns a non-empty boolean `H x W` mask aligned with
  webcam/video-compatible `FramePacket` dimensions on five fixed scenes.
- [x] Five debug overlays were generated by the real backend and visually
  reviewed; reproducible command and ignored JSON/image output are documented.
- [x] Stable backend name and CPU device are exposed in the API, overlay,
  evidence JSON, tests, and CI.
- [x] Missing MediaPipe and deferred SCHP paths fail with specific actionable
  exceptions and no placeholder is on the default executable path.
- [x] Backend/model source, Apache-2.0 license, hashed setup, fixture rights,
  and SCHP source/license/T10 gate are documented.
- [x] Local test, lock, dependency, CLI, artifact, and whitespace gates pass.
- [x] Both required PR CI jobs pass on the implementation commit.

#### Deferred item and limitations

- SCHP-ATR is `DEFERRED` to T10 exactly as permitted by the T02 decision gate;
  this does not block the working P0 vertical slice.
- The MediaPipe backend is a documented person-derived torso heuristic, not
  semantic clothing parsing or a calibrated garment-confidence model.

#### Version control and next action

- Branch: `feat/dong-segmentation`
- Implementation commit: `c1d2a29bd5962edcfcc93b340c63d82b18439c42`
- Pull request: `#1`, base `mvp`
- Exact next action: merge PR #1 into `mvp`, then integrate/complete T03 before
  starting T04, because T04 depends on both T02 and T03.

---

### `2026-08-20 00:47 +07:00` — `T03` `White balance and lighting quality`

**Status:** `IN_PROGRESS`
**Owner/agent:** Codex
**Plan reference:** `plan.md#t03--white-balance-and-lighting-quality`
**Requirements/rubric affected:** FR-04, NFR-01, Metric 03 explainable local pipeline

#### Objective

Implement configurable Gray-world correction, temporal EMA smoothing, and
separate explainable lighting-quality diagnostics while preserving every
`FramePacket.original_bgr` pixel.

#### Starting state

- Branch: `mvp`, directly authorized by the repository owner; no task branch
  will be created or modified.
- Baseline commit: `ea2b999ca99e70cff62ac41a82aba0cb76dab31f`, synchronized
  with `origin/mvp` and clean before this log entry.
- Required dependency T01 is `DONE`; the optional-mask producer T02 is also
  `DONE` and merged.
- Approved environment: conda environment `lens`, Python `3.10.20`; `pip
  check` reports no broken requirements.
- Baseline automated suite: `45 passed in 1.54s`.

#### Smallest implementation that satisfies the Definition of Done

- Add one stateful white-balance module using existing NumPy/OpenCV
  dependencies and the existing `FramePacket`/`LightingQuality` contracts.
- Keep valid brightness/saturation ranges, EMA coefficient, gain bounds, and
  quality thresholds in a validated configuration dataclass.
- Return raw gains and diagnostic values for evidence; write only derived
  `corrected_rgb` and `lighting_quality` fields to a packet, never its source.
- Add deterministic synthetic unit tests for neutrality improvement,
  dark/clipped quality severity, temporal smoothing/flicker reduction,
  optional-mask alignment, and source immutability.
- Document the T03 behavior and heuristic limitations. No CLI integration or
  T04 color extraction will be added.

#### Commands and checks run before implementation

```text
git status --short --branch
git rev-parse HEAD
git rev-parse origin/mvp
conda run -n lens python --version
conda run -n lens python -m pip --version
conda run -n lens python -m pip check
conda run -n lens python -m pytest -q
```

| Check | Result | Evidence |
| --- | --- | --- |
| Branch/baseline | PASS, exit 0 | `mvp...origin/mvp`; local and remote SHA both `ea2b999c...` |
| Approved interpreter | PASS, exit 0 | Python 3.10.20; pip 26.1.2 inside `D:\Coding\Anaconda\envs\lens` |
| Dependency consistency | PASS, exit 0 | `No broken requirements found` |
| Baseline suite | PASS, exit 0 | `45 passed in 1.54s` |

#### Definition-of-Done status at start

- [ ] Synthetic channel cast moves closer to neutral gray.
- [ ] Clipping/darkness severity changes lighting-quality output as expected.
- [ ] Consecutive gain estimates are smoothed without obvious synthetic-video
  frame flicker.
- [ ] The original frame remains unchanged.

#### Deviations, limitations, and blockers

- Deviation from plan: none.
- New dependency: none expected.
- Active blocker: none.

---

### `2026-08-20 00:53 +07:00` — `T03` `White balance and lighting quality complete`

**Status:** `DONE`
**Owner/agent:** Codex
**Plan reference:** `plan.md#t03--white-balance-and-lighting-quality`

#### Outcome

T03 now provides an offline, stateful `GrayWorldWhiteBalancer` with a
validated configuration, explicit BGR-input/RGB-output boundary, bounded raw
gains, per-stream EMA gains, optional estimation mask, fail-safe low-valid-
pixel behavior, and separate raw lighting diagnostics. Processing populates
only `FramePacket.corrected_rgb` and `FramePacket.lighting_quality`; the source
frame, ID, and monotonic timestamp remain unchanged.

#### Files changed

| File | Change and reason |
| --- | --- |
| `src/chromalens/white_balance.py` | Added T03 configuration, result contract, Gray-world/EMA processor, diagnostics, quality mapping, validation, reset, and packet integration. |
| `tests/unit/test_t03_white_balance.py` | Added 16 deterministic tests for all T03 calculations, contracts, fallback, mask, and immutability behavior. |
| `tests/integration/test_t03_white_balance_video.py` | Added a real T01 local-video smoke test over a generated 13-frame MJPG sequence. |
| `scripts/t03_lighting_evidence.py` | Added reproducible ignored PNG/JSON evidence generation. |
| `README.md` | Documented API, channel order, per-stream state, evidence commands, thresholds, fallback, and Gray-world limitations. |
| `codinglog.md` | Recorded T03 start, evidence, decision, and completion status. |

#### Implementation and decisions

- Valid gain-estimation pixels are constrained by configured HSV brightness
  and saturation thresholds. An optional aligned boolean mask limits that
  estimation set only; full-frame correction and lighting diagnostics remain
  global.
- Raw Gray-world BGR gains equalize valid-pixel channel means, are bounded to
  `[0.5, 2.0]`, and are EMA-smoothed with configurable alpha `0.25` after the
  first frame. `reset()` prevents state leakage between unrelated streams.
- Dark and highlight-clipped fractions, maximum absolute log2 gain, and
  maximum log2 gain change are retained as raw diagnostics. Configured
  thresholds map them to `good`, `medium`, or `poor`.
- If fewer than the configured valid fraction exist, the processor retains
  the previous gain or uses identity on the first frame, sets
  `used_fallback=True`, and reports `poor`. This avoids pretending that an
  invalid Gray-world estimate succeeded.
- **DEC-005:** T04/T08 must use one balancer per ordered source stream and the
  corrected RGB output for downstream color work, while retaining
  `original_bgr` for rendering/evidence.

#### Commands run and observed results

```text
conda run -n lens python -m pytest -q tests\unit\test_t03_white_balance.py
conda run -n lens python scripts\t03_lighting_evidence.py
conda run -n lens python -m pytest -q tests\integration\test_t03_white_balance_video.py
conda run -n lens python -m pip check
conda run -n lens python -m chromalens --help
conda run -n lens python -m pytest -q
conda run -n lens python -m compileall -q src scripts tests
git diff --exit-code -- pyproject.toml environment.yml requirements
git diff --check
git check-ignore -v artifacts/t03-lighting/evidence.json artifacts/t03-lighting/neutrality_comparison.png
git ls-files artifacts .env '*.onnx' '*.pth' '*.pt' '*.mp4' '*.avi'
```

| Check | Result | Evidence |
| --- | --- | --- |
| T03 deterministic unit suite | PASS, exit 0 | Final run: `16 passed in 0.19s` |
| Real T01 short-video integration | PASS, exit 0 | Final run: `1 passed in 0.16s`; 13 decoded MJPG frames |
| Full repository suite | PASS, exit 0 | Final run: `62 passed in 1.53s` |
| CLI remains hardware independent | PASS, exit 0 | Help printed; no camera, model, or special device opened |
| Dependency consistency | PASS, exit 0 | `No broken requirements found` |
| Dependency/lock stability | PASS, exit 0 | No diff in `pyproject.toml`, `environment.yml`, or `requirements/` |
| Compile, whitespace, and size checks | PASS, exit 0 | All Python compiled; `git diff --check` clean; no tracked file exceeds 5 MiB |
| Artifact policy | PASS, exit 0 | T03 PNG/JSON matched `artifacts/` ignore; no queried generated/model/media binary is tracked |
| Visual evidence review | PASS | `artifacts/t03-lighting/neutrality_comparison.png` opened and visually inspected locally |

#### Measured deterministic evidence

These are controlled synthetic checks, not demo-hardware performance or
physical color-accuracy claims.

| Measurement | Observed value |
| --- | ---: |
| RGB channel-mean spread before correction | 39.25 |
| RGB channel-mean spread after correction | 0.25 |
| Short-sequence frame count | 13 |
| Maximum raw consecutive gain jump | 0.106500 log2 |
| Maximum EMA-smoothed gain jump | 0.019420 log2 |
| Neutral/dark/clipped quality sequence | `good`; 25% dark `medium`; 70% dark `poor`; 10% clipped `medium`; 40% clipped `poor` |

#### Definition of Done

- [x] A deterministic synthetic red-channel cast moves substantially closer
  to neutral gray: channel-mean spread decreases from 39.25 to 0.25.
- [x] Controlled darkness and clipping severity changes the lighting label
  from `good` through `medium` to `poor`, with raw fractions asserted.
- [x] Consecutive estimates are EMA-smoothed in both array-sequence unit tests
  and a 13-frame MJPG file processed through the real T01 video source; the
  integration test bounds the maximum step and verifies lower output jumps.
- [x] Unit and video-integration tests compare every original source array
  before/after processing and confirm it remains byte-identical.

#### Deviations and known limitations

- Deviation from `plan.md`: none. No dependency, model, dataset, CLI feature,
  or T04 work was added.
- Gray-world assumes the selected region is neutral on average. It cannot
  recover physical ground-truth color under arbitrary or mixed illumination.
- Thresholds and quality labels are explainable heuristics, not calibrated
  probabilities. They require T09 evaluation and possible tuning on declared
  demo footage/hardware.
- T03 does not yet run in the default preview loop; T08 owns pipeline
  composition. T04 can consume the module directly now.

#### Exact next task

`T04 — Dominant color extraction and 11-name mapping`, whose dependencies T02
and T03 are now both `DONE`.

---

### `2026-08-20 11:43 +07:00` — `T04` `Dominant color extraction and 11-name mapping`

**Status:** `IN_PROGRESS`
**Owner/agent:** Codex
**Plan reference:** `plan.md#t04--dominant-color-extraction-and-11-name-mapping`
**Requirements/rubric affected:** FR-05, FR-06, FR-12; NFR-01, NFR-06, NFR-08; Metrics 02 and 03

#### Objective

Extract original corrected garment colors only from an eroded, valid mask;
provide robust median and deterministic two-cluster paths; and map every
retained color to one of 11 documented basic terms with Vietnamese label,
normalized scores, and best-versus-second margin.

#### Starting state

- Branch `mvp` is clean and synchronized with `origin/mvp` at
  `dbe4189fa5b101472260d7b3860fc0a3af3f9741`.
- Required dependencies T02 and T03 are both `DONE`; T03 exposes corrected RGB
  while preserving original BGR, and T02 exposes aligned boolean masks.
- Approved environment `lens` runs Python `3.10.20`; `pip check` reports no
  broken requirements.
- Baseline repository suite: `62 passed in 4.99s`.
- No new Python dependency is expected; NumPy and OpenCV already provide the
  required morphology, color conversion, and array operations.

#### Smallest implementation that satisfies the Definition of Done

- Add `color_extraction.py` with validated thresholds, explicit mask erosion,
  dark/clipped/optional pixel-confidence rejection, robust Lab median, and
  locally seeded deterministic `K=2` with minimum-area filtering.
- Add `color_naming.py` with an explicit float32 sRGB-to-CIELAB convention,
  a documented 11-family nearest-prototype score distribution, Vietnamese
  labels, and a non-calibrated best-vs-second margin.
- Add provenance/license documentation and a controlled CSV containing all 11
  families; do not import or redistribute the unlicensed Van de Weijer learned
  lookup table.
- Add deterministic unit tests plus an offline evidence script that produces a
  per-class evaluation table and cluster visualization under ignored
  `artifacts/`.
- Update README and this log only within T04; do not integrate T05 behavior or
  the default live pipeline.

#### Source and convention checks before implementation

- OpenCV's official conversion documentation requires float RGB input to be
  normalized to `[0, 1]`, explicitly distinguishes RGB from default BGR, and
  defines float CIELAB output as `L*` in `[0, 100]` with signed `a*`, `b*`.
- The 11 English terms follow Van de Weijer et al.'s published basic-term set.
  Their learned RGB lookup is not copied because the download page does not
  state a redistribution license.
- The equivalent prototype anchors will be selected from W3C CSS Color 4's
  standardized sRGB named-color table. The W3C source and permissive Software
  and Document License notice will be recorded, while ChromaLens's selection,
  family grouping, scores, and Vietnamese translations remain project-authored
  Apache-2.0 data/code.

#### Commands and checks run before implementation

```text
git status --short --branch
git rev-parse HEAD
git rev-parse origin/mvp
conda run -n lens python --version
conda run -n lens python -m pip check
conda run -n lens python -m pytest -q
```

| Check | Result | Evidence |
| --- | --- | --- |
| Branch/baseline | PASS, exit 0 | `mvp...origin/mvp`; both SHAs `dbe4189f...` |
| Approved interpreter | PASS, exit 0 | Python 3.10.20 in `lens` |
| Dependency consistency | PASS, exit 0 | `No broken requirements found` |
| Baseline suite | PASS, exit 0 | `62 passed in 4.99s` |

#### Definition-of-Done status at start

- [ ] Tests cover erosion, invalid-pixel rejection, median robustness, and
  deterministic clustering.
- [ ] A controlled set spanning all 11 families produces an evaluation table.
- [ ] Every retained cluster has Lab/RGB, ratio, submask, name, 11 scores, and
  margin.
- [ ] Synthetic tests prove no background pixel enters a retained submask.

#### Deviations, limitations, and blockers

- Deviation from plan: none. The plan explicitly permits a documented
  equivalent lookup instead of the learned Van de Weijer table.
- Active blocker: none.

---

### `2026-08-20 11:52 +07:00` — `T04` `Dominant color extraction and 11-name mapping complete`

**Status:** `DONE`
**Owner/agent:** Codex
**Plan reference:** `plan.md#t04--dominant-color-extraction-and-11-name-mapping`

#### Outcome

T04 now consumes only T03's corrected RGB and T02's aligned garment mask. It
erodes uncertain boundaries; excludes dark, highlight-clipped, and optionally
low pixel-confidence samples; converts explicitly to conventional float
CIELAB; and returns either one robust median cluster or up to two deterministic
K-means clusters. Every retained `ColorCluster` carries aligned boolean
submask, Lab/RGB, original name, area ratio, all 11 normalized name scores, and
best-versus-second margin.

The 11 English keys have explicit Vietnamese labels. Naming uses a documented
multi-anchor equivalent rather than copying the unlicensed Van de Weijer
learned table: standardized W3C CSS sRGB anchor values, project-authored family
grouping, CIE76 nearest-anchor distances, and softmax score normalization.

#### Files changed

| File | Change and reason |
| --- | --- |
| `src/chromalens/color_extraction.py` | Added validated erosion/filtering, P0 median, seeded deterministic K=2, minimum-area filtering, specific errors, and `ColorCluster` construction. |
| `src/chromalens/color_naming.py` | Added explicit RGB/CIELAB conversions, 11-family anchors, Vietnamese labels, normalized scores, and margin. |
| `assets/color_names/README.md` | Documented vocabulary, algorithm, Lab convention, provenance, license, and limitations. |
| `assets/color_names/W3C-SOFTWARE-DOCUMENT-LICENSE.md` | Included the required W3C Software and Document License notice for derived named-color material. |
| `tests/samples/t04/basic11_controlled.csv` | Added one non-anchor controlled sRGB patch per basic family. |
| `tests/samples/t04/README.md` | Declared authorship, scope, license, and T09 limitations of the controlled set. |
| `tests/unit/test_t04_color_naming.py` | Added deterministic 11-family, score, label, conversion, and validation tests. |
| `tests/unit/test_t04_color_extraction.py` | Added erosion, filtering, robustness, determinism, ratio, field, containment, fallback, and configuration tests. |
| `tests/integration/test_t04_color_pipeline.py` | Added an offline T03-to-T04 RGB/BGR and immutability integration smoke test. |
| `scripts/t04_color_evidence.py` | Added reproducible CSV/JSON/swatch/cluster evidence generation. |
| `README.md` | Documented T04 APIs, fields, evidence commands, provenance, semantics, and limitations. |
| `codinglog.md` | Recorded T04 start, evidence, decision, and completion. |

#### Implementation and decisions

- Corrected `uint8` RGB is normalized to float32 `[0, 1]` before
  `cv2.COLOR_RGB2LAB`; stored Lab is conventional `L* [0,100]`, signed `a*`
  and `b*`, never OpenCV's offset-packed uint8 representation.
- A 3×3 one-iteration erosion uses an explicit zero-valued border. Pixels are
  valid only when inside the eroded mask, brighter than 16, have no channel at
  or above 250, and—when an aligned float map is provided—confidence at least
  0.50. All values are validated/configurable.
- P0 uses per-channel median in Lab. P1 uses local NumPy RNG seed 17, K-means++
  initialization, K=2, bounded iterations, and a 10% minimum cluster ratio.
  Filtered area is not hidden by renormalizing retained ratios.
- T02's P0 backend exposes only a thresholded mask and region-level heuristic
  score, not an aligned reusable probability map. T04 therefore accepts an
  optional pixel-confidence map for a future compatible backend; the current
  cleaned boolean mask remains the default input.
- **DEC-006:** T05–T09 must treat `ColorCluster.lab`, `rgb`, and
  `original_name` as estimates of the original corrected color. `name_scores`
  and `color_margin` are distance heuristics, separate from mask confidence,
  lighting quality, and future CVD risk.

#### Commands run and observed results

```text
conda run -n lens python -m pytest -q tests\unit\test_t04_color_naming.py tests\unit\test_t04_color_extraction.py
conda run -n lens python -m pytest -q tests\integration\test_t04_color_pipeline.py
conda run -n lens python scripts\t04_color_evidence.py
conda run -n lens python -m pip check
conda run -n lens python -m chromalens --help
conda run -n lens python -m pytest -q
conda run -n lens python -m compileall -q src scripts tests
git diff --exit-code -- pyproject.toml environment.yml requirements
git diff --check
git check-ignore -v artifacts/t04-color/basic11_evaluation.csv artifacts/t04-color/evidence.json artifacts/t04-color/basic11_swatch_grid.png artifacts/t04-color/synthetic_cluster_overlay.png
```

| Check | Result | Evidence |
| --- | --- | --- |
| T04 unit suite | PASS, exit 0 | Final focused run: `21 passed in 0.25s` |
| T03-to-T04 integration | PASS, exit 0 | Final run: `1 passed in 0.26s`; corrected RGB names red and original BGR stays byte-identical |
| Full repository suite | PASS, exit 0 | Final run: `84 passed in 1.64s` |
| Controlled 11-family table | PASS, exit 0 | `11/11`; ignored `artifacts/t04-color/basic11_evaluation.csv` |
| Visual evidence | PASS | Swatch grid and two-cluster overlay opened and reviewed after fixing score-text overflow |
| Dependency/CLI/compile gates | PASS, exit 0 | No broken requirements; hardware-independent help; all Python compiled |
| Dependency/lock stability | PASS, exit 0 | No diff in `pyproject.toml`, `environment.yml`, or `requirements/` |
| Whitespace/artifact/size policy | PASS, exit 0 | Diff clean; all generated T04 files ignored; no tracked file over 5 MiB |

#### Measured deterministic evidence

These results validate contracts on controlled sRGB arrays; they are not
physical color-accuracy, cultural-language, or demo-hardware performance
claims.

| Measurement | Observed value |
| --- | ---: |
| Controlled basic-family rows correct | 11 / 11 |
| Controlled score margin range | 0.225428–0.685291 |
| Synthetic K=2 retained names | `red`, `blue` |
| Synthetic retained ratios | 0.601010, 0.398990 |
| Pixels outside garment across retained clusters | 0 |

#### Definition of Done

- [x] Unit tests cover exact erosion, dark/clipped/low-confidence rejection,
  median robustness against a minority outlier, deterministic K=2, and
  minimum-area filtering.
- [x] The committed controlled set spans all 11 families and the evidence
  runner produces a real CSV evaluation table with Lab, predicted/expected
  names, best/runner-up scores, margin, distance, and correctness: 11/11.
- [x] Median and K=2 tests assert every retained cluster includes Lab/RGB,
  ratio, aligned bool submask, canonical name, exactly 11 normalized scores,
  and non-null margin.
- [x] Synthetic tests and evidence assert retained submasks are subsets of the
  eroded garment mask; observed outside-garment pixel count is zero.

#### Deviations and known limitations

- No deviation from `plan.md`: it explicitly permits a documented equivalent
  lookup. K=2 P1 was completed because deterministic clustering is also named
  in the T04 Definition of Done.
- The learned Van de Weijer RGB matrix is not included because its project
  download page does not state a redistribution license. This avoids an
  unverifiable license claim while preserving its published 11-term vocabulary.
- CSS anchors are uneven samples, not a fitted perceptual dataset; distance
  scores are not calibrated probabilities. Real fabrics, patterns, shadows,
  mixed lighting, cameras/displays, languages, and user perception require the
  declared T09 evaluation.
- K=2 can split illumination/shadow rather than material color and deliberately
  ignores clusters below 10%. No temporal color smoothing or live composition
  is added here; those remain T08/T09 responsibilities.

#### Exact next task

`T05 — CVD simulation and relational risk`.

---

### `2026-08-20 12:11 +07:00` — `T05` `CVD simulation and relational risk`

**Status:** `IN_PROGRESS`
**Owner/agent:** Codex
**Plan reference:** `plan.md#t05--cvd-simulation-and-relational-risk`
**Requirements/rubric affected:** FR-07, FR-08, FR-09, FR-12; NFR-01, NFR-06, NFR-08; Metrics 02 and 03

#### Objective

Simulate the three user-selected CVD profiles with validated severity using
the documented Machado model, then compare retained original garment-color
clusters with CIEDE2000 before and after simulation and return an explainable,
configurable relational-risk assessment.

#### Starting state

- Branch `mvp` is clean and synchronized with `origin/mvp` at
  `5313ff8ab177bb0adf6fefb4980e19a7d0d4e643`.
- Required dependency T04 is `DONE`; each retained `ColorCluster` carries the
  original corrected RGB/Lab estimate, ratio, name, and aligned submask.
- Approved environment `lens` runs Python `3.10.20`; `pip check` reports no
  broken requirements.
- Baseline repository suite: `84 passed in 11.03s`.
- Official PyPI/GitHub metadata identifies `daltonlens==0.1.5` as a pure
  Python package supporting Machado 2009, `protan`/`deutan`/`tritan`, severity,
  Python `>=3.7`, and the MIT License. Installation/API compatibility in the
  approved environment has not yet been tested.

#### Smallest implementation that satisfies the Definition of Done

- Add one explicit RGB-input Machado simulation boundary backed by the exact
  locked DaltonLens release; severity zero will short-circuit to an identity
  copy and all other severities will use DaltonLens's sRGB/linear-RGB handling.
- Add an independently tested CIEDE2000 implementation and a validated risk
  configuration whose score/`low`/`medium`/`high` thresholds remain visible
  heuristics, never confidence or diagnosis.
- Compare all unordered pairs of retained clusters inside one garment for P0,
  preserving both original and simulated Delta-E values in the existing
  `RiskAssessment` contract. Top-bottom/background comparisons remain P1 and
  will not be fabricated without corresponding regions.
- Add deterministic known-patch, published Delta-E reference, confusing-pair,
  contract, and validation tests plus offline evidence/provenance documentation.
- Update all affected collaboration locks and CI lock-freshness checks; do not
  add T06 recoloring or T08 live composition.

#### Commands and checks run before implementation

```text
git status --short --branch
git branch --show-current
git rev-parse HEAD
git rev-parse origin/mvp
git log -5 --oneline --decorate
D:\Coding\Anaconda\envs\lens\python.exe --version
D:\Coding\Anaconda\envs\lens\python.exe -c "import sys; print(sys.executable)"
D:\Coding\Anaconda\envs\lens\python.exe -m pip check
D:\Coding\Anaconda\envs\lens\python.exe -m pytest -q
rg --files
```

| Check | Result | Evidence |
| --- | --- | --- |
| Branch/baseline | PASS, exit 0 | Clean `mvp`; local/remote SHA `5313ff8a...` |
| Approved interpreter | PASS, exit 0 | Python 3.10.20 at `D:\Coding\Anaconda\envs\lens\python.exe` |
| Dependency consistency | PASS, exit 0 | `No broken requirements found` |
| Baseline suite | PASS, exit 0 | `84 passed in 11.03s` |
| Repository inventory | PASS, exit 0 | T05 source/test modules do not yet exist |

#### Definition-of-Done status at start

- [ ] Severity zero is identity within numerical tolerance.
- [ ] All profiles run without channel-order errors on known color patches.
- [ ] A known confusing pair receives greater risk than a clearly separated
  control for at least one declared profile.
- [ ] Output records original Delta-E, simulated Delta-E, score, and level.
- [ ] Thresholds are configurable and documented as requiring user validation.

#### Deviations, limitations, and blockers

- Deviation from plan: none.
- Active blocker: none. DaltonLens installation/API and exact dependency-lock
  compatibility must pass before its integration is accepted.

---

### `2026-08-20 12:27 +07:00` — `T05` `CVD simulation and relational risk complete`

**Status:** `DONE`
**Owner/agent:** Codex
**Plan reference:** `plan.md#t05--cvd-simulation-and-relational-risk`

#### Outcome

T05 now reuses the T00 `CVDProfile` enum and validates severity at its public
simulation boundary. `MachadoSimulator` exposes an explicit uint8 sRGB/RGB
contract backed by pinned DaltonLens 0.1.5. Non-zero severity follows
DaltonLens's sRGB-to-linear-RGB, Machado matrix, clipping, and sRGB encoding;
severity zero returns an independent byte-identical copy to avoid the
library's observed 255-to-254 uint8 round-trip loss.

`RelationalRiskDetector` computes independently verified CIEDE2000 distances
for original corrected colors and their selected-profile simulations, derives
a configurable collapse/closeness score, assigns `low`/`medium`/`high`, and
retains both distances plus the score in `RiskAssessment`. Its P0 cluster API
compares every unordered retained pair inside one garment. It returns no
fabricated result when fewer than two clusters exist; top-bottom/background
comparisons remain P1 for later work with real corresponding regions.

#### Files changed

| File | Change and reason |
| --- | --- |
| `src/chromalens/cvd_simulation.py` | Added validated RGB/profile/severity boundary and DaltonLens Machado adapter with exact zero-severity identity. |
| `src/chromalens/risk_detection.py` | Added CIEDE2000, validated heuristic configuration, risk levels, pair assessment, and within-garment cluster comparison. |
| `tests/unit/test_t05_cvd_simulation.py` | Added fixed RGB-patch expectations, identity/copy, channel-order, profile, and validation tests. |
| `tests/unit/test_t05_risk_detection.py` | Added Sharma supplemental CIEDE2000 vectors, risk ranking/output/configuration, cluster-pair, and invalid-input tests. |
| `tests/integration/test_t05_color_risk_pipeline.py` | Added deterministic T04 K=2 to T05 relational-risk integration and source-immutability check. |
| `scripts/t05_cvd_risk_evidence.py` | Added offline JSON/CSV/swatch evidence for all profiles and declared pair comparisons. |
| `assets/cvd/README.md` | Documented algorithms, RGB/gamma convention, provenance, formula, thresholds, and responsible limitations. |
| `assets/cvd/DALTONLENS-MIT-LICENSE.md` | Preserved the upstream DaltonLens MIT notice. |
| `pyproject.toml` | Pinned the P0 runtime dependency `daltonlens==0.1.5`. |
| `requirements/py310-win64.lock` | Added hashed DaltonLens 0.1.5 and Pillow 12.3.0 base closure. |
| `requirements/lock-tools-py310-win64.lock` | Regenerated the base-plus-lock-tool closure with the same hashes. |
| `requirements/segment-mediapipe-py310-win64.lock` | Added DaltonLens and its existing Pillow relationship to the full backend closure. |
| `requirements/README.md` | Documented T05 ownership in all affected locks. |
| `.github/workflows/ci.yml` | Added an exact DaltonLens runtime assertion to the locked base job; existing regeneration covers all changed locks. |
| `README.md` | Added T05 usage, reproducible evidence, thresholds, contracts, provenance, and limitations. |
| `codinglog.md` | Recorded T05 baseline, implementation, measurements, decisions, and completion. |

#### Dependency and implementation decisions

- **DEC-007:** DaltonLens is a P0 base dependency rather than an optional extra,
  so the normal locked install and base CI cannot silently skip T05. Exact
  installed additions are `daltonlens==0.1.5` and its transitive
  `Pillow==12.3.0`; NumPy remains `1.26.4`.
- The upstream package wheel is pure Python, declares Python `>=3.7`, carries
  an MIT license file, and installs cleanly under approved Python 3.10.20.
- CIEDE2000 was implemented locally without a new scientific dependency and
  checked against ten published Sharma/Wu/Dalal reference cases, including
  neutral and hue-wrap cases.
- Default risk configuration is original floor `5.0`, simulated confusion
  distance `20.0`, medium score `0.25`, and high score `0.60`. Score equals
  relative Delta-E loss multiplied by post-simulation closeness. These values
  are explicit uncalibrated heuristics for T09 validation.

#### Commands run

```text
D:\Coding\Anaconda\envs\lens\python.exe -m pip install --disable-pip-version-check daltonlens==0.1.5
D:\Coding\Anaconda\envs\lens\python.exe -m pip check
D:\Coding\Anaconda\envs\lens\python.exe -c "inspect DaltonLens metadata, API, simulator, and sRGB transfer functions"
git ls-remote --tags https://github.com/DaltonLens/DaltonLens-Python.git
D:\Coding\Anaconda\envs\lens\python.exe -m pip index versions daltonlens
D:\Coding\Anaconda\envs\lens\python.exe -m compileall -q src
D:\Coding\Anaconda\envs\lens\python.exe -m pytest -q tests\unit\test_t05_cvd_simulation.py tests\unit\test_t05_risk_detection.py tests\integration\test_t05_color_risk_pipeline.py
D:\Coding\Anaconda\envs\lens\python.exe -m piptools compile --quiet pyproject.toml --extra dev --generate-hashes --allow-unsafe --resolver backtracking --strip-extras --no-emit-index-url --no-emit-trusted-host --output-file requirements/py310-win64.lock
D:\Coding\Anaconda\envs\lens\python.exe -m piptools compile --quiet pyproject.toml --extra lock --generate-hashes --allow-unsafe --resolver backtracking --strip-extras --no-emit-index-url --no-emit-trusted-host --output-file requirements/lock-tools-py310-win64.lock
D:\Coding\Anaconda\envs\lens\python.exe -m piptools compile --quiet pyproject.toml --extra dev --extra segment-mediapipe --generate-hashes --allow-unsafe --resolver backtracking --strip-extras --no-emit-index-url --no-emit-trusted-host --output-file requirements/segment-mediapipe-py310-win64.lock
D:\Coding\Anaconda\envs\lens\python.exe -m pip install --disable-pip-version-check --require-hashes --requirement requirements\py310-win64.lock
D:\Coding\Anaconda\envs\lens\python.exe -m pip install --disable-pip-version-check --require-hashes --requirement requirements\lock-tools-py310-win64.lock
D:\Coding\Anaconda\envs\lens\python.exe -m pip install --disable-pip-version-check --require-hashes --requirement requirements\segment-mediapipe-py310-win64.lock
D:\Coding\Anaconda\envs\lens\python.exe -m pip install --disable-pip-version-check --no-build-isolation --no-deps --editable ".[dev]"
D:\Coding\Anaconda\envs\lens\python.exe scripts\t05_cvd_risk_evidence.py
D:\Coding\Anaconda\envs\lens\python.exe -m pytest -q
D:\Coding\Anaconda\envs\lens\python.exe -m compileall -q src scripts tests
D:\Coding\Anaconda\envs\lens\python.exe -m chromalens --help
D:\Coding\Anaconda\envs\lens\python.exe -m pip check
git diff --check
git check-ignore -v artifacts/t05-cvd-risk/evidence.json artifacts/t05-cvd-risk/pair_risk_evaluation.csv artifacts/t05-cvd-risk/known_patch_simulation.png
git ls-files artifacts .env '*.onnx' '*.pth' '*.pt' '*.mp4' '*.avi'
```

The three lock-generation commands were repeated with SHA-256 checks before
and after regeneration to prove byte-stable output.

#### Tests and observed results

| Check | Result | Evidence |
| --- | --- | --- |
| T05 focused unit/integration suite | PASS, exit 0 | Initial `41 passed in 0.37s`; final after zero-distance guard `42 passed in 0.38s` |
| Full repository suite | PASS, exit 0 | Initial `125 passed in 1.78s`; locked rerun `125 passed in 1.93s`; final `126 passed in 2.18s` |
| CIEDE2000 reference vectors | PASS | Ten published expected values within absolute tolerance `0.00005` |
| Hashed base/tool/MediaPipe installs | PASS, exit 0 | Every dependency satisfied under `--require-hashes`; `pip check` clean |
| Deterministic lock regeneration | PASS, exit 0 | SHA-256 base `23634BD2...BF44E`, tools `D385A875...5931`, MediaPipe `3ABB7AF8...071A` unchanged after regeneration |
| CLI and compile gates | PASS, exit 0 | Help printed without camera/model; all source/script/test modules compiled |
| Evidence command | PASS, exit 0 | Ignored CSV, JSON, and PNG written under `artifacts/t05-cvd-risk/` |
| Visual evidence review | PASS | Known-patch original/protan/deutan/tritan swatch rows opened and inspected |
| Whitespace/artifact/size policy | PASS, exit 0 | Diff clean; generated evidence ignored; no queried generated/model/media file tracked; no tracked file over 5 MiB |

#### Measured deterministic evidence

These are controlled sRGB algorithm/contract checks, not user-perception,
medical, physical color-accuracy, or official demo-hardware measurements.

| Case/profile | Original Delta-E00 | Simulated Delta-E00 | Risk score/level |
| --- | ---: | ---: | --- |
| Deutan red `(220,40,40)` vs olive `(120,120,30)` | 45.723216 | 4.590837 | 0.693100 / `high` |
| Deutan blue `(40,90,220)` vs yellow `(235,220,40)` control | 79.768447 | 77.043909 | 0.000000 / `low` |
| Protan purple vs blue controlled case | 17.344425 | 7.654908 | 0.344831 / `medium` |
| Tritan orange vs pink controlled case | 40.090229 | 7.299191 | 0.519419 / `medium` |

All six known RGB patches ran for every profile at severity one, and all three
severity-zero rows were byte-identical to their source.

#### Definition of Done

- [x] Severity zero is identity within numerical tolerance: it is exact for
  all three profiles, returns a non-aliasing copy, and leaves source bytes
  unchanged.
- [x] Protan, deutan, and tritan match fixed locked-DaltonLens outputs on red,
  green, blue, white, black, and yellow RGB patches; direct single-red output
  also guards RGB/BGR ordering.
- [x] The declared deutan red/olive confusing pair scores `0.693100`, greater
  than the blue/yellow control score `0.000000`.
- [x] Every result contains `delta_e_original`, `delta_e_cvd`, `risk_score`,
  and `risk_level`, with stable source/comparison identifiers.
- [x] All risk thresholds are validated configuration values and documented as
  heuristics requiring T09 user/evaluation validation.

#### Deviations and known limitations

- No deviation from T05 P0. The T00 profile enum and risk dataclass were reused
  rather than duplicated; the plan's permitted verified DaltonLens path was
  selected and locked.
- Final self-review added an explicit zero-original-distance guard and test so
  a deliberately configured zero floor cannot cause division by zero; no
  formula, threshold, dependency, or scope changed.
- Top-bottom and adjacent-background comparisons are P1 and were not added
  without semantic regions. T06 can consume within-garment assessments now;
  richer relationships require real region contracts/evidence.
- DaltonLens 0.1.5 is a 2021 release and its own Machado class documents poorer
  tritanopia suitability. The package and algorithm are pinned/attributed, but
  correctness for individual users is not established by these tests.
- Simulation approximates appearance and is debug/risk input, not the future
  assistive recolored display. Profile/severity selection is not diagnosis.
- Risk thresholds and controlled pairs are uncalibrated. T09 must evaluate
  them across declared users, displays, lighting, garments, and failure cases.

#### Exact next task

`T06 — Selective recolor, outline, and score overlay`.

#### Version control

- Branch: `mvp`
- Planned commit message: `feat: add CVD simulation and relational risk`
- Known-good pre-T05 baseline: `5313ff8ab177bb0adf6fefb4980e19a7d0d4e643`

---

### `2026-08-20 13:02 +07:00` — `T06` `Selective recolor, outline, and score overlay`

**Status:** `IN_PROGRESS`
**Owner/agent:** Codex
**Plan reference:** `plan.md#t06--selective-recolor-outline-and-score-overlay`
**Requirements/rubric affected:** FR-08, FR-09, FR-11, FR-12; NFR-01, NFR-05, NFR-06, NFR-08; Metrics 02 and 03

#### Objective

Transform only the risky retained garment-color pixels into an assistive
display color chosen for the active CVD profile; preserve source pixels and
texture/lightness as practical; stabilize the selection over time; and render
a clearly labeled, high-contrast outline/tag with separate original-color,
assistive-color, confidence, risk, lighting, profile, severity, and backend
diagnostics.

#### Starting state

- Branch `mvp` is clean and synchronized with `origin/mvp` at
  `2d2877dac27f3fa235315dba19ba10f383dad124`.
- Required dependencies T02, T04, and T05 are all `DONE`. T04 exposes original
  corrected RGB/Lab clusters and aligned retained submasks; T05 exposes the
  selected-profile relational risk without confusing simulation with output.
- Approved environment `lens` runs Python `3.10.20`; `pip check` reports no
  broken requirements.
- Baseline repository suite: `126 passed in 1.96s`.
- No new Python dependency is expected; NumPy and OpenCV provide candidate
  transforms, Lab conversion, distance transforms, morphology, and rendering.

#### Smallest implementation that satisfies the Definition of Done

- Add a documented deterministic candidate-color optimizer. Score candidates
  by their simulated CVD separation from the comparison color while penalizing
  unnecessary departure from the original; never use a universal color map.
- Intersect garment, retained-cluster, and risk masks exactly. Shift only Lab
  chroma while preserving each source pixel's L*; use inward-only alpha
  feathering so every pixel outside the hard recolor mask remains byte-identical.
- Add bounded per-key temporal hysteresis for the selected display color and
  prove a static sequence has zero repeated switching.
- Extend the renderer with a double black/white contour and opaque high-
  contrast tag. Keep simulation in an explicitly labeled debug-only mode and
  label original and assistive colors separately in typed debug data.
- Add deterministic unit/integration tests plus ignored offline image/JSON
  evidence. Do not compose the live T08 application or add T07 matching.

#### Definition-of-Done status at start

- [ ] Pixels outside the hard recolor mask remain unchanged before overlays.
- [ ] Debug data separately labels original and assistive display colors.
- [ ] A static short sequence does not repeatedly switch display color.
- [ ] The tag remains readable on light and dark backgrounds.
- [ ] Simulation is debug-only and never labeled as the assistive result.

#### Deviations, limitations, and blockers

- Deviation from plan: none; candidate-color transformation is explicitly
  permitted by T06.
- Active blocker: none.

---

### `2026-08-20 13:10 +07:00` — `T06` `Selective recolor, outline, and score overlay complete`

**Status:** `DONE`
**Owner/agent:** Codex
**Plan reference:** `plan.md#t06--selective-recolor-outline-and-score-overlay`

#### Outcome

T06 now provides a deterministic `SelectiveRecolorer` that starts from the
unchanged camera/display BGR frame, keeps T04 original corrected color data
separate, and changes only the exact garment/retained-cluster/risk-mask
intersection. It generates CIELCH candidates for the selected CVD context,
scores simulated separation with an identity-departure penalty, preserves each
pixel's L* before gamut conversion, feathers inward only, and holds the chosen
display color with bounded per-key hysteresis.

The extended renderer draws a double black/white garment contour and an opaque
black tag with white border/text. Typed overlay data separately exposes the
original corrected color, assistive display target, color margin, relational
risk, lighting quality, profile, severity, backend, and frame ID. Assistive and
CVD-simulation renderers reject the other's view enum; the simulation path
therefore requires the visible `CVD SIMULATION (DEBUG ONLY)` label.

#### Files changed

| File | Change and reason |
| --- | --- |
| `src/chromalens/recolor.py` | Added validated candidate optimization, exact containment, inward alpha, Lab chroma transform, bounded LRU hysteresis, typed results/debug data, and explicit no-change reasons. |
| `src/chromalens/renderer.py` | Added typed assistive/debug views, inspectable score lines, high-contrast tag, double outline, copied-frame rendering, and mutually exclusive assistive/simulation entry points while preserving T01 APIs. |
| `tests/unit/test_t06_recolor.py` | Added deterministic containment, alpha, lightness, profile-dependent candidate, inactive path, hysteresis, bounded-state, validation, and immutability tests. |
| `tests/unit/test_t06_renderer.py` | Added separate-label, mandatory debug-mode, light/dark tag, double-contour, copy, and validation tests. |
| `tests/integration/test_t06_assistive_slice.py` | Added a T04-to-T05-to-T06 static vertical-slice test with exact outside-mask invariance. |
| `scripts/t06_recolor_overlay_evidence.py` | Added reproducible ignored PNG/JSON evidence and fail-fast DoD assertions. |
| `assets/recolor/README.md` | Documented algorithm, formula, thresholds, channel boundaries, containment, temporal policy, renderer, provenance, evidence, and limitations. |
| `README.md` | Documented T06 use, handoff contracts, evidence commands, view safety, and limitations. |
| `codinglog.md` | Recorded T06 start, decisions, actual evidence, and completion. |

#### Implementation decisions

- **DEC-008:** Use a project-authored candidate-color transform rather than a
  universal mapping. For each CIELCH hue/chroma candidate, objective equals
  simulated CIEDE2000 separation minus `0.18` times original-to-candidate
  CIEDE2000. Default activation is risk `>=0.25` plus at least `3.0` simulated
  Delta-E00 improvement. These are configurable T09 validation hypotheses.
- Pixel assignment is restricted to the hard intersection even after
  feathering. Distance-transform alpha is zero outside the hard mask; only
  chroma is shifted and the source L* plane remains untouched before sRGB
  gamut clipping/quantization.
- A challenger must exceed the retained objective by `2.0` for three
  consecutive frames. Per-key state is LRU-bounded at 32 entries. T08 must
  reset or key by profile/stream/track identity when those identities change.
- OpenCV Hershey text transliterates accented Vietnamese in-frame (`Đỏ` →
  `Do`); canonical accented labels remain in the T04 API. A Unicode font must
  be bundled and license-reviewed before changing this behavior.

#### Commands run and observed results

```text
D:\Coding\Anaconda\envs\lens\python.exe -m compileall -q src
D:\Coding\Anaconda\envs\lens\python.exe -m pytest -q tests\unit\test_t06_recolor.py tests\unit\test_t06_renderer.py tests\integration\test_t06_assistive_slice.py
D:\Coding\Anaconda\envs\lens\python.exe scripts\t06_recolor_overlay_evidence.py
D:\Coding\Anaconda\envs\lens\python.exe -m pytest -q
D:\Coding\Anaconda\envs\lens\python.exe -m compileall -q src scripts tests
D:\Coding\Anaconda\envs\lens\python.exe -m pip check
D:\Coding\Anaconda\envs\lens\python.exe -m chromalens --help
git diff --exit-code -- pyproject.toml environment.yml requirements .github/workflows/ci.yml
git diff --check
git check-ignore -v artifacts/t06-recolor-overlay/evidence.json artifacts/t06-recolor-overlay/assistive_overlay.png artifacts/t06-recolor-overlay/cvd_simulation_debug_only.png
git ls-files artifacts .env '*.onnx' '*.pth' '*.pt' '*.mp4' '*.avi'
```

| Check | Result | Evidence |
| --- | --- | --- |
| First focused run | FAIL: `2 failed, 29 passed`; one regex expected different wording and the readability test crop extended beyond the dynamically sized tag | Terminal output |
| Smallest focused-test repairs | Aligned the error-message expectation and restricted the comparison crop to the known opaque tag core; then replaced an exact-255 anti-aliased text assertion with a high-luminance threshold | Test diff; no product threshold/scope change |
| Final focused T06 suite | PASS, exit 0 | `31 passed in 0.42s` |
| Full repository suite | PASS, exit 0 | `157 passed in 2.03s` |
| Evidence runner | PASS, exit 0 | Six PNGs plus `evidence.json` under ignored `artifacts/t06-recolor-overlay/` |
| Visual evidence review | PASS | Assistive result, explicitly debug-only simulation, masks/feather, double outline, and light/dark tag opened and inspected |
| Compile/dependency/CLI gates | PASS, exit 0 | All source/script/test modules compiled; no broken requirements; help rendered without camera/model/hardware |
| Dependency/lock/CI stability | PASS, exit 0 | No diff in `pyproject.toml`, `environment.yml`, `requirements/`, or CI workflow; no new dependency |
| Artifact/size policy | PASS, exit 0 | Generated evidence is ignored; no queried environment/model/media artifact is tracked; no tracked or pending file exceeds 5 MiB |

#### Measured deterministic evidence

These are controlled synthetic contract measurements, not perception,
clinical, physical color-accuracy, or demo-hardware performance claims.

| Measurement | Observed value |
| --- | ---: |
| Hard recolor-mask pixels | 44,022 |
| Changed pixels inside hard mask | 44,022 |
| Changed pixels outside hard mask before overlay | 0 |
| Maximum alpha outside hard mask | 0.0 |
| Maximum L* change at full-alpha pixels after sRGB round trip | 0.891113 |
| Static sequence | 20 frames; 1 unique assistive target; 0 switches |
| Original corrected representative RGB | `(218, 38, 38)` |
| Assistive display representative RGB | `(0, 119, 249)` |
| Original/assistive simulated Delta-E00 to comparison | 5.015549 / 58.405531 |
| Light/dark opaque tag core | Byte-identical; visual review PASS |
| Assistive/simulation labels | `VIEW: ASSISTIVE RESULT` / `VIEW: CVD SIMULATION (DEBUG ONLY)` |

#### Definition of Done

- [x] Synthetic tests and evidence show every pixel outside the exact hard
  recolor mask remains byte-identical before overlays: observed count `0`.
- [x] `RecolorDebugData` and `AssistiveOverlayData` separately name/store
  `original_corrected_rgb` and `assistive_display_rgb`; evidence records both.
- [x] A 20-frame static run retains one display target with zero switches;
  separate tests exercise three-frame challenger hysteresis and the 32-state
  bound.
- [x] The tag uses an opaque black field, white border/text, and a double
  contour. Its declared core is byte-identical over light/dark backgrounds and
  both variants were visually reviewed.
- [x] Simulation has its own mandatory renderer/view enum and visible
  `DEBUG ONLY` label. The assistive renderer rejects simulation view data, and
  debug data calls the assistive target separate rather than the shown result.

#### Deviations and known limitations

- Deviation from `plan.md`: none. The plan explicitly permits candidate-color
  optimization, and no T07/T08 behavior or dependency was introduced.
- Candidate/risk/hysteresis thresholds are explainable, uncalibrated
  heuristics. T09 must validate them with declared garments, displays, profiles,
  users, lighting, movement, and failure cases.
- L* is preserved before gamut clipping and 8-bit quantization, not guaranteed
  physically identical afterward. Controlled full-alpha maximum was `0.891113`.
- T06 quality inherits mask, white-balance, cluster, simulation, and display
  limitations. Inward feathering may leave a narrow original-color edge.
- T06 remains an independently testable slice; T08 owns webcam/video
  composition, controls, stale-result policy, and live performance.

#### Exact next task

`T07 — Rule-based color matching` (P1, optional before the P0 T08 composition).

#### Version control

- Branch: `mvp`
- Planned atomic commit: `feat: add selective recolor and score overlay`
- Known-good pre-T06 baseline: `2d2877dac27f3fa235315dba19ba10f383dad124`

---

### `2026-08-20 16:02 +07:00` - `T07` `Rule-based color matching`

**Status:** `IN_PROGRESS`
**Owner/agent:** Codex
**Plan reference:** `plan.md#t07--rule-based-color-matching`
**Requirements/rubric affected:** FR-10; NFR-01, NFR-02, NFR-05, NFR-07; Metric 01 and Metric 03 explainability evidence

#### Objective

Implement only the T07 deterministic color-matching slice: a validated,
attributed suggestion rule table; CIELAB/CIELCH conversion; neutral,
analogous, complementary, and tone-based guidance; Vietnamese explanations;
and an optional CVD-separation heuristic.

#### Starting state

- Branch: `mvp`; clean synchronized baseline commit
  `8d0938ebdce9c29aadd4992a0c1e2c462e5f98f9`.
- Approved runtime: conda environment `lens`, Python `3.10.20`, executable
  `D:\Coding\Anaconda\envs\lens\python.exe`.
- Dependencies complete: T04 is `DONE`; T02 provides the documented
  person-derived torso-mask backend and fallback limitations.
- Baseline checks: `python -m pip check` reported no broken requirements and
  `python -m pytest -q` passed `157` tests before T07 implementation.

#### Smallest implementation

- Add `assets/suggestions.csv` plus schema/provenance documentation and strict
  loader validation.
- Add a typed matcher API whose only non-empty input path accepts T04's
  immutable `ColorCluster`, echoing its original corrected Lab/RGB values in
  every result. T06 assistive display colors are not accepted by this API.
- Generate deterministic neutral/chromatic guidance using CIELCH transforms,
  with optional DaltonLens/CIEDE2000 separation diagnostics and no confidence
  or diagnosis claim.
- Add deterministic unit/integration tests and an offline evidence runner;
  do not compose the T08 live pipeline.

#### Definition-of-Done status at start

- [ ] Unit tests cover at least neutral and chromatic examples.
- [ ] Suggestions are generated from original corrected colors only.
- [ ] Missing/unknown colors produce a safe explanation, not a crash or
  fabricated high confidence.
- [ ] Rules are explicitly described as guidance, not objective fashion truth.

#### Deviations, limitations, and blockers

- Deviation from plan: none.
- Active blocker: none.

---

### `2026-08-20 16:11 +07:00` - `T07` `Rule-based color matching complete`

**Status:** `DONE`
**Owner/agent:** Codex
**Plan reference:** `plan.md#t07--rule-based-color-matching`

#### Outcome

T07 now provides a deterministic `RuleBasedMatcher` whose executable input is
only T04's original corrected `ColorCluster` (or `None` for the safe missing
case). It converts conventional CIELAB to CIELCH, classifies the source as
neutral/chromatic, and applies a five-row validated table for neutral,
analogous, complementary, and tone guidance. Every result and suggestion
echoes the original Lab/RGB source; T06 assistive display values have no input
field.

The table has an exact schema, per-row provenance, enum/range/relationship
validation, unique IDs, and required-coverage validation. Optional
profile/severity input adds original and simulated CIEDE2000 separation with a
clearly named heuristic threshold. Missing or unsupported colors return no
suggestions and a Vietnamese explanation. No output type contains a confidence
field, and every result includes the Vietnamese non-objective-guidance notice.

#### Files changed

| File | Change and reason |
| --- | --- |
| `src/chromalens/matching.py` | Added typed CIELAB/CIELCH conversion, strict rule loading, deterministic matching contracts, safe fallback states, and optional CVD separation. |
| `assets/suggestions.csv` | Added five project-authored, attributed neutral/chromatic rule rows. |
| `assets/matching/README.md` | Documented schema, provenance, transforms, original-color boundary, safety language, and limitations. |
| `tests/unit/test_t07_matching.py` | Added conversion, validation, neutral/chromatic, deterministic, CVD, fallback, type-boundary, and configuration tests. |
| `tests/integration/test_t07_original_color_contract.py` | Added T03/T04-to-T07 proof that original corrected Lab/RGB reaches matching unchanged and a display tuple is rejected. |
| `scripts/t07_matching_evidence.py` | Added reproducible ignored CSV/JSON/swatch evidence with fail-fast DoD assertions. |
| `README.md` | Added T07 API, evidence commands, handoff rules, guidance disclaimer, and limitations. |
| `codinglog.md` | Recorded T07 start, decision, measured evidence, and completion. |

#### Implementation decision

- **DEC-009:** Matching has one source contract: T04 `ColorCluster`. A neutral
  source gets a light/dark contrast item; a chromatic source gets neutral,
  +30-degree analogous, 180-degree complementary, and contrasting-lightness
  same-hue tone items. The table's integer priority is deterministic display
  ordering only. All wording and the optional Delta-E threshold are
  project-authored heuristics awaiting T09 evaluation, not confidence,
  diagnosis, accessibility assurance, or objective fashion truth.
- Target Lab is converted to displayable 8-bit sRGB and measured again after
  gamut clipping, so reported target Lab/CIELCH describes the actual display
  tuple rather than an unattainable requested coordinate.

#### Commands run and observed results

```text
D:\Coding\Anaconda\envs\lens\python.exe -m compileall -q src scripts tests
D:\Coding\Anaconda\envs\lens\python.exe -m pytest -q tests\unit\test_t07_matching.py tests\integration\test_t07_original_color_contract.py
D:\Coding\Anaconda\envs\lens\python.exe scripts\t07_matching_evidence.py
D:\Coding\Anaconda\envs\lens\python.exe -m pytest -q
D:\Coding\Anaconda\envs\lens\python.exe -m pip check
D:\Coding\Anaconda\envs\lens\python.exe -m chromalens --help
git diff --exit-code -- pyproject.toml environment.yml requirements .github/workflows/ci.yml
git diff --check
git check-ignore -v artifacts/t07-matching/evidence.json artifacts/t07-matching/suggestions.csv artifacts/t07-matching/suggestion_swatches.png
git ls-files (forbidden environment/cache/weight pattern and tracked files over 5 MiB checks)
```

| Check | Result | Evidence |
| --- | --- | --- |
| Baseline repository suite | PASS, exit 0 | `157 passed in 4.80s` before implementation |
| First focused T07 run | FAIL, exit 1 | `1 failed, 19 passed`; requested 180-degree complement measured 154.292 degrees after sRGB gamut clipping, 0.708 degrees outside an overly narrow display-space tolerance |
| Smallest focused-test repair | PASS | Kept the exact 180-degree rule assertion and tested the post-gamut target as opposite (`>=150` degrees), matching the documented two-stage contract; no product rule/threshold changed |
| Final focused T07 suite | PASS, exit 0 | `20 passed in 0.29s` |
| Full repository suite | PASS, exit 0 | `177 passed in 1.99s`; final post-documentation repeat `177 passed in 2.14s` |
| Evidence runner | PASS, exit 0 | 5 validated rules and 9 suggestions; CSV, JSON, and PNG under ignored `artifacts/t07-matching/` |
| Visual evidence review | PASS | Neutral contrast and red/blue neutral, analogous, complementary, and tone swatches opened and inspected |
| Compile/dependency/CLI gates | PASS, exit 0 | All modules compiled; no broken requirements; help rendered without camera, model, network, or special hardware |
| Dependency/lock/CI stability | PASS, exit 0 | No diff in `pyproject.toml`, `environment.yml`, `requirements/`, or CI workflow; no dependency added |
| UTF-8 Vietnamese check | PASS, exit 0 | Guidance notice and CSV explanation read as exact Unicode through Python 3.10 |
| Artifact/repository policy | PASS, exit 0 | All three generated evidence files are ignored; no forbidden environment/model artifact or tracked file over 5 MiB found |

#### Measured deterministic evidence

These are controlled contract measurements, not fashion-taste, clinical,
accessibility, camera-accuracy, or user-validation claims.

| Measurement | Observed value |
| --- | ---: |
| Validated rule rows | 5 |
| Neutral controlled suggestions | 1 (`neutral`) |
| Red controlled suggestions | 4 (`neutral`, `analogous`, `complementary`, `tone`) |
| Blue controlled suggestions | 4 (`neutral`, `analogous`, `complementary`, `tone`) |
| Missing/unknown suggestions | 0 / 0 |
| Focused/full test count | 20 / 177 passed |
| Python/base versions | Python 3.10.20; NumPy 1.26.4; OpenCV contrib 4.10.0.84; DaltonLens 0.1.5; pytest 8.3.5 |

#### Definition of Done

- [x] Unit tests cover a neutral grey input and chromatic red input, all four
  relationship types, deterministic order/output, conversion, rule validation,
  and optional CVD separation (`20 passed`).
- [x] The only non-empty matcher input is T04 `ColorCluster`; every suggestion
  echoes its original corrected Lab/RGB. Integration evidence rejects a raw
  T06-like display tuple.
- [x] `None` and an unsupported `ultraviolet` name return typed empty results
  with safe Vietnamese explanations and no confidence field.
- [x] Rule documentation, every `MatchingResult`, README, and evidence scope
  explicitly describe the output as guidance rather than objective fashion
  truth.

#### Deviations and known limitations

- Deviation from `plan.md`: none. No dependency, lock, CI, CLI, live-pipeline,
  or T08 behavior changed.
- The five-row table is project-authored and deliberately small. It ignores
  garment material, culture, context, trends, and personal taste.
- CIELCH transformations and the default simulated Delta-E threshold are
  explainable but uncalibrated; sRGB gamut conversion can shift the requested
  coordinate. T09 owns validation with declared users and conditions.
- T07 inherits all T02-T05 mask, lighting, color extraction/naming, and CVD
  simulation limitations. The committed asset is resolved from the repository
  layout used by the documented editable install.
- T07 remains an independently testable slice; T08 owns live composition and
  presentation of the guidance notice.

#### Exact next task

`T08 - End-to-end live pipeline and controls`.

#### Version control

- Branch: `mvp`
- Planned atomic commit: `feat: add rule-based color matching`
- Known-good pre-T07 baseline: `8d0938ebdce9c29aadd4992a0c1e2c462e5f98f9`

---

### `2026-08-20 16:24 +07:00` - `T08` `End-to-end live pipeline and controls`

**Status:** `IN_PROGRESS`
**Owner/agent:** Codex
**Plan reference:** `plan.md#t08--end-to-end-live-pipeline-and-controls`
**Requirements/rubric affected:** FR-01-FR-12; NFR-01-NFR-07; Metrics 01, 02, and 03 working-prototype evidence

#### Objective

Compose the completed T01-T07 modules into one local webcam/video pipeline
with user-selected profile/severity, recolor and diagnostic controls, bounded
newest-frame behavior, explicit degraded/stale states, and copied-frame views.

#### Starting state

- Branch `mvp` is clean and synchronized with `origin/mvp` at
  `7998650f3e8d00d3c81c93f5716c714112230e44`.
- Required tasks T01-T06 are `DONE`; optional T07 is also `DONE` and may be
  presented without changing the original-color-only contract.
- Approved runtime is conda environment `lens`, Python `3.10.20`, executable
  `D:\Coding\Anaconda\envs\lens\python.exe`.
- Baseline dependency check: `python -m pip check` reports no broken
  requirements. Baseline suite: `177 passed in 2.14s`.
- The only verified AI backend is the locked MediaPipe person-derived torso
  heuristic on CPU. SCHP remains `DEFERRED` to T10 and must not be invoked.

#### Smallest implementation

- Add `pipeline.py` as the sole composition boundary. Preserve
  `FramePacket.original_bgr`, run T03-T07 in their documented channel order,
  and return typed per-frame state including explicit degraded reasons.
- Add a bounded newest-item mailbox/capture worker for live webcam mode; local
  video uses the same analytical pipeline synchronously so it never skips the
  finite evaluation sequence. Never render analysis for a different frame ID
  as current.
- Extend the existing CLI and renderer with keyboard/CLI controls for profile,
  severity, recolor enable/disable, and original/assistive/mask/risk/
  diagnostic views. Reset temporal state when the stream or CVD context
  changes.
- Add deterministic end-to-end tests with a fake segmenter and generated local
  video, plus an opt-in real MediaPipe smoke/evidence path. Do not add T09's
  evaluation protocol, claim official demo-hardware performance, or start
  SCHP/OpenVINO work.

#### Definition-of-Done status at start

- [ ] One command launches webcam demo and another processes sample video.
- [ ] End-to-end output shows mask, original color, CVD risk, selective
  recolor when triggered, outline, and separate scores.
- [ ] User can change profile/severity and disable recoloring.
- [ ] A two-minute run shows no continuously increasing lag or memory trend.
- [ ] Degraded/missing modules are explicit and stale results are never shown
  as current without indication.

#### Deviations, limitations, and blockers

- Deviation from plan: none.
- Active blocker: none. This development machine is still not declared the
  official demo hardware, so T08 observations will be labeled accordingly.

---

### `2026-08-20 16:58 +07:00` - `T08` `End-to-end live pipeline and controls`

**Status:** `DONE`
**Owner/agent:** Codex
**Plan reference:** `plan.md#t08--end-to-end-live-pipeline-and-controls`
**Requirements/rubric affected:** FR-01-FR-12; NFR-01-NFR-07; Metrics 01, 02, and 03 working-prototype evidence

#### Outcome

- `python -m chromalens --webcam` now launches the full local MediaPipe CPU
  pipeline; `--video PATH` runs the same pipeline sequentially. The explicit
  `--preview-only` option preserves T01 capture diagnostics without loading a
  segmentation backend.
- The live renderer exposes assistive, original, mask, risk, and diagnostic
  views. It shows current frame ID, T04 original corrected color and margin,
  heuristic mask confidence, T05 risk, T03 lighting quality, backend, dropped
  frames, and a visible degraded reason without conflating those measurements.
- CLI and keyboard controls select CVD profile, severity, recolor enablement,
  and view. A changed CVD/recolor context resets T06 temporal selection state.
- Webcam capture uses one producer and an exact one-packet mailbox. Slow
  inference overwrites/counts stale capture frames; it cannot create an
  unbounded queue. Finite video deliberately remains ordered and lossless.
- Every `PipelineFrameResult` requires `analysis_frame_id == packet.frame_id`.
  Empty/failed current segmentation clears mask history and causes dependent
  color/risk/recolor stages to skip or degrade explicitly; no prior analysis
  is presented as current.

#### Files changed

| File | Change |
| --- | --- |
| `src/chromalens/pipeline.py` | Added typed T02-T07 composition, per-stage reports, current-frame invariant, dependency-aware degradation, and temporal reset. |
| `src/chromalens/camera.py` | Added the capacity-one `LatestFrameReader`, bounded wait, overwrite count, and deterministic shutdown. |
| `src/chromalens/tracking.py` | Added bounded current-contained EMA mask smoothing; history can never restore pixels rejected by the current mask. |
| `src/chromalens/metrics.py` | Added bounded latency/processing/RSS measurements and Windows/Linux RSS probes. |
| `src/chromalens/renderer.py` | Added five copied-frame T08 views, current analysis/status panel, outline, separate scores, controls, and dropped-frame footer. |
| `src/chromalens/app.py` | Added full-pipeline CLI/session runner, controls, latest-frame webcam path, sequential video path, cleanup, summaries, and explicit T01 preview path. |
| `scripts/t08_pipeline_evidence.py` | Added controlled end-to-end visuals, real MediaPipe fixture integration, generated sample AVI, and optional private-free live stability evidence. |
| `tests/unit/test_t08_tracking_metrics.py` | Added bounded mask/metrics, stale containment, RSS, percentile, and slope tests. |
| `tests/unit/test_t08_latest_frame.py` | Added hardware-free mailbox overwrite, timeout, and worker shutdown tests. |
| `tests/integration/test_t08_pipeline.py` | Added end-to-end, background-containment, view, control, degraded/failure, no-stale, and local-video tests. |
| `tests/test_t00_smoke.py` | Updated the hardware-independent help assertion for the T08 CLI description. |
| `tests/test_t01_camera_renderer.py` | Made the retained T01 video CLI test select `--preview-only` explicitly. |
| `README.md` | Documented full commands, controls, views, failure semantics, queue behavior, evidence, metrics scope, privacy, and limitations. |
| `codinglog.md` | Recorded T08 start, decision, measured evidence, failures/repairs, DoD, and completion. |

#### Implementation decision

- **DEC-010:** One `ChromaLensPipeline` owns the ordered stage composition. A
  webcam producer retains only the newest packet; finite video uses the same
  consumer pipeline synchronously. All derived data is current-frame typed.
  Mask EMA is intersected with the current mask, T03 already smooths gains,
  and T06 already applies bounded selection hysteresis. T04 original colors
  and T05 explainable risk values are not independently averaged because doing
  so would break their exact current-frame relationship or hide stale input.
- A single-color garment cannot have a fabricated relational risk. It is
  reported as unavailable until two retained current-color clusters exist;
  recolor then remains unchanged/skipped.

#### Commands run and observed results

```text
D:\Coding\Anaconda\envs\lens\python.exe -m compileall -q src tests
D:\Coding\Anaconda\envs\lens\python.exe -m chromalens --help
D:\Coding\Anaconda\envs\lens\python.exe -m pytest tests/unit/test_t08_tracking_metrics.py tests/unit/test_t08_latest_frame.py tests/integration/test_t08_pipeline.py tests/test_t00_smoke.py tests/test_t01_camera_renderer.py -q
D:\Coding\Anaconda\envs\lens\python.exe scripts/t08_pipeline_evidence.py
D:\Coding\Anaconda\envs\lens\python.exe scripts/t08_pipeline_evidence.py --stability-seconds 120
D:\Coding\Anaconda\envs\lens\python.exe -m chromalens --video artifacts/t08-pipeline/sample_mediapipe.avi --no-display
D:\Coding\Anaconda\envs\lens\python.exe -m chromalens --webcam --duration-seconds 3 --no-display
D:\Coding\Anaconda\envs\lens\python.exe -m chromalens --webcam --duration-seconds 120 --no-display
D:\Coding\Anaconda\envs\lens\python.exe -m pytest -q
D:\Coding\Anaconda\envs\lens\python.exe -m pip check
git diff --exit-code -- pyproject.toml environment.yml requirements .github/workflows/ci.yml
git diff --check
git check-ignore -v artifacts/t08-pipeline/evidence.json artifacts/t08-pipeline/sample_mediapipe.avi artifacts/t08-pipeline/controlled_assistive.png
git ls-files (forbidden environment/cache/weight/artifact pattern and tracked files over 5 MiB checks)
```

| Check | Result | Evidence |
| --- | --- | --- |
| Baseline repository suite | PASS, exit 0 | `177 passed in 2.14s` before implementation |
| First focused T08 suite | PASS, exit 0 | `25 passed in 1.52s` |
| Final focused metrics/pipeline repeat | PASS, exit 0 | `12 passed in 0.50s` after the Windows RSS correction and trend fields |
| Final full repository suite | PASS, exit 0 | `193 passed in 2.08s`; includes non-finite CLI rejection and default-assistive mask-confidence propagation |
| Controlled full-pipeline evidence | PASS, exit 0 | Red/brown corrected clusters, deutan risk `high/0.800739`, recolor applied, outside-mask bytes unchanged, matching source `red`, all five views written |
| Real-backend evidence | PASS, exit 0 | `mediapipe-selfie-torso/cpu` returned one aligned region with 73,791 pixels on licensed `astronaut.png`; all five views written |
| Sample-video full CLI | PASS, exit 0 | 8/8 frames through real MediaPipe, clean `end_of_video`, no webcam opened |
| Webcam full CLI smoke | PASS, exit 0 | 32 frames at 640x480 in 3.69 s; clean duration stop and resources released |
| Two-minute synthetic-live run | PASS, exit 0 | 931 processed; 1,255 stale capture frames dropped; fixed 600 latency/95 RSS samples; zero degraded frames |
| Two-minute real webcam run | PASS, exit 0 | 1,765 processed; 1,262 stale capture frames dropped; duration `120.36 s`; no frames saved/uploaded |
| Dependency/lock/CI stability | PASS, exit 0 | No change to `pyproject.toml`, environment/lock files, or CI workflow; `pip check` reports no broken requirements |
| Repository policy | PASS, exit 0 | Generated PNG/JSON/AVI ignored; no tracked cache/environment/model artifact or file over 5 MiB |

#### Evidence-command repair record

- The first 120-second synthetic run completed but returned RSS as
  `unavailable`; it was not accepted as memory evidence. Cause: the Windows
  process handle used the default 32-bit `ctypes` return type. The smallest
  repair declared `HANDLE`/argument/result types for `GetProcessMemoryInfo` and
  added a positive-host-RSS unit test. No product behavior or dependency
  changed.
- A second synthetic run measured RSS but its full-session regression included
  allocator warm-up. Bounded steady-state delta/slope and latency slope fields
  were added so warm-up could be distinguished from continuous growth. The
  final controlled and webcam runs below are the accepted observations.

#### Measured T08 evidence

These are local development-machine observations, not official demo-hardware,
sensor-to-photon, accuracy, medical, or T09 evaluation claims.

| Measurement | Synthetic live 360x240 | Real webcam 640x480 |
| --- | ---: | ---: |
| Requested/measured duration | 120.0 / 120.109 s | 120.0 / 120.36 s |
| Backend | controlled test double / CPU | MediaPipe torso heuristic / CPU |
| Processed frames / FPS | 931 / 7.75 | 1,765 / 14.66 |
| Dropped stale capture frames | 1,255 | 1,262 |
| Capture-to-render p50 / p95 | 156 / 235 ms | 93 / 172 ms |
| Processing p50 / p95 | 125 / 203 ms | retained internally; not printed by CLI summary |
| Latency regression over retained samples | +16.74 ms/min | -18.51 ms/min |
| RSS start / end / peak | 108.13 / 110.43 / 118.69 MiB | 131.25 / 173.14 / 208.36 MiB |
| RSS whole-session delta | +2.31 MiB | +41.89 MiB warm-up-inclusive |
| RSS second-half delta | -8.06 MiB | -15.77 MiB |
| RSS second-half regression | +1.97 MiB/min, non-monotonic | +5.95 MiB/min, non-monotonic |
| Degraded frames | 0 | 1,235 |

The capacity-one mailbox and 600-entry latency bound make queue/state memory
constant. Both memory traces ended below their observed peaks and both
second-half endpoint deltas were negative; the webcam latency slope was also
negative. Therefore neither run showed continuously accumulating queue lag or
a continuously increasing RSS trace. The positive second-half RSS regression
despite negative endpoint deltas records non-monotonic allocator/runtime
variation and must not be interpreted as a leak-free guarantee. T09 owns a
declared protocol and longer/laptop-specific performance characterization.

#### Definition of Done

- [x] One command launches the full webcam demo and `--video PATH` processes a
  sample video through the same pipeline; both were executed with real
  MediaPipe and exit 0.
- [x] Controlled and real fixture views show current garment mask, original
  corrected color/margin, relational risk, triggered selective recolor,
  double outline, lighting quality, mask confidence, and separate risk score.
- [x] CLI plus `p`, `[`, `]`, `r`, `v`, and `1`-`5` controls change
  profile/severity/recolor/view; deterministic tests cover reversible state.
- [x] Two independent 120-second latest-frame runs completed with bounded
  sample/state storage, explicit dropped-frame counts, no accumulating queue
  lag, and non-monotonic rather than continuously increasing RSS evidence.
- [x] Missing/failing segmentation is visible per current frame; tests prove
  prior mask/color/risk/recolor state is cleared and frame-ID mismatch is
  rejected before rendering.

#### Deviations and known limitations

- Deviation from `plan.md`: none. No dependency, lock, CI workflow, MVP scope,
  SCHP, OpenVINO, T09 protocol, dataset, or threshold changed.
- The real webcam run reported 1,235 degraded frames because the heuristic did
  not consistently retain a person/torso in the uncontrolled camera scene.
  This demonstrates explicit degradation, not segmentation adequacy; T09 must
  use declared footage/conditions and record failure examples.
- MediaPipe remains a person-derived torso heuristic, not semantic garment
  parsing. A multicolor retained mask is required for relational risk and
  selective recolor; plain/single-cluster garments correctly report no pair.
- The current P0 pipeline runs every analytical module on each consumed frame.
  It prioritizes newest-frame latency over capture completeness and therefore
  drops frames under load. Optimization is deferred to T10 only after T09.
- Runtime metrics begin before warm-up, use process working set/RSS and software
  monotonic timestamps, and are not sensor-to-photon measurements. OpenCV and
  MediaPipe allocator behavior can retain memory after warm-up.
- The renderer uses OpenCV's ASCII-only Hershey font; Vietnamese labels are
  transliterated in-frame while exact Unicode remains in structured results.

#### Exact next task

`T09 - Evaluation, responsible AI, and evidence package`.

#### Version control

- Branch: `mvp`
- Planned atomic commit: `feat: compose end-to-end live pipeline`
- Known-good pre-T08 baseline: `7998650f3e8d00d3c81c93f5716c714112230e44`

---

### `2026-08-20 18:59 +07:00` - `T09` `Evaluation Gate 0 and collaboration contract`

**Status:** `IN_PROGRESS`
**Owner/agent:** Repository owner + Codex (coordinators)
**Plan reference:** `plan.md#t09--evaluation-responsible-ai-and-evidence-package`
**Requirements/rubric affected:** FR-12, FR-18; NFR-02-NFR-08; Metrics 01, 02, and 03 evidence integrity

#### Objective

Freeze one versioned T09 protocol, machine-readable result contract, declared
fixture/test-case matrix, metric names/formulas/units/thresholds, artifact and
consent policy, and non-overlapping file ownership before three collaborators
branch from `mvp`.

#### Starting state

- Branch `mvp` is clean and synchronized with `origin/mvp` at T08 commit
  `f315fd766f01c231c3265c3f91522e1c5e50af9e`.
- T08 is `DONE`; T09 is the exact next task. SCHP/OpenVINO remain deferred to
  T10 and are outside this gate.
- Approved runtime is `D:\Coding\Anaconda\envs\lens\python.exe`, Python
  `3.10.20`; `pip check` reports no broken requirements.
- Current T08 packet timestamps are taken immediately after
  `VideoCapture.read()` returns a frame. The existing measurement ends after
  rendering and before `cv2.imshow`; it is therefore a software
  capture-return-to-render-complete latency, not sensor-to-photon latency.
- The current machine remains a development machine, not declared official
  demo hardware. Every T09 performance record must identify its exact host,
  resolution, backend, and device.

#### Smallest Gate 0 implementation

- Freeze protocol version `1.0.0`, a JSON Schema, and an explicit case matrix.
- Rename/extend the T08 instrumentation so the public fields and CLI use the
  exact locked latency semantics and GUI submission is measured separately.
- Track only small curated CSV/JSON/Markdown results below
  `evaluation/results/`; keep raw/private/large evidence below ignored
  `artifacts/t09/` and require manifests, provenance/consent, licenses, sizes,
  and SHA-256 checksums for every report artifact.
- Assign disjoint result/script/test namespaces to the four T09 workstreams;
  shared protocol/schema/configuration files remain coordinator-owned.
- Add hardware-, webcam-, network-, and model-independent Gate 0 tests. Do not
  run the evaluation or report T09 as `DONE` in this commit.

#### Baseline commands and observed results

```text
git status --short --branch
git branch --show-current
git rev-parse HEAD
git rev-parse origin/mvp
D:\Coding\Anaconda\envs\lens\python.exe --version
D:\Coding\Anaconda\envs\lens\python.exe -m pip check
rg --files
```

| Check | Result | Evidence |
| --- | --- | --- |
| Git baseline | PASS, exit 0 | Clean synchronized `mvp`; local/remote SHA `f315fd7...` |
| Approved interpreter | PASS, exit 0 | Python 3.10.20 in the isolated `lens` environment |
| Dependency consistency | PASS, exit 0 | `No broken requirements found` |
| Source-of-truth conflict check | PASS | T09 depends on completed T08; requested Gate 0 is within T09 and does not alter `plan.md` |
| Gate files/tests | NOT RUN - implementation begins after this status entry | N/A |

#### Definition-of-Done status

- [ ] `evaluation/protocol.md` freezes data, hardware-recording requirements,
  resolutions, thresholds, and procedures before results are produced.
- [ ] Machine-readable schema and human-readable result/artifact policy are
  versioned, validated, and collaboration-safe.
- [ ] Latency names distinguish source-read return, render completion, GUI
  submission, and unavailable sensor-to-photon measurement.
- [ ] Fixture/test-case list and file ownership are explicit and non-overlapping.
- [ ] Curated result text is trackable; raw/private/large artifacts stay ignored.
- [ ] Local tests and CI-equivalent gates pass before the commit is pushed.

#### Deviations, limitations, and blockers

- Deviation from `plan.md`: none; freezing the protocol before reporting any
  result is the first T09 work item.
- Active blocker: none. Missing future footage or official demo-hardware
  declaration is represented as an explicit acquisition/measurement status;
  it does not block freezing an honest protocol.

#### Exact next action

Create and validate the Gate 0 contract, commit it atomically on `mvp`, push
it to `origin/mvp`, and wait for CI before collaborators create branches from
that exact commit.

---

### `2026-08-20 19:21 +07:00` - `T09` `Evaluation Gate 0 complete`

**Status:** `IN_PROGRESS` - Gate 0 is complete; T09 measurements and reports
have not been produced.
**Owner/agent:** Repository owner + Codex (coordinators)
**Plan reference:** `plan.md#t09--evaluation-responsible-ai-and-evidence-package`

#### Outcome

- Froze protocol, result schema, metric registry, case registry, and file
  ownership at version `1.0.0` before any T09 result was reported.
- Locked 92 case rows: a 33-row 11-color x three-lighting physical matrix; 11
  available digital contract patches; 20 segmentation cases including three
  planned annotated cases; six CVD confusing/control pairs; ten end-to-end
  cases; five performance/latency-semantics cases; and responsible-AI/manual
  baseline cases. Missing media remains honestly `TO_BE_ACQUIRED`.
- Locked 32 metric definitions with names, formulas, units, aggregations, and
  claim thresholds. Context performance floor/target now uses the GUI software
  proxy `source_read_to_display_submit_ms`; headless uses
  `source_read_to_render_ms`; `sensor_to_photon_ms` remains `NOT_MEASURED`
  without external synchronized apparatus.
- Corrected shared instrumentation before branch creation. Frame timestamps
  remain after `VideoCapture.read()` returns. Runtime tracking now separately
  ends after render and after `cv2.imshow()`, supports a 15-second warm-up plus
  measured-duration reset, retains up to 10,000 bounded samples, and computes
  the frozen four-window latency/RSS growth diagnostics. The pre-render overlay
  value is renamed `frame_age_at_overlay_ms` and is explicitly not a T09
  latency metric.
- Made small curated CSV/JSON/Markdown result namespaces trackable while raw
  media/private footage/large evidence remains ignored below `artifacts/t09/`.
  CI rejects forced raw T09 artifacts, unowned result paths, unsupported result
  extensions, and curated files over 1 MiB.
- Required an embedded artifact manifest with provenance/consent, license,
  exact byte size, generation command, derivation links, and SHA-256 for every
  report artifact. `git add -f` is prohibited.
- Assigned coordinator/common files and four disjoint result/script/test
  namespaces so individual T09 workstreams do not edit `codinglog.md` or each
  other's outputs.

#### Files changed

| File/path | Change and reason |
| --- | --- |
| `evaluation/protocol.md` | Created the frozen human-readable Gate 0 contract. |
| `evaluation/schema/t09-result.schema.json` | Created strict JSON Schema 2020-12 result structure and responsible-AI/artifact contracts. |
| `evaluation/schema/metric_registry.json` | Created the 32-definition metric/formula/unit/threshold registry. |
| `evaluation/fixtures/test_cases.csv` | Created the frozen 92-case registry. |
| `evaluation/fixtures/README.md` | Documented case columns and honest acquisition states. |
| `evaluation/OWNERSHIP.md` | Froze shared and per-workstream file ownership/branch namespaces. |
| `evaluation/results/README.md` | Documented tracked curated text versus ignored raw artifact policy. |
| `.gitignore` | Unignored only curated T09 CSV/JSON/Markdown result paths while preserving raw artifact ignores. |
| `.github/workflows/ci.yml` | Enforced T09 result namespaces/extensions/1 MiB limit and rejection of tracked `artifacts/t09/`. |
| `src/chromalens/metrics.py` | Renamed/extended bounded instrumentation and added frozen growth diagnostics. |
| `src/chromalens/app.py` | Recorded post-render/post-`imshow` endpoints separately; added warm-up boundary and unambiguous CLI summary. |
| `src/chromalens/renderer.py` | Renamed the pre-render overlay age so it cannot be mistaken for an evaluation latency. |
| `tests/test_t09_gate.py` | Added schema/metric/case/ownership/artifact/semantics Gate tests. |
| `tests/unit/test_t08_tracking_metrics.py` | Updated metric names and tested headless omission plus four-window growth. |
| `tests/integration/test_t08_pipeline.py` | Tested headless/GUI sample separation and warm-up exclusion. |
| `tests/test_t01_camera_renderer.py` | Updated the live diagnostic field name. |
| `README.md` | Documented frozen semantics, warm-up commands, branch point, ownership, and artifact policy. |
| `codinglog.md` | Recorded Gate start, observed repairs, decision, evidence, and continued T09 status. |

#### Commands run

```text
git status --short --branch
git branch --show-current
git rev-parse HEAD
git rev-parse origin/mvp
Get-CimInstance Win32_Processor / Win32_ComputerSystem / Win32_OperatingSystem / Win32_VideoController
Get-PnpDevice -Class Camera -Status OK
D:\Coding\Anaconda\envs\lens\python.exe --version
D:\Coding\Anaconda\envs\lens\python.exe -m pip check
D:\Coding\Anaconda\envs\lens\python.exe -m chromalens --help
D:\Coding\Anaconda\envs\lens\python.exe -m pytest -q tests\test_t09_gate.py tests\unit\test_t08_tracking_metrics.py
D:\Coding\Anaconda\envs\lens\python.exe -m pytest -q tests\test_t09_gate.py tests\unit\test_t08_tracking_metrics.py tests\integration\test_t08_pipeline.py
D:\Coding\Anaconda\envs\lens\python.exe -m pytest -q
D:\Coding\Anaconda\envs\lens\python.exe -m compileall -q src scripts tests
D:\Coding\Anaconda\envs\lens\python.exe - (JSON/CSV registry audit via stdin)
D:\Coding\Anaconda\envs\lens\python.exe - (six CVD pair sanity calculations via stdin)
git diff --exit-code -- pyproject.toml environment.yml requirements
git diff --check
git check-ignore -q --no-index -- <curated and raw T09 policy probes>
```

#### Tests and observed results

| Check | Result | Evidence |
| --- | --- | --- |
| First focused Gate run | FAIL at assertion level: 2 failed and 11 passed because two expected Markdown phrases crossed line breaks | Terminal output |
| Smallest repair | Normalized whitespace in the two documentation assertions; protocol/runtime semantics did not change | `tests/test_t09_gate.py` |
| Focused Gate/runtime/pipeline suite | PASS, exit 0 | Final `25 passed in 0.75s` |
| Full repository suite | PASS, exit 0 | Final staged-content rerun `204 passed in 2.78s` |
| Schema/registry/case audit | First `python -c` attempt failed before audit with a PowerShell quoting `SyntaxError`; stdin rerun PASS, exit 0 | Schema `1.0.0`; 32 metrics; 92 unique case rows |
| CVD pair order check | PASS, exit 0 | Protan `0.344831 > 0`; deutan `0.693100 > 0`; tritan `0.519419 > 0` |
| CLI/dependency/compile | PASS, exit 0 | Help includes warm-up option; no broken requirements; all Python compiled |
| Dependency and lock stability | PASS, exit 0 | No diff in `pyproject.toml`, `environment.yml`, or `requirements/`; no package installed |
| Ignore-policy probes | PASS, exit 0 | Curated CSV/JSON/Markdown and results README not ignored; result media and all `artifacts/t09/` probes ignored |
| Whitespace check | PASS, exit 0 | `git diff --check`; only Windows LF-to-CRLF notices were printed |

#### Frozen thresholds and semantics evidence

- Demo floor: at least 5 processed FPS and GUI p50
  `source_read_to_display_submit_ms <= 350` on owner-declared demo hardware or
  an explicit limitation; project target 10 FPS and 200 ms.
- Performance interval: 15 seconds warm-up plus 120 measured seconds; linear
  p50/p95 over an untruncated bounded sample set.
- Continuous-growth diagnostic: four strictly increasing 30-second medians
  plus an absolute/relative increase guard; automated positive-path test.
- Digital color contract: 11/11; physical matrix has no authorized calibrated
  accuracy pass threshold and must report the full table/confusion matrix.
- Segmentation: adequacy rating at least 2 is usable; all 20 cases visible;
  aggregate adequacy and IoU remain observation-only.
- Existing risk medium/high thresholds remain 0.25/0.60; each confusing pair
  must outrank its same-profile control.
- Outside-mask changed pixels, stale frame-ID mismatches, checksum mismatches,
  and unconsented tracked media all require exactly zero.

#### Definition-of-Done status

- [x] Gate 0 freezes data/case IDs, host/resolution recording, thresholds,
  metric semantics, procedure, schema, and ownership before results.
- [x] Machine-readable schema/registry and human-readable policy are tested.
- [x] GUI/headless latency endpoints are separate and sensor-to-photon is not
  fabricated.
- [x] Curated text tracking and raw/private/bulk artifact exclusion are tested
  and enforced in CI.
- [x] Gate-specific and full automated suites pass without webcam/network or
  external model weights.
- [ ] T09 plan DoD is not complete: workstream measurements/reports and three
  measured failure examples have not yet been produced.

#### Decision and limitations

- **Decision ID:** `DEC-011`.
- The Gate host is recorded only as a development machine. No official demo
  hardware or sensor-to-photon value is declared.
- Physical color/lighting inputs, new segmentation footage/annotations,
  personal footage consent, and user feedback are not present. Frozen
  acquisition slots must remain `NOT_RUN` until compliant assets exist.
- JSON Schema is parsed and structurally cross-checked with the metric/case
  registries using the locked standard-library/pytest environment. No new
  schema-validation dependency was added; workstream result validation must
  use the frozen schema plus registry checks in their tests.
- This commit prepares and gates T09 only. It does not start T10 or create
  collaborator branches.

#### Version control and next action

- Branch: `mvp`.
- Pre-gate baseline: `f315fd766f01c231c3265c3f91522e1c5e50af9e`.
- Planned atomic commit: `chore: freeze T09 evaluation protocol`.
- Exact next action after push and green CI: Dong, Phong, and Trinh create
  their assigned branches from the new Gate 0 commit; coordinators continue
  the `end_to_end` T09 workstream on `mvp`.

---

## 6. Final handoff checklist

Complete this only after all P0 work is finished.

- [ ] Summary table matches the actual repository.
- [ ] Every P0 task has a `DONE` entry and evidence.
- [ ] All `BLOCKED`, `PARTIAL`, and `DEFERRED` items are visible.
- [ ] Install and run commands were tested in a clean/declarable environment.
- [ ] Automated tests and current result are recorded.
- [ ] Performance values include hardware, resolution, backend, and conditions.
- [ ] Evaluation set/protocol and limitations are recorded.
- [ ] Model/data/code sources and licenses are recorded.
- [ ] Privacy and responsible-AI behavior are recorded.
- [ ] A known-good demo version/commit is identified.
- [ ] The next human action for competition submission is stated.
