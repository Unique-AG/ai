"""Interactive pydantic-ai agent with MCP search server integration.

This module serves as the main entry point and orchestrator for the
MCP Search Agent. It composes functionality from specialized modules
following SOLID principles:

- SRP: Each module has a single responsibility
- OCP: Agent behavior is extensible through instruction providers
- LSP: Protocol implementations are substitutable
- ISP: Small, focused interfaces (protocols)
- DIP: High-level modules depend on abstractions (protocols)
"""

import asyncio
import os
import sys
from typing import Any, Optional

from openai import AsyncOpenAI

from console_agent.agent_factory import (
    AgentConfig,
    AgentFactory,
    AgentInstructions,
    DefaultInstructionProvider,
    create_agent,
)
from console_agent.console_ui import (
    ConsoleUI,
    UIConfig,
    format_token_usage,
    get_default_ui,
)
from console_agent.interactive_runner import (
    ConversationState,
    InputHandler,
    InteractiveRunner,
    run_agent_interactive,
)
from console_agent.mcp_service import (
    MCPConnectionResult,
    MCPService,
    check_mcp_server_available,
    get_mcp_server_url,
)
from console_agent.token_tracker import (
    ModelInfoExtractor,
    TokenStats,
    TokenTracker,
    create_tracker_from_model,
)
from unique_toolkit.language_model import LanguageModelName

__all__ = [
    # Main entry points
    "main",
    "cli_main",
    # Agent factory
    "AgentConfig",
    "AgentFactory",
    "AgentInstructions",
    "DefaultInstructionProvider",
    "create_agent",
    # Console UI
    "ConsoleUI",
    "UIConfig",
    "format_token_usage",
    "get_default_ui",
    # Interactive runner
    "ConversationState",
    "InputHandler",
    "InteractiveRunner",
    "run_agent_interactive",
    # MCP service
    "MCPConnectionResult",
    "MCPService",
    "check_mcp_server_available",
    "get_mcp_server_url",
    # Token tracking
    "ModelInfoExtractor",
    "TokenStats",
    "TokenTracker",
    "create_tracker_from_model",
]


