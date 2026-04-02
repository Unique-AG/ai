"""Factory for creating a fully configured MCP server with auth."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from fastmcp import FastMCP
from unique_toolkit.app.unique_settings import UniqueSettings

from unique_mcp.auth.zitadel.oauth_proxy import (
    ZitadelOAuthProxySettings,
    create_zitadel_oauth_proxy,
)
from unique_mcp.provider import UniqueContextProvider
from unique_mcp.settings import ServerSettings


@dataclass
class UniqueMCPServerBundle:
    """Typed result of :func:`create_unique_mcp_server`.
    Dataclass for type safety, no need for serialization and validation.
    """

    mcp: FastMCP
    context_provider: UniqueContextProvider
    server_settings: ServerSettings


def create_unique_mcp_server(
    name: str,
    *,
    settings: UniqueSettings | None = None,
    server_settings: ServerSettings | None = None,
    zitadel_settings: ZitadelOAuthProxySettings | None = None,
    **fastmcp_kwargs: Any,
) -> UniqueMCPServerBundle:
    """Create a FastMCP server wired with Zitadel OAuth and a context provider.

    Args:
        name: Display name for the MCP server.
        settings: UniqueSettings; defaults to ``from_env_auto_with_sdk_init()``.
        server_settings: ServerSettings; defaults to env-based.
        zitadel_settings: Zitadel settings; defaults to env-based.
        **fastmcp_kwargs: Extra kwargs forwarded to :class:`FastMCP`.

    Returns:
        UniqueMCPServerBundle with *mcp*, *context_provider*, and *server_settings*.
    """
    settings = settings or UniqueSettings.from_env_auto_with_sdk_init()
    server_settings = server_settings or ServerSettings()  # type: ignore[assignment]
    zitadel_settings = zitadel_settings or ZitadelOAuthProxySettings()

    oauth_proxy = create_zitadel_oauth_proxy(
        mcp_server_base_url=server_settings.base_url.encoded_string(),
        zitadel_oauth_proxy_settings=zitadel_settings,
    )

    context_provider = UniqueContextProvider(
        settings=settings,
        zitadel_settings=zitadel_settings,
    )

    mcp = FastMCP(name, auth=oauth_proxy, **fastmcp_kwargs)

    return UniqueMCPServerBundle(
        mcp=mcp,
        context_provider=context_provider,
        server_settings=server_settings,
    )
