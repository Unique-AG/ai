"""OpenAPI HTTP SDK for the unique-search-proxy service.

The low-level client is **generated** under :mod:`unique_search_proxy_sdk._generated`
(``openapi-python-client``). :class:`UniqueSearchProxyClient` is a thin facade with
proxy error mapping and Pydantic config conversion.

Regenerate after API changes::

    uv run poe generate-sdk
"""

from unique_search_proxy_sdk._generated.client import Client as OpenAPIClient
from unique_search_proxy_sdk.client import UniqueSearchProxyClient
from unique_search_proxy_sdk.errors import UniqueSearchProxyClientError

__all__ = [
    "OpenAPIClient",
    "UniqueSearchProxyClient",
    "UniqueSearchProxyClientError",
]
