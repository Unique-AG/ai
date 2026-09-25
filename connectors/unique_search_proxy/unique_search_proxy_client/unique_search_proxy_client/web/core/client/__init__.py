from unique_search_proxy_client.web.core.client.credentials import (
    ProxyIdentity,
    resolve_identity,
)
from unique_search_proxy_client.web.core.client.service import (
    DirectRoute,
    EgressRoute,
    HttpClientPool,
    HttpClientRegistry,
    ProxiedRoute,
    build_async_client,
    build_route,
    create_http_client_pool,
    create_http_client_registry,
    get_http_client_pool,
    get_http_client_registry,
)
from unique_search_proxy_client.web.settings.client import (
    HTTP_CLIENT_ENV_PREFIX,
    HttpClientSettings,
    ProxyAuthMode,
    ProxyProtocol,
    http_client_settings,
)

__all__ = [
    "DirectRoute",
    "EgressRoute",
    "HttpClientPool",
    "HttpClientRegistry",
    "HTTP_CLIENT_ENV_PREFIX",
    "HttpClientSettings",
    "ProxiedRoute",
    "ProxyAuthMode",
    "ProxyIdentity",
    "ProxyProtocol",
    "build_async_client",
    "build_route",
    "create_http_client_pool",
    "create_http_client_registry",
    "get_http_client_pool",
    "get_http_client_registry",
    "http_client_settings",
    "resolve_identity",
]
