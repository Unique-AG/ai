# import threading
from unittest.mock import AsyncMock, Mock, patch

import pytest

from unique_sdk import _error
from unique_sdk._http_client import (
    AIOHTTPClient,
    HTTPXClient,
    NoImportFoundAsyncClient,
    RequestsClient,
    new_default_http_client,
    new_http_client_async_fallback,
)


# Mock requests, httpx, and aiohttp to simulate dependencies
@pytest.fixture
def mock_requests():
    with patch("unique_sdk._http_client.requests") as mock_requests:
        yield mock_requests


@pytest.fixture
def mock_httpx():
    with patch("unique_sdk._http_client.httpx") as mock_httpx:
        mock_httpx.AsyncClient.return_value.request = AsyncMock()
        yield mock_httpx


@pytest.fixture
def mock_anyio():
    with patch("unique_sdk._http_client.anyio") as mock_anyio:
        yield mock_anyio


@pytest.fixture
def mock_aiohttp():
    with patch("unique_sdk._http_client.aiohttp") as mock_aiohttp:
        mock_aiohttp.ClientSession.return_value.close = AsyncMock()
        mock_aiohttp.ClientSession.return_value.request = AsyncMock()
        yield mock_aiohttp


@pytest.fixture
def mock_threading():
    with patch("unique_sdk._http_client.threading.local") as mock_local:
        mock_local_instance = Mock()
        mock_local.return_value = mock_local_instance
        yield mock_local_instance


# Testing new_default_http_client
def test_new_default_http_client(mock_anyio):
    mock_anyio.return_value = True
    client = new_default_http_client()
    assert isinstance(client, RequestsClient)


# Testing new_http_client_async_fallback
def test_new_http_client_async_fallback_httpx(mock_httpx, mock_anyio):
    mock_httpx.return_value = True
    mock_anyio.return_value = True
    client = new_http_client_async_fallback()
    assert isinstance(client, HTTPXClient)


def test_new_http_client_async_fallback_aiohttp(mock_aiohttp, mock_anyio):
    mock_anyio.return_value = None
    mock_aiohttp.return_value = True
    client = new_http_client_async_fallback()
    assert isinstance(client, AIOHTTPClient)


def test_new_http_client_async_fallback_no_imports(mock_anyio):
    mock_anyio.return_value = None
    client = new_http_client_async_fallback()
    assert isinstance(client, NoImportFoundAsyncClient)


# Testing RequestsClient
def test_requests_client_sync(mock_requests):
    # Mock response from requests
    mock_response = Mock()
    mock_response.content = b"mocked response"
    mock_response.status_code = 200
    mock_response.headers = {"content-type": "application/json"}
    mock_requests.Session.return_value.request.return_value = mock_response

    client = RequestsClient()
    content, status, headers = client.request(
        "GET", "https://mock-url", {"header": "value"}
    )

    assert content == b"mocked response"
    assert status == 200
    assert headers["content-type"] == "application/json"


def test_requests_client_error(mock_requests):
    mock_requests.Session.return_value.request.side_effect = Exception("Network error")

    client = RequestsClient()

    with pytest.raises(_error.APIConnectionError):
        client.request("GET", "https://mock-url", {"header": "value"})


def test_requests_client_close(mock_requests, mock_threading):
    # Simulate a session in the thread local storage
    mock_threading.session = mock_requests.Session.return_value

    client = RequestsClient()

    # Close the client, which should close the session
    client.close()

    # Ensure the session's close method was called
    mock_threading.session.close.assert_called_once()

    # After closing, thread-local session should still exist but closed
    assert mock_threading.session is not None


def test_requests_client_no_session_to_close(mock_requests, mock_threading):
    # Simulate that there's no session in thread local
    mock_threading.session = None

    client = RequestsClient()

    # Closing should not raise any errors or try to close a non-existent session
    client.close()

    # Ensure that no close was attempted
    if mock_threading.session is not None:
        mock_threading.session.close.assert_not_called()


# Testing HTTPXClient
@pytest.mark.asyncio
async def test_httpx_client_async_request(mock_httpx, mock_anyio):
    mock_response = Mock()
    mock_response.content = b"async response"
    mock_response.status_code = 200
    mock_response.headers = {"content-type": "application/json"}
    mock_httpx.AsyncClient.return_value.request.return_value = mock_response

    client = HTTPXClient()
    content, status, headers = await client.request_async(
        "GET", "https://mock-url", {"header": "value"}
    )

    assert content == b"async response"
    assert status == 200
    assert headers["content-type"] == "application/json"


def test_httpx_client_sync_request(mock_httpx, mock_anyio):
    mock_response = Mock()
    mock_response.content = b"sync response"
    mock_response.status_code = 200
    mock_response.headers = {"content-type": "application/json"}
    mock_httpx.Client.return_value.request.return_value = mock_response

    client = HTTPXClient()
    content, status, headers = client.request(
        "GET", "https://mock-url", {"header": "value"}
    )

    assert content == b"sync response"
    assert status == 200
    assert headers["content-type"] == "application/json"


# Testing AIOHTTPClient
@pytest.mark.asyncio
async def test_aiohttp_client_async_request(mock_aiohttp):
    mock_response = Mock()
    mock_response.content.read = AsyncMock(return_value=b"async aiohttp response")
    mock_response.status = 200
    mock_response.headers = {"content-type": "application/json"}
    mock_aiohttp.ClientSession.return_value.request.return_value = mock_response

    client = AIOHTTPClient()
    content, status, headers = await client.request_async(
        "GET", "https://mock-url", {"header": "value"}
    )

    assert content == b"async aiohttp response"
    assert status == 200
    assert headers["content-type"] == "application/json"


@pytest.mark.asyncio
async def test_aiohttp_client_async_error(mock_aiohttp):
    mock_aiohttp.ClientSession.return_value.request.side_effect = Exception(
        "Network error"
    )

    client = AIOHTTPClient()

    with pytest.raises(_error.APIConnectionError):
        await client.request_async("GET", "https://mock-url", {"header": "value"})


@pytest.mark.asyncio
async def test_aiohttp_client_close(mock_aiohttp):
    client = AIOHTTPClient()
    await client.close_async()
    assert mock_aiohttp.ClientSession.return_value.close.called


# Testing NoImportFoundAsyncClient
@pytest.mark.asyncio
async def test_no_import_found_async_client_request_error():
    client = NoImportFoundAsyncClient()
    with pytest.raises(ImportError):
        await client.request_async("GET", "https://mock-url", {"header": "value"})


@pytest.mark.asyncio
async def test_no_import_found_async_client_close_error():
    client = NoImportFoundAsyncClient()
    with pytest.raises(ImportError):
        await client.close_async()
