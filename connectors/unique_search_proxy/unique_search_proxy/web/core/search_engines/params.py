from __future__ import annotations

from typing import Any, TypeVar

from pydantic import BaseModel

from unique_search_proxy.web.core.param_policy import QUERY_FIELD
from unique_search_proxy.web.core.param_policy.exposable_param import (
    ExposableParam,
    is_exposable_param_field,
    unwrap_exposable_param_value,
)
from unique_search_proxy.web.core.projection import build_request_model
from unique_search_proxy.web.core.search_engines.base import SearchEngineType

ENGINE_FIELD = "engine"
FETCH_SIZE_FIELD = "fetch_size"
TIMEOUT_FIELD = "timeout"
SEARCH_ENGINE_ID_FIELD = "search_engine_id"

RequestT = TypeVar("RequestT", bound=BaseModel)


def _should_merge_value(value: Any) -> bool:
    return value is not None


def config_defaults(config: BaseModel) -> dict[str, Any]:
    """Deployment defaults merged into each search/request (plain values)."""
    config_model = type(config)
    defaults: dict[str, Any] = {}
    for field_name, field_info in config_model.model_fields.items():
        if field_name == ENGINE_FIELD:
            continue
        raw = getattr(config, field_name)
        if is_exposable_param_field(field_info):
            merged = unwrap_exposable_param_value(raw)
            if _should_merge_value(merged):
                defaults[field_name] = merged
            continue
        if _should_merge_value(raw) or field_name in (
            FETCH_SIZE_FIELD,
            TIMEOUT_FIELD,
            "safe",
        ):
            defaults[field_name] = raw
    return defaults


def llm_exposed_field_names(config: BaseModel) -> list[str]:
    """Field names for LLM call-schema projection (``query`` + ``expose=True`` params)."""
    names = [QUERY_FIELD]
    for field_name, field_info in type(config).model_fields.items():
        if not is_exposable_param_field(field_info):
            continue
        raw = getattr(config, field_name)
        if isinstance(raw, ExposableParam) and raw.llm_exposed():
            names.append(field_name)
    return names


def merge_config_and_invocation(
    config: BaseModel,
    invocation: dict[str, Any],
    *,
    engine: SearchEngineType | None = None,
) -> BaseModel:
    """Merge deployment config defaults with LLM/caller partial args into a request model."""
    request_model = build_request_model(type(config))
    defaults = config_defaults(config)
    merged: dict[str, Any] = {**defaults, **invocation}
    if engine is not None and ENGINE_FIELD in request_model.model_fields:
        merged[ENGINE_FIELD] = engine.value
    return request_model.model_validate(merged)


def provider_param_exclude_fields(config_cls: type[BaseModel]) -> set[str]:
    """Config fields omitted from upstream provider query strings."""
    return {
        ENGINE_FIELD,
        TIMEOUT_FIELD,
        QUERY_FIELD,
        FETCH_SIZE_FIELD,
        SEARCH_ENGINE_ID_FIELD,
    }


def provider_query_params_from_request(
    request: BaseModel,
    config_cls: type[BaseModel],
) -> dict[str, Any]:
    """Serialize provider knobs from a derived request model."""
    return request.model_dump(
        mode="json",
        exclude_none=True,
        exclude=provider_param_exclude_fields(config_cls),
        by_alias=True,
    )


def call_query(request: BaseModel) -> str:
    """Return the query string from a resolved search request model."""
    query = getattr(request, QUERY_FIELD, None)
    if not isinstance(query, str) or not query:
        raise ValueError("Resolved search request is missing a non-empty query")
    return query
