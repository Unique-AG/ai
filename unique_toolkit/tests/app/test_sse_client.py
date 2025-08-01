from unittest.mock import patch

import pytest
from pydantic import SecretStr

from unique_toolkit.app.sse_client import get_sse_client
from unique_toolkit.app.unique_settings import UniqueApp, UniqueAuth, UniqueSettings


@pytest.fixture
def unique_settings():
    app = UniqueApp(
        id=SecretStr("test-app-id"),
        key=SecretStr("test-api-key"),
        base_url="https://api.example.com",
        endpoint="test-endpoint",
        endpoint_secret=SecretStr("test-endpoint-secret"),
    )

    auth = UniqueAuth(
        company_id=SecretStr("test-company-id"),
        user_id=SecretStr("test-user-id"),
    )

    return UniqueSettings(auth=auth, app=app)


@patch("unique_toolkit.app.sse_client.SSEClient")
def test_get_sse_client_configuration(mock_sse_client, unique_settings):
    # Test data
    subscriptions = ["event1", "event2"]
    expected_url = "https://api.example.com/public/event-socket/events/stream?subscriptions=event1,event2"
    expected_headers = {
        "Authorization": "Bearer test-api-key",
        "x-app-id": "test-app-id",
        "x-company-id": "test-company-id",
    }

    # Call the function
    get_sse_client(unique_settings, subscriptions)

    # Verify SSEClient was called with correct arguments
    mock_sse_client.assert_called_once_with(url=expected_url, headers=expected_headers)
