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
    ToolCall,
    ToolMessage,
)
from langchain_core.runnables import RunnableConfig
from langgraph.graph import END, START, StateGraph
from langgraph.types import Command
from unique_toolkit.app.unique_settings import UniqueSettings
from unique_toolkit.framework_utilities.utils import get_default_headers

from ..config import TEMPLATE_ENV
from .state import (
    AgentState,
    ResearcherOutputState,
    ResearcherState,
    SupervisorState,
)
from .tools import (
    format_tools_for_prompt,
    get_research_tools,
    get_supervisor_tools,
    get_today_str,
    internal_fetch,
    internal_search,
    research_complete,
    research_complete_tool_called,
    think_tool,
    web_fetch,
    web_search,
)
from .utils import (
    ainvoke_with_token_handling,
    execute_tool_safely,
    get_engine_config,
    get_notes_from_tool_calls,
    write_state_message_log,
)

_LOGGER = logging.getLogger(__name__)


# Settings for OpenAI model initialization
_unique_settings = UniqueSettings.from_env_auto()


def get_configurable_model(config: RunnableConfig):
    """
    Get the configurable model with additional headers merged from config.

    Args:
        config: RunnableConfig that contains additional_openai_proxy_headers

    Returns:
        The configurable model with merged headers
    """
    # Get base default headers
    base_default_headers = get_default_headers(
        _unique_settings.app, _unique_settings.auth
    )

    # Get additional headers from config
    configurable = config.get("configurable", {})
    additional_openai_proxy_headers = configurable.get(
        "additional_openai_proxy_headers", {}
    )

    # Merge additional headers with base headers
    merged_headers = {**base_default_headers, **additional_openai_proxy_headers}

    # Create and return a new model instance with merged headers
    return init_chat_model(
        model_provider="openai",
        openai_api_key=_unique_settings.app.key.get_secret_value(),
        openai_api_base=_unique_settings.api.openai_proxy_url(),
        default_headers=merged_headers,
        configurable_fields=("model", "max_tokens", "temperature"),
    )


async def setup_research_supervisor(
    state: AgentState, config: RunnableConfig
) -> Command[Literal["research_supervisor"]]:
    """
    Setup the research supervisor with the pre-generated research brief.

    The research brief was already generated in the main service flow,
    so we just need to initialize the supervisor state.
    """
    _LOGGER.info("Initializing research supervisor...")

    # Get the pre-generated research brief from state
    research_brief = state.get("research_brief")
    assert research_brief, "Research brief is required"

    engine_config = get_engine_config(config)

    # Initialize supervisor state with config values
    max_concurrent = engine_config.max_parallel_researchers
    max_iterations = engine_config.max_research_iterations_lead_researcher

    # Get supervisor tools and format their descriptions
    supervisor_tools = get_supervisor_tools()
    tools_description = format_tools_for_prompt(supervisor_tools)

    # Get research tools and format their descriptions for template
    research_tools = get_research_tools(config)
    research_tools_description = format_tools_for_prompt(research_tools)

    supervisor_system_prompt = TEMPLATE_ENV.get_template(
        "unique/lead_agent_system.j2"
    ).render(
        date=get_today_str(),
        tools=tools_description,
        max_concurrent_research_units=max_concurrent,
        max_researcher_iterations=max_iterations,
        research_tools_description=research_tools_description,
        enable_internal_tools=engine_config.tools.internal_tools,
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
    state: SupervisorState, config: RunnableConfig
) -> Command[Literal["supervisor_tools"]]:
    """
    Lead research supervisor that plans research strategy and delegates to researchers.
    """
    _LOGGER.info("Research supervisor determining next steps")

    # Configure the supervisor model with tools
    engine_config = get_engine_config(config)

    model_config = {
        "model": engine_config.research_model.name,
        "max_tokens": min(
            10_000,
            int(engine_config.research_model.token_limits.token_limit_output * 0.9),
        ),
    }

    # Available tools for the supervisor
    supervisor_tools = get_supervisor_tools()

    # Check if we should force tool usage
    research_iterations = state.get("research_iterations", 0)
    max_iterations = engine_config.max_research_iterations_lead_researcher
    should_force_complete = research_iterations >= max_iterations

    # Get model with additional headers from config
    model = get_configurable_model(config)

    if should_force_complete:
        _LOGGER.info(
            f"Forcing research_complete at iteration {research_iterations}/{max_iterations}"
        )
        model_with_tools = model.bind_tools(
            supervisor_tools,
            tool_choice="research_complete",
        )
    else:
        model_with_tools = model.bind_tools(supervisor_tools)

    research_model = model_with_tools.with_config(model_config)

    # Generate supervisor response with comprehensive token limit handling
    supervisor_messages = state.get("supervisor_messages", [])

    response = await ainvoke_with_token_handling(
        research_model, supervisor_messages, model_info=engine_config.research_model
    )
    if should_force_complete and not response.tool_calls:
        _LOGGER.error("Failed to force research_complete tool call")

    return Command(
        goto="supervisor_tools",
        update={
            "supervisor_messages": [response],
            "research_iterations": state.get("research_iterations", 0) + 1,
        },
    )


