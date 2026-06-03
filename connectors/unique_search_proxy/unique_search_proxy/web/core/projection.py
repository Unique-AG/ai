from __future__ import annotations

from typing import Any, cast

from pydantic import BaseModel, Field, create_model
from pydantic.fields import FieldInfo

from unique_search_proxy.web.core.schema import camelized_model_config


def project_call_schema(
    call_schema: type[BaseModel],
    exposed_fields: list[str],
    *,
    model_name_suffix: str = "LlmProjection",
) -> type[BaseModel]:
    """Project a call schema down to the fields exposed to LLM-driven callers."""
    if not exposed_fields:
        raise ValueError("exposed_fields must contain at least one field name")

    field_definitions: dict[str, tuple[Any, Any]] = {}
    for exposed_name in exposed_fields:
        field_name = _resolve_field_name(call_schema, exposed_name)
        field_info = call_schema.model_fields[field_name]
        field_definitions[field_name] = _field_definition_from_info(field_info)

    model_config = call_schema.model_config or camelized_model_config
    return create_model(
        f"{call_schema.__name__}{model_name_suffix}",
        __config__=model_config,
        **cast(Any, field_definitions),
    )


def project_json_schema(
    call_schema: type[BaseModel],
    exposed_fields: list[str],
) -> dict[str, Any]:
    """Return the JSON schema for the LLM-facing projection of a call schema."""
    projected = project_call_schema(call_schema, exposed_fields)
    return projected.model_json_schema()


def _resolve_field_name(call_schema: type[BaseModel], exposed_name: str) -> str:
    if exposed_name in call_schema.model_fields:
        return exposed_name

    for field_name, field_info in call_schema.model_fields.items():
        if field_info.alias == exposed_name:
            return field_name
        if field_info.serialization_alias == exposed_name:
            return field_name

    raise ValueError(
        f"Field {exposed_name!r} is not defined on {call_schema.__name__}",
    )


def _field_definition_from_info(field_info: FieldInfo) -> tuple[Any, Any]:
    if field_info.is_required():
        return (
            field_info.annotation,
            Field(
                description=field_info.description,
                json_schema_extra=field_info.json_schema_extra,
            ),
        )

    default = field_info.get_default(call_default_factory=True)
    return (
        field_info.annotation,
        Field(
            default=default,
            description=field_info.description,
            json_schema_extra=field_info.json_schema_extra,
        ),
    )
