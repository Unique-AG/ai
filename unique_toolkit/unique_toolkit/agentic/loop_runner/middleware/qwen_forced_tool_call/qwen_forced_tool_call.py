import logging
from typing import Unpack

from unique_toolkit.agentic.loop_runner.base import (
    LoopIterationRunner,
    _LoopIterationRunnerKwargs,
)
from unique_toolkit.agentic.loop_runner.middleware.qwen_forced_tool_call.helpers import (
    append_qwen_forced_tool_call_instruction,
)
from unique_toolkit.chat.service import LanguageModelStreamResponse

_LOGGER = logging.getLogger(__name__)

QWEN_FORCED_TOOL_CALL_PROMPT_INSTRUCTION = (
    "Tool Call Instruction: \nYou always have to return a tool call. "
    "You must start the response with <tool_call> and end with </tool_call>. "
    "Do NOT provide natural language explanations, summaries, or any text outside the <tool_call> block."
)


class QwenForcedToolCallMiddleware(LoopIterationRunner):
    def __init__(
        self,
        *,
        loop_runner: LoopIterationRunner,
        qwen_forced_tool_call_prompt_instruction: str,
    ) -> None:
        self._qwen_forced_tool_call_prompt_instruction = (
            qwen_forced_tool_call_prompt_instruction
        )
        self._loop_runner = loop_runner

    async def __call__(
        self, **kwargs: Unpack[_LoopIterationRunnerKwargs]
    ) -> LanguageModelStreamResponse:
        tool_choices = kwargs.get("tool_choices", [])
        iteration_index = kwargs["iteration_index"]

        # For Qwen models, append tool call instruction to the last user message. These models ignore the parameter tool_choice.
        if len(tool_choices) > 0 and iteration_index == 0 and kwargs.get("messages"):
            _LOGGER.info(
                "Appending tool call instruction to the last user message for Qwen models to force tool calls."
            )
            kwargs["messages"] = append_qwen_forced_tool_call_instruction(
                messages=kwargs["messages"],
                forced_tool_call_instruction=self._qwen_forced_tool_call_prompt_instruction,
            )

        return await self._loop_runner(**kwargs)
