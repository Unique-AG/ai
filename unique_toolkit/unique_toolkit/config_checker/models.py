"""Internal data models for config checker."""

from dataclasses import dataclass
from typing import Any

from pydantic import BaseModel


@dataclass
class ConfigEntry:
    """Represents a registered config model."""

    name: str
    model: type[BaseModel]
    source: str  # "auto_discovery" or "explicit_decorator"
    module_path: str | None = None  # Path to the module containing the config


@dataclass
class ValidationError:
    """Represents a schema validation error."""

    field_path: str
    message: str
    old_value: Any | None = None
    new_value: Any | None = None


@dataclass
class DefaultChange:
    """Represents a detected default value change."""

    field_path: str
    old_value: Any
    new_value: Any


@dataclass
class ConfigValidationResult:
    """Result of validating old JSON against new schema."""

    config_name: str
    valid: bool
    errors: list[ValidationError] | None = None
    default_changes: list[DefaultChange] | None = None


@dataclass
class EnvironmentVarWarning:
    """Warning about environment variables during export."""

    var_name: str
    value: str | None = None
    message: str = ""
