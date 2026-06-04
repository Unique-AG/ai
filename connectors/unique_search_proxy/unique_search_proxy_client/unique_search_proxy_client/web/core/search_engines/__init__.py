from unique_search_proxy_core.search_engines.base import SearchEngineType
from unique_search_proxy_core.search_engines.google.schema import GoogleConfig

from unique_search_proxy_client.web.core.search_engines.descriptor import (
    SearchEngineDescriptor,
)
from unique_search_proxy_client.web.core.search_engines.factory import (
    get_request_model_for_engine,
    get_search_engine_service,
    resolve_engine_call,
    resolve_engine_request,
)
from unique_search_proxy_client.web.core.search_engines.google.service import (
    GoogleSearchService,
)


def register_builtin_search_engines() -> None:
    from unique_search_proxy_client.web.core.registry import register_search_engine

    register_search_engine(
        SearchEngineType.GOOGLE.value,
        GoogleSearchService,
        descriptor=SearchEngineDescriptor(
            config_model=GoogleConfig,
            service_cls=GoogleSearchService,
        ),
    )


__all__ = [
    "GoogleConfig",
    "GoogleSearchService",
    "SearchEngineDescriptor",
    "SearchEngineType",
    "get_request_model_for_engine",
    "get_search_engine_service",
    "register_builtin_search_engines",
    "resolve_engine_call",
    "resolve_engine_request",
]
