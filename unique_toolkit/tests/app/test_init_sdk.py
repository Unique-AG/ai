"""Tests for init_sdk.py functionality."""

from unittest.mock import patch

import pytest

from unique_toolkit.app.init_sdk import (
    get_endpoint_secret,
    get_env,
    init_sdk,
    init_unique_sdk,
)


@pytest.mark.ai_generated
class TestGetEnv:
    """Test the get_env function."""

    def test_get_env_with_existing_variable(self, monkeypatch):
        """Test getting an existing environment variable."""
        monkeypatch.setenv("TEST_VAR", "test_value")
        assert get_env("TEST_VAR") == "test_value"

    def test_get_env_with_default(self):
        """Test getting a non-existing environment variable with default."""
        assert get_env("NON_EXISTING_VAR", default="default_value") == "default_value"

    def test_get_env_with_none_default(self):
        """Test getting a non-existing environment variable with None default."""
        assert get_env("NON_EXISTING_VAR", default=None) is None

    def test_get_env_strict_mode_with_existing_variable(self, monkeypatch):
        """Test strict mode with existing variable."""
        monkeypatch.setenv("TEST_VAR", "test_value")
        assert get_env("TEST_VAR", strict=True) == "test_value"

    def test_get_env_strict_mode_with_missing_variable(self):
        """Test strict mode with missing variable raises ValueError."""
        with pytest.raises(ValueError, match="NON_EXISTING_VAR is not set"):
            get_env("NON_EXISTING_VAR", strict=True)

    def test_get_env_strict_mode_with_default(self):
        """Test strict mode with default value."""
        # When strict=True and no value exists, it should raise ValueError even with default
        with pytest.raises(ValueError, match="NON_EXISTING_VAR is not set"):
            get_env("NON_EXISTING_VAR", default="default", strict=True)


@pytest.mark.ai_generated
class TestInitSdk:
    """Test the deprecated init_sdk function."""

    @patch("unique_toolkit.app.init_sdk.unique_sdk")
    def test_init_sdk_with_strict_all_vars_false(self, mock_unique_sdk):
        """Test init_sdk with strict_all_vars=False."""
        with patch("unique_toolkit.app.init_sdk.get_env") as mock_get_env:
            mock_get_env.side_effect = ["dummy_key", "dummy_id", "dummy_base"]

            init_sdk(strict_all_vars=False)

            mock_get_env.assert_any_call("API_KEY", default="dummy", strict=False)
            mock_get_env.assert_any_call("APP_ID", default="dummy", strict=False)
            mock_get_env.assert_any_call("API_BASE", default=None, strict=False)

            assert mock_unique_sdk.api_key == "dummy_key"
            assert mock_unique_sdk.app_id == "dummy_id"
            assert mock_unique_sdk.api_base == "dummy_base"

    @patch("unique_toolkit.app.init_sdk.unique_sdk")
    def test_init_sdk_with_strict_all_vars_true(self, mock_unique_sdk):
        """Test init_sdk with strict_all_vars=True."""
        with patch("unique_toolkit.app.init_sdk.get_env") as mock_get_env:
            mock_get_env.side_effect = ["strict_key", "strict_id", "strict_base"]

            init_sdk(strict_all_vars=True)

            mock_get_env.assert_any_call("API_KEY", default="dummy", strict=True)
            mock_get_env.assert_any_call("APP_ID", default="dummy", strict=True)
            mock_get_env.assert_any_call("API_BASE", default=None, strict=True)

            assert mock_unique_sdk.api_key == "strict_key"
            assert mock_unique_sdk.app_id == "strict_id"
            assert mock_unique_sdk.api_base == "strict_base"


@pytest.mark.ai_generated
class TestInitUniqueSdk:
    """Test the init_unique_sdk function."""

    @patch("unique_toolkit.app.init_sdk.unique_sdk")
    def test_init_unique_sdk_with_unique_settings(
        self, mock_unique_sdk, base_unique_settings
    ):
        """Test init_unique_sdk with UniqueSettings object."""

        init_unique_sdk(unique_settings=base_unique_settings)

        assert mock_unique_sdk.api_key == "test-key"
        assert mock_unique_sdk.app_id == "test-id"
        assert mock_unique_sdk.api_base == "https://api.example.com/public/chat/"

    @patch("unique_toolkit.app.init_sdk.unique_sdk")
    def test_init_unique_sdk_with_env_file(self, mock_unique_sdk, tmp_path):
        """Test init_unique_sdk with env_file parameter."""
        # Create a temporary .env file
        env_file = tmp_path / ".env"
        env_content = """
UNIQUE_AUTH_COMPANY_ID=file-company
UNIQUE_AUTH_USER_ID=file-user
UNIQUE_APP_ID=file-id
UNIQUE_APP_KEY=file-key
UNIQUE_APP_BASE_URL=https://api.file-example.com
UNIQUE_APP_ENDPOINT=/v1/file-endpoint
UNIQUE_APP_ENDPOINT_SECRET=file-endpoint-secret
UNIQUE_API_BASE_URL=https://api.file-example.com
UNIQUE_API_VERSION=2023-12-06
"""
        env_file.write_text(env_content)

        init_unique_sdk(env_file=env_file)

        assert mock_unique_sdk.api_key == "file-key"
        assert mock_unique_sdk.app_id == "file-id"
        assert mock_unique_sdk.api_base == "https://api.file-example.com/public/chat/"


@pytest.mark.ai_generated
class TestGetEndpointSecret:
    """Test the get_endpoint_secret function."""

    def test_get_endpoint_secret_with_existing_variable(self, monkeypatch):
        """Test getting an existing ENDPOINT_SECRET environment variable."""
        monkeypatch.setenv("ENDPOINT_SECRET", "test_secret")
        assert get_endpoint_secret() == "test_secret"

    def test_get_endpoint_secret_with_missing_variable(self, monkeypatch):
        """Test getting a missing ENDPOINT_SECRET environment variable."""
        monkeypatch.delenv("ENDPOINT_SECRET", raising=False)
        assert get_endpoint_secret() is None

    def test_get_endpoint_secret_with_empty_variable(self, monkeypatch):
        """Test getting an empty ENDPOINT_SECRET environment variable."""
        monkeypatch.setenv("ENDPOINT_SECRET", "")
        assert get_endpoint_secret() == ""
