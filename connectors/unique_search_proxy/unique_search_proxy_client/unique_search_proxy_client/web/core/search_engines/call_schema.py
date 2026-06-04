"""LLM-facing call JSON Schema derived from deployment config."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from pydantic import BaseModel
from unique_search_proxy_core.errors import ValidationProxyError
from unique_search_proxy_core.projection import build_llm_call_model
from unique_search_proxy_core.search_engines.base import SearchEngineType
from unique_search_proxy_core.search_engines.config_types import (
    SearchEngineConfigTypes,
    parse_search_engine_config,
)

from unique_search_proxy_client.web.core.search_engines.factory import (
    get_search_engine_service,
)


@dataclass(frozen=True)
class SearchCallSchemaDescriptor:
    """Metadata and JSON Schema for the engine call model on ``POST /v1/search``."""

    engine: str
    mode: str
    snippet_only: bool
    call_schema: dict[str, Any]


def resolve_search_call_schema_from_config(
    engine_id: str,
    config: SearchEngineConfigTypes,
    *,
    strict: bool = True,
) -> SearchCallSchemaDescriptor:
    """Project the LLM-visible call surface from a parsed deployment config."""
    from unique_search_proxy_client.web.core.registry import get_search_engine_descriptor

    try:
        engine_type = SearchEngineType(engine_id.lower())
    except ValueError as exc:
        raise ValidationProxyError(
            f"Unknown search engine: {engine_id!r}",
            engine=engine_id,
        ) from exc

    descriptor = get_search_engine_descriptor(engine_type.value)
    if descriptor is None:
        raise ValidationProxyError(
            f"Unknown search engine: {engine_id!r}",
            engine=engine_id,
        )

    engine = get_search_engine_service(engine_type)
    projected = build_llm_call_model(
        descriptor.config_model,
        config,
        strict_required=strict,
    )

    return SearchCallSchemaDescriptor(
        engine=engine_type.value,
        mode=engine.mode,
        snippet_only=engine.snippet_only,
        call_schema=projected.model_json_schema(),
    )


def resolve_search_call_schema(
    engine_id: str,
    *,
    config: SearchEngineConfigTypes | dict[str, Any] | None = None,
    strict: bool = True,
) -> SearchCallSchemaDescriptor:
    """Resolve call schema from deployment config or engine defaults."""
    if config is not None:
        if isinstance(config, BaseModel):
            parsed = config
        else:
            parsed = parse_search_engine_config(config)
        return resolve_search_call_schema_from_config(
            engine_id,
            parsed,
            strict=strict,
        )

    return resolve_search_call_schema_from_config(
        engine_id,
        _default_config(engine_id),
        strict=strict,
    )


def _default_config(engine_id: str) -> SearchEngineConfigTypes:
    from unique_search_proxy_client.web.core.provider_config_schema import (
        provider_default_config,
    )

    return parse_search_engine_config(
        {"engine": engine_id, **provider_default_config("search_engine", engine_id)},
    )


__all__ = [
    "SearchCallSchemaDescriptor",
    "resolve_search_call_schema",
    "resolve_search_call_schema_from_config",
]
