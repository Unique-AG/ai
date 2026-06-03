"""LLM-facing call JSON Schema derived from a validated search-engine config."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from unique_search_proxy.web.core.search_engines.base import SearchEngineType
from unique_search_proxy.web.core.search_engines.config_types import (
    SearchEngineConfigTypes,
)
from unique_search_proxy.web.core.search_engines.factory import (
    get_search_engine_service,
)
from unique_search_proxy.web.core.search_engines.google.schema import GoogleConfig
from unique_search_proxy.web.core.search_engines.google.service import (
    GoogleSearchService,
)


@dataclass(frozen=True)
class SearchCallSchemaDescriptor:
    """Metadata and JSON Schema for ``SearchRequest.call`` given a deployment config."""

    engine: str
    mode: str
    snippet_only: bool
    call_schema: dict[str, Any]


def resolve_search_call_schema(
    config: SearchEngineConfigTypes,
) -> SearchCallSchemaDescriptor:
    """Project the per-invocation call surface implied by ``config``."""
    engine = get_search_engine_service(config)
    match config.engine:
        case SearchEngineType.GOOGLE:
            google_config = GoogleConfig.model_validate(config.model_dump())
            projected = GoogleSearchService.llm_call_schema(google_config)
            call_schema = projected.model_json_schema()
        case _:
            raise ValueError(f"Unsupported search engine: {config.engine}")

    return SearchCallSchemaDescriptor(
        engine=config.engine.value,
        mode=engine.mode,
        snippet_only=engine.snippet_only,
        call_schema=call_schema,
    )


__all__ = ["SearchCallSchemaDescriptor", "resolve_search_call_schema"]
