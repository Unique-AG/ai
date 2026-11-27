"""Tests for the outbound response size cap."""

from __future__ import annotations

import gzip
from collections.abc import AsyncIterator, Callable

import httpx
import pytest

from unique_search_proxy_core.errors import ResponseTooLargeError
from unique_search_proxy_core.http_client import (
    MAX_RESPONSE_BYTES_EXTENSION,
    ByteBudget,
    ProxyCredentials,
    ProxySettings,
    async_client_factory,
    build_async_client,
    install_response_size_cap,
    read_capped_body,
)
from unique_search_proxy_core.schema import ProxyErrorCode

Handler = Callable[[httpx.Request], httpx.Response]


def _capped_client(handler: Handler, max_bytes: int | None) -> httpx.AsyncClient:
    client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    return install_response_size_cap(client, max_bytes)


async def _endless_body() -> AsyncIterator[bytes]:
    while True:
        yield b"x" * 4096


async def _body_of(size: int) -> AsyncIterator[bytes]:
    yield b"x" * size


@pytest.mark.ai
async def test_response_size_cap__returns_body__when_under_limit() -> None:
    """
    Purpose: Verify responses within the limit are returned unchanged.
    Why this matters: The cap must not change behaviour for normal pages.
    Setup summary: 1 KiB body with a 4 KiB cap; assert the full body is read.
    """
    async with _capped_client(
        lambda _: httpx.Response(200, content=b"a" * 1024), max_bytes=4096
    ) as client:
        response = await client.get("https://example.com")

    assert response.content == b"a" * 1024


@pytest.mark.ai
async def test_response_size_cap__rejects_early__when_content_length_over_limit() -> (
    None
):
    """
    Purpose: Verify an oversized declared Content-Length is rejected up front.
    Why this matters: Avoids reading any of a body we already know is too big.
    Setup summary: 8 KiB body with a 4 KiB cap; assert ResponseTooLargeError.
    """
    async with _capped_client(
        lambda _: httpx.Response(200, content=b"a" * 8192), max_bytes=4096
    ) as client:
        with pytest.raises(ResponseTooLargeError):
            await client.get("https://example.com")


@pytest.mark.ai
async def test_response_size_cap__aborts_mid_stream__when_content_length_lies() -> None:
    """
    Purpose: Verify bytes are counted even when Content-Length understates them.
    Why this matters: A hostile server controls the header, not the byte count.
    Setup summary: Header claims 10 bytes, body is 8 KiB; assert the read aborts.
    """
    async with _capped_client(
        lambda _: httpx.Response(
            200,
            headers={"content-length": "10"},
            content=_body_of(8192),
        ),
        max_bytes=4096,
    ) as client:
        with pytest.raises(ResponseTooLargeError):
            await client.get("https://example.com")


@pytest.mark.ai
async def test_response_size_cap__aborts__when_body_is_endless() -> None:
    """
    Purpose: Verify an endless chunked body is aborted at the limit.
    Why this matters: Without a cap an endless body grows until the pod OOMs.
    Setup summary: Infinite generator body with a 64 KiB cap; assert abort.
    """
    async with _capped_client(
        lambda _: httpx.Response(200, content=_endless_body()), max_bytes=65536
    ) as client:
        with pytest.raises(ResponseTooLargeError):
            await client.get("https://example.com")


@pytest.mark.ai
async def test_response_size_cap__caps_redirect_bodies__when_following_redirects() -> (
    None
):
    """
    Purpose: Verify the cap applies to each redirect hop, not only the last one.
    Why this matters: httpx reads intermediate redirect bodies when following.
    Setup summary: 302 with an endless body; assert the redirect hop aborts.
    """

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/start":
            return httpx.Response(
                302,
                headers={"location": "/final"},
                content=_endless_body(),
            )
        return httpx.Response(200, content=b"ok")

    async with _capped_client(handler, max_bytes=65536) as client:
        with pytest.raises(ResponseTooLargeError):
            await client.get("https://example.com/start", follow_redirects=True)


@pytest.mark.ai
async def test_response_size_cap__lowers_limit__when_request_extension_set() -> None:
    """
    Purpose: Verify a request can tighten the limit through extensions.
    Why this matters: Callers with smaller budgets reuse the shared client.
    Setup summary: 2 KiB body, 4 KiB default, 1 KiB override; assert rejection.
    """
    async with _capped_client(
        lambda _: httpx.Response(200, content=b"a" * 2048), max_bytes=4096
    ) as client:
        with pytest.raises(ResponseTooLargeError):
            await client.get(
                "https://example.com",
                extensions={MAX_RESPONSE_BYTES_EXTENSION: 1024},
            )


