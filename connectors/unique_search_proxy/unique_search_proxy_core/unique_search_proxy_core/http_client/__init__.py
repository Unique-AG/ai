"""Shared outbound HTTP client: proxy settings, credentials, and registry."""

from unique_search_proxy_core.http_client.client import (
    DirectRoute,
    EgressRoute,
    HttpClientRegistry,
    ProxiedRoute,
    ResolvedEgress,
    async_client_factory,
    build_async_client,
    build_route,
)
from unique_search_proxy_core.http_client.credentials import (
    ProxyCredentialResolver,
    ProxyCredentials,
    SettingsProxyCredentials,
    UserMetadataProxyCredentials,
    resolver_from_settings,
)
from unique_search_proxy_core.http_client.response_cap import (
    MAX_RESPONSE_BYTES_EXTENSION,
    ByteBudget,
    install_response_size_cap,
    read_capped_body,
    response_size_cap_hook,
)
from unique_search_proxy_core.http_client.secrets import (
    read_secret,
    read_secret_mapping,
)
from unique_search_proxy_core.http_client.settings import (
    ProxyAuthMode,
    ProxyProtocol,
    ProxySettings,
    ProxyUsernameSource,
)

__all__ = [
    "MAX_RESPONSE_BYTES_EXTENSION",
    "ByteBudget",
    "DirectRoute",
    "EgressRoute",
    "HttpClientRegistry",
    "ProxiedRoute",
    "ProxyAuthMode",
    "ProxyCredentials",
    "ProxyCredentialResolver",
    "ProxyProtocol",
    "ProxySettings",
    "ProxyUsernameSource",
    "ResolvedEgress",
    "SettingsProxyCredentials",
    "UserMetadataProxyCredentials",
    "async_client_factory",
    "build_async_client",
    "build_route",
    "install_response_size_cap",
    "read_capped_body",
    "read_secret",
    "read_secret_mapping",
    "resolver_from_settings",
    "response_size_cap_hook",
]
