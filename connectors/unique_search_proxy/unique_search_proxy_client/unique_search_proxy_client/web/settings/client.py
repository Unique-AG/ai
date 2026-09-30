from pydantic_settings import SettingsConfigDict
from unique_search_proxy_core.http_client import (
    ProxyAuthMode,
    ProxyProtocol,
    ProxySettings,
)

from unique_search_proxy_client.web.helm.metadata import helm_settings
from unique_search_proxy_client.web.settings.base import get_settings

HTTP_CLIENT_ENV_PREFIX = "HTTP_CLIENT_"


@helm_settings(
    title="HTTP Client",
    helm_key="httpClient",
    kind="httpClient",
    # Always-on client config: proxy behaviour is driven by proxy_auth_mode and
    # the proxy fields, not by a chart-only toggle. Gating it would silently drop
    # proxy config from overlays that set it without ``enabled: true``.
    gated=False,
    egress=None,
    env_prefix=HTTP_CLIENT_ENV_PREFIX,
    sections={
        "tuning": [
            "pool_timeout_seconds",
            "max_connections",
            "max_keepalive_connections",
            "http_client_cache_size",
        ],
    },
)
class HttpClientSettings(ProxySettings):
    """Outbound HTTP client settings under the ``HTTP_CLIENT_`` env prefix.

    Every proxy field is inherited. Scalars are exposed to the chart
    automatically, so nothing needs re-declaring here.
    """

    model_config = SettingsConfigDict(
        env_prefix=HTTP_CLIENT_ENV_PREFIX,
        extra="ignore",
    )


def get_http_client_settings() -> HttpClientSettings:
    return get_settings(HttpClientSettings, env_prefix=HTTP_CLIENT_ENV_PREFIX)


http_client_settings: HttpClientSettings = get_http_client_settings()

__all__ = [
    "HTTP_CLIENT_ENV_PREFIX",
    "HttpClientSettings",
    "ProxyAuthMode",
    "ProxyProtocol",
    "get_http_client_settings",
    "http_client_settings",
]
