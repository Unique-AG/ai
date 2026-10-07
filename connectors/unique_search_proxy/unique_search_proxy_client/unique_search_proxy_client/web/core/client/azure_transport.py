"""Azure SDK transport configured from the shared egress route."""

from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

import aiohttp
from azure.core.pipeline.transport import AioHttpTransport, AsyncHttpTransport
from unique_search_proxy_core.http_client import EgressRoute, ProxiedRoute


def _client_certificate(
    route: EgressRoute,
) -> tuple[str, ...] | None:
    if not isinstance(route, ProxiedRoute) or route.cert is None:
        return None
    if isinstance(route.cert, str):
        return (route.cert,)
    return route.cert


def _proxy_auth(route: EgressRoute) -> aiohttp.BasicAuth | None:
    if not isinstance(route, ProxiedRoute) or route.proxy.auth is None:
        return None
    username, password = route.proxy.auth
    return aiohttp.BasicAuth(username, password)


@asynccontextmanager
async def azure_transport_for_route(
    route: EgressRoute,
) -> AsyncIterator[AsyncHttpTransport]:
    """Yield an Azure transport with the same route as the shared HTTPX client."""
    proxy = str(route.proxy.url) if isinstance(route, ProxiedRoute) else None
    session = aiohttp.ClientSession(
        headers=dict(route.headers) or None,
        proxy=proxy,
        proxy_auth=_proxy_auth(route),
        trust_env=route.trust_env,
    )
    transport = AioHttpTransport(
        session=session,
        session_owner=False,
        connection_verify=route.verify,
        connection_cert=_client_certificate(route),
        use_env_settings=route.trust_env,
    )
    try:
        yield transport
    finally:
        await session.close()
