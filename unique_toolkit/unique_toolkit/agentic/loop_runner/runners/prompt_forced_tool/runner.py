"""Loop runner for models that reject forced tool_choice values."""

from typing import Unpack

from unique_toolkit.agentic.loop_runner._iteration_handler_utils import (
    run_forced_tools_iteration,
)
from unique_toolkit.agentic.loop_runner.base import _LoopIterationRunnerKwargs
from unique_toolkit.agentic.loop_runner.runners.basic import (
    BasicLoopIterationRunner,
)
from unique_toolkit.agentic.loop_runner.runners.prompt_forced_tool.helpers import (
    append_prompt_forced_tool_instruction,
)
from unique_toolkit.chat.functions import LanguageModelStreamResponse

PROMPT_FORCED_TOOL_CALL_INSTRUCTION = (
    "You must call the tool {TOOL_NAME}. Call it instead of replying with text."
)


class PromptForcedToolLoopIterationRunner(BasicLoopIterationRunner):
    """Runner for models that reject named and ``any`` tool choices.

    Claude Opus 5.5 and Fable 5.1 return HTTP 400 for those ``tool_choice``
    types. This runner keeps one request per forced tool, limits ``tools`` to
    that tool, sends ``tool_choice="auto"``, and asks for the call in the prompt.
    """

    async def _handle_forced_tools(
        self,
        **kwargs: Unpack[_LoopIterationRunnerKwargs],
    ) -> LanguageModelStreamResponse:
        original_messages = kwargs["messages"].model_copy(deep=True)

        def _prepare(
            func_name: str | None,
            per_choice_kwargs: _LoopIterationRunnerKwargs,
        ) -> _LoopIterationRunnerKwargs:
            instruction = PROMPT_FORCED_TOOL_CALL_INSTRUCTION.format(
                TOOL_NAME=func_name or ""
            )
            per_choice_kwargs["messages"] = append_prompt_forced_tool_instruction(
                messages=original_messages,
                instruction=instruction,
            )
            return per_choice_kwargs

        return await run_forced_tools_iteration(
            loop_runner_kwargs=kwargs,
            prepare_loop_runner_kwargs=_prepare,
            tool_choice_override="auto",
        )
