# Post-MVP T12-T17 File Ownership

Protocol version: `2.0.0`
Status: `FROZEN`

This map prevents parallel work from editing shared integration surfaces.
Repository owner + Codex are the coordinators. A contributor proposes shared
contract changes instead of resolving them silently on a feature branch.

## Coordinator-owned shared files

- `plan.md`, `codinglog.md`, `README.md`, `AGENTS.md`, `context.md`, `rubric.md`
- `evaluation/protocol-v2.md`, `evaluation/OWNERSHIP-v2.md`
- `evaluation/schema/post-mvp-*`
- `evaluation/fixtures/post-mvp-*`
- `evaluation/results/curated/post_mvp/summary.md`
- `.gitignore`, `.gitattributes`, `.github/workflows/**`
- `pyproject.toml`, `environment.yml`, `requirements/**`
- `src/chromalens/app.py`, `pipeline.py`, `config.py`, `contracts.py`

`AGENTS.md`, `context.md`, and `rubric.md` remain source-of-truth files and are
listed here to prevent task branches from modifying them, not to authorize a
Gate change.

## Disjoint task namespaces

| Task | Owned implementation paths | Owned tests/scripts/results |
| --- | --- | --- |
| T12 | `src/chromalens/color_naming.py`, `assets/color_names/extended_palette.csv` | `tests/unit/test_t12_*`, `tests/evaluation/test_t12_*`, `scripts/t12_*`, `evaluation/results/curated/post_mvp/t12/**` |
| T13 | `src/chromalens/manual_selection.py`, segmentation adapters limited to standalone/manual contracts | `tests/unit/test_t13_*`, `tests/evaluation/test_t13_*`, `scripts/t13_*`, `evaluation/results/curated/post_mvp/t13/**` |
| T14 | `src/chromalens/display.py`; `presentation.py` changes are coordinator-integrated | `tests/unit/test_t14_*`, `tests/integration/test_t14_*`, `scripts/t14_*`, `evaluation/results/curated/post_mvp/t14/**` |
| T15 | `src/chromalens/metrics.py`; performance wiring into shared files is coordinator-integrated | `tests/unit/test_t15_*`, `tests/evaluation/test_t15_*`, `scripts/t15_*`, `evaluation/results/curated/post_mvp/t15/**` |
| T16 | `src/chromalens/spatial_risk.py`; existing risk/recolor wiring is coordinator-integrated | `tests/unit/test_t16_*`, `tests/evaluation/test_t16_*`, `scripts/t16_*`, `evaluation/results/curated/post_mvp/t16/**` |
| T17 | Coordinator-only integration and release changes | `tests/integration/test_t17_*`, `scripts/t17_*`, `evaluation/results/curated/post_mvp/t17/**` |

Gate 0 baseline files under
`evaluation/results/curated/post_mvp/gate0/**`, its validator/tests, and all
shared result summaries are coordinator-owned.

## Shared-file merge rule

Task branches do not independently edit `app.py`, `pipeline.py`, configuration,
cross-module contracts, dependency locks, CI, protocol/schema/fixtures, plan,
README, or coding log. They submit a typed integration request or a narrow
patch for coordinator application. A task must not rename another task's
fixture IDs, metrics, or result namespace.

T12-T16 can be implemented in parallel after Gate 0. T15 final acceptance is
rerun after integration. T17 is never parallelized and starts only when T12-T16
have terminal, evidence-backed statuses.

## Artifact ownership and Git policy

Raw artifacts mirror task namespaces below ignored
`artifacts/post_mvp/<task>/`. Small curated outputs live below the corresponding
tracked task result namespace. No branch uses `git add -f`. Personal media
requires recorded consent and non-identifying provenance; signed consent forms
stay outside Git. Model weights, private footage, raw video, and bulk outputs
remain untracked.
