"""Application-owned HTTP client registry around unique_search_proxy_core."""

from __future__ import annotations

from functools import partial
from typing import TYPE_CHECKING

from httpx import AsyncClient
from unique_search_proxy_core.http_client import (
    DirectRoute,
    EgressRoute,
    HttpClientRegistry,
    ProxiedRoute,
    resolver_from_settings,
)
from unique_search_proxy_core.http_client import (
    async_client_factory as _async_client_factory,
)
from unique_search_proxy_core.http_client import (
    build_async_client as _build_async_client,
)
from unique_search_proxy_core.http_client import (
    build_route as _build_route,
)
from unique_search_proxy_core.http_client.credentials import ProxyCredentials

from unique_search_proxy_client.web.core.client.credentials import (
    resolver_from_settings as client_resolver_from_settings,
)
from unique_search_proxy_client.web.settings.client import (
    HttpClientSettings,
    http_client_settings,
)

if TYPE_CHECKING:
    from fastapi import FastAPI


def _settings() -> HttpClientSettings:
    return http_client_settings


def build_route(
    settings: HttpClientSettings,
    credentials: ProxyCredentials,
) -> EgressRoute:
    return _build_route(settings, credentials)


def build_async_client(
    settings: HttpClientSettings,
    credentials: ProxyCredentials,
    *,
    timeout: float,
) -> AsyncClient:
    return _build_async_client(settings, credentials, timeout=timeout)


def async_client_factory(
    *,
    settings: HttpClientSettings | None = None,
    timeout: float | None = None,
) -> partial[AsyncClient]:
    return _async_client_factory(settings or _settings(), timeout=timeout)


async def create_http_client_registry() -> HttpClientRegistry:
    """Create the application-owned HTTP client registry."""
    settings = _settings()
    return HttpClientRegistry(
        settings=settings,
        resolver=client_resolver_from_settings(settings),
    )


def get_http_client_registry(app: FastAPI) -> HttpClientRegistry:
    """Return the initialized application-owned HTTP client registry."""
    registry = getattr(app.state, "http_client_registry", None)
    if registry is None:
        raise RuntimeError("HTTP client registry is not initialized")
    return registry


# Compatibility aliases for fixtures and callers still named around the pool.
HttpClientPool = HttpClientRegistry
create_http_client_pool = create_http_client_registry
get_http_client_pool = get_http_client_registry


__all__ = [
    "DirectRoute",
    "EgressRoute",
    "HttpClientPool",
    "HttpClientRegistry",
    "ProxiedRoute",
    "async_client_factory",
    "build_async_client",
    "build_route",
    "create_http_client_pool",
    "create_http_client_registry",
    "get_http_client_pool",
    "get_http_client_registry",
    "resolver_from_settings",
]
