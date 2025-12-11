"""
Base classes for tool providers.
"""

from typing import Protocol

from fastmcp import FastMCP


class BaseResourceProvider(Protocol):
    """Base class for tool providers."""

    def register(self, *, mcp: FastMCP) -> None:
        """
        Register this provider's resources with the MCP server.
        """
