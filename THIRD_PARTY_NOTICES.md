# Third-party notices and credits

ChromaLens-authored code and documentation are licensed under Apache License
2.0; see `LICENSE`. This inventory covers the default MVP runtime and
redistributed evidence inputs. Package lock files contain exact distributions
and hashes.

| Component/material | Pinned version or identity | Use | License/credit record |
| --- | --- | --- | --- |
| NumPy | `1.26.4` | Arrays and numerical operations | BSD-3-Clause; NumPy Developers; installed wheel includes its transitive binary notices. |
| OpenCV contrib Python | `4.10.0.84` | Camera/video, colour conversion, morphology, display | Apache-2.0; OpenCV contributors. |
| MediaPipe | `0.10.21` | Selfie Segmentation and Face Detection model/runtime | Apache-2.0; MediaPipe Authors/Google LLC; bundled model assets. See `models/README.md`. |
| SCHP source graph | upstream commit `eb84c432cc697f494d99662a05f2335eb2f26095` | Primary ATR semantic human/garment parsing graph | MIT; Peike Li. ChromaLens uses a portable activated-BatchNorm inference adaptation; see `models/README.md`. |
| SCHP ATR checkpoint | SHA-256 `e9d7c91ce3b4e7133df56b599fc817b533e3439c5e8d282a59126d2fda339a2a` | External primary-demo model weights | Checkpoint redistribution license is not separately stated upstream. The owner-reviewed local object and derived IR are ignored and are not redistributed by this repository. |
| PyTorch | `2.5.1` | Strict SCHP checkpoint loading and reference inference/export | BSD-3-Clause; PyTorch contributors. |
| OpenVINO | `2025.4.1` | Preferred FP32 SCHP CPU runtime | Apache-2.0; Intel Corporation and contributors. |
| DaltonLens | `0.1.5`, upstream tag commit `3c41b9457aeda18cc3780aaff3052d53d34a9293` | Machado CVD simulation | MIT; DaltonLens. Full notice: `assets/cvd/DALTONLENS-MIT-LICENSE.md`. |
| CSS Color Module Level 4 named colours | W3C document accessed for T04 | sRGB anchors selected/grouped into 11 ChromaLens families | W3C Software and Document License. Full notice: `assets/color_names/W3C-SOFTWARE-DOCUMENT-LICENSE.md`. |
| NASA astronaut fixture | SHA-256 `88431cd9653ccd539741b555fb0a46b61558b301d4110412b5bc28b5e3ea6cb5` | Real-backend integration, screenshots, fallback video | Eileen Collins/NASA public-domain image redistributed by scikit-image. See `tests/samples/t02/README.md`. |
| Four additional T02 public fixtures | Exact hashes in fixture record | Segmentation evaluation | CC0, public-domain, or no-known-restriction sources as itemized in `tests/samples/t02/README.md`. |

## Algorithm and research attribution

- Machado, Oliveira, and Fernandes, “A Physiologically-based Model for
  Simulation of Color Vision Deficiency,” IEEE TVCG 2009,
  <https://doi.org/10.1109/TVCG.2009.113>.
- Sharma, Wu, and Dalal, “The CIEDE2000 Color-Difference Formula,” Color
  Research & Application 2005, <https://doi.org/10.1002/col.20070>.
- van de Weijer, Schmid, Verbeek, and Larlus, “Learning Color Names for
  Real-World Applications,” IEEE TIP 2009. ChromaLens uses its 11-term
  vocabulary but does not copy or redistribute the authors' learned lookup
  matrix because redistribution rights were not stated.

ChromaLens authors implemented the Gray-world stage, relational-risk formula,
selective recolour candidate search, matching table, pipeline composition, and
evaluation tooling. Their behavior and provenance are detailed under `assets/`
and `evaluation/`.

## External/non-redistributed assets

The SCHP ATR checkpoint is active only as an owner-reviewed local demo asset.
Its official download page does not state a separate checkpoint redistribution
license, so neither the `.pth` nor derived OpenVINO `.xml`/`.bin` is committed
or packaged. `models/README.md` records exact setup, integrity, attribution,
fallback, and claim boundaries.

Private/consented T09 inputs, consent records, generated media, and bulk/raw
artifacts are not redistributed in Git. Their curated reports retain only
non-identifying provenance references, checksums, and limitations.
