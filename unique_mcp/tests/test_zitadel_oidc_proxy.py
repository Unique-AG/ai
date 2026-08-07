"""Tests for Zitadel OIDC proxy functionality."""

from unittest.mock import patch

import pytest
from key_value.aio.stores.memory import MemoryStore

from unique_mcp.auth.zitadel.oidc_proxy import (
    ZitadelOIDCProxySettings,
    create_zitadel_oidc_proxy,
)
from unique_mcp.auth.zitadel.scopes import ZITADEL_DEFAULT_MCP_SCOPES


@pytest.mark.ai
def test_zitadel_oidc_proxy_settings__constructs_config_url__with_base_url(
    sample_base_url: str,
) -> None:
    """
    Purpose: Verify ZitadelOIDCProxySettings builds the discovery endpoint URL.
    Why this matters: OIDCProxy discovers every other endpoint from this URL, so a
    malformed value fails at startup rather than at first login.
    Setup summary: Construct settings with a base URL, assert the derived config URL.
    """
    # Arrange
    settings = ZitadelOIDCProxySettings(
        base_url=sample_base_url,
        client_id="test_client",
        client_secret="test_secret",
    )

    # Act & Assert
    assert settings.config_url == f"{sample_base_url}/.well-known/openid-configuration"


@pytest.mark.ai
def test_create_zitadel_oidc_proxy__raises__when_client_storage_omitted() -> None:
    """
    Purpose: Verify client_storage is a required argument.
    Why this matters: FastMCP's default is a per-pod on-disk store. In a container
    that path may not exist on a read-only root filesystem (crash on boot), and when
    it does exist it is ephemeral — losing it invalidates every live session, because
    FastMCP access tokens are reference tokens resolved via a JTI lookup in that
    store. Callers must choose a backend deliberately rather than inherit one.
    Setup summary: Call the factory with no client_storage, expect TypeError.
    """
    # Arrange & Act & Assert
    with pytest.raises(TypeError, match="client_storage"):
        create_zitadel_oidc_proxy()  # pyright: ignore[reportCallIssue]


def test_create_zitadel_oidc_proxy__raises__when_client_storage_is_none() -> None:
    """Explicit None must not reach FastMCP's on-disk fallback."""
    with pytest.raises(ValueError, match="client_storage must not be None"):
        create_zitadel_oidc_proxy(
            client_storage=None,  # type: ignore[arg-type]
            mcp_server_base_url="http://localhost:8003",
            zitadel_oidc_proxy_settings=ZitadelOIDCProxySettings(
                base_url="http://localhost:10116",
                client_id="test_client",
                client_secret="test_secret",
            ),
        )


@pytest.mark.ai
def test_create_zitadel_oidc_proxy__forwards_client_storage__to_oidc_proxy(
    sample_mcp_server_url: str,
) -> None:
    """
    Purpose: Verify the supplied client_storage reaches OIDCProxy.
    Why this matters: A storage backend that is accepted but silently dropped would
    reintroduce the ephemeral-store failure this argument exists to prevent.
    Setup summary: Pass a known store, assert it is forwarded verbatim.
    """
    # Arrange
    storage = MemoryStore()
    settings = ZitadelOIDCProxySettings(
        base_url="http://localhost:10116",
        client_id="test_client",
        client_secret="test_secret",
    )

    # Act
    with patch("unique_mcp.auth.zitadel.oidc_proxy.OIDCProxy") as mock_oidc:
        create_zitadel_oidc_proxy(
            client_storage=storage,
            mcp_server_base_url=sample_mcp_server_url,
            zitadel_oidc_proxy_settings=settings,
        )

    # Assert
    assert mock_oidc.call_args.kwargs["client_storage"] is storage
    assert mock_oidc.call_args.kwargs["base_url"] == sample_mcp_server_url


@pytest.mark.ai
def test_create_zitadel_oidc_proxy__sets_authorize_scope__by_default(
    sample_mcp_server_url: str,
) -> None:
    """
    Purpose: Verify a non-empty scope is always sent on /authorize.
    Why this matters: Zitadel rejects or silently downgrades an authorize request
    with no scope, which surfaces later as an opaque invalid_token rather than as a
    login error.
    Setup summary: Construct without explicit scopes, inspect extra_authorize_params.
    """
    # Arrange
    settings = ZitadelOIDCProxySettings(
        base_url="http://localhost:10116",
        client_id="test_client",
        client_secret="test_secret",
    )

    # Act
    with patch("unique_mcp.auth.zitadel.oidc_proxy.OIDCProxy") as mock_oidc:
        create_zitadel_oidc_proxy(
            client_storage=MemoryStore(),
            mcp_server_base_url=sample_mcp_server_url,
            zitadel_oidc_proxy_settings=settings,
        )

    # Assert
    scope = mock_oidc.call_args.kwargs["extra_authorize_params"]["scope"]
    assert scope == " ".join(ZITADEL_DEFAULT_MCP_SCOPES)
