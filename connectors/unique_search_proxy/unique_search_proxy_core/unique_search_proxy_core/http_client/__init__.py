"""Shared outbound HTTP client: proxy settings, identity, and registry."""

from unique_search_proxy_core.http_client.client import (
    DirectRoute,
    EgressRoute,
    HttpClientRegistry,
    ProxiedRoute,
    build_async_client,
    build_route,
)
from unique_search_proxy_core.http_client.credentials import (
    ProxyIdentity,
    resolve_identity,
)
from unique_search_proxy_core.http_client.secrets import (
    read_secret,
    read_secret_mapping,
)
from unique_search_proxy_core.http_client.settings import (
    ProxyAuthMode,
    ProxyProtocol,
    ProxySettings,
)

__all__ = [
    "DirectRoute",
    "EgressRoute",
    "HttpClientRegistry",
    "ProxiedRoute",
    "ProxyAuthMode",
    "ProxyIdentity",
    "ProxyProtocol",
    "ProxySettings",
    "build_async_client",
    "build_route",
    "read_secret",
    "read_secret_mapping",
    "resolve_identity",
]
