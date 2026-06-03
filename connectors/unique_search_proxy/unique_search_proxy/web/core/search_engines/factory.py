from __future__ import annotations

from typing import TYPE_CHECKING, Any

from unique_search_proxy.web.core.search_engines.base import (
    SearchEngine,
    SearchEngineType,
)
from unique_search_proxy.web.core.search_engines.config_types import (
    SearchEngineConfigTypes,
)
from unique_search_proxy.web.core.search_engines.google.schema import (
    GoogleConfig,
    GoogleEngineParameters,
    GoogleSearchCall,
)
from unique_search_proxy.web.core.search_engines.google.service import (
    GoogleSearchService,
)
from unique_search_proxy.web.core.search_engines.params import resolve_search_call

if TYPE_CHECKING:
    from httpx import AsyncClient
    from pydantic import BaseModel


def resolve_engine_call(
    config: SearchEngineConfigTypes,
    invocation: dict[str, Any],
) -> BaseModel:
    """Build the resolved per-engine call model from config defaults + invocation."""
    match config.engine:
        case SearchEngineType.GOOGLE:
            google_config = GoogleConfig.model_validate(config.model_dump())
            return resolve_search_call(
                GoogleSearchCall,
                GoogleEngineParameters,
                google_config,
                invocation,
            )
        case _:
            raise ValueError(f"Unsupported search engine: {config.engine}")


def get_search_engine_service(
    config: SearchEngineConfigTypes,
    *,
    http_client: AsyncClient | None = None,
) -> SearchEngine[Any, Any]:
    """Instantiate a search engine from a validated discriminated config."""
    match config.engine:
        case SearchEngineType.GOOGLE:
            return GoogleSearchService(config, http_client=http_client)
        case _:
            raise ValueError(f"Unsupported search engine: {config.engine}")
