import logging
from typing import Unpack

from unique_toolkit.agentic.loop_runner._responses_stream_handler_utils import (
    responses_stream_response,
)
from unique_toolkit.agentic.loop_runner.base import (
    _ResponsesLoopIterationRunnerKwargs,
)
from unique_toolkit.language_model.schemas import ResponsesLanguageModelStreamResponse

_LOGGER = logging.getLogger(__name__)


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
        responses.append(
            await responses_stream_response(loop_runner_kwargs=kwargs, tool_choice=opt)
        )

    # Merge responses and refs:
    tool_calls = []
    references = []
    for r in responses:
        if r.tool_calls:
            tool_calls.extend(r.tool_calls)
        references.extend(r.message.references)

    response = responses[0]
    response.tool_calls = tool_calls if len(tool_calls) > 0 else None
    response.message.references = references

    return response
