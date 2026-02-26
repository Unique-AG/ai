"""Tests for Bing client utilities: credential validation and project client creation."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from unique_web_search.services.search_engine.utils.bing.client import (
    credentials_are_valid,
    get_project_client,
)

_CLIENT_MODULE = "unique_web_search.services.search_engine.utils.bing.client"


# ---------------------------------------------------------------------------
# credentials_are_valid tests
# ---------------------------------------------------------------------------


class TestCredentialsAreValid:
    """Tests for the async credential validation function."""

    @pytest.mark.ai
    @pytest.mark.asyncio
    @patch(f"{_CLIENT_MODULE}.env_settings")
    async def test_credentials_valid__get_token_succeeds__returns_true(
        self, mock_env: MagicMock
    ) -> None:
        """
        Purpose: Verify credentials_are_valid returns True when get_token succeeds.
        Why this matters: Valid credentials must allow the Bing search flow to proceed.
        Setup summary: Mock credential whose get_token resolves successfully; assert True.
        """
        # Arrange
        mock_env.azure_identity_credentials_validate_token_url = (
            "https://management.azure.com/.default"
        )
        mock_credentials = AsyncMock()
        mock_credentials.get_token = AsyncMock(return_value=MagicMock())

        # Act
        result = await credentials_are_valid(mock_credentials)

        # Assert
        assert result is True
        mock_credentials.get_token.assert_called_once_with(
            "https://management.azure.com/.default"
        )

    @pytest.mark.ai
    @pytest.mark.asyncio
    @patch(f"{_CLIENT_MODULE}.env_settings")
    async def test_credentials_valid__get_token_raises__returns_false(
        self, mock_env: MagicMock
    ) -> None:
        """
        Purpose: Verify credentials_are_valid returns False when get_token raises.
        Why this matters: Invalid credentials must be detected without crashing.
        Setup summary: Mock credential whose get_token raises Exception; assert False.
        """
        # Arrange
        mock_env.azure_identity_credentials_validate_token_url = (
            "https://management.azure.com/.default"
        )
        mock_credentials = AsyncMock()
        mock_credentials.get_token = AsyncMock(
            side_effect=Exception("Authentication failed")
        )

        # Act
        result = await credentials_are_valid(mock_credentials)

        # Assert
        assert result is False


# ---------------------------------------------------------------------------
# get_project_client tests
# ---------------------------------------------------------------------------


class TestGetProjectClient:
    """Tests for the project client factory function."""

    @pytest.mark.ai
    @patch(f"{_CLIENT_MODULE}.env_settings")
    def test_get_client__env_endpoint_set__uses_env_endpoint(
        self, mock_env: MagicMock
    ) -> None:
        """
        Purpose: Verify env endpoint takes precedence over the parameter endpoint.
        Why this matters: Environment-level config must override per-call values.
        Setup summary: Set both env and param endpoints; assert env endpoint is used.
        """
        # Arrange
        mock_env.azure_ai_project_endpoint = "https://env-endpoint.azure.com"
        mock_env.use_unique_private_endpoint_transport = False
        mock_credentials = MagicMock()

        # Act
        with patch(f"{_CLIENT_MODULE}.AIProjectClient") as mock_client_cls:
            get_project_client(mock_credentials, "https://param-endpoint.azure.com")

        # Assert
        call_kwargs = mock_client_cls.call_args[1]
        assert call_kwargs["endpoint"] == "https://env-endpoint.azure.com"

    @pytest.mark.ai
    @patch(f"{_CLIENT_MODULE}.env_settings")
    def test_get_client__env_endpoint_none__uses_param_endpoint(
        self, mock_env: MagicMock
    ) -> None:
        """
        Purpose: Verify param endpoint is used when env endpoint is not set.
        Why this matters: Enables per-config endpoint specification as fallback.
        Setup summary: Set env endpoint to None, provide param endpoint; assert param used.
        """
        # Arrange
        mock_env.azure_ai_project_endpoint = None
        mock_env.use_unique_private_endpoint_transport = False
        mock_credentials = MagicMock()

        # Act
        with patch(f"{_CLIENT_MODULE}.AIProjectClient") as mock_client_cls:
            get_project_client(mock_credentials, "https://param-endpoint.azure.com")

        # Assert
        call_kwargs = mock_client_cls.call_args[1]
        assert call_kwargs["endpoint"] == "https://param-endpoint.azure.com"

    @pytest.mark.ai
    @patch(f"{_CLIENT_MODULE}.env_settings")
    def test_get_client__no_endpoint_at_all__raises_value_error(
        self, mock_env: MagicMock
    ) -> None:
        """
        Purpose: Verify ValueError when neither env nor param endpoint is set.
        Why this matters: Clear error prevents silent misconfiguration.
        Setup summary: Set env endpoint to None and param to empty; assert ValueError.
        """
        # Arrange
        mock_env.azure_ai_project_endpoint = None
        mock_credentials = MagicMock()

        # Act & Assert
        with pytest.raises(ValueError) as exc_info:
            get_project_client(mock_credentials, "")
        assert "not set" in str(exc_info.value)

    @pytest.mark.ai
    @patch(f"{_CLIENT_MODULE}.env_settings")
    def test_get_client__private_transport__uses_requests_transport(
        self, mock_env: MagicMock
    ) -> None:
        """
        Purpose: Verify RequestsTransport is used when private endpoint transport is enabled.
        Why this matters: Private endpoint connectivity requires custom transport layer.
        Setup summary: Enable private transport; assert AIProjectClient receives transport kwarg.
        """
        # Arrange
        mock_env.azure_ai_project_endpoint = "https://private.azure.com"
        mock_env.use_unique_private_endpoint_transport = True
        mock_credentials = MagicMock()

        # Act
        with patch(f"{_CLIENT_MODULE}.AIProjectClient") as mock_client_cls:
            get_project_client(mock_credentials, "")

        # Assert
        call_kwargs = mock_client_cls.call_args[1]
        assert "transport" in call_kwargs
        assert call_kwargs["endpoint"] == "https://private.azure.com"

    @pytest.mark.ai
    @patch(f"{_CLIENT_MODULE}.env_settings")
    def test_get_client__no_private_transport__no_transport_kwarg(
        self, mock_env: MagicMock
    ) -> None:
        """
        Purpose: Verify no transport kwarg when private endpoint transport is disabled.
        Why this matters: Default transport must be used for standard connectivity.
        Setup summary: Disable private transport; assert no transport kwarg on client.
        """
        # Arrange
        mock_env.azure_ai_project_endpoint = "https://standard.azure.com"
        mock_env.use_unique_private_endpoint_transport = False
        mock_credentials = MagicMock()

        # Act
        with patch(f"{_CLIENT_MODULE}.AIProjectClient") as mock_client_cls:
            get_project_client(mock_credentials, "")

        # Assert
        call_kwargs = mock_client_cls.call_args[1]
        assert "transport" not in call_kwargs


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
