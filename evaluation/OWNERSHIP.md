# T09 File Ownership

Protocol version: `1.0.0`
Status: `FROZEN`

This map prevents four T09 workstreams from editing the same files. The human
repository owner is the coordinator; Codex assists with integration and
instrumentation on `mvp`.

## Shared coordinator-owned files

Only the coordinators edit these paths during T09:

- `evaluation/protocol.md`
- `evaluation/OWNERSHIP.md`
- `evaluation/schema/**`
- `evaluation/fixtures/**`
- `evaluation/results/README.md`
- `evaluation/results/curated/summary.md`
- `.gitignore`
- `.github/workflows/**`
- `pyproject.toml`, `environment.yml`, and `requirements/**`
- `src/chromalens/metrics.py` and shared `src/chromalens/app.py` instrumentation
- `codinglog.md`, `README.md`, and `plan.md`

Contributors treat the frozen protocol/schema/case list as read-only. They
send a proposed change to the coordinators instead of resolving it locally.
No workstream changes dependencies, models, risk thresholds, MVP scope, or
the plan independently.

T09 is already `IN_PROGRESS` in `codinglog.md`. The workstreams are partitions
of that one plan task rather than new plan tasks, so contributors record their
start/handoff commands and status in their owned result/report files and do
not edit the shared coding log. The coordinators append those verified
handoffs and the final T09 status to `codinglog.md` during integration. This
preserves the repository execution record without four-way merge conflicts.

## Disjoint workstream namespaces

| Owner / suggested branch | Owned result paths | Owned implementation paths |
| --- | --- | --- |
| Repository owner + Codex / `mvp` | `evaluation/results/curated/end_to_end/**` | `scripts/t09_end_to_end_*`, `tests/evaluation/test_t09_end_to_end*` |
| Dong / `eval/t09-segmentation-dong` | `evaluation/results/curated/segmentation/**` | `scripts/t09_segmentation_*`, `tests/evaluation/test_t09_segmentation*` |
| Phong / `eval/t09-color-science-phong` | `evaluation/results/curated/color_science/**` | `scripts/t09_color_science_*`, `tests/evaluation/test_t09_color_science*` |
| Trinh / `eval/t09-performance-rai-trinh` | `evaluation/results/curated/performance_responsible_ai/**` | `scripts/t09_benchmark_*`, `scripts/t09_responsible_ai_*`, `tests/evaluation/test_t09_performance*` |

Raw workstream evidence mirrors the same keys below ignored
`artifacts/t09/<workstream>/` and is never forced into Git.

Trinh's workstream report is
`evaluation/results/curated/performance_responsible_ai/report.md`. The
coordinators own the cross-workstream final summary so Trinh does not need to
edit another contributor's result files.

## Merge contract

1. Branch from the pushed Gate 0 commit, not pre-gate commit `f315fd7`.
2. Rebase/merge the Gate baseline only when instructed; never rewrite shared
   protocol files to resolve a task-branch conflict.
3. Validate JSON against schema version `1.0.0`, preserve case IDs, and include
   artifact manifests/checksums.
4. Submit one workstream-focused PR. CI and owner review are required.
5. Coordinators merge result namespaces and create the final summary.

`git add -f` is prohibited for T09 artifacts. If a required small curated text
file is ignored unexpectedly, stop and ask the coordinator to fix the policy.
