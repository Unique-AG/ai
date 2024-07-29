import calendar
import datetime
import json
import platform
import time
from collections import OrderedDict
from typing import Any, Dict, Mapping, NoReturn, Optional, cast
from urllib.parse import urlencode, urlsplit, urlunsplit

import unique_sdk
from unique_sdk import _error, _http_client, _util, _version
from unique_sdk._unique_response import UniqueResponse


def _encode_datetime(dttime: datetime.datetime):
    if dttime.tzinfo and dttime.tzinfo.utcoffset(dttime) is not None:
        utc_timestamp = calendar.timegm(dttime.utctimetuple())
    else:
        utc_timestamp = time.mktime(dttime.timetuple())

    return int(utc_timestamp)


def _encode_nested_dict(key, data, fmt="%s[%s]"):
    d = OrderedDict()
    for subkey, subvalue in data.items():
        d[fmt % (key, subkey)] = subvalue
    return d


def _api_encode(data):
    for key, value in data.items():
        if value is None:
            continue
        elif hasattr(value, "unique_id"):
            yield (key, value.unique_id)
        elif isinstance(value, list) or isinstance(value, tuple):
            for i, sv in enumerate(value):
                if isinstance(sv, dict):
                    subdict = _encode_nested_dict("%s[%d]" % (key, i), sv)
                    for k, v in _api_encode(subdict):
                        yield (k, v)
                else:
                    yield ("%s[%d]" % (key, i), sv)
        elif isinstance(value, dict):
            subdict = _encode_nested_dict(key, value)
            for subkey, subvalue in _api_encode(subdict):
                yield (subkey, subvalue)
        elif isinstance(value, datetime.datetime):
            yield (key, _encode_datetime(value))
        else:
            yield (key, value)


def _build_api_url(url, query):
    scheme, netloc, path, base_query, fragment = urlsplit(url)

    if base_query:
        query = "%s&%s" % (base_query, query)

    return urlunsplit((scheme, netloc, path, query, fragment))