@pytest.mark.ai
async def test_response_size_cap__keeps_default__when_extension_is_higher() -> None:
    """
    Purpose: Verify a request cannot raise the limit above the client default.
    Why this matters: The server-side ceiling must not be bypassable per call.
    Setup summary: 8 KiB body, 4 KiB default, 1 MiB override; assert rejection.
    """
    async with _capped_client(
        lambda _: httpx.Response(200, content=b"a" * 8192), max_bytes=4096
    ) as client:
        with pytest.raises(ResponseTooLargeError):
            await client.get(
                "https://example.com",
                extensions={MAX_RESPONSE_BYTES_EXTENSION: 1024 * 1024},
            )


@pytest.mark.ai
async def test_response_size_cap__does_not_cap__when_limit_disabled() -> None:
    """
    Purpose: Verify max_bytes=None leaves responses uncapped.
    Why this matters: Operators can disable the limit through settings.
    Setup summary: 64 KiB body with no limit; assert the full body is read.
    """
    async with _capped_client(
        lambda _: httpx.Response(200, content=b"a" * 65536), max_bytes=None
    ) as client:
        response = await client.get("https://example.com")

    assert len(response.content) == 65536


@pytest.mark.ai
async def test_read_capped_body__aborts__when_decompressed_body_over_limit() -> None:
    """
    Purpose: Verify the decoded-size limit stops a gzip decompression bomb.
    Why this matters: The network cap counts compressed bytes only.
    Setup summary: 4 MiB of zeros gzipped (a few KiB on the wire), 1 MiB
        network cap and 64 KiB decoded cap; assert ResponseTooLargeError.
    """
    bomb = gzip.compress(b"\0" * (4 * 1024 * 1024))

    async with _capped_client(
        lambda _: httpx.Response(
            200, headers={"content-encoding": "gzip"}, content=bomb
        ),
        max_bytes=1024 * 1024,
    ) as client:
        async with client.stream("GET", "https://example.com") as response:
            with pytest.raises(ResponseTooLargeError):
                await read_capped_body(response, max_bytes=65536)


@pytest.mark.ai
async def test_read_capped_body__returns_decoded_body__when_under_limit() -> None:
    """
    Purpose: Verify gzip bodies within the limit are returned decoded.
    Why this matters: Normal compressed pages must still crawl correctly.
    Setup summary: Gzipped 1 KiB body with a 4 KiB decoded cap; assert bytes.
    """
    async with _capped_client(
        lambda _: httpx.Response(
            200,
            headers={"content-encoding": "gzip"},
            content=gzip.compress(b"a" * 1024),
        ),
        max_bytes=4096,
    ) as client:
        async with client.stream("GET", "https://example.com") as response:
            body = await read_capped_body(response, max_bytes=4096)

    assert body == b"a" * 1024


@pytest.mark.ai
def test_response_too_large_error__maps_to_non_retryable_502() -> None:
    """
    Purpose: Verify the error contract of ResponseTooLargeError.
    Why this matters: Callers rely on code and retryability to handle it.
    Setup summary: Build the error; assert code, status and retryable flag.
    """
    error = ResponseTooLargeError.for_limit(4096)

    detail = error.to_detail()

    assert error.status_code == 502
    assert detail.code == ProxyErrorCode.RESPONSE_TOO_LARGE.value
    assert detail.retryable is False
    assert "4096" in detail.message


@pytest.mark.ai
@pytest.mark.parametrize(
    ("max_response_kib", "expected_bytes"),
    [(2, 2048), (None, None)],
)
def test_proxy_settings__converts_kib_to_bytes(
    max_response_kib: int | None,
    expected_bytes: int | None,
) -> None:
    """
    Purpose: Verify max_response_bytes is derived from max_response_kib.
    Why this matters: The setting is in KiB so Helm renders it as an integer.
    Setup summary: Build settings with a KiB value or None; assert bytes.
    """
    settings = ProxySettings(max_response_kib=max_response_kib)

    assert settings.max_response_bytes == expected_bytes


