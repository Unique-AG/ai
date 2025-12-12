"""
Base classes for tool providers.
"""

from typing import Protocol

from fastmcp import FastMCP


class BaseProvider(Protocol):
    """Base class for tool providers."""

    def register(self, *, mcp: FastMCP) -> None:
        """
        Register this provider's resources, routes and tools with the MCP server.
        """
