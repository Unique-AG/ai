import logging
from typing import Unpack

from unique_toolkit.agentic.loop_runner._iteration_handler_utils import (
    handle_last_iteration,
    handle_normal_iteration,
    run_forced_tools_iteration,
)
from unique_toolkit.agentic.loop_runner.base import (
    LoopIterationRunner,
    _LoopIterationRunnerKwargs,
)
from unique_toolkit.agentic.loop_runner.runners.qwen.helpers import (
    append_qwen_forced_tool_call_instruction,
    append_qwen_last_iteration_assistant_message,
)
from unique_toolkit.chat.service import ChatService, LanguageModelStreamResponse

_LOGGER = logging.getLogger(__name__)

QWEN_FORCED_TOOL_CALL_INSTRUCTION = (
    "**Tool Call Instruction:** \nYou MUST call the tool {TOOL_NAME}. "
    "You must start the response with <tool_call>. "
    "Do NOT provide natural language explanations, summaries, or any text outside the <tool_call> block."
)

QWEN_LAST_ITERATION_INSTRUCTION = "The maximum number of loop iteration have been reached. Not further tool calls are allowed. Based on the found information, an answer should be generated"


class QwenLoopIterationRunner(LoopIterationRunner):
    def __init__(
        self,
        *,
        qwen_forced_tool_call_instruction: str,
        qwen_last_iteration_instruction: str,
        max_loop_iterations: int,
        chat_service: ChatService,
    ) -> None:
        self._qwen_forced_tool_call_instruction = qwen_forced_tool_call_instruction
        self._qwen_last_iteration_instruction = qwen_last_iteration_instruction
        self._max_loop_iterations = max_loop_iterations
        self._chat_service = chat_service

    async def __call__(
        self, **kwargs: Unpack[_LoopIterationRunnerKwargs]
    ) -> LanguageModelStreamResponse:
        tool_choices = kwargs.get("tool_choices") or []
        iteration_index = kwargs["iteration_index"]

        if len(tool_choices) > 0 and iteration_index == 0:
            return await self._qwen_handle_forced_tools_iteration(**kwargs)
        elif iteration_index == self._max_loop_iterations - 1:
            return await self._qwen_handle_last_iteration(**kwargs)
        else:
            return await self._qwen_handle_normal_iteration(**kwargs)

    async def _qwen_handle_forced_tools_iteration(
        self, **kwargs: Unpack[_LoopIterationRunnerKwargs]
    ) -> LanguageModelStreamResponse:
        # For Qwen models, append tool call instruction to the last user message. These models ignore the parameter tool_choice.
        # As the message has to be modified for each tool call instruction, the function from the basic runner cant be used.
        original_messages = kwargs["messages"].model_copy(deep=True)

        def _prepare(
            func_name: str | None,
            per_choice_kwargs: _LoopIterationRunnerKwargs,
        ) -> _LoopIterationRunnerKwargs:
            prompt_instruction = self._qwen_forced_tool_call_instruction.format(
                TOOL_NAME=func_name or ""
            )
            per_choice_kwargs["messages"] = append_qwen_forced_tool_call_instruction(
                messages=original_messages,
                forced_tool_call_instruction=prompt_instruction,
            )
            return per_choice_kwargs

        response = await run_forced_tools_iteration(
            loop_runner_kwargs=kwargs,
            prepare_loop_runner_kwargs=_prepare,
        )
        return self._process_response(response)

    async def _qwen_handle_last_iteration(
        self, **kwargs: Unpack[_LoopIterationRunnerKwargs]
    ) -> LanguageModelStreamResponse:
        # For Qwen models, append an assistant message with instructions to not call any tool in this iteration.
        _LOGGER.info(
            "Reached last iteration, removing tools. Appending assistant message with instructions to not call any tool in this iteration."
        )
        kwargs["messages"] = append_qwen_last_iteration_assistant_message(
            messages=kwargs["messages"],
            last_iteration_instruction=self._qwen_last_iteration_instruction,
        )

        response = await handle_last_iteration(
            **kwargs,
        )

        return self._process_response(response)

    async def _qwen_handle_normal_iteration(
        self, **kwargs: Unpack[_LoopIterationRunnerKwargs]
    ) -> LanguageModelStreamResponse:
        response = await handle_normal_iteration(**kwargs)
        return self._process_response(response)

    def _process_response(
        self, response: LanguageModelStreamResponse
    ) -> LanguageModelStreamResponse:
        # Check if content of response is </tool_call>
        if "</tool_call>" == response.message.text.strip():
            _LOGGER.warning(
                "Response contains only <tool_call>. This is not allowed. Returning empty response."
            )
            self._chat_service.modify_assistant_message(content="")
            response.message.text = ""

        return response
