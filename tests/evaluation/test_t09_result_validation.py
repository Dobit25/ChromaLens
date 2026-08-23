from __future__ import annotations

import json

import pytest

from scripts import t09_result_validation as validator


def test_validator_rejects_schema_additional_properties() -> None:
    schema = json.loads(validator.SCHEMA_PATH.read_text(encoding="utf-8"))
    minimal = {key: None for key in schema["required"]}
    minimal["unexpected"] = True

    with pytest.raises(validator.ResultValidationError):
        validator._validate_schema(
            minimal, schema, schema, "$", strict_formats=True
        )


def test_registry_and_frozen_case_files_are_loaded_without_optional_dependency() -> None:
    cases = validator.load_case_registry()
    registry = json.loads(validator.REGISTRY_PATH.read_text(encoding="utf-8"))

    assert len(cases) == 92
    assert len({row["case_id"] for row in cases}) == 92
    assert len(registry["metrics"]) == 32
