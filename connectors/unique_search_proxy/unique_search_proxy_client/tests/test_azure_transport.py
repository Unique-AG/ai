from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import aiohttp
import httpx
import pytest
from azure.core.rest import HttpRequest
from unique_search_proxy_core.http_client import DirectRoute, ProxiedRoute

from unique_search_proxy_client.web.core.client.azure_transport import (
    azure_transport_for_route,
)


@pytest.mark.ai
class TestAzureTransport:
    async def test_proxied_route_uses_proxy_auth_on_the_wire(self) -> None:
        received: list[bytes] = []

        async def handle_proxy(
            reader: asyncio.StreamReader,
            writer: asyncio.StreamWriter,
        ) -> None:
            received.append(await reader.readuntil(b"\r\n\r\n"))
            writer.write(
                b"HTTP/1.1 200 OK\r\nContent-Length: 2\r\nConnection: close\r\n\r\nok"
            )
            await writer.drain()
            writer.close()
            await writer.wait_closed()

        server = await asyncio.start_server(handle_proxy, "127.0.0.1", 0)
        socket = server.sockets[0]
        port = socket.getsockname()[1]
        route = ProxiedRoute(
            proxy=httpx.Proxy(
                f"http://127.0.0.1:{port}",
                auth=("tenant-user", "proxy-password"),
            ),
            verify=True,
            headers={},
            cert=None,
        )
        try:
            async with azure_transport_for_route(route) as transport:
                response = await transport.send(
                    HttpRequest("GET", "http://upstream.example/resource")
                )
                assert response.status_code == 200
        finally:
            server.close()
            await server.wait_closed()

        request = received[0]
        assert request.startswith(b"GET http://upstream.example/resource HTTP/1.1\r\n")
        assert (
            b"Proxy-Authorization: Basic dGVuYW50LXVzZXI6cHJveHktcGFzc3dvcmQ="
            in request
        )
        assert b"tenant-user:proxy-password@" not in request

    async def test_proxied_route_configures_aiohttp_session(self) -> None:
        route = ProxiedRoute(
            proxy=httpx.Proxy(
                "https://proxy.example.com:8443",
                auth=("tenant-user", "proxy-password"),
            ),
            verify="/etc/proxy/ca.pem",
            headers={"X-Proxy-Tenant": "tenant-a"},
            cert=("/etc/proxy/client.pem", "/etc/proxy/client.key"),
        )
        session = MagicMock()
        session.close = AsyncMock()

        with patch(
            "unique_search_proxy_client.web.core.client.azure_transport.aiohttp.ClientSession",
            return_value=session,
        ) as create_session:
            async with azure_transport_for_route(route) as transport:
                assert transport.session is session
                assert transport.connection_config.verify == "/etc/proxy/ca.pem"
                assert transport.connection_config.cert == (
                    "/etc/proxy/client.pem",
                    "/etc/proxy/client.key",
                )

        create_session.assert_called_once_with(
            headers={"X-Proxy-Tenant": "tenant-a"},
            proxy="https://proxy.example.com:8443",
            proxy_auth=aiohttp.BasicAuth("tenant-user", "proxy-password"),
            trust_env=False,
        )
        session.close.assert_awaited_once()

    async def test_direct_route_uses_environment_without_proxy(self) -> None:
        route = DirectRoute(verify=True, trust_env=True, headers={})
        session = MagicMock()
        session.close = AsyncMock()

        with patch(
            "unique_search_proxy_client.web.core.client.azure_transport.aiohttp.ClientSession",
            return_value=session,
        ) as create_session:
            async with azure_transport_for_route(route):
                pass

        create_session.assert_called_once_with(
            headers=None,
            proxy=None,
            proxy_auth=None,
            trust_env=True,
        )
        session.close.assert_awaited_once()
