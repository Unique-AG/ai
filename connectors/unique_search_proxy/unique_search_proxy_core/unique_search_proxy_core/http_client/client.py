"""Build and cache httpx clients keyed by proxy credentials."""

from __future__ import annotations

import asyncio
import logging
from collections import OrderedDict
from collections.abc import Mapping
from dataclasses import dataclass
from functools import partial

import httpx
from httpx import AsyncClient
from unique_search_proxy_core.context import RequestContext
from unique_search_proxy_core.http_client.credentials import (
    ProxyCredentials,
    ProxyCredentialResolver,
    SettingsProxyCredentials,
    resolver_from_settings,
)
from unique_search_proxy_core.http_client.secrets import read_secret_mapping
from unique_search_proxy_core.http_client.settings import (
    ProxyAuthMode,
    ProxySettings,
)

_LOGGER = logging.getLogger(__name__)


@dataclass(frozen=True)
class DirectRoute:
    """Leave the cluster without a forward proxy."""

    verify: bool | str
    trust_env: bool
    headers: Mapping[str, str]


@dataclass(frozen=True)
class ProxiedRoute:
    """Leave the cluster through a forward proxy."""

    proxy: httpx.Proxy
    verify: bool | str
    headers: Mapping[str, str]
    cert: tuple[str, str] | str | None
    trust_env: bool = False


EgressRoute = DirectRoute | ProxiedRoute


def _get_proxy_host_and_port(settings: ProxySettings) -> tuple[str, int]:
    proxy_host = settings.proxy_host
    proxy_port = settings.proxy_port
    if proxy_host is None or proxy_port is None:
        raise ValueError("Proxy host and port are required")
    return proxy_host, proxy_port


def _proxy_url(settings: ProxySettings) -> str:
    proxy_host, proxy_port = _get_proxy_host_and_port(settings)
    return f"{settings.proxy_protocol}://{proxy_host}:{proxy_port}"


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


def _proxy_headers(settings: ProxySettings) -> dict[str, str]:
    return read_secret_mapping(settings.proxy_headers)


def _build_httpx_proxy(
    settings: ProxySettings,
    credentials: ProxyCredentials,
) -> httpx.Proxy:
    """Describe the proxy hop. Credentials stay on ``auth``, never in the URL."""
    if credentials.is_anonymous:
        return httpx.Proxy(url=_proxy_url(settings))
    return httpx.Proxy(
        url=_proxy_url(settings),
        auth=(credentials.username, credentials.password),
    )


def build_route(
    settings: ProxySettings,
    credentials: ProxyCredentials,
) -> EgressRoute:
    """Turn settings and credentials into a concrete egress route."""
    auth_mode: ProxyAuthMode = settings.proxy_auth_mode
    headers = _proxy_headers(settings)
    match auth_mode:
        case "none":
            if credentials.is_anonymous:
                _LOGGER.info("Proxy auth mode: none. Using no proxy")
                return DirectRoute(verify=True, trust_env=True, headers={})
            _LOGGER.info(
                "Proxy auth mode: none with request credentials. "
                "Using proxy with per-request username",
            )
            return ProxiedRoute(
                proxy=_build_httpx_proxy(settings, credentials),
                verify=settings.proxy_ssl_ca_bundle_path or True,
                headers=headers,
                cert=None,
            )
        case "username_password":
            _LOGGER.info(
                "Proxy auth mode: username_password. Using proxy with username "
                "and password",
            )
            return ProxiedRoute(
                proxy=_build_httpx_proxy(settings, credentials),
                verify=settings.proxy_ssl_ca_bundle_path or True,
                headers=headers,
                cert=None,
            )
        case "ssl_tls":
            _LOGGER.info("Proxy auth mode: ssl_tls. Using proxy with SSL/TLS")
            return ProxiedRoute(
                proxy=_build_httpx_proxy(settings, credentials),
                verify=settings.proxy_ssl_ca_bundle_path or True,
                headers=headers,
                cert=_get_cert_args(settings),
            )
        case _:
            raise ValueError(f"Invalid proxy auth mode: {auth_mode}")


