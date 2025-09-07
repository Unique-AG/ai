"""
LangGraph workflow implementation for Unique Custom Deep Research Engine

This module implements the multi-agent research workflow using LangGraph,
following the pattern from open_deep_research but integrated with unique_toolkit.
"""

import asyncio
import logging
from typing import Any, Dict, Literal

from langchain.chat_models import init_chat_model
from langchain_core.messages import (
    AIMessage,
    HumanMessage,
    SystemMessage,
    ToolMessage,
)
from langchain_core.runnables import RunnableConfig
from langgraph.graph import END, START, StateGraph
from langgraph.types import Command

from ..config import TEMPLATE_ENV
from .state import (
    CustomAgentState,
    CustomResearcherState,
    CustomSupervisorState,
)
from .tools import get_research_tools, get_supervisor_tools, get_today_str
from .utils import get_custom_engine_config, write_state_message_log

logger = logging.getLogger(__name__)

# Initialize a configurable model for all agents
configurable_model = init_chat_model(
    configurable_fields=("model", "max_tokens", "api_key"),
)


async def setup_research_supervisor(
    state: CustomAgentState, config: RunnableConfig
) -> Command[Literal["research_supervisor"]]:
    """
    Setup the research supervisor with the pre-generated research brief.

    The research brief was already generated in the main service flow,
    so we just need to initialize the supervisor state.
    """
    write_state_message_log(state, "Initializing research supervisor...")

    # Get the pre-generated research brief from state
    research_brief = state.get("research_brief")
    assert research_brief, "Research brief is required"

    # Initialize supervisor state with config values
    custom_config = get_custom_engine_config(config)
    max_concurrent = custom_config.max_parallel_researchers
    max_iterations = custom_config.max_research_iterations

    supervisor_system_prompt = TEMPLATE_ENV.get_template(
        "unique/lead_agent_system.j2"
    ).render(
        date=get_today_str(),
        max_concurrent_research_units=max_concurrent,
        max_researcher_iterations=max_iterations,
    )

    return Command(
        goto="research_supervisor",
        update={
            "research_brief": research_brief,
            "supervisor_messages": {
                "type": "override",
                "value": [
                    SystemMessage(content=supervisor_system_prompt),
                    HumanMessage(content=research_brief),
                ],
            },
        },
    )


async def research_supervisor(
    state: CustomSupervisorState, config: RunnableConfig
) -> Command[Literal["supervisor_tools"]]:
    """
    Lead research supervisor that plans research strategy and delegates to researchers.
    """
    write_state_message_log(state, "Planning research strategy...")

    # Configure the supervisor model with tools
    custom_config = get_custom_engine_config(config)
    lead_model = custom_config.lead_agent_model.name

    model_config = {
        "model": lead_model,
        "max_tokens": 4000,
        "temperature": 0.1,
    }

    # Available tools for the supervisor
    supervisor_tools = get_supervisor_tools()

    # Configure model with tools
    model_with_tools = configurable_model.bind_tools(supervisor_tools)
    research_model = model_with_tools.with_config(model_config)  # type: ignore[arg-type]

    # Generate supervisor response
    supervisor_messages = state.get("supervisor_messages", [])
    response = await research_model.ainvoke(supervisor_messages)

    return Command(
        goto="supervisor_tools",
        update={
            "supervisor_messages": [response],
            "research_iterations": state.get("research_iterations", 0) + 1,
        },
    )


