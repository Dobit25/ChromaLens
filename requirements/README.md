# Dependency locks

`conda-win-64.lock` records the exact Conda bootstrap artifacts, builds, URLs,
and MD5 checksums. `py310-win64.lock` is generated from the base dependencies
and `dev` extra in `pyproject.toml`, including the T05 DaltonLens/Pillow
runtime. `lock-tools-py310-win64.lock` is generated
from the base and `lock` extra so CI can verify lock freshness using a hashed
lock generator. `segment-mediapipe-py310-win64.lock` contains the base, `dev`,
and `segment-mediapipe` closures, including every transitive MediaPipe/JAX and
base DaltonLens/Pillow artifact hash. `segment-schp-py310-win64.lock` is the
combined demo closure: base, `dev`, `segment-mediapipe`, and `segment-schp`.
It keeps the explicit fallback compatible while adding PyTorch 2.5.1 strict
loading/export and OpenVINO 2025.4.1 CPU runtime. Direct PyTorch-to-OpenVINO
conversion was verified, so no unused ONNX dependency is carried. The ATR
checkpoint and generated OpenVINO IR remain ignored external assets.

All five target the declared Windows/Python 3.10 collaboration platform and
are never edited casually. The integration owner regenerates them with the
exact commands documented in the repository root `README.md` whenever an
approved direct or bootstrap dependency changes.
