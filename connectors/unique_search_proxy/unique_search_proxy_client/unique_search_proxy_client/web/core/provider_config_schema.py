"""JSON Schema and defaults for registered search-engine and crawler config models."""

from __future__ import annotations

import operator
from functools import reduce
from typing import Any, Literal

from pydantic import BaseModel, TypeAdapter
from unique_search_proxy_core.errors import EngineNotConfiguredError

from unique_search_proxy_client.web.core.registry import (
    build_crawler_config_union,
    build_search_engine_config_union,
    get_crawler_config_model,
    get_search_engine_config_model,
    registered_crawlers,
    registered_search_engines,
)

ProviderKind = Literal["search_engine", "crawler"]


def _registered_ids(kind: ProviderKind) -> frozenset[str]:
    if kind == "search_engine":
        return registered_search_engines()
    return registered_crawlers()


def get_provider_config_model(
    kind: ProviderKind,
    provider_id: str,
) -> type[BaseModel]:
    """Resolve a registered provider id to its deployment config model."""
    normalized = provider_id.lower()
    if kind == "search_engine":
        model = get_search_engine_config_model(normalized)
    else:
        model = get_crawler_config_model(normalized)
    if model is None:
        raise EngineNotConfiguredError(normalized, kind=kind)
    return model


def provider_config_json_schema(kind: ProviderKind, provider_id: str) -> dict[str, Any]:
    """JSON Schema for one provider's deployment config (admin / manifest UI)."""
    return get_provider_config_model(kind, provider_id).model_json_schema()


def provider_default_config(kind: ProviderKind, provider_id: str) -> dict[str, Any]:
    """Default deployment config instance serialized with camelCase aliases."""
    model = get_provider_config_model(kind, provider_id)
    return model().model_dump(mode="json", by_alias=True)


def _union_json_schema(models: list[type[BaseModel]]) -> dict[str, Any]:
    if not models:
        raise ValueError("At least one config model is required")
    if len(models) == 1:
        return models[0].model_json_schema()
    union_type = reduce(operator.or_, models)
    return TypeAdapter(union_type).model_json_schema()


def registered_search_engines_config_json_schema() -> dict[str, Any]:
    """Discriminated union JSON Schema for all registered search engines (``engine``)."""
    return _union_json_schema(build_search_engine_config_union())


def registered_crawlers_config_json_schema() -> dict[str, Any]:
    """Discriminated union JSON Schema for all registered crawlers (``crawler``)."""
    return _union_json_schema(build_crawler_config_union())


def list_registered_providers() -> dict[str, list[str]]:
    return {
        "search_engines": sorted(_registered_ids("search_engine")),
        "crawlers": sorted(_registered_ids("crawler")),
    }


__all__ = [
    "ProviderKind",
    "get_provider_config_model",
    "list_registered_providers",
    "provider_config_json_schema",
    "provider_default_config",
    "registered_crawlers_config_json_schema",
    "registered_search_engines_config_json_schema",
]
