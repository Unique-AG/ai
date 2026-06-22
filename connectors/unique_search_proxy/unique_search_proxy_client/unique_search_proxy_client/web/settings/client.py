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
    egress=None,
    env_prefix=HTTP_CLIENT_ENV_PREFIX,
    sections={
        "tuning": [
            "pool_timeout_seconds",
            "max_connections",
            "max_keepalive_connections",
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
    proxy_ssl_cert_path: str | None = None
    proxy_ssl_key_path: str | None = None

    pool_timeout_seconds: float = 30.0
    max_connections: int = 100
    max_keepalive_connections: int = 20


def get_http_client_settings() -> HttpClientSettings:
    return get_settings(HttpClientSettings, env_prefix=HTTP_CLIENT_ENV_PREFIX)


http_client_settings: HttpClientSettings = get_http_client_settings()
