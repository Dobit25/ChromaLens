"""Hardware/model-independent contracts for the T10 SCHP backend."""

from __future__ import annotations

import importlib.util
from pathlib import Path

import numpy as np
import pytest

from chromalens.app import build_parser
from chromalens.segmentation.schp_backend import (
    SCHPBackendUnavailableError,
    SCHPSegmenter,
    SCHPSegmenterConfig,
    _prepare_input,
    _remove_small_components,
)


def test_cli_promotes_schp_but_preserves_explicit_mediapipe_fallback() -> None:
    parser = build_parser()
    defaults = parser.parse_args(["--video", "sample.avi"])
    fallback = parser.parse_args(
        ["--video", "sample.avi", "--backend", "mediapipe-selfie-torso"]
    )

    assert defaults.backend == "schp-atr"
    assert defaults.schp_runtime == "auto"
    assert fallback.backend == "mediapipe-selfie-torso"


@pytest.mark.parametrize(
    ("kwargs", "message"),
    [
        ({"input_size": 100}, "divisible by 32"),
        ({"min_component_area_ratio": 1.0}, r"within \[0, 1\)"),
        ({"torch_threads": 0}, "positive"),
    ],
)
def test_config_rejects_invalid_values(
    kwargs: dict[str, object],
    message: str,
) -> None:
    with pytest.raises(ValueError, match=message):
        SCHPSegmenterConfig(**kwargs)  # type: ignore[arg-type]


def test_missing_checkpoint_fails_before_optional_runtime_import(tmp_path: Path) -> None:
    with pytest.raises(SCHPBackendUnavailableError, match="checkpoint is missing"):
        SCHPSegmenter(
            SCHPSegmenterConfig(
                checkpoint_path=tmp_path / "missing.pth",
                runtime="pytorch",
            )
        )


def test_preprocessing_is_bgr_float_nchw_and_does_not_mutate_source() -> None:
    frame = np.zeros((40, 80, 3), dtype=np.uint8)
    frame[10:30, 20:60] = (12, 34, 56)
    original = frame.copy()

    model_input, inverse = _prepare_input(frame, input_size=64)

    assert model_input.shape == (1, 3, 64, 64)
    assert model_input.dtype == np.float32
    assert inverse.shape == (2, 3)
    np.testing.assert_array_equal(frame, original)
    center = model_input[0, :, 32, 32]
    expected = (np.asarray((12, 34, 56)) / 255.0 - (0.406, 0.456, 0.485)) / (
        0.225,
        0.224,
        0.229,
    )
    np.testing.assert_allclose(center, expected, atol=1e-5)


def test_small_component_cleanup_preserves_only_adequate_regions() -> None:
    mask = np.zeros((20, 20), dtype=np.bool_)
    mask[1:3, 1:3] = True
    mask[8:16, 8:16] = True

    cleaned = _remove_small_components(mask, min_area=8)

    assert cleaned.dtype == np.bool_
    assert not np.any(cleaned[1:3, 1:3])
    assert np.all(cleaned[8:16, 8:16])


@pytest.mark.skipif(
    importlib.util.find_spec("torch") is None,
    reason="locked segment-schp runtime is not installed",
)
def test_portable_model_graph_runs_without_custom_cpp_extension() -> None:
    import torch

    from chromalens.segmentation.schp_model import SCHPResNet101

    model = SCHPResNet101(num_classes=18).eval()
    with torch.inference_mode():
        output = model(torch.zeros((1, 3, 64, 64), dtype=torch.float32))

    assert tuple(output.shape) == (1, 18, 64, 64)
    assert bool(torch.isfinite(output).all())
