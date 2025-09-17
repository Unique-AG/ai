"""
Unique Custom Deep Research Engine

This package provides a custom implementation of deep research using LangGraph
multi-agent orchestration, integrated with unique_toolkit's ChatService.
"""

from .agents import custom_agent
from .state import (
    AgentState,
    ResearcherOutputState,
    ResearcherState,
    SupervisorState,
)
from .tools import (
    ConductResearch,
    ResearchComplete,
    get_research_tools,
    get_supervisor_tools,
    internal_fetch,
    internal_search,
    think_tool,
    web_fetch,
    web_search,
)
from .utils import (
    ServiceAccessError,
    cleanup_request_counter,
    execute_tool_safely,
    get_chat_service_from_config,
    get_content_service_from_config,
    get_custom_engine_config,
    write_state_message_log,
    write_tool_message_log,
)

__all__ = [
    "custom_agent",
    "AgentState",
    "ResearcherOutputState",
    "ResearcherState",
    "SupervisorState",
    "ConductResearch",
    "ResearchComplete",
    "get_research_tools",
    "get_supervisor_tools",
    "internal_fetch",
    "internal_search",
    "think_tool",
    "web_fetch",
    "web_search",
    "ServiceAccessError",
    "cleanup_request_counter",
    "execute_tool_safely",
    "get_chat_service_from_config",
    "get_content_service_from_config",
    "get_custom_engine_config",
    "write_state_message_log",
    "write_tool_message_log",
]
