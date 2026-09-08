# T09 Results Policy

Small curated UTF-8 `.csv`, `.json`, and `.md` results are tracked only below:

```text
evaluation/results/curated/end_to_end/
evaluation/results/curated/segmentation/
evaluation/results/curated/color_science/
evaluation/results/curated/performance_responsible_ai/
```

Each JSON result conforms to `evaluation/schema/t09-result.schema.json` and
uses metric names from `evaluation/schema/metric_registry.json`. Each
workstream also provides human-readable CSV or Markdown. Curated files are at
most 1 MiB and contain no base64, media, raw arrays, personal identifiers,
private consent forms, or secrets.

Raw videos, private footage, images, arrays, profiler traces, and bulk evidence
remain below ignored `artifacts/t09/<workstream>/`. Every artifact used in a
report is represented by a committed manifest entry with provenance/consent,
license, exact byte size, and SHA-256. Do not use `git add -f` to bypass this
policy.

The directories may not exist until a workstream writes a real result. Empty
placeholder result files are not evidence.

The coordinator-owned
[`curated/summary.md`](curated/summary.md) reports cross-workstream coverage
and remaining gaps. It never converts `NOT_RUN` or `NOT_MEASURED` rows into a
success claim.

## Post-MVP T12-T17 results

Protocol 2.0.0 results are tracked separately below:

```text
evaluation/results/curated/post_mvp/gate0/
evaluation/results/curated/post_mvp/t12/
evaluation/results/curated/post_mvp/t13/
evaluation/results/curated/post_mvp/t14/
evaluation/results/curated/post_mvp/t15/
evaluation/results/curated/post_mvp/t16/
evaluation/results/curated/post_mvp/t17/
```

They conform to `evaluation/schema/post-mvp-result.schema.json`, use exact
case IDs from `evaluation/fixtures/post-mvp-cases.csv`, and use metrics from
`evaluation/schema/post-mvp-metric-registry.json`. The same 1 MiB curated-text
limit applies. Raw/private/large v2 artifacts stay under ignored
`artifacts/post_mvp/<task>/` and receive provenance, consent, license, size,
and SHA-256 manifest entries. Present bytes must verify; absent ignored bytes
remain unavailable. `git add -f` remains prohibited.
