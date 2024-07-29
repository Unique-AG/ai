import json
import threading
from typing import ClassVar, Mapping, Optional, Tuple

try:
    import requests
except ImportError:
    requests = None

try:
    import anyio
    import httpx
except ImportError:
    httpx = None
    anyio = None

try:
    import aiohttp
except ImportError:
    aiohttp = None

import unique_sdk
from unique_sdk import _error


def new_default_http_client(*args, **kwargs) -> "HTTPClient":
    impl = RequestsClient
    return impl(*args, **kwargs)


def new_http_client_async_fallback(*args, **kwargs) -> "HTTPClient":
    if aiohttp:
        impl = AIOHTTPClient
    elif httpx:
        impl = HTTPXClient
    else:
        impl = NoImportFoundAsyncClient
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
            method,
            url,
            headers,
            post_data,
            is_streaming=False,
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
        timeout: Optional[float] = 600,
        **kwargs,
    ):
        super(HTTPXClient, self).__init__(**kwargs)

        assert httpx is not None
        assert anyio is not None

        self.httpx = httpx
        self.anyio = anyio

        self._client_async = httpx.AsyncClient(**kwargs)
        self._client = httpx.Client(**kwargs)
        self._timeout = timeout

    def _get_request_args_kwargs(
        self, method: str, url: str, headers: Mapping[str, str], post_data
    ):
        kwargs = {}

        if self._timeout:
            kwargs["timeout"] = self._timeout
        return [
            (method, url),
            {"headers": headers, "data": json.dumps(post_data) or {}, **kwargs},
        ]

    def request(
        self,
        method: str,
        url: str,
        headers: Mapping[str, str],
        post_data=None,
    ) -> Tuple[bytes, int, Mapping[str, str]]:
        args, kwargs = self._get_request_args_kwargs(method, url, headers, post_data)
        try:
            response = self._client.request(*args, **kwargs)
        except Exception:
            raise _error.APIConnectionError(
                "Unexpected error communicating with Unique. "
                "If this problem persists, let us know at support@unique.ch",
                http_status=500,
            )

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
        args, kwargs = self._get_request_args_kwargs(method, url, headers, post_data)
        try:
            response = await self._client_async.request(*args, **kwargs)
        except Exception:
            raise _error.APIConnectionError(
                "Unexpected error communicating with Unique. "
                "If this problem persists, let us know at support@unique.ch",
                http_status=500,
            )

        content = response.content
        status_code = response.status_code
        response_headers = response.headers
        return content, status_code, response_headers


class AIOHTTPClient(HTTPClient):
    name = "aiohttp"

    def __init__(
        self,
        timeout: Optional[float] = 80,
        **kwargs,
    ):
        super(AIOHTTPClient, self).__init__(**kwargs)

        if aiohttp is None:
            raise ImportError(
                "Unexpected: tried to initialize AIOHTTPClient but the aiohttp module is not present."
            )

        self._timeout = timeout
        self._cached_session = None

    @property
    def _session(self):
        assert aiohttp is not None

        if self._cached_session is None:
            kwargs = {}
            kwargs["connector"] = aiohttp.TCPConnector(verify_ssl=False)
            self._cached_session = aiohttp.ClientSession(**kwargs)

        return self._cached_session

    def request(self) -> Tuple[bytes, int, Mapping[str, str]]:
        raise NotImplementedError(
            "AIOHTTPClient does not support synchronous requests."
        )

    def _get_request_args_kwargs(
        self, method: str, url: str, headers: Mapping[str, str], post_data
    ):
        args = (method, url)
        kwargs = {}
        if self._timeout:
            kwargs["timeout"] = self._timeout

        kwargs["headers"] = headers
        kwargs["data"] = json.dumps(post_data)
        return args, kwargs

    async def request_async(
        self,
        method: str,
        url: str,
        headers: Mapping[str, str],
        post_data=None,
    ) -> Tuple[bytes, int, Mapping[str, str]]:
        (
            content,
            status_code,
            response_headers,
        ) = await self._internal_request_async(
            method, url, headers, post_data=post_data
        )

        return (await content.read()), status_code, response_headers

    async def _internal_request_async(
        self, method: str, url: str, headers: Mapping[str, str], post_data=None
    ):
        args, kwargs = self._get_request_args_kwargs(method, url, headers, post_data)
        try:
            response = await self._session.request(*args, **kwargs)
        except Exception:
            raise _error.APIConnectionError(
                "Unexpected error communicating with Unique. "
                "If this problem persists, let us know at support@unique.ch",
                http_status=500,
            )

        content = response.content
        status_code = response.status
        response_headers = response.headers
        return content, status_code, response_headers


class NoImportFoundAsyncClient(HTTPClient):
    def __init__(self, **kwargs):
        super(NoImportFoundAsyncClient, self).__init__(**kwargs)

    @staticmethod
    def raise_async_client_import_error():
        raise ImportError(
            (
                "Import httpx and aiohttp not found. To make async http requests,"
                "you must either install httpx or aiohttp."
            )
        )

    async def request_async(
        self, method: str, url: str, headers: Mapping[str, str], post_data=None
    ):
        self.raise_async_client_import_error()

    async def request_stream_async(
        self, method: str, url: str, headers: Mapping[str, str], post_data=None
    ):
        self.raise_async_client_import_error()
