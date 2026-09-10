from pydantic import Field
from pydantic_settings import SettingsConfigDict
from unique_search_proxy_core.http_client import (
    ProxyAuthMode,
    ProxyProtocol,
    ProxySettings,
    ProxyUsernameSource,
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
    """Outbound HTTP client settings under the ``HTTP_CLIENT_`` env prefix."""

    model_config = SettingsConfigDict(
        env_prefix=HTTP_CLIENT_ENV_PREFIX,
        extra="ignore",
    )

    proxy_username_source: ProxyUsernameSource = Field(
        default="settings",
        description=(
            "Where the proxy username comes from: fixed settings, or a field on "
            "the request's user metadata."
        ),
        json_schema_extra={"helm": {"overridable": True}},
    )
    per_user_proxy_company_ids: list[str] = Field(
        default_factory=list,
        description=(
            "Company IDs whose egress authenticates as the end user when "
            "proxy_username_source is user_metadata. Empty means every company."
        ),
        json_schema_extra={"helm": {"overridable": True}},
    )


def get_http_client_settings() -> HttpClientSettings:
    return get_settings(HttpClientSettings, env_prefix=HTTP_CLIENT_ENV_PREFIX)


http_client_settings: HttpClientSettings = get_http_client_settings()

__all__ = [
    "HTTP_CLIENT_ENV_PREFIX",
    "HttpClientSettings",
    "ProxyAuthMode",
    "ProxyProtocol",
    "ProxyUsernameSource",
    "get_http_client_settings",
    "http_client_settings",
]
