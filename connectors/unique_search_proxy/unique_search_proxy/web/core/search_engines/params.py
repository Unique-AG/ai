from __future__ import annotations

from enum import StrEnum
from typing import Any, TypeVar

from pydantic import BaseModel
from pydantic.fields import FieldInfo

QUERY_FIELD = "query"
FETCH_SIZE_FIELD = "fetch_size"
FETCH_SIZE_JSON = "fetchSize"

CallT = TypeVar("CallT", bound=BaseModel)


class ParamExposure(StrEnum):
    """How a search-engine parameter participates in config vs LLM surfaces."""

    ALWAYS_EXPOSED = "always_exposed"
    CONFIG_ONLY = "config_only"
    EXPOSABLE = "exposable"
    PRIVATE = "private"


def field_exposure(field_info: FieldInfo) -> ParamExposure | None:
    extra = field_info.json_schema_extra
    if not isinstance(extra, dict):
        return None
    raw = extra.get("exposure")
    if raw is None:
        return None
    return ParamExposure(str(raw))


def resolve_field_name(model: type[BaseModel], name: str) -> str:
    if name in model.model_fields:
        return name
    for field_name, field_info in model.model_fields.items():
        if field_info.alias == name or field_info.serialization_alias == name:
            return field_name
    raise ValueError(f"Field {name!r} is not defined on {model.__name__}")


def validate_exposed_fields(
    model: type[BaseModel],
    exposed_fields: list[str],
    *,
    always_exposed: frozenset[str] = frozenset({QUERY_FIELD}),
    config_only: frozenset[str] = frozenset({FETCH_SIZE_FIELD}),
) -> list[str]:
    """Ensure exposed_fields only references LLM-optional knobs on ``model``."""
    invalid_in_list = always_exposed | config_only
    for exposed_name in exposed_fields:
        field_name = resolve_field_name(model, exposed_name)
        if field_name in invalid_in_list:
            msg = f"{exposed_name!r} cannot be listed in exposedFields"
            raise ValueError(msg)
        exposure = field_exposure(model.model_fields[field_name])
        if exposure is not ParamExposure.EXPOSABLE:
            msg = f"{exposed_name!r} is not exposable on {model.__name__}"
            raise ValueError(msg)
    return exposed_fields


def llm_field_names(
    model: type[BaseModel],
    exposed_fields: list[str],
    *,
    always_exposed: frozenset[str] = frozenset({QUERY_FIELD}),
) -> list[str]:
    """Field names for LLM projection: always-exposed + configured allowlist."""
    validate_exposed_fields(model, exposed_fields)
    optional = [resolve_field_name(model, name) for name in exposed_fields]
    ordered: list[str] = []
    for name in always_exposed:
        if name in model.model_fields and name not in ordered:
            ordered.append(name)
    for name in optional:
        if name not in ordered:
            ordered.append(name)
    return ordered


def to_provider_params(model: BaseModel) -> dict[str, Any]:
    """Serialize engine parameters for the upstream provider query string."""
    exclude: set[str] = set()
    for field_name, field_info in type(model).model_fields.items():
        if field_exposure(field_info) is ParamExposure.PRIVATE:
            exclude.add(field_name)
    return model.model_dump(
        mode="json", exclude_none=True, exclude=exclude, by_alias=True
    )


def config_parameter_defaults(
    config: BaseModel,
    parameters_type: type[BaseModel],
) -> dict[str, Any]:
    """Extract engine-parameter defaults from a config object."""
    config_data = config.model_dump()
    return {
        key: config_data[key]
        for key in parameters_type.model_fields
        if key in config_data
    }


def resolve_search_call(
    call_type: type[CallT],
    parameters_type: type[BaseModel],
    config: BaseModel,
    invocation: dict[str, Any],
) -> CallT:
    """Merge config parameter defaults with per-invocation overrides into a call model."""
    defaults = config_parameter_defaults(config, parameters_type)
    merged = {**defaults, **invocation}
    return call_type.model_validate(merged)


def call_query(call: BaseModel) -> str:
    """Return the query string from a resolved search call model."""
    query = getattr(call, "query", None)
    if not isinstance(query, str) or not query:
        raise ValueError("Resolved search call is missing a non-empty query")
    return query