def build_async_client(
    settings: ProxySettings,
    credentials: ProxyCredentials,
    *,
    timeout: float,
) -> AsyncClient:
    """Build an httpx client for one credential set."""
    route = build_route(settings, credentials)
    limits = httpx.Limits(
        max_connections=settings.max_connections,
        max_keepalive_connections=settings.max_keepalive_connections,
    )
    match route:
        case DirectRoute():
            return AsyncClient(
                headers=dict(route.headers) or None,
                verify=route.verify,
                trust_env=route.trust_env,
                timeout=timeout,
                limits=limits,
            )
        case ProxiedRoute():
            return AsyncClient(
                proxy=route.proxy,
                headers=dict(route.headers) or None,
                verify=route.verify,
                trust_env=route.trust_env,
                cert=route.cert,
                timeout=timeout,
                limits=limits,
            )


def async_client_factory(
    settings: ProxySettings,
    *,
    timeout: float | None = None,
) -> partial[AsyncClient]:
    """Factory for short-lived clients with the shared settings credentials."""
    resolver = resolver_from_settings(settings)
    credentials = resolver.resolve(
        RequestContext(company_id="local", user_id="local", chat_id="local"),
    )
    effective_timeout = timeout or settings.pool_timeout_seconds
    route = build_route(settings, credentials)
    match route:
        case DirectRoute():
            return partial(
                AsyncClient,
                headers=dict(route.headers) or None,
                verify=route.verify,
                trust_env=route.trust_env,
                timeout=effective_timeout,
            )
        case ProxiedRoute():
            return partial(
                AsyncClient,
                proxy=route.proxy,
                headers=dict(route.headers) or None,
                verify=route.verify,
                trust_env=route.trust_env,
                cert=route.cert,
                timeout=effective_timeout,
            )


class HttpClientRegistry:
    """Bounded LRU of httpx clients keyed by proxy credentials.

    Settings mode holds one long-lived client. User-metadata mode holds one
    client per username so CONNECT tunnels never cross users. The settings
    fallback entry is pinned lazily (never resolved at construction) and never
    evicted once known.
    """

    def __init__(
        self,
        settings: ProxySettings,
        resolver: ProxyCredentialResolver,
        *,
        fixed_client: AsyncClient | None = None,
    ) -> None:
        self._settings = settings
        self._resolver = resolver
        self._fixed_client = fixed_client
        self._clients: OrderedDict[ProxyCredentials, AsyncClient] = OrderedDict()
        self._pinned: ProxyCredentials | None = None
        self._pin_resolved = False
        self._lock = asyncio.Lock()
        self._closed = False

    def _ensure_pinned_credentials(self) -> ProxyCredentials | None:
        """Resolve settings credentials once for eviction protection.

        Skipped entirely when settings cannot produce an identity (typical
        user_metadata deployments with no technical username).
        """
        if self._pin_resolved:
            return self._pinned
        self._pin_resolved = True
        try:
            self._pinned = SettingsProxyCredentials(self._settings).resolve(
                RequestContext(
                    company_id="__pin__",
                    user_id="local",
                    chat_id="local",
                ),
            )
        except ValidationProxyError:
            self._pinned = None
        return self._pinned

    @classmethod
    def fixed(cls, client: AsyncClient) -> HttpClientRegistry:
        """Test helper: always return the same client regardless of credentials."""
        return cls(
            settings=ProxySettings(),
            resolver=resolver_from_settings(ProxySettings()),
            fixed_client=client,
        )

    async def client_for(self, context: RequestContext) -> AsyncClient:
        """Return the cached client for the request's resolved credentials."""
        if self._fixed_client is not None:
            return self._fixed_client
        if self._closed:
            raise RuntimeError("HTTP client registry is closed")

        credentials = self._resolver.resolve(context)
        evicted: AsyncClient | None = None
        async with self._lock:
            cached = self._clients.get(credentials)
            if cached is not None:
                self._clients.move_to_end(credentials)
                return cached

            client = build_async_client(
                self._settings,
                credentials,
                timeout=self._settings.pool_timeout_seconds,
            )
            self._clients[credentials] = client

            pinned = self._ensure_pinned_credentials()
            while len(self._clients) > self._settings.http_client_cache_size:
                for key in list(self._clients.keys()):
                    # Never evict the settings fallback or the client we just
                    # inserted (avoids returning a closed httpx client).
                    if key == pinned or key == credentials:
                        continue
                    evicted = self._clients.pop(key)
                    break
                else:
                    break

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
    "async_client_factory",
    "build_async_client",
    "build_route",
]
