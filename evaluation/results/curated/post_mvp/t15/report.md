# T15 Instrumentation and Pre-optimization Baseline

Status: `PARTIAL` — instrumentation slice complete; optimization and final
300-second acceptance remain pending.

## Scope completed

- CI now triggers on `main`, `mvp`, and `feature/**` pushes and on pull requests
  targeting `main` or `mvp`.
- T15 is `IN_PROGRESS`.
- A pre-instrumentation and an instrumented 60-second SCHP webcam baseline were
  captured without saving or uploading frames.
- All eight frozen protocol-v2 stage names are implemented with thread-safe,
  bounded storage, warm-up reset, skip/error counts, and p50/p95 summaries.
- No OpenVINO, optical-flow, renderer, model-resolution, or cadence setting was
  optimized.

## Development-host observation

Host: Lenovo 83DV, Intel Core i5-13450HX, Windows 11, Python 3.10.20 `lens`.
Webcam requested 480×360 and delivered 640×360. Backend was SCHP-ATR FP32,
OpenVINO CPU, asynchronous keyframes. Both runs used 15 seconds warm-up and a
60-second headless measured interval.

| Observation | Before instrumentation | Instrumented |
| --- | ---: | ---: |
| Processed FPS | 14.88 | 14.96 |
| `source_read_to_render_ms` p50 | 47 ms | 47 ms |
| `source_read_to_render_ms` p95 | 78 ms | 78 ms |
| Frame-processing p50 | 32 ms | 32 ms |
| SCHP inference FPS | 2.28 | 2.31 |
| Measured degraded frames | 893/893 | 899/899 |

The sequential-run FPS delta is +0.54%. This is consistent with low timer
overhead, but it is not treated as a calibrated `<2%` proof because a live
webcam scene and host scheduling vary.

## Named-stage result

| Stage | Count | Skipped | Errors | Mean | p50 | p95 |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| `segmentation_inference` | 149 | 0 | 0 | 401.32 ms | 391 ms | 453 ms |
| `optical_flow` | 0 | 749 | 0 | — | — | — |
| `white_balance` | 899 | 0 | 0 | 20.58 ms | 16 ms | 32 ms |
| `color_extraction` | 0 | 899 | 0 | — | — | — |
| `risk` | 0 | 899 | 0 | — | — | — |
| `recolor_render` | 0 | 899 | 0 | — | — | — |
| `presentation` | 899 | 0 | 0 | 16.09 ms | 16 ms | 31 ms |
| `display_submit` | 0 | 899 | 0 | — | — | — |

SCHP inference executes concurrently on the worker thread; its duration must
not be added to main-thread stage durations. The mask-empty scene means this
run cannot rank optical flow or downstream garment analysis.

A separate three-frame synchronous video smoke using the real SCHP/OpenVINO
backend produced valid masks and exercised color, risk, recolor, and
presentation. Its observed 1.56 FPS and p95 794.2 ms are not a benchmark. A
preceding 30-frame attempt timed out and its child processes were explicitly
terminated before further measurements.

## Current target state

- Processed FPS target `>=20`: **FAIL** at 14.96.
- Headless p95 target `<=120 ms`: **PASS** at 78 ms for this partial run.
- 300-second latency/RSS growth: **NOT MEASURED**.
- GUI display-submit latency: **NOT MEASURED**.
- Sensor-to-photon latency: **NOT MEASURED**.

The next step is a controlled garment-present/motion baseline that exercises
optical flow and downstream analysis. Only then should the largest measured
main-thread bottleneck be selected for optimization.
