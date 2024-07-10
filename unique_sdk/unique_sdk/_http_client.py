import json
import threading
from typing import ClassVar

try:
    import requests
except ImportError:
    requests = None

import unique_sdk
from unique_sdk import _error


def new_default_http_client(*args, **kwargs) -> "HTTPClient":
    impl = RequestsClient
    return impl(*args, **kwargs)


class HTTPClient(object):
    name: ClassVar[str]

    def __init__(self):
        self._thread_local = threading.local()

    def request(self, method, url, headers, post_data=None):
        raise NotImplementedError("HTTPClient subclasses must implement `request`")


class RequestsClient(HTTPClient):
    name = "requests"

    def __init__(self, timeout=600, session=None, **kwargs):
        super(RequestsClient, self).__init__(**kwargs)
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
