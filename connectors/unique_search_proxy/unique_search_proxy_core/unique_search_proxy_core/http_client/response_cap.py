"""Bound how many bytes an outbound response may deliver.

The limit is enforced while the body streams in, so an oversized, chunked, or
endless response is aborted before it is buffered in memory. It is installed as
an httpx response hook rather than a custom transport: a custom transport makes
httpx ignore ``trust_env`` proxy discovery and every transport-level option.
"""

from __future__ import annotations

from collections.abc import AsyncIterator, Awaitable, Callable

import httpx

from unique_search_proxy_core.errors import ResponseTooLargeError

MAX_RESPONSE_BYTES_EXTENSION = "max_response_bytes"

# Raw chunks are re-sliced before httpx decompresses them, which bounds how much
# a single gzip/deflate decode step can expand.
_RAW_SLICE_BYTES = 16 * 1024

ResponseHook = Callable[[httpx.Response], Awaitable[None]]


class _CappedRawStream(httpx.AsyncByteStream):
    """Wrap a response byte stream and abort once it delivers too many bytes.

    Counts bytes as received from the network (before decompression), so it
    also catches responses with a missing or understated ``Content-Length``.
    """

    def __init__(self, stream: httpx.AsyncByteStream, *, max_bytes: int) -> None:
        self._stream = stream
        self._max_bytes = max_bytes

    async def __aiter__(self) -> AsyncIterator[bytes]:
        received = 0
        async for chunk in self._stream:
            received += len(chunk)
            if received > self._max_bytes:
                raise ResponseTooLargeError.for_limit(self._max_bytes)
            for start in range(0, len(chunk), _RAW_SLICE_BYTES):
                yield chunk[start : start + _RAW_SLICE_BYTES]

    async def aclose(self) -> None:
        await self._stream.aclose()


def _effective_max_bytes(
    request: httpx.Request,
    default_max_bytes: int | None,
) -> int | None:
    """Combine the client default with a per-request override; lower wins."""
    override = request.extensions.get(MAX_RESPONSE_BYTES_EXTENSION)
    if override is None:
        return default_max_bytes
    if default_max_bytes is None:
        return int(override)
    return min(int(override), default_max_bytes)


def _declared_content_length(response: httpx.Response) -> int | None:
    header = response.headers.get("content-length")
    if header is None:
        return None
    try:
        return int(header)
    except ValueError:
        return None


def response_size_cap_hook(default_max_bytes: int | None) -> ResponseHook:
    """Build an httpx response hook that caps the response body size.

    Requests can lower the limit with
    ``extensions={"max_response_bytes": n}``; they cannot raise it above
    ``default_max_bytes``.

    Args:
        default_max_bytes (int | None): Limit applied when a request sets no
            override. ``None`` leaves such requests uncapped.

    Returns:
        ResponseHook: Coroutine to register under ``event_hooks["response"]``.
    """

    async def _cap_response_size(response: httpx.Response) -> None:
        max_bytes = _effective_max_bytes(response.request, default_max_bytes)
        if max_bytes is None:
            return
        declared = _declared_content_length(response)
        if declared is not None and declared > max_bytes:
            raise ResponseTooLargeError.for_limit(max_bytes)
        if isinstance(response.stream, httpx.AsyncByteStream):
            response.stream = _CappedRawStream(response.stream, max_bytes=max_bytes)

    return _cap_response_size


def install_response_size_cap(
    client: httpx.AsyncClient,
    max_bytes: int | None,
) -> httpx.AsyncClient:
    """Register the response size cap on an existing client.

    Args:
        client (httpx.AsyncClient): Client to protect, e.g. a test client.
        max_bytes (int | None): Default limit for the client's requests.

    Returns:
        httpx.AsyncClient: The same client, for chaining.
    """
    client.event_hooks["response"].append(response_size_cap_hook(max_bytes))
    return client


class ByteBudget:
    """Shared allowance of decoded body bytes across several responses.

    Bounds what one caller keeps in memory at once, e.g. every page of a crawl
    request, which a per-response limit alone cannot do. Not thread-safe; share
    it only between tasks of one event loop.
    """

    def __init__(self, max_bytes: int) -> None:
        self._max_bytes = max_bytes
        self._used = 0

    @property
    def exhausted(self) -> bool:
        return self._used >= self._max_bytes

    def consume(self, num_bytes: int) -> None:
        """Reserve bytes, raising once the budget is exceeded.

        Raises:
            ResponseTooLargeError: When the reservation exceeds the budget.
        """
        self._used += num_bytes
        if self._used > self._max_bytes:
            raise ResponseTooLargeError(
                f"Combined upstream responses exceeded the {self._max_bytes} "
                "byte budget",
            )

    def release(self, num_bytes: int) -> None:
        """Return bytes from a body that was discarded."""
        self._used = max(0, self._used - num_bytes)


async def read_capped_body(
    response: httpx.Response,
    *,
    max_bytes: int | None,
    budget: ByteBudget | None = None,
) -> bytes:
    """Read a streamed response body, limiting its decompressed size.

    The response hook limits bytes received from the network; this limits the
    bytes after gzip/deflate decoding, which stops decompression bombs.

    Args:
        response (httpx.Response): Response opened with ``stream=True``.
        max_bytes (int | None): Largest decoded body allowed. ``None`` reads
            the whole body.
        budget (ByteBudget | None): Shared budget the body is charged against.
            Bytes are returned to it when the read fails.

    Returns:
        bytes: The decoded response body.

    Raises:
        ResponseTooLargeError: When the decoded body exceeds ``max_bytes`` or
            the shared budget.
    """
    chunks: list[bytes] = []
    received = 0
    charged = 0
    try:
        async for chunk in response.aiter_bytes():
            received += len(chunk)
            if max_bytes is not None and received > max_bytes:
                raise ResponseTooLargeError.for_limit(max_bytes)
            if budget is not None:
                charged += len(chunk)
                budget.consume(len(chunk))
            chunks.append(chunk)
    except BaseException:
        if budget is not None:
            budget.release(charged)
        raise
    return b"".join(chunks)


__all__ = [
    "MAX_RESPONSE_BYTES_EXTENSION",
    "ByteBudget",
    "ResponseHook",
    "install_response_size_cap",
    "read_capped_body",
    "response_size_cap_hook",
]
