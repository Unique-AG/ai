"""Build and cache httpx clients keyed by proxy identity."""

from __future__ import annotations

import asyncio
import logging
from collections import OrderedDict
from dataclasses import dataclass

import httpx
from httpx import AsyncClient

from unique_search_proxy_core.context import RequestContext
from unique_search_proxy_core.http_client.credentials import (
    ProxyIdentity,
    resolve_identity,
)
from unique_search_proxy_core.http_client.secrets import read_secret_mapping
from unique_search_proxy_core.http_client.settings import ProxySettings

_LOGGER = logging.getLogger(__name__)


@dataclass(frozen=True)
class DirectRoute:
    """Leave the cluster without a forward proxy."""

    verify: bool | str
    trust_env: bool


@dataclass(frozen=True)
class ProxiedRoute:
    """Leave the cluster through a forward proxy.

    Everything addressed to the proxy — credentials and headers alike — lives on
    ``proxy``, so nothing intended for the proxy can leak onto target requests.
    """

    proxy: httpx.Proxy
    verify: bool | str
    cert: tuple[str, str] | str | None
    trust_env: bool = False


EgressRoute = DirectRoute | ProxiedRoute


def _proxy_url(settings: ProxySettings) -> str:
    return f"{settings.proxy_protocol}://{settings.proxy_host}:{settings.proxy_port}"


def _get_cert_args(settings: ProxySettings) -> tuple[str, str] | str:
    proxy_ssl_cert_path = settings.proxy_ssl_cert_path
    if proxy_ssl_cert_path is None:
        raise ValueError("Proxy SSL cert path is required")

    proxy_ssl_key_path = settings.proxy_ssl_key_path
    if proxy_ssl_key_path is None:
        _LOGGER.warning(
            "Proxy SSL key path is not set. Assuming cert path includes key path"
        )
        return proxy_ssl_cert_path
    return proxy_ssl_cert_path, proxy_ssl_key_path


def _connect_headers(
    settings: ProxySettings,
    identity: ProxyIdentity,
) -> dict[str, str]:
    """Headers addressed to the proxy, not to the target.

    For ``https://`` targets these ride the ``CONNECT`` and stop at the proxy.
    For plain ``http://`` targets a forward proxy is itself the recipient, so
    httpx puts them on the absolute-form request; a conforming proxy strips
    ``Proxy-Authorization`` but will relay end-to-end fields such as the UID
    header to the origin. Every search engine is https, so this only matters
    when crawling a plain-http page.
    """
    headers = read_secret_mapping(settings.proxy_headers)
    if settings.proxy_user_id_header and identity.end_user_id:
        # Applied last so a per-request UID wins over a static header of the
        # same name.
        headers[settings.proxy_user_id_header] = identity.end_user_id
    return headers


def _build_httpx_proxy(
    settings: ProxySettings,
    identity: ProxyIdentity,
) -> httpx.Proxy:
    """Describe the proxy hop. Credentials stay on ``auth``, never in the URL."""
    return httpx.Proxy(
        url=_proxy_url(settings),
        auth=None if identity.is_anonymous else (identity.username, identity.password),
        headers=_connect_headers(settings, identity) or None,
    )


def build_route(
    settings: ProxySettings,
    identity: ProxyIdentity,
) -> EgressRoute:
    """Turn settings and identity into a concrete egress route.

    Whether a proxy is used at all follows from ``proxy_host``/``proxy_port``;
    ``proxy_auth_mode`` only decides how we authenticate to it.
    """
    if not settings.proxy_configured:
        _LOGGER.info("No proxy host configured. Using direct egress")
        return DirectRoute(verify=True, trust_env=True)

    _LOGGER.info("Proxy auth mode: %s. Using proxy", settings.proxy_auth_mode)
    is_mutual_tls = settings.proxy_auth_mode == "ssl_tls"
    return ProxiedRoute(
        proxy=_build_httpx_proxy(settings, identity),
        verify=settings.proxy_ssl_ca_bundle_path or True,
        cert=_get_cert_args(settings) if is_mutual_tls else None,
    )


def build_async_client(
    settings: ProxySettings,
    identity: ProxyIdentity,
    *,
    timeout: float,
) -> AsyncClient:
    """Build an httpx client for one proxy identity."""
    route = build_route(settings, identity)
    limits = httpx.Limits(
        max_connections=settings.max_connections,
        max_keepalive_connections=settings.max_keepalive_connections,
    )
    match route:
        case DirectRoute():
            return AsyncClient(
                verify=route.verify,
                trust_env=route.trust_env,
                timeout=timeout,
                limits=limits,
            )
        case ProxiedRoute():
            return AsyncClient(
                proxy=route.proxy,
                verify=route.verify,
                trust_env=route.trust_env,
                cert=route.cert,
                timeout=timeout,
                limits=limits,
            )


class HttpClientRegistry:
    """Bounded LRU of httpx clients keyed by proxy identity.

    The key includes the end-user ID, not just the credentials. With a single
    service account every user resolves to identical credentials, so keying on
    credentials alone would hand every user a pooled connection carrying the
    first user's UID header.
    """

    def __init__(
        self,
        settings: ProxySettings,
        *,
        fixed_client: AsyncClient | None = None,
    ) -> None:
        self._settings = settings
        self._fixed_client = fixed_client
        self._clients: OrderedDict[ProxyIdentity, AsyncClient] = OrderedDict()
        self._lock = asyncio.Lock()
        self._closed = False

    @classmethod
    def fixed(cls, client: AsyncClient) -> HttpClientRegistry:
        """Test helper: always return the same client regardless of identity."""
        return cls(settings=ProxySettings(), fixed_client=client)

    async def client_for(self, context: RequestContext) -> AsyncClient:
        """Return the cached client for the request's resolved identity."""
        if self._fixed_client is not None:
            return self._fixed_client
        if self._closed:
            raise RuntimeError("HTTP client registry is closed")

        identity = resolve_identity(self._settings, context)
        evicted: AsyncClient | None = None
        async with self._lock:
            cached = self._clients.get(identity)
            if cached is not None:
                self._clients.move_to_end(identity)
                return cached

            client = build_async_client(
                self._settings,
                identity,
                timeout=self._settings.pool_timeout_seconds,
            )
            self._clients[identity] = client

            if len(self._clients) > self._settings.http_client_cache_size:
                # Never evict the client just inserted, or callers would receive
                # a closed httpx client.
                _key, evicted = self._clients.popitem(last=False)

        if evicted is not None:
            await evicted.aclose()
        return client

    @property
    def is_open(self) -> bool:
        """Whether the registry can still serve clients."""
        if self._fixed_client is not None:
            return not self._fixed_client.is_closed
        return not self._closed

    @property
    def size(self) -> int:
        """Number of cached clients."""
        if self._fixed_client is not None:
            return 1
        return len(self._clients)

    async def aclose(self) -> None:
        """Close and drop every cached client."""
        if self._fixed_client is not None:
            await self._fixed_client.aclose()
            self._closed = True
            return
        async with self._lock:
            clients = list(self._clients.values())
            self._clients.clear()
            self._closed = True
        await asyncio.gather(*(client.aclose() for client in clients))


__all__ = [
    "DirectRoute",
    "EgressRoute",
    "HttpClientRegistry",
    "ProxiedRoute",
    "build_async_client",
    "build_route",
]
