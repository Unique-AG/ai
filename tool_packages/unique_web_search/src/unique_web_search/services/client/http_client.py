"""Process-wide HTTP client registry for the web-search tool's direct egress path.

Clients are created lazily on first use via ``client_for`` / the registry — never
at import time — so a process can load before any proxy identity is resolvable.
"""

from __future__ import annotations

from httpx import AsyncClient
from pydantic import SecretStr
from unique_search_proxy_core.context import RequestContext
from unique_search_proxy_core.http_client import (
    HttpClientRegistry,
    ProxySettings,
)

from unique_web_search.settings import env_settings

_registry: HttpClientRegistry | None = None


def proxy_settings_from_env() -> ProxySettings:
    """Build core ProxySettings from the tool's process env settings."""
    return ProxySettings(
        proxy_auth_mode=env_settings.proxy_auth_mode,
        proxy_protocol=env_settings.proxy_protocol,
        proxy_host=env_settings.proxy_host,
        proxy_port=env_settings.proxy_port,
        proxy_headers={
            name: SecretStr(value) for name, value in env_settings.proxy_headers.items()
        },
        proxy_ssl_ca_bundle_path=env_settings.proxy_ssl_ca_bundle_path,
        proxy_username=(
            SecretStr(env_settings.proxy_username)
            if env_settings.proxy_username is not None
            else None
        ),
        proxy_password=SecretStr(env_settings.proxy_password or ""),
        proxy_ssl_cert_path=env_settings.proxy_ssl_cert_path,
        proxy_ssl_key_path=env_settings.proxy_ssl_key_path,
        proxy_user_id_header=env_settings.proxy_user_id_header,
        proxy_user_id_metadata_field=env_settings.proxy_user_id_metadata_field,
        http_client_cache_size=env_settings.http_client_cache_size,
    )


def get_http_client_registry() -> HttpClientRegistry:
    """Return the process-wide registry for direct (non-proxy-service) egress."""
    global _registry
    if _registry is None:
        _registry = HttpClientRegistry(settings=proxy_settings_from_env())
    return _registry


async def client_for(context: RequestContext) -> AsyncClient:
    """Resolve the egress client for a request context."""
    return await get_http_client_registry().client_for(context)


__all__ = [
    "client_for",
    "get_http_client_registry",
    "proxy_settings_from_env",
]
