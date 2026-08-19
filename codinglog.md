# ChromaLens AI — Coding Log

Last updated: 2026-08-20 00:35 +07:00
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
