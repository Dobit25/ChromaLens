from __future__ import annotations

import numpy as np
import pytest

from chromalens.config import CVDProfile
from chromalens.cvd_simulation import MachadoSimulator, validate_severity


KNOWN_PATCHES = np.asarray(
    [
        [
            [255, 0, 0],
            [0, 255, 0],
            [0, 0, 255],
            [255, 255, 255],
            [0, 0, 0],
            [255, 255, 0],
        ]
    ],
    dtype=np.uint8,
)

EXPECTED_SEVERITY_ONE = {
    CVDProfile.PROTAN: np.asarray(
        [[[108, 95, 0], [254, 229, 0], [0, 88, 254], [254, 254, 254], [0, 0, 0], [254, 243, 0]]],
        dtype=np.uint8,
    ),
    CVDProfile.DEUTAN: np.asarray(
        [[[163, 144, 0], [238, 214, 58], [0, 61, 251], [254, 254, 254], [0, 0, 0], [254, 249, 49]]],
        dtype=np.uint8,
    ),
    CVDProfile.TRITAN: np.asarray(
        [[[254, 0, 14], [0, 247, 216], [0, 107, 149], [254, 254, 254], [0, 0, 0], [254, 237, 217]]],
        dtype=np.uint8,
    ),
}


@pytest.mark.parametrize("profile", list(CVDProfile))
def test_severity_zero_is_exact_identity_copy(profile: CVDProfile) -> None:
    simulator = MachadoSimulator()
    source = KNOWN_PATCHES.copy()

    result = simulator.simulate_rgb(source, profile=profile, severity=0.0)

    assert np.array_equal(result, KNOWN_PATCHES)
    assert np.array_equal(source, KNOWN_PATCHES)
    assert result is not source
    assert not np.shares_memory(result, source)


@pytest.mark.parametrize("profile", list(CVDProfile))
def test_known_rgb_patches_match_locked_daltonlens_outputs(
    profile: CVDProfile,
) -> None:
    result = MachadoSimulator().simulate_rgb(
        KNOWN_PATCHES,
        profile=profile,
        severity=1.0,
    )

    assert result.dtype == np.uint8
    assert result.shape == KNOWN_PATCHES.shape
    assert np.array_equal(result, EXPECTED_SEVERITY_ONE[profile])


def test_single_color_api_preserves_rgb_channel_order() -> None:
    result = MachadoSimulator().simulate_color(
        (255, 0, 0),
        profile=CVDProfile.DEUTAN,
        severity=1.0,
    )

    assert result == (163, 144, 0)


@pytest.mark.parametrize("severity", [-0.01, 1.01, float("nan"), float("inf"), True])
def test_invalid_severity_fails_before_simulation(severity: float) -> None:
    with pytest.raises(ValueError, match="severity"):
        validate_severity(severity)


def test_invalid_profile_and_rgb_contract_fail_clearly() -> None:
    simulator = MachadoSimulator()

    with pytest.raises(TypeError, match="CVDProfile"):
        simulator.simulate_rgb(
            KNOWN_PATCHES,
            profile="deutan",  # type: ignore[arg-type]
            severity=1.0,
        )
    with pytest.raises(ValueError, match="uint8"):
        simulator.simulate_rgb(
            KNOWN_PATCHES.astype(np.float32),  # type: ignore[arg-type]
            profile=CVDProfile.DEUTAN,
            severity=1.0,
        )
    with pytest.raises(ValueError, match="three integer channels"):
        simulator.simulate_color(
            (256, 0, 0),
            profile=CVDProfile.DEUTAN,
            severity=1.0,
        )