async def supervisor_tools(
    state: CustomSupervisorState, config: RunnableConfig
) -> Command[Literal["research_supervisor", "__end__"]]:
    """
    Execute tools called by the supervisor.
    """
    supervisor_messages = state.get("supervisor_messages", [])
    research_iterations = state.get("research_iterations", 0)
    most_recent_message = supervisor_messages[-1] if supervisor_messages else None

    # Check exit conditions
    custom_config = get_custom_engine_config(config)
    max_iterations = custom_config.max_research_iterations
    exceeded_iterations = research_iterations > max_iterations

    # Type guard for AIMessage with tool_calls
    no_tool_calls = True
    research_complete_called = False

    if most_recent_message and isinstance(most_recent_message, AIMessage):
        tool_calls = getattr(most_recent_message, "tool_calls", None) or []
        no_tool_calls = not tool_calls
        research_complete_called = any(
            tool_call.get("name") == "ResearchComplete" for tool_call in tool_calls
        )

    if exceeded_iterations or no_tool_calls or research_complete_called:
        # Extract notes from all supervisor messages for final report
        notes = []
        for msg in supervisor_messages:
            if hasattr(msg, "content") and msg.content:
                notes.append(str(msg.content))

        return Command(
            goto="__end__",
            update={
                "notes": notes,
                "research_brief": state.get("research_brief", ""),
            },
        )

    # Process tool calls
    all_tool_messages = []
    conduct_research_calls = []

    if most_recent_message and isinstance(most_recent_message, AIMessage):
        tool_calls = getattr(most_recent_message, "tool_calls", None) or []
        conduct_research_calls = [
            tool_call
            for tool_call in tool_calls
            if tool_call.get("name") == "ConductResearch"
        ]

    if conduct_research_calls:
        write_state_message_log(
            state, f"Delegating {len(conduct_research_calls)} research tasks..."
        )

        try:
            # Limit concurrent research tasks
            max_concurrent = (
                custom_config.max_parallel_researchers if custom_config else 3
            )
            allowed_calls = conduct_research_calls[:max_concurrent]

            # Execute research tasks in parallel
            research_tasks = [
                researcher_subgraph.ainvoke(
                    {
                        "researcher_messages": [
                            HumanMessage(content=tool_call["args"]["research_topic"])
                        ],
                        "research_topic": tool_call["args"]["research_topic"],
                        "tool_call_iterations": 0,
                        "chat_service": state["chat_service"],
                        "message_id": state["message_id"],
                    },
                    config,
                )
                for tool_call in allowed_calls
            ]

            tool_results = await asyncio.gather(*research_tasks)

            # Create tool messages with research results
            for observation, tool_call in zip(tool_results, allowed_calls):
                all_tool_messages.append(
                    ToolMessage(
                        content=observation.get(
                            "compressed_research", "No research results"
                        ),
                        name=tool_call["name"],
                        tool_call_id=tool_call["id"],
                    )
                )

        except Exception as e:
            logger.error(f"Research execution failed: {e}")
            # Return end command on error
            return Command(
                goto="__end__",
                update={
                    "notes": ["Research failed due to error"],
                    "research_brief": state.get("research_brief", ""),
                },
            )

    return Command(
        goto="research_supervisor", update={"supervisor_messages": all_tool_messages}
    )


# Research Agent Functions


async def researcher(
    state: CustomResearcherState, config: RunnableConfig
) -> Command[Literal["researcher_tools"]]:
    """
    Individual researcher that conducts focused research on specific topics.
    """
    research_tools = get_research_tools()

    # Configure the researcher model
    custom_config = get_custom_engine_config(config)
    research_model_name = custom_config.research_agent_model.name

    model_config = {
        "model": research_model_name,
        "max_tokens": 4000,
        "temperature": 0.1,
    }

    # Prepare system prompt
    researcher_prompt = TEMPLATE_ENV.get_template(
        "unique/research_agent_system.j2"
    ).render(date=get_today_str())

    # Configure model with research tools
    model_with_tools = configurable_model.bind_tools(research_tools)
    research_model = model_with_tools.with_config(model_config)  # type: ignore[arg-type]

    # Generate researcher response
    researcher_messages = state.get("researcher_messages", [])
    messages = [SystemMessage(content=researcher_prompt)] + researcher_messages
    response = await research_model.ainvoke(messages)

    return Command(
        goto="researcher_tools",
        update={
            "researcher_messages": [response],
            "tool_call_iterations": state.get("tool_call_iterations", 0) + 1,
        },
    )


