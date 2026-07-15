from pydantic import BaseModel

from unique_web_search.services.search_engine.base import (
    SearchEngine,
    SearchEngineMode,
)
from unique_web_search.services.search_engine.registry import (
    SEARCH_ENGINE_REGISTRY,
    get_search_engine_mode,
    get_search_engine_service,
    resolve_search_engine_mode,
)

SEARCH_ENGINE_REGISTRY.autodiscover(__path__, __name__, exclude=frozenset({"schema"}))

from unique_search_proxy_core.search_engines import (  # noqa: E402
    BraveConfig,
    GoogleConfig,
    PerplexityConfig,
    SearchEngineType,
)

from unique_web_search.services.search_engine.bing import (  # noqa: E402
    BingSearch,
    BingSearchConfig,
)
from unique_web_search.services.search_engine.brave import BraveSearch  # noqa: E402
from unique_web_search.services.search_engine.custom_api import (  # noqa: E402
    CustomAPI,
    CustomAPIConfig,
)
from unique_web_search.services.search_engine.google import GoogleSearch  # noqa: E402
from unique_web_search.services.search_engine.perplexity import (  # noqa: E402
    PerplexitySearch,
)
from unique_web_search.services.search_engine.vertexai import (  # noqa: E402
    VertexAI,
    VertexAIConfig,
)

SearchEngineTypes = (
    GoogleSearch | BingSearch | CustomAPI | BraveSearch | PerplexitySearch | VertexAI
)
SearchEngineConfigTypes = (
    GoogleConfig
    | BingSearchConfig
    | CustomAPIConfig
    | BraveConfig
    | PerplexityConfig
    | VertexAIConfig
)

ENGINE_NAME_TO_CONFIG = SEARCH_ENGINE_REGISTRY.name_to_config()


def get_search_engine_config_types_from_names(
    engine_names: list[str],
) -> type[BaseModel]:
    return SEARCH_ENGINE_REGISTRY.config_types_from_names(engine_names)


def get_default_search_engine_config(
    engine_names: list[str],
) -> type[BaseModel]:
    return SEARCH_ENGINE_REGISTRY.default_config(engine_names)


__all__ = [
    "SearchEngineMode",
    "SearchEngineType",
    "get_search_engine_mode",
    "resolve_search_engine_mode",
    "GoogleConfig",
    "GoogleSearch",
    "BingSearchConfig",
    "BingSearch",
    "BraveSearch",
    "BraveConfig",
    "PerplexitySearch",
    "PerplexityConfig",
    "get_search_engine_service",
    "SearchEngine",
    "get_search_engine_config_types_from_names",
    "get_default_search_engine_config",
    "VertexAIConfig",
    "VertexAI",
]
