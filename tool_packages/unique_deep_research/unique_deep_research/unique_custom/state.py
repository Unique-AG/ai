"""
LangGraph state management for Unique Custom Deep Research Engine

This module defines the state structures used by the LangGraph workflow
to manage the research process and integrate with unique_toolkit ChatService.
"""

import operator
from typing import Annotated, List, Optional, Required, TypedDict

from langchain_core.messages import MessageLikeRepresentation
from langgraph.graph import MessagesState
from unique_toolkit.agentic.tools.tool import ToolProgressReporter
from unique_toolkit.chat.service import ChatService


def override_reducer(current_value, new_value):
    """Reducer function that allows overriding values in state."""
    if isinstance(new_value, dict) and new_value.get("type") == "override":
        return new_value.get("value", new_value)
    else:
        return operator.add(current_value, new_value)


class AgentState(MessagesState):
    """
    Main agent state for the complete research workflow.

    This state is passed through the entire LangGraph workflow from
    clarification through final report generation.

    Inherits from MessagesState which provides the 'messages' field
    with proper LangGraph message handling.
    """

    # Core research state
    research_brief: Optional[str]  # Generated research instructions
    notes: Annotated[List[str], override_reducer]  # Accumulated research findings
    final_report: str  # Generated final report

    # Supervisor state (shared with supervisor subgraph)
    supervisor_messages: Annotated[
        List[MessageLikeRepresentation], override_reducer
    ]  # Supervisor conversation history
    research_iterations: int  # Number of supervisor iterations

    # Essential services (required for functionality)
    chat_service: Required[ChatService]  # ChatService instance for message logging
    message_id: Required[str]  # Assistant message ID for logging
    tool_progress_reporter: Optional[
        ToolProgressReporter
    ]  # Tool progress reporter instance


class SupervisorState(TypedDict, total=False):
    """
    State for the research supervisor (lead agent) subgraph.

    The supervisor manages the overall research strategy, delegates tasks
    to research agents, and makes decisions about when research is complete.
    """

    # Supervisor-specific state
    supervisor_messages: Annotated[
        List[MessageLikeRepresentation], override_reducer
    ]  # Supervisor conversation history
    research_iterations: int  # Number of supervisor iterations
    research_brief: str  # Research instructions
    notes: Annotated[List[str], override_reducer]  # Processed research findings

    # ChatService integration for logging (required)
    chat_service: Required[ChatService]
    message_id: Required[str]


class ResearcherState(TypedDict, total=False):
    """
    State for individual research agents.

    Each research agent works on a specific research topic and uses
    available tools to gather comprehensive information.
    """

    # Researcher-specific state
    researcher_messages: Annotated[
        List[MessageLikeRepresentation], operator.add
    ]  # Researcher conversation history
    research_topic: str  # Specific topic being researched
    research_iterations: int  # Number of researcher agent iterations

    # ChatService integration for tool logging (required)
    chat_service: Required[ChatService]
    message_id: Required[str]


class ResearcherOutputState(TypedDict, total=False):
    """
    Output state returned by individual research agents.

    This represents the final output from a research agent that gets
    aggregated by the supervisor.
    """

    compressed_research: str  # Synthesized research findings
