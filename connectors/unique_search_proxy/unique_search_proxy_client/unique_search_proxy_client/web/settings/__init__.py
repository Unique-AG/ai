"""Shared settings helpers and package-level exports."""

from unique_search_proxy_client.web.settings.client import (
    HTTP_CLIENT_ENV_PREFIX,
    HttpClientSettings,
    ProxyAuthMode,
    ProxyProtocol,
    ProxyUsernameSource,
    get_http_client_settings,
    http_client_settings,
)

__all__ = [
    "HTTP_CLIENT_ENV_PREFIX",
    "HttpClientSettings",
    "ProxyAuthMode",
    "ProxyProtocol",
    "ProxyUsernameSource",
    "get_http_client_settings",
    "http_client_settings",
]
