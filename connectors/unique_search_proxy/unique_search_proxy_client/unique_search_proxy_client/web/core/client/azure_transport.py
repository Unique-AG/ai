"""Azure SDK transport configured from the shared egress route."""

from __future__ import annotations

from collections.abc import AsyncIterator, MutableMapping
from contextlib import asynccontextmanager
from ipaddress import ip_address
from typing import Any
from urllib.parse import urlsplit

import aiohttp
from azure.core.pipeline.transport import (
    AioHttpTransport,
    AsyncHttpResponse,
    AsyncHttpTransport,
    HttpRequest,
)
from azure.core.rest import (
    AsyncHttpResponse as RestAsyncHttpResponse,
)
from azure.core.rest import (
    HttpRequest as RestHttpRequest,
)
from unique_search_proxy_core.http_client import EgressRoute, ProxiedRoute


def _client_certificate(
    route: EgressRoute,
) -> tuple[str, ...] | None:
    if not isinstance(route, ProxiedRoute) or route.cert is None:
        return None
    if isinstance(route.cert, str):
        return (route.cert,)
    return route.cert


def _proxy_headers(route: EgressRoute) -> dict[str, str] | None:
    if not isinstance(route, ProxiedRoute):
        return None
    headers = dict(route.headers)

    # aiohttp promotes Authorization from proxy_headers to Proxy-Authorization
    # for both absolute-form HTTP requests and HTTPS CONNECT requests.
    for name in list(headers):
        if name.lower() == "proxy-authorization":
            headers["Authorization"] = headers.pop(name)
            break
    if route.proxy.auth is not None:
        username, password = route.proxy.auth
        headers["Authorization"] = aiohttp.encode_basic_auth(username, password)
    return headers or None


def _bypasses_egress_proxy(url: str) -> bool:
    """Keep Azure managed-identity endpoints on the local network."""
    hostname = urlsplit(url).hostname
    if hostname is None:
        return False
    if hostname.lower() == "localhost":
        return True
    try:
        address = ip_address(hostname)
    except ValueError:
        return False
    return address.is_loopback or address.is_link_local


class _RouteAwareAioHttpTransport(AioHttpTransport):
    """Apply the egress proxy except to local Azure identity endpoints."""

    def __init__(
        self,
        *,
        proxy: str,
        proxy_headers: dict[str, str] | None,
        **kwargs: Any,
    ) -> None:
        super().__init__(**kwargs)
        self._egress_proxy = proxy
        self._egress_proxy_headers = proxy_headers

    async def send(
        self,
        request: HttpRequest | RestHttpRequest,
        *,
        stream: bool = False,
        proxies: MutableMapping[str, str] | None = None,
        **config: Any,
    ) -> AsyncHttpResponse | RestAsyncHttpResponse:
        # DefaultAzureCredential probes IMDS and other managed-identity endpoints.
        # Sending those local requests to an external proxy can hang and can expose
        # metadata-path traffic outside the workload.
        config.pop("proxy_auth", None)
        if _bypasses_egress_proxy(str(request.url)):
            config.pop("proxy", None)
            config.pop("proxy_headers", None)
            return await super().send(
                request,
                stream=stream,
                proxies=None,
                **config,
            )

        config["proxy"] = self._egress_proxy
        if self._egress_proxy_headers is not None:
            config["proxy_headers"] = self._egress_proxy_headers
        return await super().send(
            request,
            stream=stream,
            proxies=None,
            **config,
        )


@asynccontextmanager
async def azure_transport_for_route(
    route: EgressRoute,
) -> AsyncIterator[AsyncHttpTransport]:
    """Yield an Azure transport with the same route as the shared HTTPX client."""
    session = aiohttp.ClientSession(
        # Proxied-route headers belong on the proxy hop, not on direct IMDS calls
        # or inside the TLS tunnel to the provider.
        headers=None
        if isinstance(route, ProxiedRoute)
        else dict(route.headers) or None,
        trust_env=route.trust_env,
    )
    transport_options = {
        "session": session,
        "session_owner": False,
        "connection_verify": route.verify,
        "connection_cert": _client_certificate(route),
        "use_env_settings": route.trust_env,
    }
    if isinstance(route, ProxiedRoute):
        transport: AsyncHttpTransport = _RouteAwareAioHttpTransport(
            proxy=str(route.proxy.url),
            proxy_headers=_proxy_headers(route),
            **transport_options,
        )
    else:
        transport = AioHttpTransport(**transport_options)
    try:
        yield transport
    finally:
        await session.close()
