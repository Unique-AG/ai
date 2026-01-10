"""MCP Search Agent - Interactive AI agent with MCP server integration.

This package can be extracted to a separate repository.
"""

from console_agent.agent import (
    AgentOrchestrator,
    cli_main,
    main,
)
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
from console_agent.protocols import (
    AgentProtocol,
    AgentRunResult,
    ConsoleOutputProtocol,
    MCPClientProtocol,
    ModelInfoProtocol,
    OpenAIClientProtocol,
    ServerSettingsProtocol,
    TokenUsage,
    URLProtocol,
)
from console_agent.token_tracker import (
    ModelInfoExtractor,
    TokenStats,
    TokenTracker,
    create_tracker_from_model,
)

__all__ = [
    "AgentOrchestrator",
    "cli_main",
    "main",
    "AgentConfig",
    "AgentFactory",
    "AgentInstructions",
    "DefaultInstructionProvider",
    "create_agent",
    "ConsoleUI",
    "UIConfig",
    "format_token_usage",
    "get_default_ui",
    "ConversationState",
    "InputHandler",
    "InteractiveRunner",
    "run_agent_interactive",
    "MCPConnectionResult",
    "MCPService",
    "check_mcp_server_available",
    "get_mcp_server_url",
    "AgentProtocol",
    "AgentRunResult",
    "ConsoleOutputProtocol",
    "MCPClientProtocol",
    "ModelInfoProtocol",
    "OpenAIClientProtocol",
    "ServerSettingsProtocol",
    "TokenUsage",
    "URLProtocol",
    "ModelInfoExtractor",
    "TokenStats",
    "TokenTracker",
    "create_tracker_from_model",
]
