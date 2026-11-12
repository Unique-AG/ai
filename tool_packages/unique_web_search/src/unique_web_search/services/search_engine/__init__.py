from pydantic import BaseModel

from unique_web_search.services.search_engine.base import (
    SEARCH_ENGINE_DECOMMISSIONED_MESSAGE,
    SearchEngine,
    SearchEngineDecommissionedError,
    SearchEngineMode,
    is_search_engine_decommissioned,
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
from unique_web_search.services.search_engine.brave import (  # noqa: E402
    BraveSearch,
    BraveSearchConfig,
)
from unique_web_search.services.search_engine.custom_api import (  # noqa: E402
    CustomAPI,
    CustomAPIConfig,
)
from unique_web_search.services.search_engine.google import GoogleSearch  # noqa: E402
from unique_web_search.services.search_engine.perplexity import (  # noqa: E402
    PerplexitySearch,
    PerplexitySearchConfig,
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
    | BraveSearchConfig
    | PerplexitySearchConfig
    | VertexAIConfig
)

ENGINE_NAME_TO_CONFIG = SEARCH_ENGINE_REGISTRY.name_to_config()


def get_search_engine_config_types_from_names(
    engine_names: list[str],
) -> type[BaseModel]:
    return SEARCH_ENGINE_REGISTRY.config_types_from_names(engine_names)


def get_default_search_engine_config(
    engine_names: list[str],
    decommissioned_engine_names: list[str] | None = None,
) -> type[BaseModel]:
    """Return the config type of the first engine that is not decommissioned.

    Falls back to the first engine when all of them are decommissioned.
    """
    decommissioned = {name.lower() for name in decommissioned_engine_names or []}
    available = [name for name in engine_names if name.lower() not in decommissioned]
    return SEARCH_ENGINE_REGISTRY.default_config(available or engine_names)


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
    "BraveSearchConfig",
    "PerplexitySearch",
    "PerplexityConfig",
    "PerplexitySearchConfig",
    "get_search_engine_service",
    "SearchEngine",
    "SearchEngineDecommissionedError",
    "SEARCH_ENGINE_DECOMMISSIONED_MESSAGE",
    "is_search_engine_decommissioned",
    "get_search_engine_config_types_from_names",
    "get_default_search_engine_config",
    "VertexAIConfig",
    "VertexAI",
]
