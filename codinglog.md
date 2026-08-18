# ChromaLens AI — Coding Log

Last updated: 2026-08-18 22:07 +07:00
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
| T00-GATE | Collaboration dependency-lock/CI gate | `IN_PROGRESS` | Codex | 2026-08-18 21:47 +07:00 | 2026-08-18 22:07 +07:00 | T00-GATE entries and cloud-CI correction below |

## 3. Active blockers

| Blocker ID | Related task | Description | Impact | Required decision/action | Owner | Status |
| --- | --- | --- | --- | --- | --- | --- |

## 4. Decision index

Use this section only for implementation decisions that affect later tasks. Detailed reasoning remains in the chronological entry.

| Decision ID | Date | Decision | Affected tasks/modules | Entry link |
| --- | --- | --- | --- | --- |
| DEC-001 | 2026-08-16 | Use Python 3.10 only and pin the minimal T00 base/dev dependencies in `pyproject.toml`; keep inference stacks optional for later tasks. | T00 and future environment changes | T00 completion entry |

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

Copy the template below for every work session or status transition.

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

- Branch:
- Commit hash: `not committed` or hash
- Known-good tag/commit preserved:

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
