from typing import Literal

from pydantic import BaseModel, Field
from pydantic_settings import BaseSettings

from unique_search_proxy_client.web.helm.metadata import helm_settings
from unique_search_proxy_client.web.settings.base import get_settings
from unique_search_proxy_client.web.settings.secret_str import LogSecretStr

HTTP_CLIENT_ENV_PREFIX = "HTTP_CLIENT_"

ProxyAuthMode = Literal["none", "username_password", "ssl_tls"]
ProxyProtocol = Literal["http", "https"]


class ProxyConfig(BaseModel):
    verify: bool | str
    proxy: str | None
    headers: dict[str, str] | None
    cert: tuple[str, str] | str | None = None
    trust_env: bool = False


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
            "per_user_proxy_client_cache_size",
        ],
    },
)
class HttpClientSettings(BaseSettings):
    """Outbound HTTP client: corporate proxy and connection pool limits.

    Environment variables use the ``HTTP_CLIENT_`` prefix, e.g.
    ``HTTP_CLIENT_PROXY_HOST``, ``HTTP_CLIENT_POOL_TIMEOUT_SECONDS``.
    """

    proxy_auth_mode: ProxyAuthMode = "none"
    proxy_protocol: ProxyProtocol = "http"
    proxy_host: str | None = None
    proxy_port: int | None = None
    proxy_headers: dict[str, LogSecretStr] = Field(default_factory=dict)
    proxy_ssl_ca_bundle_path: str | None = None
    proxy_username: LogSecretStr | None = None
    proxy_password: LogSecretStr | None = None
    per_user_proxy_company_ids: list[str] = Field(
        default_factory=list,
        description=(
            "Company IDs whose crawl egress must authenticate to the proxy as "
            "the end user instead of the shared technical account."
        ),
        json_schema_extra={"helm": {"overridable": True}},
    )
    per_user_proxy_username_field: str = Field(
        default="userName",
        description=(
            "User-metadata field whose value becomes the proxy username. Must "
            "name a field the platform stamps after merging user configuration "
            "(userName, email); user-supplied keys are spoofable."
        ),
    )
    per_user_proxy_password: LogSecretStr | None = Field(
        default=None,
        description=(
            "Placeholder password paired with per-user proxy usernames. An "
            "explicit empty string is valid."
        ),
    )
    proxy_ssl_cert_path: str | None = None
    proxy_ssl_key_path: str | None = None

    pool_timeout_seconds: float = 30.0
    max_connections: int = 100
    max_keepalive_connections: int = 20
    per_user_proxy_client_cache_size: int = Field(default=128, ge=1)

    def per_user_proxy_enabled_for(self, company_id: str) -> bool:
        """Whether a company's crawl egress must authenticate as the end user."""
        return company_id in self.per_user_proxy_company_ids


def get_http_client_settings() -> HttpClientSettings:
    return get_settings(HttpClientSettings, env_prefix=HTTP_CLIENT_ENV_PREFIX)


http_client_settings: HttpClientSettings = get_http_client_settings()