async def supervisor_tools(
    state: SupervisorState, config: RunnableConfig
) -> Command[Literal["research_supervisor", "researcher_subgraph", "__end__"]]:
    """
    Execute tools called by the supervisor.
    """
    _LOGGER.info("Supervisor tool processing")
    supervisor_messages = state.get("supervisor_messages", [])
    research_iterations = state.get("research_iterations", 0)
    most_recent_message = supervisor_messages[-1] if supervisor_messages else None

    engine_config = get_engine_config(config)

    # Check exit conditions
    max_iterations = engine_config.max_research_iterations_lead_researcher
    exceeded_iterations = research_iterations >= max_iterations

    # Extract tool calls if available
    tool_calls = []
    if most_recent_message and isinstance(most_recent_message, AIMessage):
        tool_calls = most_recent_message.tool_calls or []

    if not tool_calls:
        _LOGGER.info("Supervisor has no tool calls - will go back to supervisor")
        return Command(
            goto="research_supervisor",
        )

    # TOOL CALL HANDLERS
    all_tool_messages = []
    conduct_research_calls = [
        tc for tc in tool_calls if tc.get("name") == "conduct_research"
    ]
    remaining_tool_calls = [
        tc for tc in tool_calls if tc.get("name") != "conduct_research"
    ]

    # 2. ConductResearch calls
    try:
        research_tool_messages = await _handle_conduct_research_batch(
            conduct_research_calls, state, config
        )
        all_tool_messages.extend(research_tool_messages)

    except Exception as e:
        _LOGGER.exception(f"Research execution failed: {e}")
        return Command(
            goto="__end__",
            update={
                "supervisor_messages": all_tool_messages,
                "notes": [f"Research failed due to error: {e}"],
                "research_brief": state.get("research_brief", ""),
            },
        )
    all_tool_messages.extend(
        await _handle_tool_call_batch(remaining_tool_calls, config)
    )

    if exceeded_iterations or research_complete_tool_called(tool_calls):
        _LOGGER.info(
            "Supervisor has reached the maximum number of iterations or has a research complete tool call. Ending supervisor"
        )
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
    state: ResearcherState, config: RunnableConfig
) -> Command[Literal["researcher_tools"]]:
    """
    Individual researcher that conducts focused research on specific topics.
    """
    _LOGGER.info("Research agent determining next steps")
    research_tools = get_research_tools(config)

    # Configure the researcher model
    engine_config = get_engine_config(config)
    model_config = {
        "model": engine_config.research_model.name,
        "max_tokens": min(
            10_000,
            int(engine_config.research_model.token_limits.token_limit_output * 0.9),
        ),
    }

    # Prepare system prompt with dynamic tool descriptions
    tools_description = format_tools_for_prompt(research_tools)

    # Get tool configuration for template
    enable_internal_tools = engine_config.tools.internal_tools
    enable_web_fetch = (
        engine_config.tools.web_tools
        and engine_config.tools.web_tools_config.enable_web_fetch
    )

    researcher_prompt = TEMPLATE_ENV.get_template(
        "unique/research_agent_system.j2"
    ).render(
        date=get_today_str(),
        tools=tools_description,
        enable_internal_tools=enable_internal_tools,
        enable_web_fetch=enable_web_fetch,
    )

    # Get model with additional headers from config
    model = get_configurable_model(config)

    # Configure model with research tools
    model_with_tools = model.bind_tools(research_tools)
    research_model = model_with_tools.with_config(model_config)  # type: ignore[arg-type]

    # Generate researcher response with comprehensive token limit handling
    researcher_messages = state.get("researcher_messages", [])
    messages = [SystemMessage(content=researcher_prompt)] + researcher_messages
    response = await ainvoke_with_token_handling(
        research_model, messages, model_info=engine_config.research_model
    )

    return Command(
        goto="researcher_tools",
        update={
            "researcher_messages": [response],
            "research_iterations": state.get("research_iterations", 0) + 1,
        },
    )


