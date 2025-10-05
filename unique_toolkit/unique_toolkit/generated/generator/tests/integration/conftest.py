"""Pytest fixtures for integration tests."""

import os
from pathlib import Path

import pytest
from dotenv import load_dotenv

from unique_toolkit._common.endpoint_requestor import RequestContext


@pytest.fixture(scope="session")
def integration_env():
    """Load environment variables from test.env file.

    Raises:
        FileNotFoundError: If test.env doesn't exist
        ValueError: If required environment variables are missing
    """
    env_file = Path(__file__).parent / "test.env"

    if not env_file.exists():
        pytest.skip(
            f"Integration tests require test.env file at {env_file}. "
            "Copy test.env.example and fill in your values."
        )

    load_dotenv(env_file)

    # Verify required vars exist
    required_vars = [
        "UNIQUE_APP_KEY",
        "UNIQUE_APP_ID",
        "UNIQUE_COMPANY_ID",
        "UNIQUE_USER_ID",
    ]

    missing = [var for var in required_vars if not os.getenv(var)]
    if missing:
        pytest.skip(f"Missing required env vars: {', '.join(missing)}")

    return {
        "app_key": os.getenv("UNIQUE_APP_KEY"),
        "app_id": os.getenv("UNIQUE_APP_ID"),
        "company_id": os.getenv("UNIQUE_COMPANY_ID"),
        "user_id": os.getenv("UNIQUE_USER_ID"),
        "api_version": os.getenv("UNIQUE_API_VERSION", "2024-10-01"),
        "base_url": os.getenv(
            "UNIQUE_BASE_URL", "https://gateway.qa.unique.app/public/chat-gen2"
        ),
        "test_chat_id": os.getenv("TEST_CHAT_ID"),
        "test_folder_scope_id": os.getenv("TEST_FOLDER_SCOPE_ID"),
        "test_assistant_id": os.getenv("TEST_ASSISTANT_ID"),
    }


@pytest.fixture(scope="session")
def request_context(integration_env):
    """Create RequestContext with auth headers from environment.

    Returns:
        RequestContext configured for API requests
    """
    headers = {
        "Authorization": f"Bearer {integration_env['app_key']}",
        "x-app-id": integration_env["app_id"],
        "x-company-id": integration_env["company_id"],
        "x-user-id": integration_env["user_id"],
        "x-api-version": integration_env["api_version"],
    }

    return RequestContext(headers=headers, base_url=integration_env["base_url"])


@pytest.fixture
def cleanup_items():
    """Track created items for cleanup after tests.

    Yields:
        List to append (resource_type, id) tuples for cleanup
    """
    items_to_cleanup = []

    yield items_to_cleanup

    # Cleanup logic would go here
    # For now, just collect the items
    if items_to_cleanup:
        print(f"\n⚠️  Remember to clean up: {items_to_cleanup}")
