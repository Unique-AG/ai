"""Application-owned HTTP client registry around unique_search_proxy_core."""

from __future__ import annotations

from typing import TYPE_CHECKING

from httpx import AsyncClient
from unique_search_proxy_core.http_client import (
    DirectRoute,
    EgressRoute,
    HttpClientRegistry,
    ProxiedRoute,
    ProxyIdentity,
)
from unique_search_proxy_core.http_client import (
    build_async_client as _build_async_client,
)
from unique_search_proxy_core.http_client import (
    build_route as _build_route,
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
    identity: ProxyIdentity,
) -> EgressRoute:
    return _build_route(settings, identity)


def build_async_client(
    settings: HttpClientSettings,
    identity: ProxyIdentity,
    *,
    timeout: float,
) -> AsyncClient:
    return _build_async_client(settings, identity, timeout=timeout)


async def create_http_client_registry() -> HttpClientRegistry:
    """Create the application-owned HTTP client registry."""
    return HttpClientRegistry(settings=_settings())


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
    "build_async_client",
    "build_route",
    "create_http_client_pool",
    "create_http_client_registry",
    "get_http_client_pool",
    "get_http_client_registry",
]
