"""
Unique Custom Deep Research Engine

This package provides a custom implementation of deep research using LangGraph
multi-agent orchestration, integrated with unique_toolkit's ChatService.
"""

from .agents import custom_agent
from .state import (
    CustomAgentState,
    CustomResearcherOutputState,
    CustomResearcherState,
    CustomSupervisorState,
)
from .tools import (
    ConductResearch,
    ResearchComplete,
    get_research_tools,
    get_supervisor_tools,
    internal_fetch,
    internal_search,
    web_fetch,
    web_search,
)
from .utils import (
    ServiceAccessError,
    get_chat_service_from_config,
    get_content_service_from_config,
    get_custom_engine_config,
    write_state_message_log,
    write_tool_message_log,
)

__all__ = [
    "custom_agent",
    "CustomAgentState",
    "CustomResearcherOutputState",
    "CustomResearcherState",
    "CustomSupervisorState",
    "ConductResearch",
    "ResearchComplete",
    "get_research_tools",
    "get_supervisor_tools",
    "internal_fetch",
    "internal_search",
    "web_fetch",
    "web_search",
    "ServiceAccessError",
    "get_chat_service_from_config",
    "get_content_service_from_config",
    "get_custom_engine_config",
    "write_state_message_log",
    "write_tool_message_log",
]
