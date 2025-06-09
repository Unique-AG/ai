"""Requests-based HTTP client implementation."""

import json
import threading
from typing import Any, Dict, Optional

import requests
from requests import Session

import unique_client
from unique_client.core import errors as _error
from unique_client.core.http_clients.protocol import (
    HTTPClientProtocol,
    HTTPHeaders,
    HTTPResponse,
    PostData,
)


class RequestsClient:
    """HTTP client implementation using the requests library."""

    name = "requests"

    def __init__(
        self,
        timeout: int = 600,
        session: Optional[Session] = None,
        async_fallback_client: Optional[HTTPClientProtocol] = None,
        **kwargs: Any,
    ) -> None:
        self._thread_local = threading.local()
        self._async_fallback_client = async_fallback_client
        self._timeout = timeout
        self._session: Optional[Session] = session
        self.requests = requests

    def request(
        self, method: str, url: str, headers: HTTPHeaders, post_data: PostData = None
    ) -> HTTPResponse:
        return self._request_internal(
            method,
            url,
            headers,
            post_data,
            is_streaming=False,
        )

    async def request_async(
        self, method: str, url: str, headers: HTTPHeaders, post_data: PostData = None
    ) -> HTTPResponse:
        if self._async_fallback_client is not None:
            return await self._async_fallback_client.request_async(
                method, url, headers, post_data
            )
        # RequestsClient doesn't support native async, so we need a fallback
        raise NotImplementedError(
            "RequestsClient requires an async_fallback_client for async operations"
        )

    async def close_async(self) -> None:
        if self._async_fallback_client is not None:
            return await self._async_fallback_client.close_async()
        # For sync client, close_async just calls close
        self.close()

    def _request_internal(
        self,
        method: str,
        url: str,
        headers: HTTPHeaders,
        post_data: PostData,
        is_streaming: bool,
    ) -> HTTPResponse:
        kwargs: Dict[str, Any] = {}

        if getattr(self._thread_local, "session", None) is None:
            self._thread_local.session = self._session or self.requests.Session()

        # Default to SSL verification enabled, #TODO: make this configurable
        verify = getattr(unique_client, "api_verify_mode", True)

        try:
            try:
                result = self._thread_local.session.request(
                    method,
                    url,
                    headers=headers,
                    data=json.dumps(post_data),
                    timeout=self._timeout,
                    verify=verify,
                    **kwargs,
                )
            except TypeError as e:
                raise TypeError(
                    "Warning: It looks like your installed version of the "
                    '"requests" library is not compatible with Unique SDK\'s '
                    "usage thereof. (HINT: The most likely cause is that "
                    'your "requests" library is out of date. You can fix '
                    'that by running "pip install -U requests".) The '
                    "underlying error was: %s" % (e,)
                )

            content: bytes = result.content
            status_code: int = result.status_code

        except Exception as e:
            raise _error.APIConnectionError(
                "Unexpected error communicating with Unique. "
                "If this problem persists, let us know at support@unique.ch",
                http_status=500,
                original_error=e,
            )

        return content, status_code, result.headers

    def close(self) -> None:
        if getattr(self._thread_local, "session", None) is not None:
            self._thread_local.session.close()
