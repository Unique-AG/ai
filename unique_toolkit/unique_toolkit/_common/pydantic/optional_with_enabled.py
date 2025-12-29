"""
OptionalWithEnabled: represent an optional config object in Python as `T | None`,
but expose `{enabled: bool, ...defaults}` in JSON Schema and JSON serialization.

Motivation:
- RJSF tends to lose defaults for nullable branches when the default value is null.
- When a user enables a previously-disabled feature, the UI doesn't know which defaults to populate.

This wrapper solves it by:
- Using a generated `TWithEnabled` model as `json_schema_input_type` (schema always shows defaults)
- Mapping `enabled=False` -> `None` in Python (clean Optional semantics)
- Serializing `None` -> `{enabled: false, ...defaults}` (RJSF sees defaults even for disabled state)
- Accepting legacy input formats: `null` or `{...}` (object without `enabled`)
"""

from __future__ import annotations

from typing import Annotated, Any, TypeVar

from pydantic import BaseModel, BeforeValidator, Field, PlainSerializer, create_model

T = TypeVar("T", bound=BaseModel)


def _create_model_with_enabled(
    base: type[T],
    default_enabled: bool = False,
) -> type[BaseModel]:
    """Create a new model that extends `base` with an 'enabled' field."""
    return create_model(
        f"{base.__name__}WithEnabled",
        enabled=(
            bool,
            Field(
                default=default_enabled,
                description="Whether this feature is enabled",
            ),
        ),
        __base__=base,
    )


def optional_with_enabled(
    base: type[T],
    default_enabled: bool = False,
) -> Any:
    """
    Convenience default helper for field definitions.

    Usage:
        class MyConfig(BaseModel):
            feature: OptionalWithEnabled(FeatureConfig) = optional_with_enabled(FeatureConfig)

    Note:
        The runtime default stays `None` (Python semantics), but serialization will
        turn it into `{enabled: false, ...defaults}`.
    """

    # Keep `None` as the Python default. The serializer handles the RJSF default object.
    return None


def OptionalWithEnabled(  # noqa: N802 - function name mimics a type factory for ergonomics
    base: type[T],
    default_enabled: bool = False,
) -> Any:
    """
    Type factory for optional config fields with an `enabled` flag in JSON.

    - Input schema is the extended model, so JSON Schema includes defaults
    - Python value is `base | None`
    - Serialization always yields a dict (never `null`)
    """

    extended_model = _create_model_with_enabled(base, default_enabled)

    def deserialize(v: Any) -> T | None:
        if v is None:
            return None

        # Allow passing the base model instance directly.
        if isinstance(v, base):
            return v

        # Backwards compatibility: object without 'enabled' means "enabled".
        if isinstance(v, dict) and "enabled" not in v:
            return base.model_validate(v)

        validated = extended_model.model_validate(v)
        if not validated.enabled:  # type: ignore[attr-defined]
            return None

        data = validated.model_dump(exclude={"enabled"})
        return base.model_validate(data)

    def serialize(v: T | None) -> dict[str, Any]:
        if v is None:
            return extended_model(enabled=False).model_dump()
        return extended_model(enabled=True, **v.model_dump()).model_dump()

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




