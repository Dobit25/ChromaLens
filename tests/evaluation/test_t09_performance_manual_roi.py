from __future__ import annotations

from scripts import t09_responsible_ai_manual_roi as manual


class Clock:
    def __init__(self, values: list[float]) -> None:
        self.values = iter(values)

    def __call__(self) -> float:
        return next(self.values)


def test_manual_roi_trials_store_timing_and_hash_only() -> None:
    paths = manual.verify_fixtures()
    trials = manual.run_trials(
        paths,
        selector=lambda _path: True,
        clock=Clock([value for pair in ((0.0, 1.0), (2.0, 4.0), (5.0, 8.0), (9.0, 13.0), (14.0, 19.0)) for value in pair]),
    )

    assert [trial.completion_seconds for trial in trials] == [1.0, 2.0, 3.0, 4.0, 5.0]
    assert all(len(trial.fixture_sha256) == 64 for trial in trials)
    assert all(not hasattr(trial, name) for trial in trials for name in ("roi", "image", "pixels"))


def test_cancelled_or_nonpositive_trial_fails_closed() -> None:
    path = manual.verify_fixtures()[0]

    try:
        manual.run_trials([path], selector=lambda _path: False, clock=Clock([0.0, 1.0]))
    except manual.ManualRoiError as error:
        assert "cancelled" in str(error)
    else:  # pragma: no cover
        raise AssertionError("cancelled selection must fail")
