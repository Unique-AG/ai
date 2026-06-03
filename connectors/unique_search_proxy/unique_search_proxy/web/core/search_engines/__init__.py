from unique_search_proxy.web.core.schema import SearchEngineRaw
from unique_search_proxy.web.core.search_engines.base import (
    BaseSearchEngineConfig,
    SearchEngine,
    SearchEngineMode,
    SearchEngineType,
    get_search_engine_mode,
)
from unique_search_proxy.web.core.search_engines.config_types import (
    ENGINE_NAME_TO_CONFIG,
    SearchEngineConfigTypes,
    get_search_engine_config_types_from_names,
    parse_search_engine_config,
)
from unique_search_proxy.web.core.search_engines.call_schema import (
    SearchCallSchemaDescriptor,
    resolve_search_call_schema,
)
from unique_search_proxy.web.core.search_engines.factory import (
    get_search_engine_service,
    resolve_engine_call,
)
from unique_search_proxy.web.core.search_engines.google.schema import GoogleConfig
from unique_search_proxy.web.core.search_engines.google.service import (
    GoogleSearchService,
)
from unique_search_proxy.web.core.search_engines.pagination import (
    DEFAULT_MAX_PAGE_SIZE,
    PageRequest,
    iter_page_requests,
)


def register_builtin_search_engines() -> None:
    from unique_search_proxy.web.core.registry import register_search_engine

    register_search_engine(
        SearchEngineType.GOOGLE.value,
        GoogleSearchService,
        config_model=GoogleConfig,
    )


__all__ = [
    "BaseSearchEngineConfig",
    "ENGINE_NAME_TO_CONFIG",
    "GoogleConfig",
    "GoogleSearchService",
    "SearchEngine",
    "SearchEngineConfigTypes",
    "SearchEngineMode",
    "SearchEngineType",
    "get_search_engine_config_types_from_names",
    "get_search_engine_mode",
    "get_search_engine_service",
    "iter_page_requests",
    "PageRequest",
    "parse_search_engine_config",
    "register_builtin_search_engines",
    "resolve_engine_call",
    "resolve_search_call_schema",
    "SearchCallSchemaDescriptor",
    "SearchEngineRaw",
    "DEFAULT_MAX_PAGE_SIZE",
]
