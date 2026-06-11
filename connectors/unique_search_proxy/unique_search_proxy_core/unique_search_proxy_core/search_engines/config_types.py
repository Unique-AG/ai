from __future__ import annotations

import operator
from functools import reduce
from typing import Annotated, Any, Mapping, TypeAlias, Union, cast

from pydantic import BaseModel, Field, TypeAdapter

from unique_search_proxy_core.projection import build_request_model
from unique_search_proxy_core.search_engines.base import (
    BaseSearchEngineConfig,
    SearchEngineType,
)
from unique_search_proxy_core.search_engines.brave.schema import BraveConfig
from unique_search_proxy_core.search_engines.google.schema import GoogleConfig
from unique_search_proxy_core.search_engines.perplexity.schema import PerplexityConfig

SearchEngineConfigTypes: TypeAlias = GoogleConfig | BraveConfig | PerplexityConfig

ENGINE_NAME_TO_CONFIG: dict[str, type[BaseSearchEngineConfig]] = {
    SearchEngineType.GOOGLE.value: GoogleConfig,
    SearchEngineType.BRAVE.value: BraveConfig,
    SearchEngineType.PERPLEXITY.value: PerplexityConfig,
}

_search_engine_config_adapter: TypeAdapter[SearchEngineConfigTypes] = TypeAdapter(
    SearchEngineConfigTypes,
)


def parse_search_engine_config(data: object) -> SearchEngineConfigTypes:
    return _search_engine_config_adapter.validate_python(data)


def get_search_engine_config_types_from_names(
    engine_names: list[str],
) -> type[BaseSearchEngineConfig]:
    """Build a union of config models for the given engine slugs (runtime narrowing)."""
    assert len(engine_names) >= 1, "At least one search engine must be active"

    selected_types = [
        ENGINE_NAME_TO_CONFIG[name.lower()]
        for name in engine_names
        if name.lower() in ENGINE_NAME_TO_CONFIG
    ]
    if not selected_types:
        raise ValueError(f"No search engine config found for names: {engine_names}")
    if len(selected_types) == 1:
        return selected_types[0]
    return cast(type[BaseSearchEngineConfig], reduce(operator.or_, selected_types))


def _union_members_from_mapping(
    mapping: Mapping[str, type[BaseModel]],
) -> tuple[type[BaseModel], ...]:
    return tuple(mapping.values())


def build_search_request_union() -> Any:
    """Discriminated union of flat ``POST /v1/search`` bodies (``engine`` discriminator)."""
    members = _union_members_from_mapping(ENGINE_NAME_TO_CONFIG)
    request_models = tuple(build_request_model(config_cls) for config_cls in members)
    if len(request_models) == 1:
        return request_models[0]
    return Annotated[
        Union[request_models],  # type: ignore[valid-type]
        Field(discriminator="engine"),
    ]


SearchRequestTypes = build_search_request_union()
SearchRequest = SearchRequestTypes

_search_request_adapter: TypeAdapter[BaseModel] = TypeAdapter(SearchRequestTypes)  # type: ignore[arg-type]


def parse_search_request(data: object) -> BaseModel:
    return _search_request_adapter.validate_python(data)