async def _handle_tool_call(tool_call: ToolCall, config: RunnableConfig) -> ToolMessage:
    """Handle a tool call."""
    tool_name = tool_call.get("name", "")
    args = tool_call.get("args", {})
    tool_map = {
        "web_search": web_search,
        "web_fetch": web_fetch,
        "internal_search": internal_search,
        "internal_fetch": internal_fetch,
        "think_tool": think_tool,
        "research_complete": research_complete,
    }
    if tool_name in tool_map:
        result = await execute_tool_safely(tool_map[tool_name], args, config)
    else:
        _LOGGER.error(f"Unknown tool: {tool_name}")
        result = f"Unknown tool: {tool_name}"
    return ToolMessage(
        content=result,
        name=tool_name,
        tool_call_id=tool_call.get("id", "unknown"),
    )


async def _handle_tool_call_batch(
    tool_calls: list[ToolCall], config: RunnableConfig
) -> list[ToolMessage]:
    """Handle a batch of tool calls."""
    return await asyncio.gather(
        *[_handle_tool_call(tool_call, config) for tool_call in tool_calls]
    )


async def researcher_tools(
    state: ResearcherState, config: RunnableConfig
) -> Command[Literal["researcher", "compress_research"]]:
    """
    Execute tools called by the researcher.
    """
    _LOGGER.info("Research agent executing tools")
    researcher_messages = state.get("researcher_messages", [])
    most_recent_message = researcher_messages[-1] if researcher_messages else None

    engine_config = get_engine_config(config)

    # Check iteration limit
    research_iterations = state.get("research_iterations", 0)
    max_iterations = engine_config.max_research_iterations_sub_researcher
    exceeded_iterations = research_iterations >= max_iterations

    # Check if any tool calls were made
    if not most_recent_message or not isinstance(most_recent_message, AIMessage):
        _LOGGER.info(
            f"Research agent has no tool calls. Ending researcher after {len(researcher_messages)} messages"
        )
        return Command(goto="compress_research")

    tool_calls = most_recent_message.tool_calls or []
    if not tool_calls:
        _LOGGER.info(
            f"Research agent has no tool calls. Ending researcher after {len(researcher_messages)} messages"
        )
        return Command(goto="compress_research")

    # Execute actual tool calls safely
    tool_outputs = await _handle_tool_call_batch(tool_calls, config)

    # Check if we should continue or finish
    if exceeded_iterations or research_complete_tool_called(tool_calls):
        _LOGGER.info(
            f"Research agent has reached the maximum number of tool calls or has a research complete tool call. Ending researcher after {len(researcher_messages)} messages"
        )
        return Command(
            goto="compress_research", update={"researcher_messages": tool_outputs}
        )

    return Command(goto="researcher", update={"researcher_messages": tool_outputs})


