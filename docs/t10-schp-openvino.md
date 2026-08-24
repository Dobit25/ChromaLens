# T10 SCHP/OpenVINO acceptance record

Date: 2026-08-24
Host: Lenovo 83DV development machine, Intel(R) Core(TM) i5-13450HX,
15.78 GiB RAM, Windows, Python 3.10.20
Precision/device: FP32 OpenVINO 2025.4.1 on `CPU`; PyTorch 2.5.1 CPU reference

This is development-host evidence. It is not an official demo-hardware,
sensor-to-photon, target-user, or broad segmentation-accuracy result.

## Conversion and integrity

The primary command is:

```powershell
conda run --name lens python scripts/t10_export_schp_openvino.py
```

It verifies the ignored 267,445,237-byte ATR checkpoint at SHA-256
`e9d7c91ce3b4e7133df56b599fc817b533e3439c5e8d282a59126d2fda339a2a`,
strict-loads every state key into the pinned MIT graph, and saves an FP32 IR
plus byte/checksum/provenance manifest. The accepted 512 graph was converted
with Torch `2.5.1+cpu` and OpenVINO
`2025.4.1-20426-82bbf0292c5-releases/2025/4`. The observed strict load took
0.68 seconds and conversion/save took 21.16 seconds in the measured run.

The old custom InPlaceABNSync extension was replaced by PyTorch BatchNorm plus
the same activation. Parameter/buffer names are preserved; `strict=True`
reported all keys matched. This is an inference compatibility adaptation, not
retraining or a new model.

## Fixed-fixture conversion comparison

`tests/integration/test_t10_schp_integration.py` compares PyTorch and OpenVINO
on all five public/licensed T02 fixtures after the same 512x512 upstream affine
preprocessing and inverse-logit restoration. Every detected garment class and
mask matched; per-class IoU was at least `0.999` (four fixtures were exactly
`1.000000`; one upper-clothes mask was `0.999998`). The real-weight test passed
`2/2` locally. CI exercises the graph/runtime contract but skips the ignored
checkpoint test when the legally external asset is absent.

Lower-resolution experiments were rejected. At 256, the 512-reference IoU was
0 for several classes/fixtures; at 384, class instability remained and IoU was
as low as 0.121 for a retained class. The primary demo therefore keeps the
upstream 512 input despite lower FPS.

## Saved MediaPipe baseline versus SCHP/OpenVINO

The comparison below uses the same five fixtures and unions each backend's
returned regions. IoU means mask overlap between two different algorithms; it
is not ground-truth accuracy. SCHP returns semantic ATR classes while the
MediaPipe baseline returns one person-derived torso heuristic, so divergence
is expected and must not be described as an automatic quality win.

| Fixture | MediaPipe pixels | SCHP pixels | Union-mask IoU | SCHP classes |
| --- | ---: | ---: | ---: | --- |
| `astronaut.png` | 73,791 | 105,983 | 0.5748 | upper-clothes |
| `cc0_woman.jpg` | 49,946 | 116,180 | 0.3910 | dress |
| `loc_lincoln.jpg` | 64,227 | 66,744 | 0.8799 | upper-clothes, pants |
| `loc_man.jpg` | 68,534 | 72,069 | 0.6206 | upper-clothes, pants |
| `nasa_shepard.jpg` | 59,520 | 641,799 | 0.0793 | upper-clothes, skirt |

This establishes the intended functional distinction: SCHP can label dress,
pants, skirt, and upper-clothes instead of applying a fixed torso crop. It does
not establish superiority on unannotated scenes. The frozen T09 MediaPipe
evaluation remains historical baseline evidence and is not rewritten.

## Development-host performance

One startup plus one pass over the five fixtures produced:

| Backend | Startup | Segmentation p50/p95 | Mean-rate reciprocal |
| --- | ---: | ---: | ---: |
| MediaPipe torso CPU | 671.20 ms | 21.62 / 191.95 ms | 15.44 FPS |
| SCHP/OpenVINO FP32 CPU | 840.19 ms | 969.86 / 1544.22 ms | 1.00 FPS |

The fixture images have different resolutions, so this table is a fixed-set
comparison rather than a constant-resolution throughput benchmark. A separate
real default-CLI observation processed 20 frames of the 640x480 T11 fallback
video with no display and no degraded frame:

```text
backend=schp-atr/openvino/CPU (13th Gen Intel(R) Core(TM) i5-13450HX)
fps=0.89
source_read_to_render_p50_ms=1195.00
source_read_to_render_p95_ms=1411.65
sensor_to_photon_ms=NOT_MEASURED
```

The optimized backend is accepted for semantic class functionality and exact
conversion fidelity, not for speed. MediaPipe remains the documented explicit
fallback for venue reliability. `--schp-runtime pytorch` preserves the
reference backend; `auto` prefers verified OpenVINO and never silently changes
the selected model family.
