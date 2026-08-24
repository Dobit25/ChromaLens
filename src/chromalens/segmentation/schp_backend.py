"""Real SCHP-ATR semantic garment segmentation backend.

Weights are intentionally external to Git. The default path and exact object
identity are documented in ``models/README.md``. PyTorch and the model graph
are imported only when this backend is constructed, so CLI help and the
MediaPipe fallback remain independent of the optional SCHP runtime.
"""

from __future__ import annotations

import hashlib
import json
from collections import OrderedDict
from dataclasses import dataclass
from pathlib import Path
from types import ModuleType
from typing import Any, Literal

import cv2
import numpy as np
from numpy.typing import NDArray

from chromalens.contracts import FramePacket, GarmentRegion
from chromalens.segmentation.base import Segmenter, SegmenterUnavailableError

SCHP_ATR_CHECKPOINT_SIZE = 267_445_237
SCHP_ATR_CHECKPOINT_SHA256 = (
    "e9d7c91ce3b4e7133df56b599fc817b533e3439c5e8d282a59126d2fda339a2a"
)
SCHP_ATR_CLASS_NAMES = {
    4: "upper-clothes",
    5: "skirt",
    6: "pants",
    7: "dress",
}
_ATR_MEAN_BGR = np.asarray((0.406, 0.456, 0.485), dtype=np.float32)
_ATR_STD_BGR = np.asarray((0.225, 0.224, 0.229), dtype=np.float32)


class SCHPBackendUnavailableError(SegmenterUnavailableError):
    """Raised when verified SCHP inference cannot be initialized."""


@dataclass(frozen=True, slots=True)
class SCHPSegmenterConfig:
    """Immutable configuration for verified ATR inference."""

    checkpoint_path: Path = Path("models/schp/exp-schp-201908301523-atr.pth")
    openvino_model_path: Path = Path("models/schp/openvino/schp-atr-512.xml")
    runtime: Literal["auto", "openvino", "pytorch"] = "auto"
    input_size: int = 512
    min_component_area_ratio: float = 0.0005
    verify_checkpoint: bool = True
    torch_threads: int | None = None

    def __post_init__(self) -> None:
        if self.input_size < 64 or self.input_size % 32 != 0:
            raise ValueError("input_size must be at least 64 and divisible by 32")
        if self.runtime not in {"auto", "openvino", "pytorch"}:
            raise ValueError("runtime must be auto, openvino, or pytorch")
        if not 0.0 <= self.min_component_area_ratio < 1.0:
            raise ValueError("min_component_area_ratio must be within [0, 1)")
        if self.torch_threads is not None and self.torch_threads <= 0:
            raise ValueError("torch_threads must be positive when provided")


