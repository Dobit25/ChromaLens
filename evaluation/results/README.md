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
