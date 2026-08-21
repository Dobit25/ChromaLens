"""SCHP-ATR (Self-Correction for Human Parsing, ATR dataset) backend."""

from __future__ import annotations

import sys
import cv2
import numpy as np
from pathlib import Path

from chromalens.contracts import FramePacket, GarmentRegion
from chromalens.segmentation.base import Segmenter, SegmenterUnavailableError


class SCHPBackendUnavailableError(SegmenterUnavailableError):
    pass


class SCHPSegmenter(Segmenter):
    def __init__(self):
        try:
            import torch
            import torchvision.transforms as transforms
        except ImportError:
            raise SCHPBackendUnavailableError("PyTorch is not installed. Install segment-schp extra.")

        self.device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')

        self.root_dir = Path(__file__).resolve().parents[3]
        schp_repo_path = self.root_dir / "scratch" / "schp_repo"
        if not schp_repo_path.exists():
            raise SCHPBackendUnavailableError(f"SCHP repository not found at {schp_repo_path}")

        if str(schp_repo_path) not in sys.path:
            sys.path.insert(0, str(schp_repo_path))

        try:
            import networks
            from utils.transforms import transform_logits
        except ImportError as e:
            raise SCHPBackendUnavailableError(f"Failed to import SCHP modules: {e}")

        model_path = self.root_dir / "models" / "schp_atr.pth"
        if not model_path.exists():
            raise SCHPBackendUnavailableError(f"SCHP model weights not found at {model_path}")

        self.num_classes = 18
        self.input_size = [512, 512]

        # Load model architecture
        self.model = networks.init_model('resnet101', num_classes=self.num_classes, pretrained=None)

        # Load weights
        state_dict = torch.load(model_path, map_location=self.device)['state_dict']
        from collections import OrderedDict
        new_state_dict = OrderedDict()
        for k, v in state_dict.items():
            name = k[7:] if k.startswith('module.') else k
            new_state_dict[name] = v
        self.model.load_state_dict(new_state_dict)
        self.model.to(self.device)
        self.model.eval()

        self.transform = transforms.Compose([
            transforms.ToTensor(),
            transforms.Normalize(mean=[0.406, 0.456, 0.485], std=[0.225, 0.224, 0.229])
        ])

        # ATR Garment classes: 4 (upper-clothes), 5 (skirt), 6 (pants), 7 (dress)
        # We EXPLICITLY exclude 11 (face), 2 (hair), 14/15 (arms), 12/13 (legs), 0 (background)
        self.garment_classes = {4, 5, 6, 7}

    @property
    def backend_name(self) -> str:
        return "schp-atr"

    @property
    def device_info(self) -> str:
        return f"schp-atr/{self.device.type}"

    def segment(self, packet: FramePacket) -> tuple[GarmentRegion, ...]:
        import torch
        from utils.transforms import get_affine_transform

        img = packet.original_bgr
        h, w = img.shape[:2]

        # Use the exact preprocessing logic from simple_extractor_dataset.py
        # Get person center and scale (assuming full image for simplicity, as we don't have a person detector here)
        center = np.zeros((2,), dtype=np.float32)
        center[0] = (w - 1) * 0.5
        center[1] = (h - 1) * 0.5

        aspect_ratio = self.input_size[1] * 1.0 / self.input_size[0]
        box_w = w - 1
        box_h = h - 1

        if box_w > aspect_ratio * box_h:
            box_h = box_w * 1.0 / aspect_ratio
        elif box_w < aspect_ratio * box_h:
            box_w = box_h * aspect_ratio

        scale = np.array([box_w, box_h], dtype=np.float32)

        trans = get_affine_transform(center, scale, 0, self.input_size)

        img_warped = cv2.warpAffine(
            img,
            trans,
            (int(self.input_size[1]), int(self.input_size[0])),
            flags=cv2.INTER_LINEAR,
            borderMode=cv2.BORDER_CONSTANT,
            borderValue=(0, 0, 0)
        )

        img_warped = cv2.cvtColor(img_warped, cv2.COLOR_BGR2RGB)
        input_tensor = self.transform(img_warped).unsqueeze(0).to(self.device)

        with torch.no_grad():
            output = self.model(input_tensor)

            upsample = torch.nn.Upsample(size=self.input_size, mode='bilinear', align_corners=True)
            upsample_output = upsample(output[0][-1][0].unsqueeze(0))
            upsample_output = upsample_output.squeeze().permute(1, 2, 0)  # HWC

            logits_numpy = upsample_output.cpu().numpy()

            from utils.transforms import transform_logits
            logits_result = transform_logits(logits_numpy, center, scale, w, h, input_size=self.input_size)
            parsing_result = np.argmax(logits_result, axis=2)

        # Create combined garment mask
        garment_mask = np.isin(parsing_result, list(self.garment_classes))

        if not np.any(garment_mask):
            return ()

        # Optional: could split into components, but contract allows a single region for MVP
        region = GarmentRegion(
            track_id=None,
            class_name="garment",
            mask=garment_mask,
            mask_confidence=0.85  # SCHP doesn't give a simple object confidence, so use pseudo-confidence
        )

        return (region,)
