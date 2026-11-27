"""Cancelled internal-search fan-out must not strand httpcore connections.

Do not rewrite this to use ``httpx.ASGITransport`` (never enters the pool) or
raw ``Task.cancel()`` (both gather and TaskGroup look clean under that).
The leak only shows up when cancellation is delivered through an anyio scope
against a real TCP server mid-body-read.
"""

from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from dataclasses import dataclass
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import anyio
import httpx
import pytest

from unique_toolkit.app.unique_settings import UniqueContext, UniqueSettings
from unique_toolkit.experimental.components.internal_search.base import (
    service as service_mod,
)
from unique_toolkit.experimental.components.internal_search.base.config import (
    InternalSearchConfig,
)
from unique_toolkit.experimental.components.internal_search.base.schemas import (
    SearchStringResult,
)
from unique_toolkit.experimental.components.internal_search.base.service import (
    InternalSearchBaseService,
)

pytestmark = pytest.mark.ai

_FANOUT_SIZE = 5


@dataclass
class _FakeDeps:
    pass


class _HttpxSearchService(InternalSearchBaseService[_FakeDeps]):
    _client: httpx.AsyncClient
    _url: str

    def _make_dependencies(
        self, settings: UniqueSettings, context: UniqueContext
    ) -> _FakeDeps:
        return _FakeDeps()

    async def _search_single_query(self, *, query: str) -> SearchStringResult:
        await self._client.get(self._url)
        return SearchStringResult(query=query, chunks=[])


def _make_http_service(client: httpx.AsyncClient, url: str) -> _HttpxSearchService:
    svc = _HttpxSearchService.from_config(InternalSearchConfig())
    svc._client = client
    svc._url = url
    svc._context = MagicMock(spec=UniqueContext)
    svc._dependencies = _FakeDeps()
    svc.reset_state()
    return svc


def _active_http_connections(client: httpx.AsyncClient) -> int:
    pool = client._transport._pool
    return sum(1 for connection in pool._connections if not connection.is_idle())


async def _wait_until_active(client: httpx.AsyncClient, count: int) -> None:
    with anyio.fail_after(2):
        while _active_http_connections(client) < count:
            await anyio.sleep(0.02)


@asynccontextmanager
async def _slow_chunked_http_server() -> AsyncIterator[str]:
    async def handle(
        reader: asyncio.StreamReader, writer: asyncio.StreamWriter
    ) -> None:
        try:
            await reader.readuntil(b"\r\n\r\n")
            writer.write(b"HTTP/1.1 200 OK\r\nTransfer-Encoding: chunked\r\n\r\n")
            await writer.drain()
            while True:
                chunk = b"x" * 64
                writer.write(f"{len(chunk):x}\r\n".encode() + chunk + b"\r\n")
                await writer.drain()
                await asyncio.sleep(0.05)
        except (ConnectionError, BrokenPipeError, asyncio.CancelledError):
            pass
        finally:
            writer.close()
            try:
                await writer.wait_closed()
            except (ConnectionError, BrokenPipeError):
                pass

    server = await asyncio.start_server(handle, "127.0.0.1", 0)
    try:
        sockets = server.sockets
        assert sockets is not None
        port = sockets[0].getsockname()[1]
        yield f"http://127.0.0.1:{port}/"
    finally:
        server.close()
        await server.wait_closed()


async def test_run__anyio_cancel_releases_pooled_http_connections():
    """
    Purpose: Cancelling run() through an anyio scope leaves no ACTIVE httpcore
        connections.
    Why this matters: asyncio.gather re-cancels children inside httpcore
        aclose, stranding the connection ACTIVE forever and hanging kb-mcp.
    Setup summary: Five queries hit a real TCP server that streams forever;
        wait until all five connections are ACTIVE, cancel via anyio, assert
        zero ACTIVE connections remain.
    """
    async with _slow_chunked_http_server() as url:
        limits = httpx.Limits(max_connections=10, max_keepalive_connections=10)
        async with httpx.AsyncClient(limits=limits, timeout=30.0) as client:
            svc = _make_http_service(client, url)
            svc._state.search_queries = ["q1", "q2", "q3", "q4", "q5"]
            with patch.object(svc, "post_progress_message", new=AsyncMock()):
                async with anyio.create_task_group() as tg:
                    tg.start_soon(svc.run)
                    await _wait_until_active(client, _FANOUT_SIZE)
                    tg.cancel_scope.cancel()
            assert _active_http_connections(client) == 0


def test_internal_search_service_does_not_use_asyncio_gather():
    """
    Purpose: The kb-mcp-reachable search fan-out must not call asyncio.gather.
    Why this matters: A later PR can reintroduce gather and the connection leak
        without any semantic test failing.
    Setup summary: Read InternalSearchBaseService's module source; gather must
        not appear.
    """
    text = Path(service_mod.__file__).read_text(encoding="utf-8")
    assert "asyncio.gather" not in text
