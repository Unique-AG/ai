"""LLM-facing call JSON Schema derived from deployment config (no HTTP)."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from pydantic import BaseModel

from unique_search_proxy_core.projection import build_llm_call_model
from unique_search_proxy_core.providers.schema import provider_default_config
from unique_search_proxy_core.search_engines.base import (
    SearchEngineType,
    get_search_engine_mode,
)
from unique_search_proxy_core.search_engines.config_types import (
    ENGINE_NAME_TO_CONFIG,
    SearchEngineConfigTypes,
    parse_search_engine_config,
)


@dataclass(frozen=True)
class SearchCallSchemaDescriptor:
    """Metadata and JSON Schema for the engine call model on ``POST /v1/search``."""

    engine: str
    mode: str
    call_schema: dict[str, Any]


def resolve_search_call_schema_from_config(
    engine_id: str,
    config: SearchEngineConfigTypes,
    *,
    strict: bool = True,
) -> SearchCallSchemaDescriptor:
    """Project the LLM-visible call surface from a parsed deployment config."""
    engine_type = SearchEngineType(engine_id.lower())
    config_cls = ENGINE_NAME_TO_CONFIG[engine_type.value]
    if type(config) is not config_cls:
        raise ValueError(
            f"Config type {type(config).__name__} does not match engine {engine_id!r}",
        )

    projected = build_llm_call_model(config_cls, config, strict_required=strict)
    return SearchCallSchemaDescriptor(
        engine=engine_type.value,
        mode=get_search_engine_mode(engine_type).value,
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
        parsed = (
            config
            if isinstance(config, BaseModel)
            else parse_search_engine_config(config)
        )
        return resolve_search_call_schema_from_config(engine_id, parsed, strict=strict)

    defaults = provider_default_config("search_engine", engine_id)
    parsed = parse_search_engine_config(defaults)
    return resolve_search_call_schema_from_config(engine_id, parsed, strict=strict)


__all__ = [
    "SearchCallSchemaDescriptor",
    "resolve_search_call_schema",
    "resolve_search_call_schema_from_config",
]
