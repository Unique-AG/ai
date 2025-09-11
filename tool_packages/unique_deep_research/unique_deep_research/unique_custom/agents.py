"""
LangGraph workflow implementation for Unique Custom Deep Research Engine

This module implements the multi-agent research workflow using LangGraph,
following the pattern from open_deep_research but integrated with unique_toolkit.
"""

import asyncio
import logging
from typing import Any, Dict, Literal, Union

from langchain.chat_models import init_chat_model
from langchain_core.messages import (
    AIMessage,
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
    CustomResearcherOutputState,
    CustomResearcherState,
    CustomSupervisorState,
)
from .tools import (
    get_research_tools,
    get_supervisor_tools,
    get_today_str,
    internal_fetch,
    internal_search,
    think_tool,
    web_fetch,
    web_search,
)
from .utils import (
    execute_tool_safely,
    get_custom_engine_config,
    get_notes_from_tool_calls,
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
    logger.info("Initializing research supervisor...")

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
    logger.info("Research supervisor determining next steps")

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
) -> Command[Literal["research_supervisor", "researcher_subgraph", "__end__"]]:
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

    # Extract tool calls if available
    tool_calls = []
    if most_recent_message and isinstance(most_recent_message, AIMessage):
        tool_calls = most_recent_message.tool_calls or []

    # Early exit if no tool calls at all
    if not tool_calls:
        notes = get_notes_from_tool_calls(supervisor_messages)
        return Command(
            goto="__end__",
            update={
                "notes": notes,
                "research_brief": state.get("research_brief", ""),
            },
        )

    # TOOL CALL HANDLERS
    all_tool_messages = []

    think_tool_calls = [tc for tc in tool_calls if tc.get("name") == "think_tool"]
    conduct_research_calls = [
        tc for tc in tool_calls if tc.get("name") == "ConductResearch"
    ]

    research_complete_calls = [
        tc for tc in tool_calls if tc.get("name") == "ResearchComplete"
    ]

    if len(research_complete_calls) > 0 and len(tool_calls) > 1:
        logger.warning("ResearchComplete called when there are other tool calls")
        # TODO: consider if we remove the other tool calls

    # Process all tool calls to ensure answers to tool calls are in history

    # 1. think_tool calls
    for tool_call in think_tool_calls:
        all_tool_messages.append(_handle_think_tool(tool_call))

    # 2. ConductResearch calls
    try:
        research_tool_messages = await _handle_conduct_research_batch(
            conduct_research_calls, state, config, custom_config
        )
        all_tool_messages.extend(research_tool_messages)

    except Exception as e:
        logger.error(f"Research execution failed: {e}")
        return Command(
            goto="__end__",
            update={
                "supervisor_messages": all_tool_messages,  # Include any tool messages created so far
                "notes": [f"Research failed due to error: {e}"],
                "research_brief": state.get("research_brief", ""),
            },
        )

    # 3. ResearchComplete calls
    for tool_call in research_complete_calls:
        all_tool_messages.append(_handle_research_complete(tool_call))

    research_complete_called = len(research_complete_calls) > 0

    if exceeded_iterations or research_complete_called:
        # Extract notes including the new tool messages we just created
        notes = get_notes_from_tool_calls(supervisor_messages + all_tool_messages)

        # Finish subgraph and proceed to final report generation
        return Command(
            goto="__end__",
            update={
                "supervisor_messages": all_tool_messages,  # MUST include tool messages for proper pairing
                "notes": notes,
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
            logger.error(f"Unknown tool: {tool_name}")
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
    # Get custom config for model selection
    custom_config = get_custom_engine_config(config)

    # Prepare synthesis model
    model_config = {
        "model": custom_config.compression_model.name,
        "max_tokens": 8192,
        "temperature": 0.1,
    }

    # PROMPTS
    compression_system_prompt = TEMPLATE_ENV.get_template(
        "unique/compress_research_system.j2"
    ).render(date=get_today_str())

    researcher_messages = state.get("researcher_messages", [])

    # Get the specific research topic assigned to this researcher
    research_topic = state.get("research_topic", "")

    # Add instruction to switch from research mode to compression mode with topic context
    compression_instruction = f"""You are compressing research findings for this SPECIFIC research topic:
    ASSIGNED TOPIC: {research_topic}
    All above messages are from research conducted SPECIFICALLY for this topic.
    Please clean up these findings, focusing ONLY on information relevant to the assigned topic above.
    DO NOT include tangential information found during searches that doesn't directly address this specific topic.
    DO NOT summarize - preserve all relevant information in a cleaner format.
    Keep all citations and references that relate to this topic."""

    # Follow reference architecture: append instruction to researcher messages
    researcher_messages.append(HumanMessage(content=compression_instruction))

    # Create messages with system prompt + all researcher messages (like reference)
    compression_messages = [
        SystemMessage(content=compression_system_prompt)
    ] + researcher_messages

    # Configure compression model
    compression_model = configurable_model.with_config(model_config)  # type: ignore[arg-type]

    # Synthesis with retry logic for token limit issues
    max_retries = 3
    iteration = 0

    while iteration <= max_retries:
        iteration += 1
        try:
            response = await compression_model.ainvoke(compression_messages)
            compressed_research = (
                str(response.content)
                if response.content
                else "No synthesis content generated"
            )
            # Success! Break out of retry loop
            break

        except Exception as e:
            # Handle token limit exceeded by removing older messages (like reference)
            if is_token_error(e):
                # Remove older messages to reduce token usage
                researcher_messages = remove_up_to_last_ai_message(researcher_messages)

                # Rebuild messages with system prompt + truncated researcher messages
                compression_messages = [
                    SystemMessage(content=compression_system_prompt)
                ] + researcher_messages
                continue
            else:
                logger.error(f"Error compressing research: {e}")
                # For other errors, continue retrying
                continue

    # If all attempts failed, use fallback
    if iteration > max_retries:
        compressed_research = (
            "Error synthesizing research report: Maximum retries exceeded"
        )

    return {
        "compressed_research": compressed_research,
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
        "model": custom_config.final_report_synthesis_model.name,
        "max_tokens": 10000,
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
                model_token_limit = custom_config.final_report_synthesis_model.token_limits.token_limit_input

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


################ TOOL HANDLERS #################


def _handle_think_tool(tool_call: Union[dict, Any]) -> ToolMessage:
    """Handle think_tool calls with strategic reflection."""
    reflection_content = tool_call["args"]["reflection"]
    return ToolMessage(
        content=f"Reflection recorded: {reflection_content}",
        name="think_tool",
        tool_call_id=tool_call["id"],
    )


def _handle_research_complete(tool_call: Union[dict, Any]) -> ToolMessage:
    """Handle ResearchComplete calls with final summary."""
    summary = tool_call["args"].get("summary", "Research completed")
    sources = tool_call["args"].get("sources", [])

    content = f"Research completed with summary: {summary}"
    if sources:
        content += f"\nSources: {', '.join(sources)}"

    return ToolMessage(
        content=content,
        name="ResearchComplete",
        tool_call_id=tool_call["id"],
    )


async def _handle_conduct_research_batch(
    conduct_research_calls: list[Union[dict, Any]],
    state: CustomSupervisorState,
    config: RunnableConfig,
    custom_config,
) -> list[ToolMessage]:
    """Handle multiple ConductResearch calls in parallel for efficiency."""
    if not conduct_research_calls:
        return []

    logger.info(f"Delegating {len(conduct_research_calls)} research tasks...")

    # Limit concurrent research tasks to prevent resource exhaustion
    max_concurrent = custom_config.max_parallel_researchers
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

    # Create tool messages with compressed research results
    tool_messages = [
        ToolMessage(
            content=observation.get("compressed_research", "No research results"),
            name=tool_call["name"],
            tool_call_id=tool_call["id"],
        )
        for observation, tool_call in zip(tool_results, allowed_calls)
    ]

    return tool_messages


################ GRAPH CONSTRUCTION #################

# Researcher Subgraph for parallel execution
researcher_builder = StateGraph(
    CustomResearcherState, output_schema=CustomResearcherOutputState
)

researcher_builder.add_node("researcher", researcher)
researcher_builder.add_node("researcher_tools", researcher_tools)
researcher_builder.add_node("compress_research", compress_research)

researcher_builder.add_edge(START, "researcher")
researcher_builder.add_edge("researcher", "researcher_tools")
researcher_builder.add_edge("researcher_tools", "compress_research")
researcher_builder.add_edge("compress_research", END)

researcher_subgraph = researcher_builder.compile()

# Supervisor Subgraph
supervisor_builder = StateGraph(CustomSupervisorState)

supervisor_builder.add_node("research_supervisor", research_supervisor)
supervisor_builder.add_node("supervisor_tools", supervisor_tools)
supervisor_builder.add_node("researcher_subgraph", researcher_subgraph)

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
