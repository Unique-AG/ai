import json
import threading
from typing import ClassVar, Optional

try:
    import requests
except ImportError:
    requests = None

try:
    import anyio
    import httpx
    from httpx import Client as HTTPXClientType
    from httpx import Timeout as HTTPXTimeout
except ImportError:
    httpx = None

import unique_sdk
from unique_sdk import _error


def new_default_http_client(*args, **kwargs) -> "HTTPClient":
    impl = RequestsClient
    return impl(*args, **kwargs)


def new_http_client_async_fallback(*args, **kwargs) -> "HTTPClient":
    impl = HTTPXClient
    return impl(*args, **kwargs)


class HTTPClient(object):
    name: ClassVar[str]

    def __init__(
        self,
        async_fallback_client: Optional["HTTPClient"] = None,
    ):
        self._thread_local = threading.local()
        self._async_fallback_client = async_fallback_client

    def request(self, method, url, headers, post_data=None):
        raise NotImplementedError("HTTPClient subclasses must implement `request`")

    async def request_async(self, method, url, headers, post_data=None):
        if self._async_fallback_client is not None:
            return await self._async_fallback_client.request_async(
                method, url, headers, post_data
            )
        raise NotImplementedError(
            "HTTPClient subclasses must implement `request_async`"
        )

    async def close_async(self):
        if self._async_fallback_client is not None:
            return await self._async_fallback_client.close_async()
        raise NotImplementedError("HTTPClient subclasses must implement `close_async`")


class RequestsClient(HTTPClient):
    name = "requests"

    def __init__(
        self,
        timeout=600,
        session=None,
        async_fallback_client: Optional[HTTPClient] = None,
        **kwargs,
    ):
        super(RequestsClient, self).__init__(
            async_fallback_client=async_fallback_client,
            **kwargs,
        )
        self._timeout = timeout
        self._session = session

        assert requests is not None
        self.requests = requests

    def request(self, method, url, headers, post_data=None):
        return self._request_internal(
            method, url, headers, post_data, is_streaming=False
        )

    def _request_internal(self, method, url, headers, post_data, is_streaming):
        kwargs = {}

        if getattr(self._thread_local, "session", None) is None:
            self._thread_local.session = self._session or self.requests.Session()

        verify = unique_sdk.api_verify_mode

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

            content = result.content
            status_code = result.status_code

        except Exception:
            raise _error.APIConnectionError(
                "Unexpected error communicating with Unique. "
                "If this problem persists, let us know at support@unique.ch",
                http_status=500,
            )

        return content, status_code, result.headers


class HTTPXClient(HTTPClient):
    name = "httpx"

    def __init__(
        self,
        timeout=600,
        allow_sync_methods=False,
        **kwargs,
    ):
        super(HTTPXClient, self).__init__(**kwargs)

        if httpx is None:
            raise ImportError(
                "Unexpected: tried to initialize HTTPXClient but the httpx module is not present."
            )

        if anyio is None:
            raise ImportError(
                "Unexpected: tried to initialize HTTPXClient but the anyio module is not present."
            )

        self.httpx = httpx
        self.anyio = anyio

        self._client_async = httpx.AsyncClient(**kwargs)
        self._client = None
        if allow_sync_methods:
            self._client = httpx.Client(**kwargs)
        self._timeout = timeout

    def request(
        self,
        method: str,
        url: str,
        headers: Mapping[str, str],
        post_data=None,
    ) -> Tuple[bytes, int, Mapping[str, str]]:
        if self._client is None:
            raise RuntimeError(
                "Stripe: HTTPXClient was initialized with allow_sync_methods=False, "
                "so it cannot be used for synchronous requests."
            )
        args, kwargs = self._get_request_args_kwargs(
            method, url, headers, post_data
        )
        try:
            response = self._client.request(*args, **kwargs)
        except Exception as e:
            self._handle_request_error(e)

        content = response.content
        status_code = response.status_code
        response_headers = response.headers
        return content, status_code, response_headers

    async def request_async(
        self,
        method: str,
        url: str,
        headers: Mapping[str, str],
        post_data=None,
    ) -> Tuple[bytes, int, Mapping[str, str]]:
        args, kwargs = self._get_request_args_kwargs(
            method, url, headers, post_data
        )
        try:
            response = await self._client_async.request(*args, **kwargs)
        except Exception as e:
            self._handle_request_error(e)

        content = response.content
        status_code = response.status_code
        response_headers = response.headers
        return content, status_code, response_headers

    async def request_async(
        self,
        method,
        url,
        headers,
        post_data=None,
    ):
        return await self._request_internal_async(
            method, url, headers, post_data, is_streaming=False
        )

    async def _request_internal_async(
        self, method, url, headers, post_data, is_streaming
    ):
        kwargs = {}

        if getattr(self._thread_local, "session", None) is None:
            self._thread_local.session = self._session or self.httpx.Client()

        try:
            try:
                result = self._thread_local.session.request(
                    method,
                    url,
                    headers=headers,
                    data=json.dumps(post_data),
                    timeout=self._timeout,
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

            content = result.content
            status_code = result.status_code

        except Exception:
            raise _error.APIConnectionError(
                "Unexpected error communicating with Unique. "
                "If this problem persists, let us know at support@unique.ch",
                http_status=500,
            )

        return content, status_code, result.headers
