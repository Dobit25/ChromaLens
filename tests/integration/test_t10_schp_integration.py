"""Local real-weight evidence for SCHP-ATR and its OpenVINO conversion."""

from __future__ import annotations

import importlib.util
from pathlib import Path
from time import monotonic_ns

import cv2
import numpy as np
import pytest

from chromalens.contracts import FramePacket
from chromalens.segmentation import SCHPSegmenter, SCHPSegmenterConfig

_CHECKPOINT = Path("models/schp/exp-schp-201908301523-atr.pth")
_OPENVINO = Path("models/schp/openvino/schp-atr-512.xml")
_HAS_TORCH = importlib.util.find_spec("torch") is not None
_HAS_OPENVINO = importlib.util.find_spec("openvino") is not None
_FIXTURES = tuple(
    Path("tests/samples/t02") / name
    for name in (
        "astronaut.png",
        "cc0_woman.jpg",
        "loc_lincoln.jpg",
        "loc_man.jpg",
        "nasa_shepard.jpg",
    )
)


@pytest.mark.skipif(
    not (_CHECKPOINT.is_file() and _HAS_TORCH),
    reason="ignored verified ATR checkpoint/runtime is not present",
)
def test_real_pytorch_backend_strict_loads_and_segments_five_fixtures() -> None:
    detected: set[str] = set()
    with SCHPSegmenter(SCHPSegmenterConfig(runtime="pytorch")) as backend:
        assert backend.device_info == "schp-atr/pytorch/cpu"
        for frame_id, path in enumerate(_FIXTURES):
            image = cv2.imread(str(path), cv2.IMREAD_COLOR)
            assert image is not None
            regions = backend.segment(
                FramePacket(frame_id, monotonic_ns(), image)
            )
            assert regions, path.name
            for region in regions:
                assert region.mask.shape == image.shape[:2]
                assert region.mask.dtype == np.bool_
                assert region.mask.any()
                assert region.mask_confidence is not None
                detected.add(region.class_name)

    assert len(_FIXTURES) == 5
    assert {"upper-clothes", "pants", "dress"} <= detected


@pytest.mark.skipif(
    not (_CHECKPOINT.is_file() and _OPENVINO.is_file() and _HAS_TORCH and _HAS_OPENVINO),
    reason="ignored verified checkpoint/OpenVINO IR/runtime is not present",
)
def test_openvino_masks_match_pytorch_on_fixed_fixture_set() -> None:
    with (
        SCHPSegmenter(SCHPSegmenterConfig(runtime="pytorch")) as pytorch_backend,
        SCHPSegmenter(SCHPSegmenterConfig(runtime="openvino")) as openvino_backend,
    ):
        for frame_id, path in enumerate(_FIXTURES):
            image = cv2.imread(str(path), cv2.IMREAD_COLOR)
            packet = FramePacket(frame_id, monotonic_ns(), image)
            pytorch_regions = {
                region.class_name: region.mask
                for region in pytorch_backend.segment(packet)
            }
            openvino_regions = {
                region.class_name: region.mask
                for region in openvino_backend.segment(packet)
            }
            assert pytorch_regions.keys() == openvino_regions.keys()
            for name, reference in pytorch_regions.items():
                candidate = openvino_regions[name]
                intersection = int(np.logical_and(reference, candidate).sum())
                union = int(np.logical_or(reference, candidate).sum())
                assert intersection / union >= 0.999, (path.name, name)