class SCHPSegmenter(Segmenter):
    """Strict, CPU-only SCHP-ATR semantic garment parser.

    The backend returns one region per detected ATR garment class among
    upper-clothes, skirt, pants, and dress. ``mask_confidence`` is the mean
    winning softmax score inside the class mask; it is a model-output heuristic,
    not a calibrated probability of segmentation correctness.
    """

    def __init__(self, config: SCHPSegmenterConfig | None = None) -> None:
        self._config = config or SCHPSegmenterConfig()
        self._closed = False
        checkpoint_path = self._config.checkpoint_path.resolve()
        _validate_checkpoint(
            checkpoint_path,
            verify_hash=self._config.verify_checkpoint,
        )
        self._torch: ModuleType | None = None
        self._model: Any = None
        self._compiled_model: Any = None
        openvino_path = self._config.openvino_model_path.resolve()
        use_openvino = self._config.runtime == "openvino" or (
            self._config.runtime == "auto" and openvino_path.is_file()
        )
        if use_openvino:
            self._initialise_openvino(openvino_path, checkpoint_path)
            self._active_runtime = "openvino"
        else:
            self._initialise_pytorch(checkpoint_path)
            self._active_runtime = "pytorch"

    def _initialise_pytorch(self, checkpoint_path: Path) -> None:
        self._torch = _import_torch()
        if self._config.torch_threads is not None:
            self._torch.set_num_threads(self._config.torch_threads)
        try:
            from chromalens.segmentation.schp_model import SCHPResNet101

            model = SCHPResNet101(num_classes=18)
            checkpoint = self._torch.load(
                checkpoint_path,
                map_location="cpu",
                weights_only=True,
            )
            if not isinstance(checkpoint, dict) or "state_dict" not in checkpoint:
                raise ValueError("checkpoint does not contain a state_dict mapping")
            raw_state = checkpoint["state_dict"]
            if not isinstance(raw_state, dict):
                raise ValueError("checkpoint state_dict is not a mapping")
            state = OrderedDict(
                (
                    key[7:] if key.startswith("module.") else key,
                    value,
                )
                for key, value in raw_state.items()
            )
            model.load_state_dict(state, strict=True)
            model.eval()
        except Exception as exc:
            raise SCHPBackendUnavailableError(
                "The verified SCHP-ATR checkpoint could not be loaded strictly. "
                "Keep MediaPipe available with --backend mediapipe-selfie-torso "
                "and review models/README.md."
            ) from exc
        self._model = model

    def _initialise_openvino(
        self,
        model_path: Path,
        checkpoint_path: Path,
    ) -> None:
        if not model_path.is_file():
            raise SCHPBackendUnavailableError(
                f"OpenVINO SCHP model is missing at {model_path}. Run the T10 "
                "export command or use --schp-runtime pytorch."
            )
        _validate_openvino_manifest(
            model_path,
            checkpoint_path=checkpoint_path,
            input_size=self._config.input_size,
        )
        try:
            import openvino as openvino_module

            core = openvino_module.Core()
            self._compiled_model = core.compile_model(model_path, "CPU")
            self._openvino_device_name = str(
                core.get_property("CPU", "FULL_DEVICE_NAME")
            )
        except (ImportError, OSError, RuntimeError) as exc:
            raise SCHPBackendUnavailableError(
                "OpenVINO could not compile the verified SCHP IR on CPU. "
                "Use --schp-runtime pytorch or --backend mediapipe-selfie-torso."
            ) from exc

    @property
    def backend_name(self) -> str:
        return "schp-atr"

    @property
    def device_info(self) -> str:
        if self._active_runtime == "openvino":
            return f"schp-atr/openvino/CPU ({self._openvino_device_name})"
        return "schp-atr/pytorch/cpu"

    def segment(self, packet: FramePacket) -> tuple[GarmentRegion, ...]:
        if self._closed:
            raise RuntimeError("SCHPSegmenter.segment() called after close()")

        frame = packet.original_bgr
        frame_height, frame_width = frame.shape[:2]
        model_input, inverse_transform = _prepare_input(
            frame,
            input_size=self._config.input_size,
        )
        try:
            if self._active_runtime == "openvino":
                raw_logits = self._compiled_model([model_input])[
                    self._compiled_model.output(0)
                ]
            else:
                assert self._torch is not None
                with self._torch.inference_mode():
                    tensor = self._torch.from_numpy(model_input)
                    raw_logits = self._model(tensor).detach().cpu().numpy()
            logits_chw = raw_logits[0]
            if logits_chw.shape[1:] != (
                self._config.input_size,
                self._config.input_size,
            ):
                raise ValueError(
                    f"unexpected SCHP logits shape: {raw_logits.shape}"
                )
            logits_hwc = logits_chw.transpose(1, 2, 0).astype(
                np.float32,
                copy=False,
            )
        except Exception as exc:
            raise RuntimeError(
                f"SCHP-ATR inference failed for frame_id={packet.frame_id}"
            ) from exc

        restored_logits = _restore_logits(
            logits_hwc,
            inverse_transform=inverse_transform,
            output_width=frame_width,
            output_height=frame_height,
        )
        labels = np.argmax(restored_logits, axis=2).astype(np.uint8)
        winning_scores = _winning_softmax_scores(restored_logits)
        min_area = round(
            frame_height * frame_width * self._config.min_component_area_ratio
        )

        regions: list[GarmentRegion] = []
        for class_id, class_name in SCHP_ATR_CLASS_NAMES.items():
            mask = _remove_small_components(labels == class_id, min_area=min_area)
            if not np.any(mask):
                continue
            confidence = float(np.mean(winning_scores[mask]))
            regions.append(
                GarmentRegion(
                    track_id=None,
                    class_name=class_name,
                    mask=np.asarray(mask, dtype=np.bool_),
                    mask_confidence=max(0.0, min(1.0, confidence)),
                )
            )
        return tuple(regions)

    def close(self) -> None:
        if not self._closed:
            self._model = None
            self._compiled_model = None
            self._closed = True