@pytest.mark.ai
async def test_build_async_client__installs_cap__from_settings() -> None:
    """
    Purpose: Verify registry clients carry the response size cap hook.
    Why this matters: Every egress client must be protected by default.
    Setup summary: Build a direct-route client; assert one response hook.
    """
    settings = ProxySettings()
    credentials = ProxyCredentials.anonymous()

    client = build_async_client(settings, credentials, timeout=5.0)
    try:
        assert len(client.event_hooks["response"]) == 1
    finally:
        await client.aclose()


@pytest.mark.ai
async def test_async_client_factory__installs_cap__from_settings() -> None:
    """
    Purpose: Verify short-lived factory clients carry the cap hook too.
    Why this matters: The factory path must not bypass the limit.
    Setup summary: Build a client from the factory; assert one response hook.
    """
    client = async_client_factory(ProxySettings())()
    try:
        assert len(client.event_hooks["response"]) == 1
    finally:
        await client.aclose()


@pytest.mark.ai
async def test_build_async_client__keeps_env_proxy__for_direct_route(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """
    Purpose: Verify direct-route clients still honour HTTPS_PROXY from the env.
    Why this matters: A custom transport would silently drop env proxies.
    Setup summary: Set HTTPS_PROXY, build a direct client; assert the URL is
        routed through a mounted proxy transport, not the default transport.
    """
    monkeypatch.setenv("HTTPS_PROXY", "http://env-proxy.internal:3128")
    settings = ProxySettings()
    credentials = ProxyCredentials.anonymous()

    client = build_async_client(settings, credentials, timeout=5.0)
    try:
        transport = client._transport_for_url(httpx.URL("https://example.com"))
        assert transport is not client._transport
    finally:
        await client.aclose()


@pytest.mark.ai
def test_byte_budget__raises__when_consumption_exceeds_budget() -> None:
    """
    Purpose: Verify ByteBudget raises once reservations exceed its size.
    Why this matters: The budget is what bounds a whole crawl's memory.
    Setup summary: 10-byte budget; consume 6 then 6; assert the second raises.
    """
    budget = ByteBudget(10)
    budget.consume(6)

    with pytest.raises(ResponseTooLargeError, match="10 byte budget"):
        budget.consume(6)


@pytest.mark.ai
def test_byte_budget__reports_exhausted__when_fully_used() -> None:
    """
    Purpose: Verify exhausted flips exactly when the budget is fully used.
    Why this matters: Callers skip remaining fetches once it is exhausted.
    Setup summary: 10-byte budget; consume 10; assert exhausted.
    """
    budget = ByteBudget(10)

    budget.consume(10)

    assert budget.exhausted is True


@pytest.mark.ai
def test_byte_budget__frees_room__when_bytes_released() -> None:
    """
    Purpose: Verify released bytes can be consumed again.
    Why this matters: A discarded body must not keep holding budget.
    Setup summary: Consume 10 of 10, release 4, consume 4; assert no error.
    """
    budget = ByteBudget(10)
    budget.consume(10)

    budget.release(4)
    budget.consume(4)

    assert budget.exhausted is True


@pytest.mark.ai
async def test_read_capped_body__releases_budget__when_read_fails() -> None:
    """
    Purpose: Verify a failed read returns its charged bytes to the budget.
    Why this matters: Bytes of a discarded body are not held in memory.
    Setup summary: 4 KiB budget, 2 KiB per-body cap, 3 KiB body; assert the
        read fails and the budget is back to empty.
    """
    budget = ByteBudget(4096)

    async with _capped_client(
        lambda _: httpx.Response(200, content=_body_of(3072)), max_bytes=None
    ) as client:
        async with client.stream("GET", "https://example.com") as response:
            with pytest.raises(ResponseTooLargeError):
                await read_capped_body(response, max_bytes=2048, budget=budget)

    budget.consume(4096)
    assert budget.exhausted is True


@pytest.mark.ai
async def test_read_capped_body__charges_budget__when_read_succeeds() -> None:
    """
    Purpose: Verify a successful read keeps its bytes charged to the budget.
    Why this matters: Kept bodies must count toward the request's total.
    Setup summary: 4 KiB budget, read a 3 KiB body; assert 1 more KiB fits
        and anything beyond raises.
    """
    budget = ByteBudget(4096)

    async with _capped_client(
        lambda _: httpx.Response(200, content=b"a" * 3072), max_bytes=None
    ) as client:
        async with client.stream("GET", "https://example.com") as response:
            await read_capped_body(response, max_bytes=None, budget=budget)

    budget.consume(1024)
    with pytest.raises(ResponseTooLargeError):
        budget.consume(1)
