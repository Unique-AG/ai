"""Smoke tests for create_unique_mcp_server factory."""

from unittest.mock import MagicMock, patch

import pytest
from fastmcp import FastMCP
from pydantic import SecretStr
from unique_toolkit.app.unique_settings import (
    AuthContext,
    UniqueApi,
    UniqueApp,
    UniqueSettings,
)

from unique_mcp.auth.zitadel.oauth_proxy import ZitadelOAuthProxySettings
from unique_mcp.provider import UniqueContextProvider
from unique_mcp.server import UniqueMCPServerBundle, create_unique_mcp_server
from unique_mcp.settings import ServerSettings

_MOD = "unique_mcp.server"


def _fake_settings() -> UniqueSettings:
    return UniqueSettings(
        auth=AuthContext(
            user_id=SecretStr("u"),
            company_id=SecretStr("c"),
        ),
        app=UniqueApp(),
        api=UniqueApi(),
    )


@pytest.mark.ai
@patch(f"{_MOD}.create_zitadel_oauth_proxy")
def test_create_unique_mcp_server__returns_bundle__with_correct_types(
    mock_oauth: MagicMock,
) -> None:
    """
    Purpose: Verify create_unique_mcp_server returns UniqueMCPServerBundle with expected
    types.
    Why this matters: Ensures the factory wires together all components correctly.
    Setup summary: Call factory with explicit settings; assert bundle field types.
    """
    # Arrange
    mock_oauth.return_value = MagicMock(name="oauth_proxy")

    # Act
    bundle = create_unique_mcp_server(
        "Test Server",
        settings=_fake_settings(),
        server_settings=ServerSettings(),
        zitadel_settings=ZitadelOAuthProxySettings(),
    )

    # Assert
    assert isinstance(bundle, UniqueMCPServerBundle)
    assert isinstance(bundle.mcp, FastMCP)
    assert isinstance(bundle.context_provider, UniqueContextProvider)
    assert isinstance(bundle.server_settings, ServerSettings)


@pytest.mark.ai
@patch(f"{_MOD}.create_zitadel_oauth_proxy")
def test_create_unique_mcp_server__wires_oauth_proxy__as_mcp_auth(
    mock_oauth: MagicMock,
) -> None:
    """
    Purpose: Verify create_unique_mcp_server sets OAuth proxy as the MCP server's auth.
    Why this matters: Ensures Zitadel authentication is attached to the server.
    Setup summary: Call factory; assert mcp.auth matches the proxy from the factory.
    """
    # Arrange
    proxy = MagicMock(name="oauth_proxy")
    mock_oauth.return_value = proxy

    # Act
    bundle = create_unique_mcp_server(
        "Test",
        settings=_fake_settings(),
        server_settings=ServerSettings(),
        zitadel_settings=ZitadelOAuthProxySettings(),
    )

    # Assert
    assert bundle.mcp.auth is proxy


@pytest.mark.ai
@patch(f"{_MOD}.create_zitadel_oauth_proxy")
def test_create_unique_mcp_server__passes_name__to_fastmcp(
    mock_oauth: MagicMock,
) -> None:
    """
    Purpose: Verify create_unique_mcp_server forwards the name argument to FastMCP.
    Why this matters: Ensures the server display name is set correctly.
    Setup summary: Call factory with a specific name, verify bundle.mcp.name matches.
    """
    # Arrange
    mock_oauth.return_value = MagicMock()

    # Act
    bundle = create_unique_mcp_server(
        "Named Server",
        settings=_fake_settings(),
        server_settings=ServerSettings(),
        zitadel_settings=ZitadelOAuthProxySettings(),
    )

    # Assert
    assert bundle.mcp.name == "Named Server"
