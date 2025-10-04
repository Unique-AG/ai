from unittest.mock import Mock, patch

from unique_toolkit.app.dev_util import get_sse_client
from unique_toolkit.app.unique_settings import UniqueSettings


@patch("unique_toolkit.app.dev_util.SSEClient")
def test_get_sse_client_configuration(
    mock_sse_client: Mock,
    base_unique_settings: UniqueSettings,
):
    # Test data
    subscriptions = ["event1", "event2"]
    expected_url = "https://api.example.com/public/event-socket/events/stream?subscriptions=event1,event2"

    # Use the values from the fixture
    expected_headers = {
        "Authorization": "Bearer test-key",
        "x-app-id": "test-id",
        "x-company-id": "test-company",
        "x-user-id": "test-user",
        "x-api-version": "2023-12-06",
    }

    # Call the function
    get_sse_client(base_unique_settings, subscriptions)

    # Verify SSEClient was called with correct arguments
    mock_sse_client.assert_called_once_with(url=expected_url, headers=expected_headers)
