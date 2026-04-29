import calendar
import datetime
import time
from collections import OrderedDict
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

import unique_sdk
from unique_sdk._api_requestor import (
    APIRequestor,
    _abs_api_url,
    _api_encode,
    _encode_datetime,
    _encode_nested_dict,
)
from unique_sdk._error import APIError

# Canonical fake gateway bases for URL composition tests (not real endpoints).
_TEST_CHAT_API_BASE = "https://gateway.example/public/chat-gen2"


@pytest.fixture
def mock_requests():
    with patch("unique_sdk._http_client.requests") as mock_requests:
        yield mock_requests


# Test _encode_datetime
@pytest.mark.parametrize(
    "dttime, expected_timestamp",
    [
        (
            datetime.datetime(2023, 1, 1, 0, 0, 0, tzinfo=None),
            time.mktime(datetime.datetime(2023, 1, 1).timetuple()),
        ),
        (
            datetime.datetime(2023, 1, 1, 0, 0, 0, tzinfo=datetime.timezone.utc),
            calendar.timegm(datetime.datetime(2023, 1, 1).utctimetuple()),
        ),
    ],
)
@patch("unique_sdk._api_requestor.calendar.timegm", side_effect=calendar.timegm)
def test_encode_datetime(mock_timegm, dttime, expected_timestamp):
    assert _encode_datetime(dttime) == int(expected_timestamp)


# Test _encode_nested_dict
def test_encode_nested_dict():
    key = "parent"
    data = {"child1": "value1", "child2": "value2"}
    expected_output = OrderedDict(
        [("parent[child1]", "value1"), ("parent[child2]", "value2")]
    )

    result = _encode_nested_dict(key, data)
    assert result == expected_output


@pytest.mark.parametrize(
    ("base", "path", "expected"),
    [
        (
            _TEST_CHAT_API_BASE,
            "/content/infos",
            f"{_TEST_CHAT_API_BASE}/content/infos",
        ),
        (
            f"{_TEST_CHAT_API_BASE}/",
            "/content/infos",
            f"{_TEST_CHAT_API_BASE}/content/infos",
        ),
        (
            f"'{_TEST_CHAT_API_BASE}'",
            "/content/infos",
            f"{_TEST_CHAT_API_BASE}/content/infos",
        ),
        (
            f"{_TEST_CHAT_API_BASE}/",
            "/content/infos'",
            f"{_TEST_CHAT_API_BASE}/content/infos",
        ),
        (
            f"{_TEST_CHAT_API_BASE}/",
            "/briefings/asst_1",
            f"{_TEST_CHAT_API_BASE}/briefings/asst_1",
        ),
    ],
)
@pytest.mark.ai
def test_AI_abs_api_url_joins_gateway_base_and_path(base, path, expected):
    """Purpose: ``api_base`` with trailing slash must not yield ``//`` before the route.

    Why this matters: GET/PUT paths like ``/content/infos`` or ``/briefings/{id}`` must
    match the same host as other resources; double slashes can break routing behind proxies.
    Setup summary: Compare _abs_api_url outputs for bases with/without trailing slash.
    """
    assert _abs_api_url(base, path) == expected


# Test _api_encode with different data types
@pytest.mark.parametrize(
    "data, expected_output",
    [
        ({"key1": "value1", "key2": None}, [("key1", "value1")]),
        ({"list": [1, 2, 3]}, [("list[0]", 1), ("list[1]", 2), ("list[2]", 3)]),
        ({"nested": {"key1": "val1"}}, [("nested[key1]", "val1")]),
        (
            {"date": datetime.datetime(2023, 1, 1)},
            [("date", int(time.mktime(datetime.datetime(2023, 1, 1).timetuple())))],
        ),
    ],
)
def test_api_encode(data, expected_output):
    result = list(_api_encode(data))
    assert result == expected_output


# Test _api_encode with nested dictionaries and lists
def test_api_encode_with_complex_data():
    data = {
        "key1": "value1",
        "list": [{"subkey1": "subval1"}, {"subkey2": "subval2"}],
        "date": datetime.datetime(2023, 1, 1, 0, 0, 0),
    }

    result = list(_api_encode(data))
    expected_output = [
        ("key1", "value1"),
        ("list[0][subkey1]", "subval1"),
        ("list[1][subkey2]", "subval2"),
        ("date", int(time.mktime(datetime.datetime(2023, 1, 1).timetuple()))),
    ]
    assert result == expected_output


# Test APIRequestor initialization
@patch("unique_sdk._http_client.requests")
def test_api_requestor_initialization(mock_requests):
    user_id = "test_user"
    company_id = "test_company"
    api_key = "test_key"
    app_id = "test_app"
    mock_requests.return_value = "response"

    requestor = APIRequestor(
        user_id=user_id, company_id=company_id, key=api_key, app_id=app_id
    )

    assert requestor.user_id == user_id
    assert requestor.company_id == company_id
    assert requestor.api_key == api_key
    assert requestor.app_id == app_id
    assert requestor.api_version == unique_sdk.api_version


# Test request_headers in APIRequestor
@patch("unique_sdk._http_client.requests")
def test_request_headers(mock_requests):
    user_id = "test_user"
    company_id = "test_company"
    api_key = "test_key"
    app_id = "test_app"
    method = "post"
    mock_requests.return_value = "response"

    requestor = APIRequestor(
        user_id=user_id, company_id=company_id, key=api_key, app_id=app_id
    )

    headers = requestor.request_headers(api_key, app_id, method)

    assert headers["Authorization"] == f"Bearer {api_key}"
    assert headers["x-user-id"] == user_id
    assert headers["x-company-id"] == company_id
    assert headers["x-api-version"] == requestor.api_version
    assert headers["x-app-id"] == app_id
    assert headers["Content-Type"] == "application/json"


