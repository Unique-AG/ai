"""HTTPX-based HTTP client implementation."""

import json
from typing import Any, Dict, Optional, Tuple

import anyio
import httpx

from unique_client.core import errors as _error
from unique_client.core.http_clients.protocol import (
    HTTPClientProtocol,
    HTTPHeaders,
    HTTPResponse,
    PostData,
)


class HTTPXClient(HTTPClientProtocol):
    """HTTP client implementation using the httpx library."""

    name = "httpx"

    def __init__(
        self,
        timeout: Optional[float] = 600,
        **kwargs: Any,
    ) -> None:
        self.httpx = httpx
        self.anyio = anyio

        self._client_async = httpx.AsyncClient(**kwargs)
        self._client = httpx.Client(**kwargs)
        self._timeout = timeout

    def _get_request_args_kwargs(
        self, method: str, url: str, headers: HTTPHeaders, post_data: PostData
    ) -> Tuple[Tuple[str, str], Dict[str, Any]]:
        kwargs: Dict[str, Any] = {}

        if self._timeout:
            kwargs["timeout"] = self._timeout
        return (
            (method, url),
            {"headers": headers, "data": json.dumps(post_data) or {}, **kwargs},
        )

    def request(
        self,
        method: str,
        url: str,
        headers: HTTPHeaders,
        post_data: PostData = None,
    ) -> HTTPResponse:
        args, kwargs = self._get_request_args_kwargs(method, url, headers, post_data)
        try:
            response = self._client.request(*args, **kwargs)
        except Exception as e:
            raise _error.APIConnectionError(
                "Unexpected error communicating with Unique. "
                "If this problem persists, let us know at support@unique.ch",
                http_status=500,
                original_error=e,
            )

        content: bytes = response.content
        status_code: int = response.status_code
        response_headers: Dict[str, str] = dict(response.headers)
        return content, status_code, response_headers

    async def request_async(
        self,
        method: str,
        url: str,
        headers: HTTPHeaders,
        post_data: PostData = None,
    ) -> HTTPResponse:
        args, kwargs = self._get_request_args_kwargs(method, url, headers, post_data)
        try:
            response = await self._client_async.request(*args, **kwargs)
        except Exception as e:
            raise _error.APIConnectionError(
                "Unexpected error communicating with Unique. "
                "If this problem persists, let us know at support@unique.ch",
                http_status=500,
                original_error=e,
            )

        content: bytes = response.content
        status_code: int = response.status_code
        response_headers: Dict[str, str] = dict(response.headers)
        return content, status_code, response_headers

    def close(self) -> None:
        if self._client is not None:
            self._client.close()

    async def close_async(self) -> None:
        await self._client_async.aclose()
