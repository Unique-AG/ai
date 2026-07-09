from unique_search_proxy_core.search_engines.base import SearchEngineType
from unique_search_proxy_core.search_engines.brave.schema import BraveConfig
from unique_search_proxy_core.search_engines.google.schema import GoogleConfig
from unique_search_proxy_core.search_engines.perplexity.schema import PerplexityConfig

from unique_search_proxy_client.web.core.search_engines.brave.service import (
    BraveSearchService,
)
from unique_search_proxy_client.web.core.search_engines.descriptor import (
    SearchEngineDescriptor,
)
from unique_search_proxy_client.web.core.search_engines.factory import (
    get_search_engine_service,
)
from unique_search_proxy_client.web.core.search_engines.google.service import (
    GoogleSearchService,
)
from unique_search_proxy_client.web.core.search_engines.perplexity.service import (
    PerplexitySearchService,
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
    register_search_engine(
        SearchEngineType.BRAVE.value,
        BraveSearchService,
        descriptor=SearchEngineDescriptor(
            config_model=BraveConfig,
            service_cls=BraveSearchService,
        ),
    )
    register_search_engine(
        SearchEngineType.PERPLEXITY.value,
        PerplexitySearchService,
        descriptor=SearchEngineDescriptor(
            config_model=PerplexityConfig,
            service_cls=PerplexitySearchService,
        ),
    )


__all__ = [
    "BraveConfig",
    "BraveSearchService",
    "GoogleConfig",
    "GoogleSearchService",
    "PerplexityConfig",
    "PerplexitySearchService",
    "SearchEngineDescriptor",
    "SearchEngineType",
    "get_search_engine_service",
    "register_builtin_search_engines",
]
