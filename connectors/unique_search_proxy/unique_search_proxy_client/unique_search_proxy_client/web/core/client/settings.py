from typing import Literal

from pydantic import BaseModel
from pydantic_settings import BaseSettings

from unique_search_proxy_client.web.settings.base import is_test_runtime, settings_config

HTTP_CLIENT_ENV_PREFIX = "HTTP_CLIENT_"

ProxyAuthMode = Literal["none", "username_password", "ssl_tls"]
ProxyProtocol = Literal["http", "https"]


class ProxyConfig(BaseModel):
    verify: bool | str
    proxy: str | None
    headers: dict[str, str] | None
    cert: tuple[str, str] | str | None = None
    trust_env: bool = False


class HttpClientSettings(BaseSettings):
    """Outbound HTTP client: corporate proxy and connection pool limits.

    Environment variables use the ``HTTP_CLIENT_`` prefix, e.g.
    ``HTTP_CLIENT_PROXY_HOST``, ``HTTP_CLIENT_POOL_TIMEOUT_SECONDS``.
    """

    model_config = settings_config(env_prefix=HTTP_CLIENT_ENV_PREFIX)

    proxy_auth_mode: ProxyAuthMode = "none"
    proxy_protocol: ProxyProtocol = "http"
    proxy_host: str | None = None
    proxy_port: int | None = None
    proxy_headers: dict[str, str] = {}
    proxy_ssl_ca_bundle_path: str | None = None
    proxy_username: str | None = None
    proxy_password: str | None = None
    proxy_ssl_cert_path: str | None = None
    proxy_ssl_key_path: str | None = None

    pool_timeout_seconds: float = 30.0
    max_connections: int = 100
    max_keepalive_connections: int = 20


class HttpClientSettingsForTests(HttpClientSettings):
    model_config = settings_config(env_prefix=HTTP_CLIENT_ENV_PREFIX, test=True)


def get_http_client_settings() -> HttpClientSettings:
    if is_test_runtime():
        return HttpClientSettingsForTests()
    return HttpClientSettings()


http_client_settings: HttpClientSettings = get_http_client_settings()
