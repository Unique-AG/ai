"""
Apply integration-test fixtures (SDK setup, folder cleanup) only to tests in this package.
Unit tests in tests/ do not use these, so they run in CI without integration_test.env.
"""

import pytest


@pytest.fixture(scope="session", autouse=True)
def _auto_setup_unique_sdk(setup_unique_sdk: None) -> None:
    """Ensure SDK is configured for all tests in api_resources (integration tests)."""
    return setup_unique_sdk


@pytest.fixture(scope="module", autouse=True)
def _auto_setup_folder_cleanup(setup_folder_cleanup: None) -> None:
    """Ensure folder cleanup runs for integration test modules."""
    return setup_folder_cleanup


@pytest.fixture(scope="module", autouse=True)
def _auto_teardown_folder_cleanup(teardown_folder_cleanup: None) -> None:
    """Ensure folder teardown runs for integration test modules."""
    return teardown_folder_cleanup
