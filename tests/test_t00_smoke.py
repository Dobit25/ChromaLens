"""Hardware-, network-, and model-independent T00 smoke tests."""

from __future__ import annotations

import subprocess
import sys
from unittest.mock import patch

import cv2
import numpy as np
import pytest

from chromalens.app import main
from chromalens.config import AppConfig
from chromalens.contracts import FramePacket
from chromalens.segmentation.mediapipe_backend import (
    MediaPipeBackendUnavailableError,
    MediaPipeSegmenter,
)
from chromalens.segmentation.schp_backend import SCHPSegmenter


def test_module_help_exits_successfully_without_hardware() -> None:
    result = subprocess.run(
        [sys.executable, "-m", "chromalens", "--help"],
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0, result.stderr
    normalized_output = " ".join(result.stdout.split())
    assert "Camera and video execution are introduced in T01" in normalized_output


def test_base_opencv_contrib_dependency_is_available() -> None:
    assert hasattr(cv2, "xphoto")


def test_config_rejects_out_of_range_severity() -> None:
    with pytest.raises(ValueError, match=r"within \[0, 1\]"):
        AppConfig(severity=1.01)


def test_placeholder_backend_fails_fast_without_fabricating_output() -> None:
    packet = FramePacket(
        frame_id=0,
        timestamp_ns=0,
        original_bgr=np.zeros((2, 2, 3), dtype=np.uint8),
    )

    with pytest.raises(MediaPipeBackendUnavailableError, match="not implemented in T00"):
        MediaPipeSegmenter().segment(packet)


def test_default_cli_does_not_call_placeholder_backends() -> None:
    with (
        patch.object(MediaPipeSegmenter, "segment") as mediapipe_segment,
        patch.object(SCHPSegmenter, "segment") as schp_segment,
    ):
        assert main([]) == 0

    mediapipe_segment.assert_not_called()
    schp_segment.assert_not_called()
