"""Tests for RestrictEnum JSON schema narrowing."""

from __future__ import annotations

from enum import StrEnum
from typing import Annotated

import pytest
from pydantic import BaseModel

from unique_toolkit._common.restrict_enum import RestrictEnum


class _Color(StrEnum):
    RED = "red"
    GREEN = "green"
    BLUE = "blue"


class _ColorModel(BaseModel):
    color: Annotated[_Color, RestrictEnum(["red", "blue"])] = _Color.RED


@pytest.mark.ai
def test_AI_restrict_enum__narrows_json_schema_enum() -> None:
    """RestrictEnum should expose only allowed values in the JSON schema."""
    schema = _ColorModel.model_json_schema()

    assert schema["properties"]["color"]["enum"] == ["red", "blue"]


@pytest.mark.ai
def test_AI_restrict_enum__does_not_narrow_runtime_validation() -> None:
    """RestrictEnum narrows schema only; full enum values still validate."""
    model = _ColorModel(color=_Color.GREEN)

    assert model.color is _Color.GREEN


@pytest.mark.ai
def test_AI_restrict_enum__callable_allowed_values() -> None:
    """RestrictEnum accepts a zero-argument factory for allowed values."""

    def allowed() -> list[str]:
        return ["red"]

    class Model(BaseModel):
        color: Annotated[_Color, RestrictEnum(allowed)] = _Color.RED

    schema = Model.model_json_schema()

    assert schema["properties"]["color"]["enum"] == ["red"]


@pytest.mark.ai
def test_AI_restrict_enum__invalid_allowed_value__raises_at_model_definition() -> None:
    """RestrictEnum rejects allowed values that are not enum members."""

    with pytest.raises(ValueError, match="not a valid value for _Color"):

        class Model(BaseModel):
            color: Annotated[_Color, RestrictEnum(["orange"])]
