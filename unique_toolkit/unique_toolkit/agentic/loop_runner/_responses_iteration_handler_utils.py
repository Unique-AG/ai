import logging
from collections.abc import Sequence
from typing import Unpack

from openai.types.responses import ToolParam, response_create_params

from unique_toolkit.agentic.loop_runner._responses_stream_handler_utils import (
    responses_stream_response,
)
from unique_toolkit.agentic.loop_runner.base import (
    _ResponsesLoopIterationRunnerKwargs,
)
from unique_toolkit.language_model.schemas import (
    LanguageModelTokenUsage,
    LanguageModelToolDescription,
    ResponsesLanguageModelStreamResponse,
)

_LOGGER = logging.getLogger(__name__)


def _is_forced_function_choice(
    tool_choice: response_create_params.ToolChoice,
) -> bool:
    return isinstance(tool_choice, dict) and tool_choice.get("type") == "function"


def _is_hosted_tool(tool: LanguageModelToolDescription | ToolParam) -> bool:
    """Return whether OpenAI executes the tool."""
    if isinstance(tool, LanguageModelToolDescription):
        return False
    return tool.get("type") != "function"


def _tools_for_forced_choice(
    tools: Sequence[LanguageModelToolDescription | ToolParam] | None,
    tool_choice: response_create_params.ToolChoice,
) -> list[LanguageModelToolDescription | ToolParam] | None:
    """Drop hosted tools from requests that force a function tool."""
    if tools is None or not _is_forced_function_choice(tool_choice):
        return list(tools) if tools is not None else None

    remaining = [tool for tool in tools if not _is_hosted_tool(tool)]
    dropped = len(tools) - len(remaining)
    if dropped > 0:
        _LOGGER.info(
            "Dropped %d hosted tool(s) from the forced function request.",
            dropped,
        )
    return remaining


async def handle_responses_last_iteration(
    **kwargs: Unpack[_ResponsesLoopIterationRunnerKwargs],
) -> ResponsesLanguageModelStreamResponse:
    _LOGGER.info("Reached last iteration, removing tools and producing final response")

    return await responses_stream_response(
        loop_runner_kwargs=kwargs,
        tools=None,
    )


async def handle_responses_normal_iteration(
    **kwargs: Unpack[_ResponsesLoopIterationRunnerKwargs],
) -> ResponsesLanguageModelStreamResponse:
    _LOGGER.info("Running loop iteration %d", kwargs["iteration_index"])

    return await responses_stream_response(loop_runner_kwargs=kwargs)


async def handle_responses_forced_tools_iteration(
    **kwargs: Unpack[_ResponsesLoopIterationRunnerKwargs],
) -> ResponsesLanguageModelStreamResponse:
    assert "tool_choices" in kwargs

    tool_choices = kwargs["tool_choices"]
    assert len(tool_choices) > 0

    _LOGGER.info("Forcing tools calls: %s", tool_choices)

    responses: list[ResponsesLanguageModelStreamResponse] = []

    for opt in tool_choices:
        tools = _tools_for_forced_choice(kwargs.get("tools"), opt)
        if tools is None:
            response = await responses_stream_response(
                loop_runner_kwargs=kwargs, tool_choice=opt
            )
        else:
            response = await responses_stream_response(
                loop_runner_kwargs=kwargs, tool_choice=opt, tools=tools
            )
        responses.append(response)

    # Merge responses and refs:
    tool_calls = []
    references = []
    for r in responses:
        if r.tool_calls:
            tool_calls.extend(r.tool_calls)
        references.extend(r.message.references or [])

    response = responses[0]
    response.tool_calls = tool_calls if len(tool_calls) > 0 else None
    response.message.references = references
    response.usage = LanguageModelTokenUsage.sum_usages(r.usage for r in responses)

    return response