async def compress_research(
    state: ResearcherState, config: RunnableConfig
) -> Dict[str, Any]:
    """
    Compress and synthesize research findings using AI-powered synthesis.

    Uses the synthesis template to create a comprehensive, well-structured
    summary of the research findings with proper citations and formatting.
    """
    # Get custom config for model selection
    custom_config = get_engine_config(config)

    # Prepare synthesis model
    model_config = {
        "model": custom_config.large_model.name,
        "max_tokens": min(
            15_000,
            int(custom_config.large_model.token_limits.token_limit_output * 0.9),
        ),
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

    # Get model with additional headers from config
    model = get_configurable_model(config)

    # Configure compression model
    compression_model = model.with_config(model_config)  # type: ignore[arg-type]

    # Use proactive token handling instead of retry logic
    response = await ainvoke_with_token_handling(
        compression_model, compression_messages, model_info=custom_config.large_model
    )

    compressed_research = (
        str(response.content) if response.content else "No synthesis content generated"
    )

    return {
        "compressed_research": compressed_research,
    }


async def final_report_generation(
    state: AgentState, config: RunnableConfig
) -> Dict[str, Any]:
    """
    Generate the final comprehensive research report using AI-powered synthesis.

    This implementation follows the open_deep_research pattern with sophisticated
    token limit handling and progressive truncation strategies.
    """
    write_state_message_log(state, "**Synthesizing final research report**")

    # Step 1: Extract research findings and prepare state cleanup
    notes = state.get("notes", [])
    cleared_state = {"notes": {"type": "override", "value": []}}
    findings = "\n".join(notes)
    research_brief = state.get("research_brief", "")

    message = f"# Research Brief\n{research_brief}"
    message += f"\n\n# Research Findings\n{findings}"

    # Step 2: Configure the final report generation model
    custom_config = get_engine_config(config)
    model_config = {
        "model": custom_config.large_model.name,
        "max_tokens": min(
            30_000, int(custom_config.large_model.token_limits.token_limit_output * 0.9)
        ),
    }
    # Get model with additional headers from config
    model = get_configurable_model(config)
    llm = model.with_config(model_config)
    report_writer_prompt = TEMPLATE_ENV.get_template(
        "unique/report_writer_system_open_deep_research.j2"
    ).render(
        date=get_today_str(),
    )
    messages = [
        SystemMessage(content=report_writer_prompt),
        HumanMessage(content=message),
    ]
    raw_report = await ainvoke_with_token_handling(
        llm, messages, model_info=custom_config.large_model
    )

    refinement_prompt = TEMPLATE_ENV.get_template("report_cleanup_prompt.j2").render()
    messages = [
        SystemMessage(content=refinement_prompt),
        HumanMessage(content=raw_report.content),
    ]
    refined_report = await ainvoke_with_token_handling(
        llm, messages, model_info=custom_config.large_model
    )

    # Return successful report generation
    return {
        "final_report": refined_report.content,
        "messages": [refined_report],
        **cleared_state,
    }


################ TOOL HANDLERS #################


async def _handle_conduct_research_batch(
    conduct_research_calls: list[Union[dict, Any]],
    state: SupervisorState,
    config: RunnableConfig,
) -> list[ToolMessage]:
    """Handle multiple ConductResearch calls in parallel for efficiency."""
    if not conduct_research_calls:
        return []

    _LOGGER.info(f"Delegating {len(conduct_research_calls)} research tasks...")

    # Limit concurrent research tasks to prevent resource exhaustion
    engine_config = get_engine_config(config)

    max_concurrent = engine_config.max_parallel_researchers
    allowed_calls = conduct_research_calls[:max_concurrent]
    skipped_calls = conduct_research_calls[max_concurrent:]

    # Execute research tasks in parallel
    research_tasks = [
        researcher_subgraph.ainvoke(
            {
                "researcher_messages": [
                    HumanMessage(content=tool_call["args"]["research_topic"])
                ],
                "research_topic": tool_call["args"]["research_topic"],
                "research_iterations": 0,
                "chat_service": state["chat_service"],
                "message_id": state["message_id"],
            },
            config,
        )
        for tool_call in allowed_calls
    ]

    # Use return_exceptions=True to handle partial failures gracefully
    tool_results = await asyncio.gather(*research_tasks, return_exceptions=True)

    # Create tool messages with compressed research results or error messages
    tool_messages = []
    for observation, tool_call in zip(tool_results, allowed_calls):
        if isinstance(observation, Exception):
            _LOGGER.exception(
                f"Research task failed: {str(observation)}", exc_info=observation
            )
            error_content = f"Research task failed: {str(observation)}"
            tool_messages.append(
                ToolMessage(
                    content=error_content,
                    name=tool_call["name"],
                    tool_call_id=tool_call["id"],
                )
            )
        else:
            # Handle successful task
            content = "No research results"
            if isinstance(observation, dict):
                content = observation.get("compressed_research", "No research results")
            tool_messages.append(
                ToolMessage(
                    content=content,
                    name=tool_call["name"],
                    tool_call_id=tool_call["id"],
                )
            )

    # Add "research not started" responses for skipped calls
    for tool_call in skipped_calls:
        tool_messages.append(
            ToolMessage(
                content=f"Research not started - exceeded concurrent research limit of {max_concurrent}. Please try again in the next iteration.",
                name=tool_call["name"],
                tool_call_id=tool_call["id"],
            )
        )

    return tool_messages


################ GRAPH CONSTRUCTION #################

# Researcher Subgraph for parallel execution
researcher_builder = StateGraph(ResearcherState, output_schema=ResearcherOutputState)

researcher_builder.add_node("researcher", researcher)
researcher_builder.add_node("researcher_tools", researcher_tools)
researcher_builder.add_node("compress_research", compress_research)

researcher_builder.add_edge(START, "researcher")
researcher_builder.add_edge("compress_research", END)

researcher_subgraph = researcher_builder.compile()

# Supervisor Subgraph
supervisor_builder = StateGraph(SupervisorState)

supervisor_builder.add_node("research_supervisor", research_supervisor)
supervisor_builder.add_node("supervisor_tools", supervisor_tools)
supervisor_builder.add_node("researcher_subgraph", researcher_subgraph)

supervisor_builder.add_edge(START, "research_supervisor")

supervisor_subgraph = supervisor_builder.compile()

# Main Custom Agent Graph
custom_agent_builder = StateGraph(AgentState)

custom_agent_builder.add_node("setup_research_supervisor", setup_research_supervisor)
custom_agent_builder.add_node("research_supervisor", supervisor_subgraph)
custom_agent_builder.add_node("final_report_generation", final_report_generation)

custom_agent_builder.add_edge(START, "setup_research_supervisor")
custom_agent_builder.add_edge("setup_research_supervisor", "research_supervisor")
custom_agent_builder.add_edge("research_supervisor", "final_report_generation")
custom_agent_builder.add_edge("final_report_generation", END)

# Compile the complete custom research workflow
custom_agent = custom_agent_builder.compile()
