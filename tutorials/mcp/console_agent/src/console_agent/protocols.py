"""Protocol definitions for the MCP Search Agent.

This module defines abstract interfaces (Protocols) that enable:
- Dependency Inversion Principle (DIP): Depend on abstractions, not concretions
- Interface Segregation Principle (ISP): Small, focused interfaces
- Liskov Substitution Principle (LSP): Implementations are substitutable
"""

from typing import Any, Optional, Protocol, runtime_checkable


@runtime_checkable
class MCPClientProtocol(Protocol):
    """Protocol for MCP client implementations.

    Defines the minimal interface required for interacting with MCP servers.
    """

    async def list_tools(self) -> list[Any]:
        """List available tools from the MCP server."""
        ...

    async def __aenter__(self) -> "MCPClientProtocol":
        """Async context manager entry."""
        ...

    async def __aexit__(
        self,
        exc_type: Optional[type[BaseException]],
        exc_val: Optional[BaseException],
        exc_tb: Any,
    ) -> Optional[bool]:
        """Async context manager exit."""
        ...


@runtime_checkable
class ConsoleOutputProtocol(Protocol):
    """Protocol for console output operations.

    Abstracts console output to enable testing and alternative implementations.
    """

    def print(self, *args: Any, **kwargs: Any) -> None:
        """Print to console."""
        ...

    @property
    def width(self) -> int:
        """Get console width."""
        ...


@runtime_checkable
class AgentProtocol(Protocol):
    """Protocol for AI agent implementations.

    Defines the interface for running agent queries.
    """

    async def run(
        self,
        prompt: str,
        message_history: Optional[list[Any]] = None,
    ) -> "AgentRunResult":
        """Run the agent with a prompt."""
        ...


class AgentRunResult(Protocol):
    """Protocol for agent run results."""

    @property
    def output(self) -> str:
        """Get the output text."""
        ...

    def all_messages(self) -> list[Any]:
        """Get all messages from the run."""
        ...

    def new_messages(self) -> list[Any]:
        """Get new messages from this run."""
        ...

    def usage(self) -> "TokenUsage":
        """Get token usage statistics."""
        ...


class TokenUsage(Protocol):
    """Protocol for token usage information."""

    @property
    def input_tokens(self) -> int:
        """Get input token count."""
        ...

    @property
    def output_tokens(self) -> int:
        """Get output token count."""
        ...


@runtime_checkable
class ModelInfoProtocol(Protocol):
    """Protocol for model information.

    Allows different model info implementations to be used interchangeably.
    """

    # Note: These are optional as implementations may have different attribute names
    max_tokens: Optional[int]
    max_context: Optional[int]
    context_window: Optional[int]


class ServerSettingsProtocol(Protocol):
    """Protocol for server settings."""

    @property
    def base_url(self) -> "URLProtocol":
        """Get the base URL."""
        ...


class URLProtocol(Protocol):
    """Protocol for URL objects."""

    def encoded_string(self) -> str:
        """Get the URL as an encoded string."""
        ...


class OpenAIClientProtocol(Protocol):
    """Protocol for AsyncOpenAI client.

    Minimal interface needed for agent creation.
    """

    # This is intentionally minimal - the actual client has many more methods
    # but we only define what we actually use
    pass
