from unittest.mock import patch

import pytest
from pydantic import SecretStr

from unique_toolkit.app.dev_util import get_sse_client
from unique_toolkit.app.unique_settings import (
    UniqueApi,
    UniqueApp,
    UniqueAuth,
    UniqueSettings,
)


@pytest.fixture
def unique_settings():
    """
    Create UniqueSettings for testing.

    Note: We cannot use the normal constructor approach like:
    UniqueApp(id=SecretStr("test-app-id"), key=SecretStr("test-api-key"), ...)

    This is because when UniqueApp uses validation_alias=AliasChoices(...),
    pydantic BaseSettings prioritizes environment variable lookup over constructor
    arguments. Even when no matching environment variables exist, it falls back
    to default values instead of using the provided constructor arguments.

    To work around this, we create the objects with default constructors (which
    triggers environment loading and warnings) and then directly set the field
    values afterwards to override them with our test values.
    """
    # Create settings objects and then directly set the field values

    # Create app settings
    app = UniqueApp()
    app.id = SecretStr("test-app-id")
    app.key = SecretStr("test-api-key")
    app.base_url = "https://api.example.com"
    app.endpoint = "test-endpoint"
    app.endpoint_secret = SecretStr("test-endpoint-secret")

    # Create auth settings
    auth = UniqueAuth()
    auth.company_id = SecretStr("test-company-id")
    auth.user_id = SecretStr("test-user-id")

    # Create api settings
    api = UniqueApi()
    api.base_url = "https://api.example.com"
    api.version = "2023-12-06"

    return UniqueSettings(auth=auth, app=app, api=api)


@patch("unique_toolkit.app.dev_util.SSEClient")
def test_get_sse_client_configuration(mock_sse_client, unique_settings):
    # Test data
    subscriptions = ["event1", "event2"]
    expected_url = "https://api.example.com/public/event-socket/events/stream?subscriptions=event1,event2"
    expected_headers = {
        "Authorization": "Bearer test-api-key",
        "x-app-id": "test-app-id",
        "x-company-id": "test-company-id",
        "x-user-id": "test-user-id",
        "x-api-version": "2023-12-06",
    }

    # Call the function
    get_sse_client(unique_settings, subscriptions)

    # Verify SSEClient was called with correct arguments
    mock_sse_client.assert_called_once_with(url=expected_url, headers=expected_headers)
