"""
LangGraph state management for Unique Custom Deep Research Engine

This module defines the state structures used by the LangGraph workflow
to manage the research process and integrate with unique_toolkit ChatService.
"""

from typing import List, TypedDict

from langchain_core.messages import BaseMessage
from unique_toolkit.chat.service import ChatService
from unique_toolkit.tools.tool import ToolProgressReporter


class CustomAgentState(TypedDict):
    """
    Main agent state for the complete research workflow.

    This state is passed through the entire LangGraph workflow from
    clarification through final report generation.
    """

    # Core LangGraph state
    messages: List[BaseMessage]  # Conversation messages
    research_brief: str  # Generated research instructions
    notes: List[str]  # Accumulated research findings
    final_report: str  # Generated final report

    # Unique Toolkit Integration
    chat_service: ChatService  # ChatService instance for message logging
    message_id: str  # Assistant message ID for logging
    message_log_idx: int  # Current message log index
    tool_progress_reporter: ToolProgressReporter  # Tool progress reporter instance


class CustomSupervisorState(TypedDict):
    """
    State for the research supervisor (lead agent) subgraph.

    The supervisor manages the overall research strategy, delegates tasks
    to research agents, and makes decisions about when research is complete.
    """

    # Supervisor-specific state
    supervisor_messages: List[BaseMessage]  # Supervisor conversation history
    research_iterations: int  # Number of supervisor iterations
    research_brief: str  # Research instructions
    raw_notes: List[str]  # Raw notes from research agents

    # ChatService integration for logging
    chat_service: ChatService
    message_id: str
    message_log_idx: int


class CustomResearcherState(TypedDict):
    """
    State for individual research agents.

    Each research agent works on a specific research topic and uses
    available tools to gather comprehensive information.
    """

    # Researcher-specific state
    researcher_messages: List[BaseMessage]  # Researcher conversation history
    research_topic: str  # Specific topic being researched
    tool_call_iterations: int  # Number of tool calls made

    # ChatService integration for tool logging
    chat_service: ChatService
    message_id: str
    message_log_idx: int


class CustomResearcherOutputState(TypedDict):
    """
    Output state returned by individual research agents.

    This represents the final output from a research agent that gets
    aggregated by the supervisor.
    """

    compressed_research: str  # Synthesized research findings
    raw_notes: List[str]  # Raw research notes and tool outputs
