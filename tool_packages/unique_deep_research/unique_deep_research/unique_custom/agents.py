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
    BaseMessage,
    HumanMessage,
    SystemMessage,
    ToolMessage,
    get_buffer_string,
)
from langchain_core.runnables import RunnableConfig
from langgraph.graph import END, START, StateGraph
from langgraph.types import Command
from unique_toolkit.app.unique_settings import UniqueSettings
from unique_toolkit.framework_utilities.utils import get_default_headers

from ..config import TEMPLATE_ENV
from .state import (
    CustomAgentState,
    CustomResearcherState,
    CustomSupervisorState,
)
from .tools import get_research_tools, get_supervisor_tools, get_today_str, think_tool
from .utils import (
    execute_tool_safely,
    get_custom_engine_config,
    is_token_error,
    remove_up_to_last_ai_message,
    write_state_message_log,
)

logger = logging.getLogger(__name__)


# Pre-configured model for all agents with OpenAI settings
unique_settings = UniqueSettings.from_env_auto()
configurable_model = init_chat_model(
    model_provider="openai",
    openai_api_key=unique_settings.app.key.get_secret_value(),
    openai_api_base=unique_settings.api.openai_proxy_url(),
    default_headers=get_default_headers(unique_settings.app, unique_settings.auth),
    configurable_fields=("model", "max_tokens", "temperature"),
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

    model_config = {
        "model": custom_config.lead_agent_model.name,
        "max_tokens": 8000,
        "temperature": 0.1,
    }

    # Available tools for the supervisor
    supervisor_tools = get_supervisor_tools()

    # Configure model with tools
    model_with_tools = configurable_model.bind_tools(supervisor_tools)
    research_model = model_with_tools.with_config(model_config)  # type: ignore[arg-type]

    # Generate supervisor response with token limit awareness
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
        tool_calls = most_recent_message.tool_calls or []
        no_tool_calls = not tool_calls
        research_complete_called = any(
            tool_call.get("name") == "ResearchComplete" for tool_call in tool_calls
        )

    if exceeded_iterations or no_tool_calls or research_complete_called:
        # Extract notes from all supervisor messages for final report
        notes = []
        for msg in supervisor_messages:
            if isinstance(msg, BaseMessage) and msg.content:
                notes.append(msg.content)

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
        tool_calls = most_recent_message.tool_calls or []
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
        goto="research_supervisor",
        update={"supervisor_messages": all_tool_messages},
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
    model_config = {
        "model": custom_config.research_agent_model.name,
        "max_tokens": 10000,
        "temperature": 0.1,
    }

    # Prepare system prompt
    researcher_prompt = TEMPLATE_ENV.get_template(
        "unique/research_agent_system.j2"
    ).render(date=get_today_str())

    # Configure model with research tools
    model_with_tools = configurable_model.bind_tools(research_tools)
    research_model = model_with_tools.with_config(model_config)  # type: ignore[arg-type]

    # Generate researcher response with token limit awareness
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

    tool_calls = most_recent_message.tool_calls or []
    if not tool_calls:
        return Command(goto="compress_research")

    # Execute actual tool calls safely
    tool_outputs = []
    for tool_call in tool_calls:
        tool_name = tool_call.get("name", "")
        args = tool_call.get("args", {})

        # Map tool names to tool functions
        tool_map = {
            "web_search": web_search,
            "web_fetch": web_fetch,
            "internal_search": internal_search,
            "internal_fetch": internal_fetch,
            "think_tool": think_tool,
        }

        if tool_name in tool_map:
            # Execute tool safely with error handling
            result = await execute_tool_safely(tool_map[tool_name], args, config)
        else:
            result = f"Unknown tool: {tool_name}"

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
    Compress and synthesize research findings using AI-powered synthesis.

    Uses the synthesis template to create a comprehensive, well-structured
    summary of the research findings with proper citations and formatting.
    """
    researcher_messages = state.get("researcher_messages", [])
    research_topic = state.get("research_topic", "Unknown topic")

    # Get custom config for model selection
    custom_config = get_custom_engine_config(config)

    # Prepare synthesis model
    model_config = {
        "model": custom_config.synthesis_model.name,
        "max_tokens": 8000,
        "temperature": 0.1,
    }

    # Prepare synthesis prompt with research context
    synthesis_prompt = TEMPLATE_ENV.get_template(
        "unique/synthesis_agent_system.j2"
    ).render(date=get_today_str())

    # Build synthesis context from messages
    research_context = f"Research Topic: {research_topic}\n\n"
    for i, msg in enumerate(researcher_messages, 1):
        if isinstance(msg, ToolMessage):
            research_context += f"Tool Result {i}:\n{msg.content}\n\n"
        elif isinstance(msg, AIMessage):
            research_context += f"Analysis {i}:\n{msg.content}\n\n"

    synthesis_messages = [
        SystemMessage(content=synthesis_prompt),
        HumanMessage(content=research_context),
    ]

    # Configure synthesis model
    synthesis_model = configurable_model.with_config(model_config)  # type: ignore[arg-type]

    # Simple synthesis with retry logic for token limit issues (like open_deep_research)
    synthesis_attempts = 0
    max_attempts = 3

    while synthesis_attempts < max_attempts:
        try:
            synthesis_response = await synthesis_model.ainvoke(synthesis_messages)
            compressed_research = (
                str(synthesis_response.content)
                if synthesis_response.content
                else research_context
            )
            # Success! Break out of retry loop
            break

        except Exception as e:
            synthesis_attempts += 1

            # Handle token limit exceeded by removing older messages
            if is_token_error(e):
                researcher_messages = remove_up_to_last_ai_message(researcher_messages)

                # Rebuild synthesis context with truncated messages
                research_context = f"Research Topic: {research_topic}\n\n"
                for i, msg in enumerate(researcher_messages, 1):
                    if isinstance(msg, ToolMessage):
                        research_context += f"Tool Result {i}:\n{msg.content}\n\n"
                    elif isinstance(msg, AIMessage):
                        research_context += f"Analysis {i}:\n{msg.content}\n\n"

                synthesis_messages = [
                    SystemMessage(content=synthesis_prompt),
                    HumanMessage(content=research_context),
                ]
                continue

            # For other errors, continue retrying
            continue

    # If all attempts failed, use fallback
    if synthesis_attempts >= max_attempts:
        compressed_research = (
            "Error synthesizing research report: Maximum retries exceeded"
        )

    # Create raw notes for backup
    raw_notes = []
    for msg in researcher_messages:
        try:
            if isinstance(msg, BaseMessage) and msg.content:
                raw_notes.append(msg.content)
            else:
                raw_notes.append(str(msg))
        except (AttributeError, TypeError):
            raw_notes.append(str(msg))

    return {
        "compressed_research": compressed_research,
        "raw_notes": raw_notes,
    }


async def final_report_generation(
    state: CustomAgentState, config: RunnableConfig
) -> Dict[str, Any]:
    """
    Generate the final comprehensive research report using AI-powered synthesis.

    This implementation follows the open_deep_research pattern with sophisticated
    token limit handling and progressive truncation strategies.
    """
    write_state_message_log(state, "Synthesizing final research report...")

    # Step 1: Extract research findings and prepare state cleanup
    notes = state.get("notes", [])
    cleared_state = {"notes": {"type": "override", "value": []}}
    findings = "\n".join(notes)

    # Step 2: Configure the final report generation model
    custom_config = get_custom_engine_config(config)
    model_config = {
        "model": custom_config.synthesis_model.name,
        "max_tokens": 8000,
        "temperature": 0.1,
    }

    # Step 3: Attempt report generation with token limit retry logic
    max_retries = 3
    iteration = 0
    findings_char_limit = None

    while iteration <= max_retries:
        iteration += 1
        try:
            # Use our existing report writer template
            report_writer_prompt = TEMPLATE_ENV.get_template(
                "unique/report_writer_system_open_deep_research.j2"
            ).render(
                research_brief=state.get("research_brief", ""),
                messages=get_buffer_string(state.get("messages", [])),
                findings=findings,
                date=get_today_str(),
            )

            # Generate the final report
            report_model = configurable_model.with_config(model_config)  # type: ignore[arg-type]
            final_report = await report_model.ainvoke(
                [HumanMessage(content=report_writer_prompt)]
            )

            # Return successful report generation
            return {
                "final_report": final_report.content,
                "messages": [final_report],
                **cleared_state,
            }

        except Exception as e:
            # Handle token limit exceeded errors with progressive truncation
            if is_token_error(e):
                model_token_limit = (
                    custom_config.synthesis_model.token_limits.token_limit_input
                )

                if iteration == 1:
                    # Reserve space for prompt and use ~4 characters per token approximation
                    # Use 70% of token limit to leave room for prompt, then convert to characters
                    available_tokens = int(model_token_limit * 0.7)
                    findings_char_limit = available_tokens * 4  # ~4 chars per token
                else:
                    # Subsequent retries: reduce by 10% each time

                    fallback_char_limit = int(model_token_limit * 0.7) * 4
                    findings_char_limit = int(
                        (findings_char_limit or fallback_char_limit) * 0.9
                    )

                # Truncate findings and retry
                findings = findings[:findings_char_limit]
                continue
            else:
                logger.error(f"Error generating final report: {e}")
                # Non-token-limit error: return error immediately
                return {
                    "final_report": f"Error generating final report: {e}",
                    "messages": [
                        AIMessage(content="Report generation failed due to an error")
                    ],
                    **cleared_state,
                }

    # Step 4: Return failure result if all retries exhausted
    return {
        "final_report": "Error generating final report: Maximum retries exceeded",
        "messages": [
            AIMessage(content="Report generation failed after maximum retries")
        ],
        **cleared_state,
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
