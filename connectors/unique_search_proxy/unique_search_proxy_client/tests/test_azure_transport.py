from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest
from azure.core.exceptions import ServiceResponseError
from azure.core.rest import HttpRequest
from unique_search_proxy_core.http_client import DirectRoute, ProxiedRoute

from unique_search_proxy_client.web.core.client.azure_transport import (
    _bypasses_egress_proxy,
    azure_transport_for_route,
)


@pytest.mark.ai
class TestAzureTransport:
    @pytest.mark.parametrize(
        ("url", "expected"),
        [
            ("http://169.254.169.254/metadata/identity/oauth2/token", True),
            ("http://127.0.0.1:40342/metadata/identity/oauth2/token", True),
            ("http://[::1]/metadata/identity/oauth2/token", True),
            ("http://localhost:40342/metadata/identity/oauth2/token", True),
            ("https://login.microsoftonline.com/tenant/oauth2/v2.0/token", False),
            ("https://example.azure.com/api/projects", False),
        ],
    )
    def test_only_local_identity_endpoints_bypass_proxy(
        self,
        url: str,
        expected: bool,
    ) -> None:
        assert _bypasses_egress_proxy(url) is expected

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
            headers={"X-Proxy-Tenant": "tenant-a"},
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

    async def test_proxied_route_authenticates_https_connect(self) -> None:
        received: list[bytes] = []

        async def handle_proxy(
            reader: asyncio.StreamReader,
            writer: asyncio.StreamWriter,
        ) -> None:
            received.append(await reader.readuntil(b"\r\n\r\n"))
            writer.write(
                b"HTTP/1.1 502 Bad Gateway\r\n"
                b"Content-Length: 0\r\n"
                b"Connection: close\r\n\r\n"
            )
            await writer.drain()
            writer.close()
            await writer.wait_closed()

        server = await asyncio.start_server(handle_proxy, "127.0.0.1", 0)
        socket = server.sockets[0]
        route = ProxiedRoute(
            proxy=httpx.Proxy(
                f"http://127.0.0.1:{socket.getsockname()[1]}",
                auth=("tenant-user", "proxy-password"),
            ),
            verify=True,
            headers={"X-Proxy-Tenant": "tenant-a"},
            cert=None,
        )
        try:
            async with azure_transport_for_route(route) as transport:
                with pytest.raises(ServiceResponseError):
                    await transport.send(
                        HttpRequest("GET", "https://upstream.example/resource")
                    )
        finally:
            server.close()
            await server.wait_closed()

        request = received[0]
        assert request.startswith(b"CONNECT upstream.example:443 HTTP/1.1\r\n")
        assert (
            b"Proxy-Authorization: Basic dGVuYW50LXVzZXI6cHJveHktcGFzc3dvcmQ="
            in request
        )
        assert b"X-Proxy-Tenant: tenant-a" in request

    async def test_proxied_route_bypasses_proxy_for_loopback(self) -> None:
        proxy_received: list[bytes] = []
        target_received: list[bytes] = []

        async def handle_proxy(
            reader: asyncio.StreamReader,
            writer: asyncio.StreamWriter,
        ) -> None:
            proxy_received.append(await reader.readuntil(b"\r\n\r\n"))
            writer.write(
                b"HTTP/1.1 502 Bad Gateway\r\n"
                b"Content-Length: 0\r\n"
                b"Connection: close\r\n\r\n"
            )
            await writer.drain()
            writer.close()
            await writer.wait_closed()

        async def handle_target(
            reader: asyncio.StreamReader,
            writer: asyncio.StreamWriter,
        ) -> None:
            target_received.append(await reader.readuntil(b"\r\n\r\n"))
            writer.write(
                b"HTTP/1.1 200 OK\r\nContent-Length: 2\r\nConnection: close\r\n\r\nok"
            )
            await writer.drain()
            writer.close()
            await writer.wait_closed()

        proxy_server = await asyncio.start_server(handle_proxy, "127.0.0.1", 0)
        target_server = await asyncio.start_server(handle_target, "127.0.0.1", 0)
        proxy_socket = proxy_server.sockets[0]
        target_socket = target_server.sockets[0]
        route = ProxiedRoute(
            proxy=httpx.Proxy(
                f"http://127.0.0.1:{proxy_socket.getsockname()[1]}",
                auth=("tenant-user", "proxy-password"),
            ),
            verify=True,
            headers={"X-Proxy-Tenant": "tenant-a"},
            cert=None,
        )
        try:
            async with azure_transport_for_route(route) as transport:
                response = await transport.send(
                    HttpRequest(
                        "GET",
                        f"http://127.0.0.1:{target_socket.getsockname()[1]}/metadata",
                    )
                )
                assert response.status_code == 200
        finally:
            proxy_server.close()
            target_server.close()
            await proxy_server.wait_closed()
            await target_server.wait_closed()

        assert target_received[0].startswith(b"GET /metadata HTTP/1.1\r\n")
        assert b"Proxy-Authorization:" not in target_received[0]
        assert (
            b"Authorization: Basic dGVuYW50LXVzZXI6cHJveHktcGFzc3dvcmQ="
            not in target_received[0]
        )
        assert b"X-Proxy-Tenant:" not in target_received[0]
        assert proxy_received == []

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
            headers=None,
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
            trust_env=True,
        )
        session.close.assert_awaited_once()
