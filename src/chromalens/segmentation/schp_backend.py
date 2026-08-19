"""SCHP-ATR (Self-Correction for Human Parsing) segmentation backend.

This backend provides true multi-class garment segmentation (upper-clothes, pants, skirt).
Requires `torch` and `torchvision`.
"""

from __future__ import annotations

import logging
from pathlib import Path

import cv2
import numpy as np

from chromalens.contracts import FramePacket, GarmentRegion
from chromalens.segmentation.base import Segmenter, SegmenterUnavailableError

_logger = logging.getLogger(__name__)

# Lazy imports
_torch = None
_transforms = None
_init_model = None

# ATR Dataset Config
_ATR_NUM_CLASSES = 18
_INPUT_SIZE = (256, 256)
_CLASS_NAMES = {
    4: "upper-clothes",
    5: "skirt",
    6: "pants",
    7: "dress",
}


def _ensure_dependencies() -> None:
    global _torch, _transforms, _init_model
    if _torch is not None:
        return

    try:
        import torch
        import torchvision.transforms as transforms
        from chromalens.segmentation.schp_network import init_model
        
        _torch = torch
        _transforms = transforms
        _init_model = init_model
    except ImportError as e:
        raise SegmenterUnavailableError(
            "SCHP backend requires torch and torchvision. "
            "Install via: pip install torch torchvision"
        ) from e


class SCHPSegmenter(Segmenter):
    """SCHP-ATR semantic segmentation backend."""

    def __init__(self, model_path: str | Path | None = None) -> None:
        _ensure_dependencies()
        
        if model_path is None:
            # Default to models/schp_atr.pth in the repository root
            root_dir = Path(__file__).resolve().parent.parent.parent.parent
            model_path = root_dir / "models" / "schp_atr.pth"
            
        self._model_path = Path(model_path)
        self._model = None
        self._device = _torch.device("cuda" if _torch.cuda.is_available() else "cpu")
        self._transform = _transforms.Compose([
            _transforms.ToTensor(),
            _transforms.Normalize(mean=[0.406, 0.456, 0.485], std=[0.225, 0.224, 0.229])
        ])
        
    def _load_model(self) -> None:
        if self._model is not None:
            return
            
        if not self._model_path.exists():
            raise SegmenterUnavailableError(
                f"Model weights not found at {self._model_path}. "
                "Please download schp_atr.pth as instructed in models/README.md."
            )
            
        _logger.info("Loading SCHP-ATR model to %s...", self._device)
        self._model = _init_model('resnet101', num_classes=_ATR_NUM_CLASSES, pretrained=None)
        
        # Load state dict
        checkpoint = _torch.load(self._model_path, map_location="cpu")
        state_dict = checkpoint.get('state_dict', checkpoint)
        
        # Strip 'module.' if it was saved with DataParallel
        from collections import OrderedDict
        new_state_dict = OrderedDict()
        for k, v in state_dict.items():
            name = k[7:] if k.startswith('module.') else k
            new_state_dict[name] = v
            
        self._model.load_state_dict(new_state_dict, strict=False)
        self._model.to(self._device)
        self._model.eval()
        _logger.info("SCHP-ATR loaded successfully.")

    def __enter__(self) -> "SCHPSegmenter":
        self._load_model()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        if self._model is not None:
            del self._model
            self._model = None
            if _torch.cuda.is_available():
                _torch.cuda.empty_cache()

    @property
    def backend_name(self) -> str:
        return "schp-atr"

    @property
    def device_info(self) -> str:
        return f"schp/{self._device.type}"

    def segment(self, packet: FramePacket) -> tuple[GarmentRegion, ...]:
        if self._model is None:
            self._load_model()
            
        h, w = packet.original_bgr.shape[:2]
        
        # 1. Preprocess
        # OpenCV reads in BGR, SCHP expects RGB
        rgb_image = cv2.cvtColor(packet.original_bgr, cv2.COLOR_BGR2RGB)
        resized_rgb = cv2.resize(rgb_image, _INPUT_SIZE, interpolation=cv2.INTER_LINEAR)
        
        # 2. To Tensor
        input_tensor = self._transform(resized_rgb).unsqueeze(0).to(self._device)
        
        # 3. Inference
        with _torch.no_grad():
            outputs = self._model(input_tensor)
            
            # SCHP CE2P output structure: outputs[0][-1] contains the final logits
            # Outputs can be nested depending on the exact model returned by AugmentCE2P
            if isinstance(outputs, tuple) or isinstance(outputs, list):
                # Typically outputs = ( [feature_map, ...], logits, ... ) 
                # Let's extract the main logits. The upstream repo uses output[0][-1][0]
                logits = outputs[0][-1][0].unsqueeze(0)
            else:
                logits = outputs
                
            # Upsample to input size
            upsample = _torch.nn.Upsample(size=_INPUT_SIZE, mode='bilinear', align_corners=True)
            upsample_output = upsample(logits)
            
            # Get argmax classes
            parsing_result = _torch.argmax(upsample_output.squeeze(), dim=0).cpu().numpy().astype(np.uint8)
            
        # 4. Post-process to GarmentRegion
        # Resize parsing map back to original frame size using nearest neighbor
        parsing_result_original_size = cv2.resize(
            parsing_result, (w, h), interpolation=cv2.INTER_NEAREST
        )
        
        regions = []
        for class_id, class_name in _CLASS_NAMES.items():
            mask = (parsing_result_original_size == class_id)
            if mask.any():
                regions.append(GarmentRegion(
                    track_id=None,
                    class_name=class_name,
                    mask=mask,
                    mask_confidence=1.0  # SCHP argmax doesn't retain conf directly here
                ))
                
        return tuple(regions)