class AgentOrchestrator:
    """Orchestrates agent initialization and startup.

    Coordinates the setup of all components needed to run the
    interactive agent.
    """

    def __init__(
        self,
        openai_client: AsyncOpenAI,
        ui: Optional[ConsoleUI] = None,
        mcp_service: Optional[MCPService] = None,
    ) -> None:
        """Initialize AgentOrchestrator.

        Args:
            openai_client: AsyncOpenAI client instance
            ui: Console UI instance (creates default if not provided)
            mcp_service: MCP service instance (creates default if not provided)
        """
        self._openai_client = openai_client
        self._ui = ui or get_default_ui()
        self._mcp_service = mcp_service or MCPService()

    async def run(
        self,
        mcp_server_url: Optional[str] = None,
        model: LanguageModelName = LanguageModelName.AZURE_GPT_4o_2024_1120,
        initial_question: Optional[str] = None,
        use_oauth: bool = True,
        debug: bool = False,
    ) -> None:
        """Run the agent orchestration.

        Args:
            mcp_server_url: Optional MCP server URL (defaults to ServerSettings)
            model: Language model to use
            initial_question: Optional initial question to ask
            use_oauth: Whether to use OAuth authentication
            debug: Whether to show debug information
        """
        # Resolve MCP server URL
        server_url = mcp_server_url or get_mcp_server_url()

        # Check server availability
        connection_result = await self._check_server(server_url, use_oauth)

        try:
            # Get model info for token tracking
            model_info = self._get_model_info(model, debug)

            # Debug: List available tools
            if debug and connection_result.available and connection_result.client:
                await self._list_tools_debug(connection_result.client)

            # Create agent
            agent = self._create_agent(
                model=model,
                server_url=server_url,
                connection_result=connection_result,
                use_oauth=use_oauth,
                debug=debug,
            )

            # Create token tracker
            max_tokens = ModelInfoExtractor.get_max_tokens(model_info)
            token_tracker = TokenTracker(max_tokens=max_tokens)

            # Run interactive loop
            runner = InteractiveRunner(
                agent=agent,
                ui=self._ui,
                token_tracker=token_tracker,
                debug=debug,
            )

            await runner.run(initial_question=initial_question)

        except Exception as e:
            self._ui.print(
                f"[bold red]Failed to start agent:[/bold red] {str(e)}",
            )
            sys.exit(1)

    async def _check_server(
        self,
        server_url: str,
        use_oauth: bool,
    ) -> MCPConnectionResult:
        """Check MCP server availability.

        Args:
            server_url: The server URL to check
            use_oauth: Whether OAuth is being used

        Returns:
            MCPConnectionResult with availability status
        """
        self._ui.print(f"[dim]Checking MCP server availability: {server_url}[/dim]")

        with self._ui.create_status("[bold yellow]Checking server...[/bold yellow]"):
            result = await self._mcp_service.check_server_available(server_url)

        # Display status
        self._ui.print_server_status(
            url=server_url,
            available=result.available,
            use_oauth=use_oauth,
        )

        return result

    def _get_model_info(
        self,
        model: LanguageModelName,
        debug: bool,
    ) -> Optional[Any]:
        """Extract model info for token tracking.

        Args:
            model: The language model name
            debug: Whether to print debug info

        Returns:
            Model info or None if extraction failed
        """
        model_info = ModelInfoExtractor.extract_from_model(model)

        if model_info is None and debug:
            self._ui.print_debug_info(
                "Could not retrieve model info for token tracking"
            )

        return model_info

    async def _list_tools_debug(self, client: Any) -> None:
        """List available tools in debug mode.

        Args:
            client: The MCP client to use
        """
        try:
            tools = await self._mcp_service.list_tools(client)
            self._ui.print_tools_list(tools, show_schema=True)
        except Exception as e:
            self._ui.print_debug_info(f"Could not list tools: {e}")

    def _create_agent(
        self,
        model: LanguageModelName,
        server_url: str,
        connection_result: MCPConnectionResult,
        use_oauth: bool,
        debug: bool,
    ) -> Any:
        """Create the agent with appropriate configuration.

        Args:
            model: The language model to use
            server_url: The MCP server URL
            connection_result: Result of server availability check
            use_oauth: Whether to use OAuth
            debug: Whether debug mode is enabled

        Returns:
            Configured pydantic-ai Agent
        """
        if debug:
            self._ui.print("\n[bold magenta]🔍 Debug: Creating agent...[/bold magenta]")
            self._ui.print(f"[dim]  Model: {model}[/dim]")
            self._ui.print(
                f"[dim]  Tools available: {connection_result.available}[/dim]"
            )
            self._ui.print(
                f"[dim]  MCP client provided: {connection_result.client is not None}[/dim]"
            )

        factory = AgentFactory(self._openai_client)
        config = AgentConfig(
            model=str(model),
            mcp_server_url=server_url if connection_result.available else None,
            use_oauth=use_oauth,
            tools_available=connection_result.available,
            mcp_client=connection_result.client,
        )
        agent = factory.create(config)

        if debug:
            self._ui.print("[dim]🔍 Debug: Agent created successfully[/dim]\n")

        return agent


async def main(
    openai_client: AsyncOpenAI,
    mcp_server_url: Optional[str] = None,
    model: LanguageModelName = LanguageModelName.AZURE_GPT_4o_2024_1120,
    initial_question: Optional[str] = None,
    use_oauth: bool = True,
    debug: bool = True,
) -> None:
    """Main entry point for the agent.

    Args:
        openai_client: AsyncOpenAI client instance
        mcp_server_url: Optional MCP server URL (defaults to ServerSettings)
        model: OpenAI model name (default: "gpt-4")
        initial_question: Optional initial question to ask
        use_oauth: Whether to use OAuth authentication (default: True)
        debug: Whether to show debug information about requests/responses (default: False)
    """
    orchestrator = AgentOrchestrator(openai_client)
    await orchestrator.run(
        mcp_server_url=mcp_server_url,
        model=model,
        initial_question=initial_question,
        use_oauth=use_oauth,
        debug=debug,
    )


def cli_main() -> None:
    """CLI entry point that creates OpenAI client and runs the agent."""
    from unique_toolkit import get_async_openai_client

    openai_client = get_async_openai_client()

    # Check for debug mode from environment variable
    debug = os.getenv("MCP_SEARCH_DEBUG", "false").lower() in ("true", "1", "yes")

    # Run the agent
    asyncio.run(main(openai_client=openai_client, debug=debug))


if __name__ == "__main__":
    cli_main()
