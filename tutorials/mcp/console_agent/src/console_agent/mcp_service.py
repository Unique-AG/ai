"""MCP server connection and client handling.

This module handles all MCP server interactions, following the
Single Responsibility Principle (SRP) by isolating MCP-specific
functionality.
"""

import asyncio
from dataclasses import dataclass
from typing import Any, Optional

from console_agent.protocols import MCPClientProtocol


@dataclass
class MCPConnectionResult:
    """Result of an MCP server connection attempt.

    Attributes:
        available: Whether the server is available and authenticated
        client: The authenticated MCP client (if available)
        error: Error message if connection failed
    """

    available: bool
    client: Optional[Any] = None  # FastMCP Client
    error: Optional[str] = None


class MCPService:
    """Service for managing MCP server connections.

    Handles server availability checks, authentication, and client creation.
    Follows the Single Responsibility Principle by focusing solely on
    MCP server interactions.
    """

    def __init__(
        self,
        default_timeout: float = 5.0,
    ) -> None:
        """Initialize MCPService.

        Args:
            default_timeout: Default timeout for server checks
        """
        self._default_timeout = default_timeout

    async def check_server_available(
        self,
        server_url: str,
        timeout: Optional[float] = None,
    ) -> MCPConnectionResult:
        """Check if the MCP server is running and reachable.

        Attempts to authenticate and list tools to verify full connectivity.

        Args:
            server_url: URL of the MCP server
            timeout: Timeout in seconds for the check (uses server-specific setting if not provided)

        Returns:
            MCPConnectionResult with availability status and client if successful
        """
        if timeout is None:
            # Get server-specific timeout setting
            from console_agent.agent import get_mcp_settings

            settings = get_mcp_settings()
            if server_url in settings.servers:
                effective_timeout = settings.servers[server_url].timeout
            else:
                effective_timeout = settings.default_timeout
        else:
            effective_timeout = timeout

        try:
            from fastmcp import Client

            # Determine OAuth usage for this specific server
            from console_agent.agent import get_oauth_setting_for_server

            use_oauth = get_oauth_setting_for_server(server_url)

            # Create client with appropriate authentication
            client = Client(server_url, auth="oauth" if use_oauth else None)

            # Try to list tools - this verifies both connection and authentication
            async with client:
                await asyncio.wait_for(
                    client.list_tools(),
                    timeout=effective_timeout,
                )

            return MCPConnectionResult(available=True, client=client)

        except asyncio.TimeoutError:
            return MCPConnectionResult(
                available=False,
                error="Connection timed out",
            )
        except Exception as e:
            return MCPConnectionResult(
                available=False,
                error=str(e),
            )

    def create_client(
        self,
        server_url: str,
        use_oauth: Optional[bool] = None,
    ) -> Any:
        """Create a new MCP client.

        Args:
            server_url: URL of the MCP server
            use_oauth: Whether to use OAuth (uses server-specific setting if not provided)

        Returns:
            FastMCP Client instance
        """
        from fastmcp import Client

        # Use explicit OAuth setting if provided, otherwise determine from server
        if use_oauth is not None:
            oauth = use_oauth
        else:
            from console_agent.agent import get_oauth_setting_for_server

            oauth = get_oauth_setting_for_server(server_url)

        if oauth:
            return Client(server_url, auth="oauth")
        return Client(server_url)

    async def list_tools(
        self,
        client: MCPClientProtocol,
    ) -> list[Any]:
        """List available tools from an MCP client.

        Args:
            client: The MCP client to use

        Returns:
            List of available tools
        """
        async with client:
            return await client.list_tools()


def get_mcp_server_url(settings: Optional[Any] = None) -> str:
    """Get the MCP server URL from settings.

    Args:
        settings: Optional ServerSettings instance (creates default if not provided)

    Returns:
        The full MCP server URL
    """
    if settings is None:
        from unique_mcp.settings import ServerSettings

        settings = ServerSettings()  # type: ignore[call-arg]

    return settings.base_url.encoded_string() + "mcp/"


# Module-level convenience functions for backward compatibility


async def check_mcp_server_available(
    mcp_server_url: str,
    timeout: float = 5.0,
) -> tuple[bool, Optional[Any]]:
    """Check if the MCP server is running and reachable.

    This is a convenience function maintaining backward compatibility
    with the original API.

    Args:
        mcp_server_url: URL of the MCP server
        timeout: Timeout in seconds for the check

    Returns:
        Tuple of (True if server is available, authenticated Client or None)
    """
    service = MCPService()
    result = await service.check_server_available(mcp_server_url, timeout)
    return result.available, result.client
