from unique_search_proxy.web.core.registry import (
    get_crawler,
    get_search_engine,
    register_crawler,
    register_search_engine,
    registered_crawlers,
    registered_search_engines,
)
from unique_search_proxy.web.core.schema import WebSearchResult

__all__ = [
    "WebSearchResult",
    "get_crawler",
    "get_search_engine",
    "register_crawler",
    "register_search_engine",
    "registered_crawlers",
    "registered_search_engines",
]