async def researcher_tools(
    state: CustomResearcherState, config: RunnableConfig
) -> Command[Literal["researcher", "compress_research"]]:
    """
    Execute tools called by the researcher.
    """
    from .tools import (
        internal_fetch,
        internal_search,
        web_fetch,
        web_search,
    )

    # Tools now access services directly through RunnableConfig

    researcher_messages = state.get("researcher_messages", [])
    most_recent_message = researcher_messages[-1] if researcher_messages else None

    # Check if any tool calls were made
    if not most_recent_message or not isinstance(most_recent_message, AIMessage):
        return Command(goto="compress_research")

    tool_calls = getattr(most_recent_message, "tool_calls", None) or []
    if not tool_calls:
        return Command(goto="compress_research")

    # Execute actual tool calls
    tool_outputs = []
    for tool_call in tool_calls:
        tool_name = tool_call.get("name", "")
        args = tool_call.get("args", {})

        try:
            # Execute real tools
            if tool_name == "web_search":
                result = await web_search.ainvoke(args)
            elif tool_name == "web_fetch":
                result = await web_fetch.ainvoke(args)
            elif tool_name == "internal_search":
                result = await internal_search.ainvoke(args)
            elif tool_name == "internal_fetch":
                result = await internal_fetch.ainvoke(args)
            else:
                result = f"Unknown tool: {tool_name}"
        except Exception as e:
            logger.error(f"Error executing tool {tool_name}: {e}")
            result = f"Error executing {tool_name}: {str(e)}"

        tool_outputs.append(
            ToolMessage(
                content=result,
                name=tool_name,
                tool_call_id=tool_call.get("id", "unknown"),
            )
        )

    # Check if we should continue or finish
    custom_config = get_custom_engine_config(config)
    max_iterations = custom_config.max_tool_calls_per_researcher
    if state.get("tool_call_iterations", 0) >= max_iterations:
        return Command(
            goto="compress_research", update={"researcher_messages": tool_outputs}
        )

    return Command(goto="researcher", update={"researcher_messages": tool_outputs})


async def compress_research(
    state: CustomResearcherState, config: RunnableConfig
) -> Dict[str, Any]:
    """
    Compress and synthesize research findings into a summary.
    """
    researcher_messages = state.get("researcher_messages", [])

    # Simple compression: extract key information
    tool_messages = [msg for msg in researcher_messages if isinstance(msg, ToolMessage)]
    ai_messages = [msg for msg in researcher_messages if isinstance(msg, AIMessage)]

    # Create compressed research summary
    research_topic = state.get("research_topic", "Unknown topic")
    tool_results = "\n".join([str(msg.content) for msg in tool_messages])
    ai_analysis = "\n".join([str(msg.content) for msg in ai_messages])

    compressed_research = f"""Research on: {research_topic}

Tool Results:
{tool_results}

Analysis:
{ai_analysis}
"""

    raw_notes = [str(msg.content) for msg in researcher_messages]

    return {
        "compressed_research": compressed_research,
        "raw_notes": raw_notes,
    }


async def final_report_generation(
    state: CustomAgentState, config: RunnableConfig
) -> Dict[str, Any]:
    """
    Generate the final comprehensive research report.
    """
    write_state_message_log(state, "Synthesizing final research report...")

    notes = state.get("notes", [])
    research_brief = state.get("research_brief", "")

    # Simple report generation for now
    final_report = f"""# Research Report

## Research Brief
{research_brief}

## Findings
{chr(10).join(notes)}

## Generated on
{get_today_str()}
"""

    return {
        "final_report": final_report,
        "messages": [AIMessage(content=final_report)],
        "notes": {"type": "override", "value": []},  # Clear notes
    }


# Graph Construction

# Researcher Subgraph for parallel execution
researcher_builder = StateGraph(CustomResearcherState)

researcher_builder.add_node("researcher", researcher)
researcher_builder.add_node("researcher_tools", researcher_tools)
researcher_builder.add_node("compress_research", compress_research)

researcher_builder.add_edge(START, "researcher")
researcher_builder.add_edge("compress_research", END)

researcher_subgraph = researcher_builder.compile()

# Supervisor Subgraph
supervisor_builder = StateGraph(CustomSupervisorState)

supervisor_builder.add_node("research_supervisor", research_supervisor)
supervisor_builder.add_node("supervisor_tools", supervisor_tools)

supervisor_builder.add_edge(START, "research_supervisor")

supervisor_subgraph = supervisor_builder.compile()

# Main Custom Agent Graph
custom_agent_builder = StateGraph(CustomAgentState)

custom_agent_builder.add_node("setup_research_supervisor", setup_research_supervisor)
custom_agent_builder.add_node("research_supervisor", supervisor_subgraph)
custom_agent_builder.add_node("final_report_generation", final_report_generation)

custom_agent_builder.add_edge(START, "setup_research_supervisor")
custom_agent_builder.add_edge("setup_research_supervisor", "research_supervisor")
custom_agent_builder.add_edge("research_supervisor", "final_report_generation")
custom_agent_builder.add_edge("final_report_generation", END)

# Compile the complete custom research workflow
custom_agent = custom_agent_builder.compile()
