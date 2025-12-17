import logging
from typing import Protocol, Unpack, cast

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
) -> LanguageModelStreamResponse:
    """
    Execute a "forced tools" iteration by running one stream_response per tool choice,
    then merging tool calls and references into a single response.

    Some models (e.g. Qwen) need per-tool-choice message rewriting; this can be done
    via prepare_loop_runner_kwargs (called once per tool choice, on a copy of kwargs).
    """
    assert "tool_choices" in loop_runner_kwargs

    tool_choices = loop_runner_kwargs["tool_choices"]
    assert len(tool_choices) > 0, "run_forced_tools_iteration requires at least one tool choice"
    _LOGGER.info("Forcing tools calls: %s", tool_choices)

    responses: list[LanguageModelStreamResponse] = []

    available_tools = {t.name: t for t in loop_runner_kwargs.get("tools") or []}

    for opt in tool_choices:
        func_name = opt.get("function", {}).get("name")

        per_choice_kwargs = cast(_LoopIterationRunnerKwargs, dict(loop_runner_kwargs))
        if prepare_loop_runner_kwargs:
            per_choice_kwargs = prepare_loop_runner_kwargs(func_name, per_choice_kwargs)

        limited_tool = available_tools.get(func_name) if func_name else None
        stream_kwargs = {"loop_runner_kwargs": per_choice_kwargs, "tool_choice": opt}
        if limited_tool:
            stream_kwargs["tools"] = [limited_tool]
        responses.append(await stream_response(**stream_kwargs))

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
