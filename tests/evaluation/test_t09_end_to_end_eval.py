from __future__ import annotations

import numpy as np

from scripts import t09_end_to_end_eval as evaluator


def test_frozen_registry_has_exact_ten_end_to_end_cases() -> None:
    cases = evaluator.load_cases(evaluator.WORKSTREAM)

    assert len(cases) == 10
    assert len({case["case_id"] for case in cases}) == 10


def test_switch_count_observes_only_consecutive_selected_values() -> None:
    assert evaluator.target_switch_count([]) == 0
    assert evaluator.target_switch_count([(1, 2, 3)]) == 0
    assert evaluator.target_switch_count(
        [(1, 2, 3), (1, 2, 3), (3, 2, 1), (3, 2, 1)]
    ) == 1


def test_containment_counts_changed_pixels_not_channel_bytes() -> None:
    source = np.zeros((2, 3, 3), dtype=np.uint8)
    assistive = source.copy()
    assistive[0, 0] = (1, 2, 3)
    assistive[1, 2] = (4, 0, 0)
    mask = np.zeros((2, 3), dtype=np.bool_)
    mask[0, 0] = True

    assert evaluator.changed_pixels_outside(source, assistive, mask) == 1


def test_controlled_frame_exercises_two_colors_only_inside_torso() -> None:
    frame = evaluator.controlled_frame(multicolor=True)
    segmenter = evaluator.ControlledTorsoSegmenter()
    packet = evaluator.FramePacket(0, 1, frame)
    region = segmenter.segment(packet)[0]

    assert frame.shape == (evaluator.HEIGHT, evaluator.WIDTH, 3)
    assert region.mask.dtype == np.bool_
    assert len({tuple(pixel) for pixel in frame[region.mask]}) == 2
