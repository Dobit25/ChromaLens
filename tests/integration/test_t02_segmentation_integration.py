"""Real-runtime T02 integration tests using five licensed person scenes.

The committed fixtures make this suite independent of cameras, network access,
and separately downloaded model weights. The module skips only in the base
dependency job; the locked MediaPipe CI job imports MediaPipe first and must
execute every test here.
"""

from __future__ import annotations

import time
from pathlib import Path

import cv2
import numpy as np
import pytest

from chromalens.contracts import FramePacket

pytest.importorskip(
    "mediapipe",
    reason=(
        "mediapipe not installed; install the committed "
        "segment-mediapipe lock"
    ),
)

from chromalens.segmentation.debug import draw_mask_overlay  # noqa: E402
from chromalens.segmentation.mediapipe_backend import (  # noqa: E402
    MediaPipeSegmenter,
)

SAMPLE_DIR = Path(__file__).parents[1] / "samples" / "t02"
SAMPLE_NAMES = (
    "astronaut.png",
    "cc0_woman.jpg",
    "loc_lincoln.jpg",
    "loc_man.jpg",
    "nasa_shepard.jpg",
)


def _load_packet(sample_name: str, frame_id: int) -> FramePacket:
    frame = cv2.imread(str(SAMPLE_DIR / sample_name), cv2.IMREAD_COLOR)
    assert frame is not None, f"Could not read committed fixture: {sample_name}"
    return FramePacket(
        frame_id=frame_id,
        timestamp_ns=time.monotonic_ns(),
        original_bgr=frame,
    )


@pytest.fixture(scope="module")
def segmenter() -> MediaPipeSegmenter:
    with MediaPipeSegmenter() as backend:
        yield backend


@pytest.mark.parametrize("sample_name", SAMPLE_NAMES)
def test_real_backend_produces_visible_aligned_mask_on_five_scenes(
    segmenter: MediaPipeSegmenter,
    sample_name: str,
    request: pytest.FixtureRequest,
    tmp_path: Path,
) -> None:
    """Exercise actual inference, mask cleanup, and rendering per fixture."""
    frame_id = SAMPLE_NAMES.index(sample_name)
    packet = _load_packet(sample_name, frame_id)
    original_copy = packet.original_bgr.copy()

    regions = segmenter.segment(packet)

    assert len(regions) == 1, f"{sample_name}: expected one torso region"
    region = regions[0]
    assert region.class_name == "upper-clothes"
    assert region.mask.shape == packet.original_bgr.shape[:2]
    assert region.mask.dtype == np.bool_
    coverage = float(region.mask.mean())
    assert 0.005 < coverage < 0.70, (
        f"{sample_name}: implausible foreground coverage {coverage:.4f}"
    )
    assert region.mask_confidence is not None
    assert 0.0 <= region.mask_confidence <= 1.0

    overlay = draw_mask_overlay(
        packet.original_bgr,
        regions,
        backend_info=segmenter.device_info,
    )
    assert overlay.shape == packet.original_bgr.shape
    assert overlay.dtype == np.uint8
    assert np.any(overlay[region.mask] != packet.original_bgr[region.mask])
    np.testing.assert_array_equal(packet.original_bgr, original_copy)

    # Retained only in pytest's temporary workspace. The evidence script is
    # the explicit path for producing reviewable artifacts outside tests.
    assert cv2.imwrite(str(tmp_path / f"overlay-{request.node.callspec.id}.jpg"), overlay)


def test_backend_and_device_are_exposed(
    segmenter: MediaPipeSegmenter,
) -> None:
    assert segmenter.backend_name == "mediapipe-selfie-torso"
    assert segmenter.device_info == "mediapipe-selfie-torso/cpu"


def test_blank_frame_does_not_fabricate_large_garment_mask(
    segmenter: MediaPipeSegmenter,
) -> None:
    packet = FramePacket(
        frame_id=99,
        timestamp_ns=time.monotonic_ns(),
        original_bgr=np.full((480, 640, 3), 255, dtype=np.uint8),
    )

    regions = segmenter.segment(packet)
    coverage = sum(float(region.mask.mean()) for region in regions)

    assert coverage < 0.30


def test_close_is_idempotent_and_segment_after_close_fails() -> None:
    backend = MediaPipeSegmenter()
    backend.close()
    backend.close()
    packet = FramePacket(
        frame_id=100,
        timestamp_ns=time.monotonic_ns(),
        original_bgr=np.zeros((32, 32, 3), dtype=np.uint8),
    )

    with pytest.raises(RuntimeError, match="close"):
        backend.segment(packet)
