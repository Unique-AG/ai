"""Tests for Zitadel OAuth proxy functionality."""

from unittest.mock import MagicMock, patch

import pytest

from unique_mcp.zitadel.oauth_proxy import (
    ZitadelOAuthProxySettings,
    create_zitadel_oauth_proxy,
)


@pytest.mark.ai
def test_zitadel_oauth_proxy_settings__constructs_urls__with_base_url(
    sample_base_url: str,
) -> None:
    """
    Purpose: Verify ZitadelOAuthProxySettings constructs correct endpoint URLs.
    Why this matters: Ensures OAuth endpoints are correctly formatted.
    Setup summary: Create settings with base URL, verify all endpoint methods.
    """
    # Arrange
    settings = ZitadelOAuthProxySettings(base_url=sample_base_url)

    # Act & Assert
    assert settings.jwks_uri() == f"{sample_base_url}/oauth/v2/keys"
    assert settings.token_endpoint() == f"{sample_base_url}/oauth/v2/token"
    assert settings.revoke_endpoint() == f"{sample_base_url}/oauth/v2/revoke"
    assert settings.authorize_endpoint() == f"{sample_base_url}/oauth/v2/authorize"
    assert settings.userinfo_endpoint() == f"{sample_base_url}/oidc/v1/userinfo"
    assert settings.introspect_endpoint() == f"{sample_base_url}/oauth/v2/introspect"


@pytest.mark.ai
def test_zitadel_oauth_proxy_settings__uses_default_values__when_no_env_set() -> None:
    """
    Purpose: Verify settings use default values when environment variables are not set.
    Why this matters: Ensures the settings have sensible defaults for development.
    Setup summary: Create settings without env vars, verify defaults.
    """
    # Arrange & Act
    settings = ZitadelOAuthProxySettings()

    # Assert
    assert settings.base_url == "http://localhost:10116"
    assert settings.upstream_client_id == "default_client_id"
    assert settings.upstream_client_secret == "default_client_secret"


@pytest.mark.ai
def test_create_zitadel_oauth_proxy__returns_oauth_proxy__with_correct_config(
    sample_mcp_server_url: str,
) -> None:
    """
    Purpose: Verify create_zitadel_oauth_proxy returns a properly configured OAuthProxy.
    Why this matters: Ensures the factory function creates valid OAuth proxy instances.
    Setup summary: Call factory with server URL, verify OAuthProxy is created.
    """
    # Arrange & Act
    with patch(
        "unique_mcp.zitadel.oauth_proxy.ZitadelOAuthProxySettings"
    ) as mock_settings:
        mock_settings_instance = MagicMock()
        mock_settings_instance.base_url = "http://localhost:10116"
        mock_settings_instance.upstream_client_id = "test_client"
        mock_settings_instance.upstream_client_secret = "test_secret"
        mock_settings_instance.jwks_uri.return_value = (
            "http://localhost:10116/oauth/v2/keys"
        )
        mock_settings_instance.authorize_endpoint.return_value = (
            "http://localhost:10116/oauth/v2/authorize"
        )
        mock_settings_instance.token_endpoint.return_value = (
            "http://localhost:10116/oauth/v2/token"
        )
        mock_settings_instance.revoke_endpoint.return_value = (
            "http://localhost:10116/oauth/v2/revoke"
        )
        mock_settings.return_value = mock_settings_instance

        with patch("unique_mcp.zitadel.oauth_proxy.JWTVerifier"):
            with patch("unique_mcp.zitadel.oauth_proxy.OAuthProxy") as mock_oauth:
                proxy = create_zitadel_oauth_proxy(sample_mcp_server_url)

                # Assert
                assert proxy is not None
                mock_oauth.assert_called_once()
                call_args = mock_oauth.call_args
                assert call_args.kwargs["base_url"] == sample_mcp_server_url


@pytest.mark.ai
def test_create_zitadel_oauth_proxy__uses_default_server_url__when_not_provided() -> (
    None
):
    """
    Purpose: Verify create_zitadel_oauth_proxy uses default server URL when not provided.
    Why this matters: Ensures the function has a sensible default for development.
    Setup summary: Call factory without arguments, verify default URL is used.
    """
    # Arrange & Act
    with patch("unique_mcp.zitadel.oauth_proxy.ZitadelOAuthProxySettings"):
        with patch("unique_mcp.zitadel.oauth_proxy.JWTVerifier"):
            with patch("unique_mcp.zitadel.oauth_proxy.OAuthProxy") as mock_oauth:
                create_zitadel_oauth_proxy()

                # Assert
                call_args = mock_oauth.call_args
                assert call_args.kwargs["base_url"] == "http://localhost:8003"
