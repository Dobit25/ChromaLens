import pytest
import numpy as np
from unittest.mock import patch, MagicMock

import sys
from pathlib import Path

# Temporarily add schp_repo to sys.path so we can mock 'networks' and 'utils'
schp_repo_path = Path(__file__).resolve().parents[3] / "scratch" / "schp_repo"
if str(schp_repo_path) not in sys.path:
    sys.path.insert(0, str(schp_repo_path))

# Only test if segment-schp extra is installed, otherwise skip
try:
    import torch
    import networks
    from utils.transforms import transform_logits
    from chromalens.segmentation.schp_backend import SCHPSegmenter, SCHPBackendUnavailableError
    HAS_SCHP = True
except ImportError as e:
    print(f"DEBUG IMPORT ERROR: {e}")
    HAS_SCHP = False


@pytest.mark.skipif(not HAS_SCHP, reason="segment-schp extra is not installed")
def test_schp_segmenter_initialization():
    # Mock network loading so we don't actually load 267MB of weights during unit tests
    with patch("networks.init_model"), patch("torch.load") as mock_load:
        mock_load.return_value = {"state_dict": {}}
        segmenter = SCHPSegmenter()

        assert segmenter.backend_name == "schp-atr"
        assert segmenter.garment_classes == {4, 5, 6, 7}


@pytest.mark.skipif(not HAS_SCHP, reason="segment-schp extra is not installed")
def test_schp_segmenter_mask_filtering():
    """Verify that ONLY garment classes are kept, and skin/hair/bg are excluded."""
    from chromalens.contracts import FramePacket

    with patch("networks.init_model"), patch("torch.load") as mock_load:
        mock_load.return_value = {"state_dict": {}}
        segmenter = SCHPSegmenter()

        # Mock the entire torch model inference and transform_logits
        with patch.object(segmenter, 'model') as mock_model, \
             patch("utils.transforms.transform_logits") as mock_transform_logits:

            # SCHP output is nested: output[0][-1][0].unsqueeze(0) needs to be 4D (N, C, H, W)
            # So output[0][-1][0] must be 3D (C, H, W)
            mock_tensor = torch.zeros(18, 512, 512)
            mock_model.return_value = [[ [mock_tensor] ]]

            # Create a mock logits output (H, W, Classes)
            # We have 18 classes. We want class 4 (upper-clothes), 11 (face), 0 (bg)
            mock_logits = np.zeros((100, 100, 18))
            mock_logits[:50, :50, 4] = 10.0   # Top-left is garment
            mock_logits[50:, :50, 11] = 10.0  # Bottom-left is face
            mock_logits[:, 50:, 0] = 10.0     # Right half is background

            mock_transform_logits.return_value = mock_logits

            packet = FramePacket(frame_id=1, timestamp_ns=0, original_bgr=np.zeros((100, 100, 3), dtype=np.uint8))

            regions = segmenter.segment(packet)
            assert len(regions) == 1

            mask = regions[0].mask
            assert mask.shape == (100, 100)

            # Top-left should be True (garment)
            assert np.all(mask[:50, :50] == True)

            # Bottom-left should be False (face)
            assert np.all(mask[50:, :50] == False)

            # Right half should be False (background)
            assert np.all(mask[:, 50:] == False)
