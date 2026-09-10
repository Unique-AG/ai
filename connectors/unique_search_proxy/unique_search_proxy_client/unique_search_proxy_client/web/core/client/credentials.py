"""Credential resolvers — re-exported from unique_search_proxy_core."""

from unique_search_proxy_core.http_client import (
    ProxyCredentialResolver,
    ProxyCredentials,
    SettingsProxyCredentials,
    UserMetadataProxyCredentials,
)
from unique_search_proxy_core.http_client import (
    resolver_from_settings as _resolver_from_settings,
)

from unique_search_proxy_client.web.settings.client import (
    HttpClientSettings,
    http_client_settings,
)


def resolver_from_settings(
    settings: HttpClientSettings | None = None,
) -> ProxyCredentialResolver:
    """Pick the credential resolver configured on the settings."""
    return _resolver_from_settings(settings or http_client_settings)


__all__ = [
    "ProxyCredentials",
    "ProxyCredentialResolver",
    "SettingsProxyCredentials",
    "UserMetadataProxyCredentials",
    "resolver_from_settings",
]
