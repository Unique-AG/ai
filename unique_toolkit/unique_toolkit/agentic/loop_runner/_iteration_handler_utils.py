import logging
from typing import Protocol, Unpack

from unique_toolkit.agentic.loop_runner._stream_handler_utils import stream_response
from unique_toolkit.agentic.loop_runner.base import (
    _LoopIterationRunnerKwargs,
)
from unique_toolkit.chat.functions import LanguageModelStreamResponse

_LOGGER = logging.getLogger(__name__)


class PrepareForcedToolIterationKwargs(Protocol):
    def __call__(
        self,
        func_name: str | None,
        per_choice_kwargs: _LoopIterationRunnerKwargs,
    ) -> _LoopIterationRunnerKwargs: ...


async def handle_last_iteration(
    **kwargs: Unpack[_LoopIterationRunnerKwargs],
) -> LanguageModelStreamResponse:
    _LOGGER.info("Reached last iteration, removing tools and producing final response")

    return await stream_response(
        loop_runner_kwargs=kwargs,
        tools=None,
    )


async def handle_normal_iteration(
    **kwargs: Unpack[_LoopIterationRunnerKwargs],
) -> LanguageModelStreamResponse:
    _LOGGER.info("Running loop iteration %d", kwargs["iteration_index"])

    return await stream_response(loop_runner_kwargs=kwargs)


async def handle_forced_tools_iteration(
    **kwargs: Unpack[_LoopIterationRunnerKwargs],
) -> LanguageModelStreamResponse:
    return await run_forced_tools_iteration(loop_runner_kwargs=kwargs)


async def run_forced_tools_iteration(
    *,
    loop_runner_kwargs: _LoopIterationRunnerKwargs,
    prepare_loop_runner_kwargs: PrepareForcedToolIterationKwargs | None = None,
    tool_choice_override: str | None = None,
) -> LanguageModelStreamResponse:
    """
    Execute a "forced tools" iteration by running one stream_response per tool choice,
    then merging tool calls and references into a single response.

    Args:
        prepare_loop_runner_kwargs: Optional callback to transform kwargs per tool choice
            (e.g. Qwen rewrites messages with tool-specific instructions).
        tool_choice_override: If set, replaces the per-tool named dict with this value
            (e.g. Mistral needs "any" instead of the named format).
    """
    assert "tool_choices" in loop_runner_kwargs

    tool_choices = loop_runner_kwargs["tool_choices"]
    assert len(tool_choices) > 0, (
        "run_forced_tools_iteration requires at least one tool choice"
    )
    _LOGGER.info("Forcing tools calls: %s", tool_choices)

    responses: list[LanguageModelStreamResponse] = []

    available_tools = {t.name: t for t in loop_runner_kwargs.get("tools") or []}

    for opt in tool_choices:
        func_name = opt.get("function", {}).get("name")

        per_choice_kwargs = loop_runner_kwargs.copy()
        if prepare_loop_runner_kwargs:
            per_choice_kwargs = prepare_loop_runner_kwargs(func_name, per_choice_kwargs)

        effective_tool_choice = tool_choice_override or opt
        limited_tool = available_tools.get(func_name) if func_name else None
        if limited_tool:
            response = await stream_response(
                loop_runner_kwargs=per_choice_kwargs,
                tool_choice=effective_tool_choice,
                tools=[limited_tool],
            )
        else:
            response = await stream_response(
                loop_runner_kwargs=per_choice_kwargs,
                tool_choice=effective_tool_choice,
            )
        responses.append(response)

    tool_calls = []
    references = []
    for r in responses:
        if r.tool_calls:
            tool_calls.extend(r.tool_calls)
        references.extend(r.message.references or [])

    response = responses[0]
    response.tool_calls = tool_calls if len(tool_calls) > 0 else None
    response.message.references = references

    return response
