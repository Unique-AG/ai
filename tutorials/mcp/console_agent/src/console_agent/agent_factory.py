"""Agent factory for creating pydantic-ai agents.

This module handles agent creation following the Factory Pattern and
Single Responsibility Principle (SRP). It also applies the
Open/Closed Principle (OCP) through extensible instruction providers.
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Optional, Protocol

from openai import AsyncOpenAI
from pydantic_ai import Agent
from pydantic_ai.models.openai import OpenAIChatModel
from pydantic_ai.providers.openai import OpenAIProvider
from pydantic_ai.toolsets.fastmcp import FastMCPToolset


class InstructionProvider(Protocol):
    """Protocol for providing agent instructions.

    Allows customization of agent behavior through different
    instruction providers (Open/Closed Principle).
    """

    def get_instructions(self, tools_available: bool) -> str:
        """Get instructions based on tool availability.

        Args:
            tools_available: Whether tools are available

        Returns:
            The instruction string
        """
        ...


class AgentMode(Enum):
    """Agent operating modes."""

    WITH_TOOLS = "with_tools"
    WITHOUT_TOOLS = "without_tools"


@dataclass(frozen=True)
class AgentInstructions:
    """Default instruction configurations for the agent."""

    with_tools: str = (
        "You are a helpful assistant. Answer questions directly using your knowledge. "
        "Only use the search tools when the user asks about specific information that "
        "might be in the knowledge base, or when you need to search for content. "
        "For general questions, conversations, or questions you can answer from your "
        "training data, respond directly without calling any tools. Be concise but thorough."
    )
    without_tools: str = (
        "You are a helpful assistant. Answer questions directly using your knowledge. "
        "Be concise but thorough in your responses."
    )


class DefaultInstructionProvider:
    """Default instruction provider using predefined templates."""

    def __init__(
        self,
        instructions: Optional[AgentInstructions] = None,
    ) -> None:
        """Initialize with optional custom instructions.

        Args:
            instructions: Custom instruction configurations
        """
        self._instructions = instructions or AgentInstructions()

    def get_instructions(self, tools_available: bool) -> str:
        """Get instructions based on tool availability.

        Args:
            tools_available: Whether tools are available

        Returns:
            The appropriate instruction string
        """
        if tools_available:
            return self._instructions.with_tools
        return self._instructions.without_tools


@dataclass
class AgentConfig:
    """Configuration for agent creation.

    Attributes:
        model: The model name to use
        mcp_server_url: Optional MCP server URL
        tools_available: Whether tools should be loaded
        mcp_client: Optional pre-authenticated MCP client
    """

    model: str = "gpt-4"
    mcp_server_url: Optional[str] = None
    tools_available: bool = False
    mcp_client: Optional[Any] = None
    instruction_provider: InstructionProvider = field(
        default_factory=DefaultInstructionProvider
    )


class AgentFactory:
    """Factory for creating pydantic-ai agents.

    Encapsulates agent creation logic and supports customization
    through configuration objects and instruction providers.
    """

    def __init__(
        self,
        openai_client: AsyncOpenAI,
        instruction_provider: Optional[InstructionProvider] = None,
    ) -> None:
        """Initialize AgentFactory.

        Args:
            openai_client: AsyncOpenAI client instance
            instruction_provider: Optional custom instruction provider
        """
        self._openai_client = openai_client
        self._instruction_provider = (
            instruction_provider or DefaultInstructionProvider()
        )

    def create(self, config: AgentConfig) -> Agent:
        """Create an agent with the given configuration.

        Args:
            config: Agent configuration

        Returns:
            Configured pydantic-ai Agent
        """
        # Create OpenAI model with custom client
        model_instance = OpenAIChatModel(
            config.model,
            provider=OpenAIProvider(openai_client=self._openai_client),
        )

        # Create toolsets if tools are available
        toolsets = self._create_toolsets(config)

        # Get instructions based on tool availability
        instructions = self._instruction_provider.get_instructions(
            tools_available=bool(toolsets)
        )

        return Agent(
            model_instance,
            toolsets=toolsets,
            instructions=instructions,
        )

    def _create_toolsets(self, config: AgentConfig) -> list[FastMCPToolset]:
        """Create toolsets based on configuration.

        Args:
            config: Agent configuration

        Returns:
            List of toolsets (empty if tools not available)
        """
        if not config.tools_available or not config.mcp_server_url:
            return []

        # Create FastMCP toolset
        if config.mcp_client is not None:
            # Reuse the authenticated client
            toolset = FastMCPToolset(config.mcp_client)  # type: ignore[arg-type]
        else:
            # Create new client
            toolset = self._create_toolset_with_new_client(config.mcp_server_url)

        return [toolset]

    def _create_toolset_with_new_client(self, server_url: str) -> FastMCPToolset:
        """Create a toolset with a new MCP client.

        Args:
            server_url: MCP server URL

        Returns:
            FastMCPToolset configured with new client
        """
        from fastmcp import Client

        from console_agent.agent import get_oauth_setting_for_server

        use_oauth = get_oauth_setting_for_server(server_url)

        if use_oauth:
            client = Client(server_url, auth="oauth")
            return FastMCPToolset(client)
        return FastMCPToolset(server_url)


# Convenience function for backward compatibility


def create_agent(
    openai_client: AsyncOpenAI,
    mcp_server_url: Optional[str] = None,
    model: str = "gpt-4",
    tools_available: bool = False,
    mcp_client: Optional[Any] = None,
) -> Agent:
    """Create a pydantic-ai agent with optional MCP tools.

    Args:
        openai_client: AsyncOpenAI client instance
        mcp_server_url: URL of the MCP server
        model: OpenAI model name to use
        tools_available: Whether MCP tools should be loaded
        mcp_client: Optional authenticated FastMCP Client to reuse

    Returns:
        Configured pydantic-ai Agent
    """
    factory = AgentFactory(openai_client)
    config = AgentConfig(
        model=model,
        mcp_server_url=mcp_server_url,
        tools_available=tools_available,
        mcp_client=mcp_client,
    )
    return factory.create(config)
