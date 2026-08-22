"""Validated configuration contracts shared by future pipeline modules."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class CVDProfile(str, Enum):
    """User-selected color-vision-deficiency profile."""

    PROTAN = "protan"
    DEUTAN = "deutan"
    TRITAN = "tritan"


@dataclass(frozen=True, slots=True)
class AppConfig:
    """Minimal user-controlled settings established by the T00 contract."""

    profile: CVDProfile = CVDProfile.DEUTAN
    severity: float = 1.0

    def __post_init__(self) -> None:
        if not 0.0 <= self.severity <= 1.0:
            raise ValueError("severity must be within [0, 1]")