def _import_torch() -> ModuleType:
    try:
        import torch
    except (ImportError, OSError) as exc:
        raise SCHPBackendUnavailableError(
            "SCHP-ATR requires the locked segment-schp dependency group. "
            "Install requirements/segment-schp-py310-win64.lock."
        ) from exc
    return torch


def _validate_checkpoint(path: Path, *, verify_hash: bool) -> None:
    if not path.is_file():
        raise SCHPBackendUnavailableError(
            f"SCHP-ATR checkpoint is missing at {path}. "
            "Follow models/README.md or select --backend mediapipe-selfie-torso."
        )
    size = path.stat().st_size
    if size != SCHP_ATR_CHECKPOINT_SIZE:
        raise SCHPBackendUnavailableError(
            f"SCHP-ATR checkpoint has {size} bytes; expected "
            f"{SCHP_ATR_CHECKPOINT_SIZE}. Refusing partial or different weights."
        )
    if verify_hash:
        digest = _sha256(path)
        if digest != SCHP_ATR_CHECKPOINT_SHA256:
            raise SCHPBackendUnavailableError(
                "SCHP-ATR checkpoint SHA-256 does not match the frozen object."
            )


def _prepare_input(
    frame_bgr: NDArray[np.uint8],
    *,
    input_size: int,
) -> tuple[NDArray[np.float32], NDArray[np.float64]]:
    height, width = frame_bgr.shape[:2]
    center = np.asarray(((width - 1) * 0.5, (height - 1) * 0.5), dtype=np.float32)
    side = float(max(width - 1, height - 1))
    scale = np.asarray((side, side), dtype=np.float32)
    forward = _get_affine_transform(center, scale, input_size, inverse=False)
    inverse = _get_affine_transform(center, scale, input_size, inverse=True)
    warped = cv2.warpAffine(
        frame_bgr,
        forward,
        (input_size, input_size),
        flags=cv2.INTER_LINEAR,
        borderMode=cv2.BORDER_CONSTANT,
        borderValue=(0, 0, 0),
    )
    normalized = warped.astype(np.float32) / 255.0
    normalized = (normalized - _ATR_MEAN_BGR) / _ATR_STD_BGR
    chw = np.ascontiguousarray(normalized.transpose(2, 0, 1))
    return chw[np.newaxis, ...], inverse


