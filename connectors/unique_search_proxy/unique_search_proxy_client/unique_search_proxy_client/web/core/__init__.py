from unique_search_proxy_core.schema import WebSearchResult

from unique_search_proxy_client.web.core.registry import (
    get_crawler,
    get_search_engine,
    register_crawler,
    register_search_engine,
    registered_crawlers,
    registered_search_engines,
)

__all__ = [
    "WebSearchResult",
    "get_crawler",
    "get_search_engine",
    "register_crawler",
    "register_search_engine",
    "registered_crawlers",
    "registered_search_engines",
]
