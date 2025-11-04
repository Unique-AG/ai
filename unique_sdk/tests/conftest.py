"""
Pytest configuration and fixtures for integration tests.
"""

from collections.abc import Generator
from pathlib import Path
from typing import Any, cast

import pytest
from dotenv import dotenv_values

import unique_sdk
from tests.test_config import IntegrationTestConfig
from unique_sdk.api_resources._folder import Folder


@pytest.fixture(scope="session")
def integration_test_config() -> IntegrationTestConfig:
    """
    Load integration test configuration from .env file.

    Requires:
        tests/.env file with all required environment variables

    Returns:
        IntegrationTestConfig instance with all required configuration

    Raises:
        ValueError: If .env file is missing or required configuration is missing
    """
    # Load from .env file in tests directory
    env_file = Path(__file__).parent / "integration_test.env"

    if not env_file.exists():
        pytest.skip(
            f"Integration test .env file not found at {env_file}. "
            + "Please create tests/.env with all required environment variables."
        )

    env_vars = dotenv_values(env_file)

    try:
        config = IntegrationTestConfig.from_env(env_vars)
        return config
    except ValueError as e:
        pytest.skip(f"Integration test configuration missing: {e}")


@pytest.fixture(scope="session", autouse=True)
def setup_unique_sdk(integration_test_config: IntegrationTestConfig) -> None:
    """
    Configure unique_sdk with API credentials and base URL from test configuration.
    This fixture runs once per test session and sets up the SDK.
    """
    unique_sdk.api_key = integration_test_config.api_key
    unique_sdk.app_id = integration_test_config.app_id
    unique_sdk.api_base = integration_test_config.base_url


@pytest.fixture(scope="module")
def created_folders() -> Generator[list[str], None, None]:
    """
    Track folder paths created during tests.
    This fixture maintains a list of folder paths that need to be cleaned up.
    """
    folders: list[str] = []
    yield folders
    # Cleanup happens in teardown_folder_cleanup fixture


@pytest.fixture(scope="module", autouse=True)
def setup_folder_cleanup(
    integration_test_config: IntegrationTestConfig,
) -> None:
    """
    Setup: Clean root folder before tests start.
    Ensures we start with only the root folder (empty root).
    """
    try:
        # Get all root folders
        result = Folder.get_infos(
            user_id=integration_test_config.user_id,
            company_id=integration_test_config.company_id,
        )

        # Extract folderInfos from the response
        # Note: API returns dict despite type annotation saying list
        result_dict = cast(dict[str, Any], cast(object, result))
        root_folders = result_dict.get("folderInfos", [])

        # Delete all folders except the root folder itself
        root_folder_id = integration_test_config.root_scope_id
        for folder in root_folders:
            if folder.get("id") != root_folder_id:
                try:
                    # Try to delete by scopeId first
                    _ = Folder.delete(
                        user_id=integration_test_config.user_id,
                        company_id=integration_test_config.company_id,
                        scopeId=folder["id"],
                    )
                except Exception:
                    # Ignore cleanup errors during setup
                    pass
    except Exception:
        # If cleanup fails, log but don't fail the test suite
        pass


@pytest.fixture(scope="module", autouse=True)
def teardown_folder_cleanup(
    integration_test_config: IntegrationTestConfig,
    created_folders: list[str],
) -> Generator[None, None, None]:
    """
    Teardown: Clean up all folders created during tests.
    This runs after all tests in the module complete.
    """
    yield  # Let tests run first

    # Cleanup: Delete all folders created during tests
    for folder_path in created_folders:
        try:
            _ = Folder.delete(
                user_id=integration_test_config.user_id,
                company_id=integration_test_config.company_id,
                folderPath=folder_path,
            )
        except Exception:
            pass  # Ignore cleanup errors during teardown
