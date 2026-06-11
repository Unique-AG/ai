from __future__ import annotations

from typing import TYPE_CHECKING, Any

from pydantic import BaseModel
from unique_search_proxy_core.search_engines.base import SearchEngine, SearchEngineType
from unique_search_proxy_core.search_engines.config_types import SearchEngineConfigTypes
from unique_search_proxy_core.search_engines.params import merge_config_and_invocation

from unique_search_proxy_client.web.core.search_engines.brave.service import (
    BraveSearchService,
)
from unique_search_proxy_client.web.core.search_engines.google.service import (
    GoogleSearchService,
)

if TYPE_CHECKING:
    from httpx import AsyncClient


def get_search_engine_service(
    engine: SearchEngineType,
    *,
    http_client: AsyncClient | None = None,
) -> SearchEngine[Any]:
    """Instantiate a search engine by registered id (deployment secrets from env)."""
    match engine:
        case SearchEngineType.GOOGLE:
            return GoogleSearchService(http_client=http_client)
        case SearchEngineType.BRAVE:
            return BraveSearchService(http_client=http_client)
        case _:
            raise ValueError(f"Unsupported search engine: {engine}")


def resolve_engine_request(
    config: SearchEngineConfigTypes,
    invocation: dict[str, object],
) -> BaseModel:
    """Merge deployment config defaults with a partial request dict (callers / tests)."""
    match config.engine:
        case SearchEngineType.GOOGLE:
            return merge_config_and_invocation(
                config,
                dict(invocation),
                engine=SearchEngineType.GOOGLE,
            )
        case SearchEngineType.BRAVE:
            return merge_config_and_invocation(
                config,
                dict(invocation),
                engine=SearchEngineType.BRAVE,
            )
        case _:
            raise ValueError(f"Unsupported search engine: {config.engine}")


def get_request_model_for_engine(engine_id: str) -> type[BaseModel]:
    from unique_search_proxy_client.web.core.registry import (
        get_search_engine_descriptor,
    )

    descriptor = get_search_engine_descriptor(engine_id)
    if descriptor is None:
        raise ValueError(f"No descriptor for search engine: {engine_id}")
    return descriptor.request_model


# Backward-compatible alias
resolve_engine_call = resolve_engine_request


__all__ = [
    "get_request_model_for_engine",
    "get_search_engine_service",
    "resolve_engine_call",
    "resolve_engine_request",
]
