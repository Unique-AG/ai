"""Deployment config JSON Schema and defaults (no HTTP)."""

from __future__ import annotations

import operator
from functools import reduce
from typing import Any, Literal

from pydantic import BaseModel, TypeAdapter

from unique_search_proxy_core.crawlers.config_types import CRAWLER_NAME_TO_CONFIG
from unique_search_proxy_core.search_engines.config_types import ENGINE_NAME_TO_CONFIG

ProviderKind = Literal["search_engine", "crawler"]


def _config_model(kind: ProviderKind, provider_id: str) -> type[BaseModel]:
    if kind == "search_engine":
        model = ENGINE_NAME_TO_CONFIG.get(provider_id.lower())
    else:
        model = CRAWLER_NAME_TO_CONFIG.get(provider_id)
    if model is None:
        raise ValueError(f"No {kind} config registered for {provider_id!r}")
    return model


def provider_config_json_schema(kind: ProviderKind, provider_id: str) -> dict[str, Any]:
    """JSON Schema for one provider's deployment config."""
    return _config_model(kind, provider_id).model_json_schema()


def provider_default_config(kind: ProviderKind, provider_id: str) -> dict[str, Any]:
    """Default deployment config instance serialized with camelCase aliases."""
    data = _config_model(kind, provider_id)().model_dump(mode="json", by_alias=True)
    if kind == "crawler":
        data.pop("urls", None)
    return data


def union_config_json_schema(models: list[type[BaseModel]]) -> dict[str, Any]:
    if not models:
        raise ValueError("At least one config model is required")
    if len(models) == 1:
        return models[0].model_json_schema()
    union_type = reduce(operator.or_, models)
    return TypeAdapter(union_type).json_schema()  # type: ignore[call-overload]


def search_engines_config_json_schema() -> dict[str, Any]:
    """Discriminated union JSON Schema for all registered search engines."""
    return union_config_json_schema(list(ENGINE_NAME_TO_CONFIG.values()))


def crawlers_config_json_schema() -> dict[str, Any]:
    """Discriminated union JSON Schema for all registered crawlers."""
    return union_config_json_schema(list(CRAWLER_NAME_TO_CONFIG.values()))


__all__ = [
    "ProviderKind",
    "crawlers_config_json_schema",
    "provider_config_json_schema",
    "provider_default_config",
    "search_engines_config_json_schema",
    "union_config_json_schema",
]
