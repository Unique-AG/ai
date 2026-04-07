"""Tests for VertexAI client utilities: credential dispatch and client creation."""

import base64
import json
from unittest.mock import MagicMock, patch

import pytest

from unique_web_search.services.search_engine.utils.vertexai.client import (
    _get_base_api_client_from_adc,
    _get_base_api_client_from_service_account,
    _get_vertexai_base_api_client,
    get_vertex_client,
)

_CLIENT_MODULE = "unique_web_search.services.search_engine.utils.vertexai.client"

_FAKE_SERVICE_ACCOUNT = base64.b64encode(
    json.dumps({"type": "service_account", "project_id": "test-project"}).encode()
).decode()


# ---------------------------------------------------------------------------
# _get_base_api_client_from_service_account tests
# ---------------------------------------------------------------------------


class TestGetBaseApiClientFromServiceAccount:
    """Tests for the service-account credential path."""

    @pytest.mark.ai
    @patch(f"{_CLIENT_MODULE}.BaseApiClient")
    @patch(f"{_CLIENT_MODULE}.load_credentials_from_dict")
    @patch(f"{_CLIENT_MODULE}.env_settings")
    def test_uses_decoded_credentials_and_default_scopes(
        self,
        mock_env: MagicMock,
        mock_load_creds: MagicMock,
        mock_base_client_cls: MagicMock,
    ) -> None:
        """
        Purpose: Verify service-account credentials are decoded and forwarded.
        Why this matters: Ensures b64-encoded JSON is correctly parsed and passed.
        Setup summary: Provide fake b64 creds, no explicit scopes; assert default scope used.
        """
        mock_env.vertexai_service_account_credentials = _FAKE_SERVICE_ACCOUNT
        mock_env.vertexai_service_account_scopes = None

        mock_credentials = MagicMock()
        mock_load_creds.return_value = (mock_credentials, "test-project")

        _get_base_api_client_from_service_account()

        mock_load_creds.assert_called_once()
        call_kwargs = mock_load_creds.call_args[1]
        assert call_kwargs["scopes"] == [
            "https://www.googleapis.com/auth/cloud-platform"
        ]

        mock_base_client_cls.assert_called_once_with(
            vertexai=True,
            credentials=mock_credentials,
            project="test-project",
        )

    @pytest.mark.ai
    @patch(f"{_CLIENT_MODULE}.BaseApiClient")
    @patch(f"{_CLIENT_MODULE}.load_credentials_from_dict")
    @patch(f"{_CLIENT_MODULE}.env_settings")
    def test_uses_custom_scopes_when_provided(
        self,
        mock_env: MagicMock,
        mock_load_creds: MagicMock,
        mock_base_client_cls: MagicMock,
    ) -> None:
        """
        Purpose: Verify custom scopes override the default scope.
        Why this matters: Deployments may require non-default OAuth scopes.
        Setup summary: Set custom scopes; assert they are forwarded to load_credentials_from_dict.
        """
        custom_scopes = ["https://www.googleapis.com/auth/custom"]
        mock_env.vertexai_service_account_credentials = _FAKE_SERVICE_ACCOUNT
        mock_env.vertexai_service_account_scopes = custom_scopes

        mock_load_creds.return_value = (MagicMock(), "test-project")

        _get_base_api_client_from_service_account()

        call_kwargs = mock_load_creds.call_args[1]
        assert call_kwargs["scopes"] == custom_scopes


# ---------------------------------------------------------------------------
# _get_base_api_client_from_adc tests
# ---------------------------------------------------------------------------


class TestGetBaseApiClientFromAdc:
    """Tests for the Application Default Credentials path."""

    @pytest.mark.ai
    @patch(f"{_CLIENT_MODULE}.BaseApiClient")
    def test_creates_client_with_vertexai_flag_only(
        self,
        mock_base_client_cls: MagicMock,
    ) -> None:
        """
        Purpose: Verify ADC path creates a BaseApiClient with only vertexai=True.
        Why this matters: ADC relies on ambient credentials; no explicit creds should be passed.
        Setup summary: Call the function; assert BaseApiClient receives only vertexai=True.
        """
        _get_base_api_client_from_adc()

        mock_base_client_cls.assert_called_once_with(vertexai=True)


# ---------------------------------------------------------------------------
# _get_vertexai_base_api_client tests (dispatch logic)
# ---------------------------------------------------------------------------


class TestGetVertexaiBaseApiClient:
    """Tests for the credential dispatch router."""

    @pytest.mark.ai
    @patch(f"{_CLIENT_MODULE}._get_base_api_client_from_service_account")
    @patch(f"{_CLIENT_MODULE}.env_settings")
    def test_dispatches_to_service_account_when_credentials_set(
        self,
        mock_env: MagicMock,
        mock_sa_fn: MagicMock,
    ) -> None:
        """
        Purpose: Verify service-account path is chosen when credentials are present.
        Why this matters: Explicit credentials must take precedence over ADC.
        Setup summary: Set credentials to a non-None value; assert SA function is called.
        """
        mock_env.vertexai_service_account_credentials = _FAKE_SERVICE_ACCOUNT

        _get_vertexai_base_api_client()

        mock_sa_fn.assert_called_once()

    @pytest.mark.ai
    @patch(f"{_CLIENT_MODULE}._get_base_api_client_from_adc")
    @patch(f"{_CLIENT_MODULE}.env_settings")
    def test_falls_back_to_adc_when_no_credentials(
        self,
        mock_env: MagicMock,
        mock_adc_fn: MagicMock,
    ) -> None:
        """
        Purpose: Verify ADC fallback is used when no explicit credentials are set.
        Why this matters: Workload Identity and other ADC flows must work without service-account JSON.
        Setup summary: Set credentials to None; assert ADC function is called.
        """
        mock_env.vertexai_service_account_credentials = None

        _get_vertexai_base_api_client()

        mock_adc_fn.assert_called_once()


# ---------------------------------------------------------------------------
# get_vertex_client tests
# ---------------------------------------------------------------------------


class TestGetVertexClient:
    """Tests for the public client factory."""

    @pytest.mark.ai
    @patch(f"{_CLIENT_MODULE}.AsyncClient")
    @patch(f"{_CLIENT_MODULE}._get_vertexai_base_api_client")
    def test_returns_async_client_on_success(
        self,
        mock_get_base: MagicMock,
        mock_async_client_cls: MagicMock,
    ) -> None:
        """
        Purpose: Verify an AsyncClient is returned when setup succeeds.
        Why this matters: Callers rely on a non-None return to proceed with search.
        Setup summary: Mock base client creation to succeed; assert AsyncClient is returned.
        """
        mock_base = MagicMock()
        mock_get_base.return_value = mock_base
        mock_client_instance = MagicMock()
        mock_async_client_cls.return_value = mock_client_instance

        result = get_vertex_client()

        assert result is mock_client_instance
        mock_async_client_cls.assert_called_once_with(api_client=mock_base)

    @pytest.mark.ai
    @patch(f"{_CLIENT_MODULE}._get_vertexai_base_api_client")
    def test_returns_none_on_exception(
        self,
        mock_get_base: MagicMock,
    ) -> None:
        """
        Purpose: Verify None is returned when client creation raises.
        Why this matters: Graceful degradation prevents VertexAI failures from crashing the service.
        Setup summary: Mock base client to raise; assert None is returned.
        """
        mock_get_base.side_effect = Exception("boom")

        result = get_vertex_client()

        assert result is None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