@patch("unique_sdk._http_client.requests")
@pytest.mark.ai
def test_AI_request_headers_put_includes_json_body(mock_requests):
    """PUT requests send JSON like POST/PATCH so upstream receives a body.

    Why this matters: New REST upserts use PUT; missing Content-Type breaks the server.
    Setup summary: Requestor with user/company; headers for method put. Assert Content-Type.
    """
    mock_requests.return_value = "response"

    requestor = APIRequestor(user_id="u", company_id="c", key="k", app_id="a")

    headers = requestor.request_headers("k", "a", "put")
    assert headers["Content-Type"] == "application/json"


# Test _get_request_args method in APIRequestor
@patch("unique_sdk._http_client.requests")
@patch("unique_sdk._api_requestor._api_encode", return_value=[("key", "value")])
@patch(
    "unique_sdk._api_requestor._build_api_url",
    return_value="https://api.example.com/resource?key=value",
)
def test_get_request_args(mock_build_api_url, mock_api_encode, mock_requests):
    mock_requests.return_value = "response"
    requestor = APIRequestor(
        user_id="user_id", company_id="company_id", key="api_key", app_id="app_id"
    )

    method = "get"
    url = "/resource"
    params = {"key": "value"}

    method, abs_url, headers, post_data = requestor._get_request_args(
        method, url, params
    )

    assert method == "get"
    assert abs_url == "https://api.example.com/resource?key=value"
    assert headers["Authorization"] == "Bearer api_key"
    assert post_data is None


@patch("unique_sdk._http_client.requests")
@pytest.mark.ai
def test_AI_get_request_args_put_sends_json_body(mock_requests):
    """PUT forwards params as post_data for JSON serialization.

    Why this matters: Upsert endpoints use PUT with a JSON body; omitting this raised Unrecognized HTTP method.
    Setup summary: Requestor._get_request_args("put", ...) with body dict. Assert post_data matches.
    """
    mock_requests.return_value = "response"
    requestor = APIRequestor(
        user_id="user_id", company_id="company_id", key="api_key", app_id="app_id"
    )

    method, abs_url, headers, post_data = requestor._get_request_args(
        "put",
        "/briefings/astr-1",
        {
            "text": "hello",
            "generatedAt": "2020-01-01T00:00:00.000Z",
        },
    )

    assert method == "put"
    assert post_data["text"] == "hello"
    assert post_data["generatedAt"] == "2020-01-01T00:00:00.000Z"
    assert abs_url.endswith("/briefings/astr-1")


# Test handling of invalid request method
@patch("unique_sdk._http_client.requests")
def test_get_request_args_invalid_method(mock_requests):
    mock_requests.return_value = "response"
    requestor = APIRequestor(
        user_id="user_id", company_id="company_id", key="api_key", app_id="app_id"
    )

    with pytest.raises(unique_sdk._error.APIConnectionError):
        requestor._get_request_args("invalid_method", "/resource", {})


@patch("unique_sdk._http_client.requests")
def test_request_raw(mock_requests):
    # Set up the mock return value for the client's request
    mock_requests.return_value = "response"
    _client = MagicMock()
    _client.name = "request_name"
    _client.request.return_value = ("response_body", 200, {"Request-Id": "req_id"})

    # Initialize the APIRequestor with mocked client
    requestor = APIRequestor(
        user_id="user_id", company_id="company_id", key="api_key", app_id="app_id"
    )

    # Mock the _client inside the requestor instance
    requestor._client = _client

    # Perform the request
    rcontent, rcode, rheaders = requestor.request_raw("get", "/resource")

    # Assertions
    assert rcontent == "response_body"
    assert rcode == 200
    assert rheaders == {"Request-Id": "req_id"}

    # Ensure the client's request method was called correctly
    _client.request.assert_called_once_with(
        "get",
        _abs_api_url(requestor.api_base, "/resource"),
        requestor.request_headers("api_key", "app_id", "get"),
        None,
    )


# Test request_raw_async in APIRequestor
@pytest.mark.asyncio
async def test_request_raw_async():
    _client = MagicMock()
    _client.name = "request_name"
    _client.request_async = AsyncMock(
        return_value=("response_body", 200, {"Request-Id": "req_id"})
    )

    requestor = APIRequestor(
        user_id="user_id", company_id="company_id", key="api_key", app_id="app_id"
    )
    requestor._client = _client

    rcontent, rcode, rheaders = await requestor.request_raw_async("get", "/resource")

    assert rcontent == "response_body"
    assert rcode == 200
    assert rheaders == {"Request-Id": "req_id"}


def test_api_requestor_handle_error_response_with_original_error():
    requestor = APIRequestor(user_id="user_id", company_id="company_id")
    mock_response = {
        "error": {
            "message": "API error",
            "type": "api_error",
            "cause": {
                "error": {"message": "Test error", "code": "TEST"},
                "status": 500,
            },
        }
    }
    mock_rbody = '{"error": {"message": "API error"}}'
    mock_rcode = 500
    mock_rheaders = {}

    with pytest.raises(APIError) as excinfo:
        requestor.handle_error_response(
            mock_rbody, mock_rcode, mock_response, mock_rheaders
        )

    assert "(Original error) TEST: Test error" in str(excinfo.value)
