"""OpenAPI HTTP SDK for the unique-search-proxy service.

The low-level client is **generated** under :mod:`unique_search_proxy_sdk._generated`
(``openapi-python-client``). :class:`UniqueSearchProxyClient` composes
:class:`SearchClient` and :class:`CrawlClient` for typed execution calls.

Config resolution and request/exposed-params model derivation live in
``unique_search_proxy_core`` (not in this SDK).

Regenerate after API changes::

    uv run poe generate-sdk
"""

from unique_search_proxy_sdk._generated.client import Client as OpenAPIClient
from unique_search_proxy_sdk.agent_search_client import AgentSearchClient
from unique_search_proxy_sdk.client import UniqueSearchProxyClient
from unique_search_proxy_sdk.crawl_client import CrawlClient
from unique_search_proxy_sdk.errors import UniqueSearchProxyClientError
from unique_search_proxy_sdk.search_client import SearchClient

__all__ = [
    "CrawlClient",
    "AgentSearchClient",
    "OpenAPIClient",
    "SearchClient",
    "UniqueSearchProxyClient",
    "UniqueSearchProxyClientError",
]
