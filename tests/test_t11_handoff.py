"""Hardware-independent contracts for the T11 competition handoff."""

from __future__ import annotations

import json
from pathlib import Path

import cv2
import numpy as np

from scripts.t11_prepare_handoff import (
    DEFAULT_FIXTURE,
    FIXTURE_SHA256,
    build_engineered_demo_frame,
    sha256_file,
    write_fallback_video,
)

ROOT = Path(__file__).resolve().parents[1]
SUBMISSION = ROOT / "docs/submission.json"


def load_submission() -> dict[str, object]:
    return json.loads(SUBMISSION.read_text(encoding="utf-8"))


def test_submission_name_description_and_public_limits_are_locked() -> None:
    submission = load_submission()
    name_words = str(submission["project_name"]).split()
    description_words = str(submission["description"]).split()
    requirements = submission["official_requirements"]

    assert len(name_words) == submission["project_name_word_count"]
    assert len(name_words) <= requirements["project_name_max_words"]
    assert len(description_words) <= submission["description_word_limit"]
    assert len(description_words) <= requirements["description_max_words"]
    assert requirements["live_form_status"].startswith("OWNER_MUST_VERIFY")


def test_two_minute_shot_list_is_contiguous_and_exact() -> None:
    video = load_submission()["video"]
    shots = video["shots"]
    assert shots[0]["start_second"] == 0
    assert shots[-1]["end_second"] == video["target_duration_seconds"] == 120
    assert all(
        current["end_second"] == following["start_second"]
        for current, following in zip(shots, shots[1:])
    )
    assert all(shot["end_second"] > shot["start_second"] for shot in shots)


def test_every_allowed_claim_points_to_tracked_evidence() -> None:
    claims = load_submission()["claims"]
    assert claims
    for claim in claims:
        assert claim["claim"].strip()
        assert claim["evidence"]
        for relative_path in claim["evidence"]:
            assert (ROOT / relative_path).is_file(), relative_path


def test_public_fallback_fixture_matches_rights_record() -> None:
    fixture = ROOT / DEFAULT_FIXTURE
    assert fixture.is_file()
    assert sha256_file(fixture) == FIXTURE_SHA256
    rights_record = (ROOT / "tests/samples/t02/README.md").read_text(
        encoding="utf-8"
    )
    assert FIXTURE_SHA256 in rights_record
    assert "public-domain nasa image" in rights_record.casefold()


def test_fallback_video_generation_needs_no_camera_network_or_model(
    tmp_path: Path,
) -> None:
    frame = np.zeros((40, 60, 3), dtype=np.uint8)
    frame[8:32, 12:48] = (10, 80, 220)
    output = tmp_path / "fallback.avi"

    frame_count, resolution = write_fallback_video(
        output, frame, duration_seconds=1.0, fps=6.0
    )

    assert frame_count == 6
    assert resolution == (640, 480)
    capture = cv2.VideoCapture(str(output))
    try:
        ok, decoded = capture.read()
    finally:
        capture.release()
    assert ok
    assert decoded.shape == (480, 640, 3)


def test_engineered_fallback_pair_uses_explicit_bgr_boundaries() -> None:
    source = np.zeros((480, 640, 3), dtype=np.uint8)
    demo = build_engineered_demo_frame(source)

    assert tuple(demo[200, 200]) == (11, 48, 164)
    assert tuple(demo[200, 400]) == (9, 145, 90)
