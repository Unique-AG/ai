from __future__ import annotations

import operator
from functools import reduce
from typing import TypeAlias, cast

from pydantic import TypeAdapter

from unique_search_proxy.web.core.search_engines.base import (
    BaseSearchEngineConfig,
    SearchEngineType,
)
from unique_search_proxy.web.core.search_engines.google.schema import GoogleConfig

SearchEngineConfigTypes: TypeAlias = GoogleConfig

ENGINE_NAME_TO_CONFIG: dict[str, type[BaseSearchEngineConfig]] = {
    SearchEngineType.GOOGLE.value: GoogleConfig,
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
