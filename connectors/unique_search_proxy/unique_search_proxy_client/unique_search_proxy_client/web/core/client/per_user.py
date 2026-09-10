"""Bounded HTTP client cache for per-user corporate proxy authentication."""

from __future__ import annotations

import asyncio
from collections import OrderedDict
from typing import TYPE_CHECKING

import httpx
from unique_search_proxy_core.context import RequestContext
from unique_search_proxy_core.errors import ValidationProxyError

from unique_search_proxy_client.web.core.client.service import (
    build_per_user_async_client,
)
from unique_search_proxy_client.web.settings.client import (
    HttpClientSettings,
    http_client_settings,
)

if TYPE_CHECKING:
    from fastapi import FastAPI

ClientKey = tuple[str, str]


class PerUserProxyClientCache:
    """Own a bounded LRU of proxy clients keyed by company and external user."""

    def __init__(self, settings: HttpClientSettings | None = None) -> None:
        self._settings = settings or http_client_settings
        self._clients: OrderedDict[ClientKey, httpx.AsyncClient] = OrderedDict()
        self._lock = asyncio.Lock()
        self._validate_configuration()

    def _validate_configuration(self) -> None:
        if not self._settings.per_user_proxy_company_ids:
            return
        if self._settings.proxy_host is None or self._settings.proxy_port is None:
            raise ValueError(
                "Proxy host and port must be configured when per-user proxy "
                "authentication is enabled"
            )
        if self._settings.per_user_proxy_password is None:
            raise ValueError(
                "Per-user proxy password must be configured when per-user proxy "
                "authentication is enabled"
            )

    def enabled_for(self, company_id: str) -> bool:
        """Return whether this cache must serve crawl egress for a company."""
        return self._settings.per_user_proxy_enabled_for(company_id)

    async def get_client(self, context: RequestContext) -> httpx.AsyncClient:
        """Return the user's cached client or create one, failing on no identity."""
        if not self.enabled_for(context.company_id):
            raise RuntimeError(
                "Per-user proxy client requested for a company without per-user "
                "proxy authentication"
            )

        raw_external_user_id = context.external_user_id
        if raw_external_user_id is None or not raw_external_user_id.strip():
            raise ValidationProxyError(
                "External user ID is required for per-user proxy authentication"
            )
        external_user_id = raw_external_user_id.strip()

        key = (context.company_id, external_user_id)
        evicted: httpx.AsyncClient | None = None
        async with self._lock:
            cached = self._clients.get(key)
            if cached is not None:
                self._clients.move_to_end(key)
                return cached

            client = build_per_user_async_client(
                external_user_id,
                settings=self._settings,
            )
            self._clients[key] = client
            if len(self._clients) > self._settings.per_user_proxy_client_cache_size:
                _key, evicted = self._clients.popitem(last=False)

        if evicted is not None:
            await evicted.aclose()
        return client

    async def aclose(self) -> None:
        """Close and remove all cached clients."""
        async with self._lock:
            clients = list(self._clients.values())
            self._clients.clear()
        await asyncio.gather(*(client.aclose() for client in clients))

    @property
    def size(self) -> int:
        """Return the number of cached clients."""
        return len(self._clients)


def create_per_user_proxy_client_cache() -> PerUserProxyClientCache:
    """Create the application-owned per-user proxy client cache."""
    return PerUserProxyClientCache()


def get_per_user_proxy_client_cache(app: FastAPI) -> PerUserProxyClientCache:
    """Return the initialized application-owned per-user proxy client cache."""
    cache = getattr(app.state, "per_user_proxy_client_cache", None)
    if cache is None:
        raise RuntimeError("Per-user proxy client cache is not initialized")
    return cache


__all__ = [
    "PerUserProxyClientCache",
    "create_per_user_proxy_client_cache",
    "get_per_user_proxy_client_cache",
]
