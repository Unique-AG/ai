"""Internal data models for config checker."""

from typing import Any

from pydantic import BaseModel, ConfigDict


class ConfigEntry(BaseModel):
    """Represents a registered config model."""

    model_config = ConfigDict(arbitrary_types_allowed=True)

    name: str
    model: type[BaseModel]
    source: str = "explicit"
    module_path: str | None = None  # Path to the module containing the config


class ValidationError(BaseModel):
    """Represents a schema validation error."""

    field_path: str
    message: str
    old_value: Any | None = None
    new_value: Any | None = None


class DefaultChange(BaseModel):
    """Represents a detected default value change."""

    field_path: str
    old_value: Any
    new_value: Any


class ConfigValidationResult(BaseModel):
    """Result of validating old JSON against new schema."""

    config_name: str
    valid: bool
    is_new: bool = False
    errors: list[ValidationError] | None = None
    warnings: list[ValidationError] | None = None
    default_changes: list[DefaultChange] | None = None


class EnvironmentVarWarning(BaseModel):
    """Warning about environment variables during export."""

    var_name: str
    value: str | None = None
    message: str = ""
