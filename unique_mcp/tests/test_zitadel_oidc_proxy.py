"""Tests for Zitadel OIDC proxy factory defaults."""

from unittest.mock import MagicMock, patch

import pytest

from unique_mcp.auth.zitadel.oidc_proxy import create_zitadel_oidc_proxy
from unique_mcp.auth.zitadel.scopes import ZITADEL_UPSTREAM_AUTHORIZE_SCOPES


@pytest.mark.ai
def test_AI_create_zitadel_oidc_proxy_defaults_safe_upstream_authorize() -> None:
    """
    Purpose: Ensure Zitadel OIDC proxy does not forward RFC 8707 resource and
    uses upstream-safe scopes on the IdP authorize request.
    Why this matters: Forwarding ``resource`` / mcp:* scopes to Zitadel has caused
    login UI failures (``Could not find authrequest (CACHE-d24aD)``).
    Setup summary: Mock OIDCProxy and settings; assert factory kwargs.
    """
    mock_settings = MagicMock()
    mock_settings.config_url = "https://id.example/.well-known/openid-configuration"
    mock_settings.client_id = "cid"
    mock_settings.client_secret = "secret"

    with (
        patch(
            "unique_mcp.auth.zitadel.oidc_proxy.ZitadelOIDCProxySettings",
            return_value=mock_settings,
        ),
        patch("unique_mcp.auth.zitadel.oidc_proxy.OIDCProxy") as mock_oidc,
    ):
        mock_proxy = MagicMock()
        mock_oidc.return_value = mock_proxy

        create_zitadel_oidc_proxy(mcp_server_base_url="https://mcp.example")

        kwargs = mock_oidc.call_args.kwargs
        assert kwargs["forward_resource"] is False
        assert kwargs["extra_authorize_params"]["scope"] == " ".join(
            ZITADEL_UPSTREAM_AUTHORIZE_SCOPES
        )
        assert "mcp:tools" not in kwargs["extra_authorize_params"]["scope"]
        mock_proxy.update_default_scopes.assert_called_once()
