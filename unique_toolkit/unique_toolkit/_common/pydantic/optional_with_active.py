"""
OptionalWithActive: represent an optional config object in Python as `T | None`,
but expose `{active: bool, ...defaults}` in JSON Schema and JSON serialization.

Motivation:
- RJSF tends to lose defaults for nullable branches when the default value is null.
- When a user activates a previously-disabled feature, the UI doesn't know which defaults to populate.

This wrapper solves it by:
- Using a generated `TWithActive` model as `json_schema_input_type` (schema always shows defaults)
- Mapping `active=False` -> `None` in Python (clean Optional semantics)
- Serializing `None` -> `{active: false, ...defaults}` (RJSF sees defaults even for disabled state)
- Accepting legacy input formats: `null` or `{...}` (object without `active`)
"""

from __future__ import annotations

from typing import Annotated, Any, TypeVar

from pydantic import BaseModel, BeforeValidator, Field, PlainSerializer, create_model
from pydantic_core import PydanticUndefined

T = TypeVar("T", bound=BaseModel)


def _create_model_with_active(
    base: type[T],
    default_active: bool = False,
) -> type[BaseModel]:
    """Create a new model that extends `base` with an 'active' field."""
    # Safety check: ensure base model doesn't already have an 'active' field
    if "active" in base.model_fields:
        raise ValueError(
            f"Cannot use OptionalWithActive with {base.__name__}: "
            f"it already has an 'active' field. "
            f"Consider renaming the existing field or using a different pattern."
        )
    
    return create_model(
        f"{base.__name__}WithActive",
        active=(
            bool,
            Field(
                default=default_active,
            ),
        ),
        __base__=base,
    )


def optional_with_active(
    base: type[T],
    default_active: bool = False,
) -> Any:
    """
    Convenience default helper for field definitions.

    Usage:
        class MyConfig(BaseModel):
            feature: OptionalWithActive(FeatureConfig) = optional_with_active(FeatureConfig)

    When default_active=True, returns an instance of the config (feature enabled).
    When default_active=False, returns None (feature disabled).

    Note: If default_active=True and the base model has required fields without defaults,
    this will raise a ValidationError. Consider adding defaults to all fields or using
    default_active=False for such models.
    """
    if default_active:
        return base()  # Return config instance when default is active
    return None  # Return None when default is inactive


def OptionalWithActive(  # noqa: N802 - function name mimics a type factory for ergonomics
    base: type[T],
    default_active: bool = False,
) -> Any:
    """
    Type factory for optional config fields with an `active` flag in JSON.

    - Input schema is the extended model, so JSON Schema includes defaults
    - Python value is `base | None`
    - Serialization always yields a dict (never `null`)
    """

    extended_model = _create_model_with_active(base, default_active)

    def deserialize(v: Any) -> T | None:
        if v is None:
            return None

        # Allow passing the base model instance directly.
        if isinstance(v, base):
            return v

        # Backwards compatibility: object without 'active' means "active".
        if isinstance(v, dict) and "active" not in v:
            return base.model_validate(v)

        validated = extended_model.model_validate(v)
        if not validated.active:  # type: ignore[attr-defined]
            return None

        data = validated.model_dump(exclude={"active"})
        return base.model_validate(data)

    def serialize(v: T | None) -> dict[str, Any]:
        if v is None:
            # Build dict manually to handle models with required fields (no defaults).
            # - Fields with defaults: use the default value
            # - Fields with default_factory: call it to get the default
            # - Required fields without defaults: use None
            result: dict[str, Any] = {"active": False}
            for field_name, field_info in base.model_fields.items():
                if field_info.default is not PydanticUndefined:
                    result[field_name] = field_info.default
                elif field_info.default_factory is not None:
                    result[field_name] = field_info.default_factory()
                else:
                    # Required field without default - use None
                    result[field_name] = None
            return result
        return extended_model(active=True, **v.model_dump()).model_dump()

    # JSON schema only shows extended_model (no null) - RJSF doesn't handle anyOf well.
    # Backwards compatibility with old data (null) is handled by:
    # - Frontend: transform-legacy-config.ts transforms null -> {active: false, ...}
    # - Backend: deserialize() accepts null input
    return Annotated[
        base | None,
        BeforeValidator(
            deserialize,
            json_schema_input_type=extended_model,
        ),
        PlainSerializer(
            serialize,
            return_type=dict[str, Any],
        ),
    ]