def _validate_openvino_manifest(
    model_path: Path,
    *,
    checkpoint_path: Path,
    input_size: int,
) -> None:
    manifest_path = model_path.with_suffix(".manifest.json")
    binary_path = model_path.with_suffix(".bin")
    if not manifest_path.is_file() or not binary_path.is_file():
        raise SCHPBackendUnavailableError(
            "OpenVINO SCHP IR requires its .xml, .bin, and .manifest.json files."
        )
    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        if manifest["schema_version"] != "1.0.0":
            raise ValueError("unsupported manifest schema")
        if manifest["input_size"] != input_size:
            raise ValueError("manifest input size differs from runtime config")
        if manifest["source_checkpoint"]["sha256"] != SCHP_ATR_CHECKPOINT_SHA256:
            raise ValueError("manifest checkpoint identity differs")
        if manifest["source_checkpoint"]["bytes"] != checkpoint_path.stat().st_size:
            raise ValueError("manifest checkpoint size differs")
        for artifact_path in (model_path, binary_path):
            record = manifest["artifacts"][artifact_path.suffix[1:]]
            if record["bytes"] != artifact_path.stat().st_size:
                raise ValueError(f"{artifact_path.name} size differs")
            if record["sha256"] != _sha256(artifact_path):
                raise ValueError(f"{artifact_path.name} checksum differs")
    except (KeyError, OSError, TypeError, ValueError, json.JSONDecodeError) as exc:
        raise SCHPBackendUnavailableError(
            "OpenVINO SCHP artifact manifest validation failed; regenerate the "
            "IR with scripts/t10_export_schp_openvino.py."
        ) from exc


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _get_affine_transform(
    center: NDArray[np.float32],
    scale: NDArray[np.float32],
    input_size: int,
    *,
    inverse: bool,
) -> NDArray[np.float64]:
    source = np.zeros((3, 2), dtype=np.float32)
    target = np.zeros((3, 2), dtype=np.float32)
    source[0] = center
    source[1] = center + np.asarray((0.0, -0.5 * scale[0]), dtype=np.float32)
    source[2] = _third_point(source[0], source[1])
    half = (input_size - 1) * 0.5
    target[0] = (half, half)
    target[1] = (half, 0.0)
    target[2] = _third_point(target[0], target[1])
    if inverse:
        return cv2.getAffineTransform(target, source)
    return cv2.getAffineTransform(source, target)


def _third_point(first: NDArray[np.float32], second: NDArray[np.float32]) -> NDArray[np.float32]:
    direction = first - second
    return second + np.asarray((-direction[1], direction[0]), dtype=np.float32)


def _restore_logits(
    logits: NDArray[np.float32],
    *,
    inverse_transform: NDArray[np.float64],
    output_width: int,
    output_height: int,
) -> NDArray[np.float32]:
    # OpenCV applies the same affine transform independently to every channel.
    # One multi-channel call is exactly equivalent to 18 scalar calls and is
    # materially faster on high-resolution webcam frames.
    return cv2.warpAffine(
        logits,
        inverse_transform,
        (output_width, output_height),
        flags=cv2.INTER_LINEAR,
        borderMode=cv2.BORDER_CONSTANT,
        borderValue=0,
    ).astype(np.float32, copy=False)


def _winning_softmax_scores(logits: NDArray[np.float32]) -> NDArray[np.float32]:
    # Labels have already been materialized by the caller, so this internal
    # logits buffer can be reused in place. Avoiding three additional HxWx18
    # arrays materially lowers peak memory on high-resolution frames.
    maxima = np.max(logits, axis=2, keepdims=True)
    np.subtract(logits, maxima, out=logits)
    np.exp(logits, out=logits)
    totals = np.sum(logits, axis=2, keepdims=True)
    np.divide(logits, totals, out=logits)
    return np.max(logits, axis=2).astype(np.float32, copy=False)


def _remove_small_components(
    mask: NDArray[np.bool_],
    *,
    min_area: int,
) -> NDArray[np.bool_]:
    binary = np.asarray(mask, dtype=np.uint8)
    if min_area <= 1 or not np.any(binary):
        return binary.astype(np.bool_)
    count, labels, stats, _centroids = cv2.connectedComponentsWithStats(
        binary,
        connectivity=8,
    )
    retained = np.zeros(binary.shape, dtype=np.bool_)
    for component in range(1, count):
        if int(stats[component, cv2.CC_STAT_AREA]) >= min_area:
            retained |= labels == component
    return retained