class APIRequestor(object):
    api_key: Optional[str]
    app_id: Optional[str]
    api_base: str
    api_version: str
    user_id: Optional[str]
    company_id: Optional[str]

    def __init__(
        self,
        user_id: Optional[str],
        company_id: Optional[str],
        key=None,
        app_id=None,
    ):
        self.api_base = unique_sdk.api_base
        self.api_key = key
        self.app_id = app_id
        self.api_version = unique_sdk.api_version
        self.user_id = user_id
        self.company_id = company_id

        if unique_sdk.default_http_client:
            self._client = unique_sdk.default_http_client
        else:
            unique_sdk.default_http_client = _http_client.new_default_http_client(
                async_fallback_client=_http_client.new_http_client_async_fallback(),
            )
            self._client = unique_sdk.default_http_client

    def request(
        self,
        method: str,
        url: str,
        params: Optional[Mapping[str, Any]] = None,
        headers: Optional[Mapping[str, str]] = None,
    ) -> UniqueResponse:
        rbody, rcode, rheaders = self.request_raw(
            method.lower(), url, params, headers, is_streaming=False
        )
        resp = self.interpret_response(rbody, rcode, rheaders)
        return resp

    async def request_async(
        self,
        method: str,
        url: str,
        params: Optional[Mapping[str, Any]] = None,
        headers: Optional[Mapping[str, str]] = None,
    ) -> UniqueResponse:
        rbody, rcode, rheaders = await self.request_raw_async(
            method.lower(), url, params, headers, is_streaming=False
        )
        resp = self.interpret_response(rbody, rcode, rheaders)
        return resp

    def request_headers(self, api_key, app_id, method):
        user_agent = "Unique SDK/v1 PythonBindings/%s" % (_version.VERSION,)

        ua = {
            "bindings_version": _version.VERSION,
            "lang": "python",
            "publisher": "unique",
            "httplib": self._client.name,
        }
        for attr, func in [
            ["lang_version", platform.python_version],
            ["platform", platform.platform],
            ["uname", lambda: " ".join(platform.uname())],
        ]:
            try:
                val = func()
            except Exception:
                val = "(disabled)"
            ua[attr] = val

        headers = {
            "X-Unique-Client-User-Agent": json.dumps(ua),
            "User-Agent": user_agent,
            "Authorization": "Bearer %s" % (api_key,),
        }

        if method == "post" or method == "patch":
            headers["Content-Type"] = "application/json"

        if self.user_id:
            headers["x-user-id"] = self.user_id
        if self.company_id:
            headers["x-company-id"] = self.company_id

        headers["x-api-version"] = self.api_version
        headers["x-app-id"] = app_id

        return headers

    def request_raw(
        self,
        method: str,
        url: str,
        params: Optional[Mapping[str, Any]] = None,
        supplied_headers: Optional[Mapping[str, str]] = None,
        is_streaming: bool = False,
    ):
        method, abs_url, headers, post_data = self._get_request_args(
            method,
            url,
            params,
            supplied_headers,
        )

        _util.log_info("Request to Unique", method=method, path=abs_url)
        _util.log_debug(
            "Request details",
            data=post_data,
            headers=headers,
            api_version=self.api_version,
        )

        rcontent, rcode, rheaders = self._client.request(
            method, abs_url, headers, post_data
        )

        _util.log_info("Unique response", path=abs_url, status=rcode)
        _util.log_debug("Unique response body", body=rcontent)

        if "Request-Id" in rheaders:
            request_id = rheaders["Request-Id"]
            _util.log_debug("Unique request id", request_id=request_id)

        return rcontent, rcode, rheaders

    async def request_raw_async(
        self,
        method: str,
        url: str,
        params: Optional[Mapping[str, Any]] = None,
        supplied_headers: Optional[Mapping[str, str]] = None,
        is_streaming: bool = False,
    ):
        method, abs_url, headers, post_data = self._get_request_args(
            method,
            url,
            params,
            supplied_headers,
        )

        _util.log_info("Async request to Unique", method=method, path=abs_url)
        _util.log_debug(
            "Async request details",
            data=post_data,
            headers=headers,
            api_version=self.api_version,
        )

        rcontent, rcode, rheaders = await self._client.request_async(
            method, abs_url, headers, post_data
        )

        _util.log_info("Unique response", path=abs_url, status=rcode)
        _util.log_debug("Unique response body", body=rcontent)

        if "Request-Id" in rheaders:
            request_id = rheaders["Request-Id"]
            _util.log_debug("Unique request id", request_id=request_id)

        return rcontent, rcode, rheaders

    def _get_request_args(
        self,
        method: str,
        url: str,
        params: Optional[Mapping[str, Any]] = None,
        supplied_headers: Optional[Mapping[str, str]] = None,
    ):
        supplied_headers_dict: Optional[Dict[str, str]] = (
            dict(supplied_headers) if supplied_headers is not None else None
        )

        if params is not None:
            res = self.rename_keys(params)
            # casting needed due to list processing in rename_keys
            params = cast(Optional[Mapping[str, Any]], res)

        if self.api_key:
            my_api_key = self.api_key
        else:
            from unique_sdk import api_key

            my_api_key = api_key

        if my_api_key is None:
            raise _error.AuthenticationError(
                "No API key provided. (HINT: set your API key using "
                '"unique_sdk.api_key = <API-KEY>"). You can generate API keys '
                "from the Unique web interface.  See https://unique.app/api "
                "for details, or email support@unique.ch if you have any "
                "questions."
            )

        if self.app_id:
            my_app_id = self.app_id
        else:
            from unique_sdk import app_id

            my_app_id = app_id

        if my_app_id is None:
            raise _error.AuthenticationError(
                "No App ID provided. (HINT: set your App ID using "
                '"unique_sdk.app_id = <APP-ID>"). You can generate App IDs '
                "from the Unique web interface.  See https://unique.app/api "
                "for details, or email support@unique.ch if you have any "
                "questions."
            )

        abs_url = "%s%s" % (self.api_base, url)

        encoded_params = urlencode(list(_api_encode(params or {})))

        # Don't use strict form encoding by changing the square bracket control
        # characters back to their literals. This is fine by the server, and
        # makes these parameter strings easier to read.
        encoded_params = encoded_params.replace("%5B", "[").replace("%5D", "]")

        if method == "get" or method == "delete":
            if params:
                abs_url = _build_api_url(abs_url, encoded_params)
            post_data = None
        elif method == "post" or method == "patch":
            post_data = params
        else:
            raise _error.APIConnectionError(
                "Unrecognized HTTP method %r.  This may indicate a bug in the "
                "Unique SDK bindings.  Please contact support@unique.ch for "
                "assistance." % (method,)
            )

        headers = self.request_headers(my_api_key, my_app_id, method)
        if supplied_headers_dict is not None:
            for key, value in supplied_headers_dict.items():
                headers[key] = value

        return method, abs_url, headers, post_data

    def rename_keys(self, obj: Optional[Mapping[str, Any]]):
        if obj is None:
            return None
        if isinstance(obj, dict):
            new_dict = {}
            for key, value in obj.items():
                # `not` and `in` are reserved keywords in Python.
                # To be able to use them, we suffix them with `_` and
                # remove the underscore before sending the request.
                new_key = key.replace("not_", "not").replace("in_", "in")
                # Recursively process nested dictionaries
                new_dict[new_key] = self.rename_keys(value)
            return new_dict
        elif isinstance(obj, list):
            # Process each item in the list if it's a list
            return [self.rename_keys(item) for item in obj]
        else:
            # Return the item itself if it's neither a dict nor a list
            return obj

    def _should_handle_code_as_error(self, rcode):
        return not 200 <= rcode < 300

    def interpret_response(
        self, rbody: object, rcode: int, rheaders: Mapping[str, str]
    ) -> UniqueResponse:
        try:
            if hasattr(rbody, "decode"):
                rbody = cast(bytes, rbody).decode("utf-8")
            resp = UniqueResponse(
                cast(str, rbody),
                rcode,
                rheaders,
            )
        except Exception:
            raise _error.APIError(
                "Invalid response body from API: %s "
                "(HTTP response code was %d)" % (rbody, rcode),
                cast(bytes, rbody),
                rcode,
                rheaders,
            )
        if self._should_handle_code_as_error(rcode):
            self.handle_error_response(rbody, rcode, resp.data, rheaders)
        return resp

    def handle_error_response(self, rbody, rcode, resp, rheaders) -> NoReturn:
        try:
            error_data = resp["error"]
        except (KeyError, TypeError):
            raise _error.APIError(
                "Invalid response object from API: %r (HTTP response code "
                "was %d)" % (rbody, rcode),
                rbody,
                rcode,
                resp,
            )

        err = None

        if isinstance(error_data, str):
            err = _error.APIError(error_data, rbody, rcode, resp, rheaders)

        if err is None:
            err = self.specific_api_error(rbody, rcode, resp, rheaders, error_data)

        raise err

    def specific_api_error(self, rbody, rcode, resp, rheaders, error_data):
        _util.log_info(
            "Unique error received",
            error_code=error_data.get("code"),
            error_type=error_data.get("type"),
            error_message=error_data.get("message"),
            error_params=error_data.get("params"),
        )

        if rcode in [400, 404]:
            return _error.InvalidRequestError(
                error_data.get("message"),
                error_data.get("params"),
                error_data.get("code"),
                rbody,
                rcode,
                resp,
                rheaders,
            )
        elif rcode == 401:
            return _error.AuthenticationError(
                error_data.get("message"), rbody, rcode, resp, rheaders
            )
        elif rcode == 403:
            return _error.PermissionError(
                error_data.get("message"), rbody, rcode, resp, rheaders
            )
        else:
            return _error.APIError(
                error_data.get("message"), rbody, rcode, resp, rheaders
            )
