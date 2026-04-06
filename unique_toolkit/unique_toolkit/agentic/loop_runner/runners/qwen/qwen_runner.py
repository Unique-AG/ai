import logging
from typing import Unpack

from unique_toolkit.agentic.loop_runner._iteration_handler_utils import (
    run_forced_tools_iteration,
)
from unique_toolkit.agentic.loop_runner.base import _LoopIterationRunnerKwargs
from unique_toolkit.agentic.loop_runner.runners.basic import (
    BasicLoopIterationRunner,
    BasicLoopIterationRunnerConfig,
)
from unique_toolkit.agentic.loop_runner.runners.qwen.helpers import (
    append_qwen_forced_tool_call_instruction,
    append_qwen_last_iteration_assistant_message,
)
from unique_toolkit.chat.service import ChatService, LanguageModelStreamResponse

_LOGGER = logging.getLogger(__name__)

QWEN_MAX_LOOP_ITERATIONS = 3

QWEN_FORCED_TOOL_CALL_INSTRUCTION = (
    "**Tool Call Instruction:** \nYou MUST call the tool {TOOL_NAME}. "
    "You must start the response with <tool_call>. "
    "Do NOT provide natural language explanations, summaries, or any text outside the <tool_call> block."
)

QWEN_LAST_ITERATION_INSTRUCTION = """The maximum number of loop iteration have been reached. Not further tool calls are allowed.
Based on the found information, an answer should be generated"""


class QwenLoopIterationRunner(BasicLoopIterationRunner):
    def __init__(
        self,
        *,
        config: BasicLoopIterationRunnerConfig,
        forced_tool_call_instruction: str,
        last_iteration_instruction: str,
        chat_service: ChatService,
    ) -> None:
        super().__init__(config)
        self._forced_tool_call_instruction = forced_tool_call_instruction
        self._last_iteration_instruction = last_iteration_instruction
        self._chat_service = chat_service

    async def _handle_forced_tools(
        self, **kwargs: Unpack[_LoopIterationRunnerKwargs]
    ) -> LanguageModelStreamResponse:
        original_messages = kwargs["messages"].model_copy(deep=True)

        def _prepare(
            func_name: str | None,
            per_choice_kwargs: _LoopIterationRunnerKwargs,
        ) -> _LoopIterationRunnerKwargs:
            prompt_instruction = self._forced_tool_call_instruction.format(
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
        return await self._process_response(response)

    async def _handle_last_iteration(
        self, **kwargs: Unpack[_LoopIterationRunnerKwargs]
    ) -> LanguageModelStreamResponse:
        _LOGGER.info(
            "Reached last iteration, removing tools. Appending assistant message with instructions to not call any tool in this iteration."
        )
        kwargs["messages"] = append_qwen_last_iteration_assistant_message(
            messages=kwargs["messages"],
            last_iteration_instruction=self._last_iteration_instruction,
        )
        response = await super()._handle_last_iteration(**kwargs)
        return await self._process_response(response)

    async def _handle_normal_iteration(
        self, **kwargs: Unpack[_LoopIterationRunnerKwargs]
    ) -> LanguageModelStreamResponse:
        response = await super()._handle_normal_iteration(**kwargs)
        return await self._process_response(response)

    async def _process_response(
        self, response: LanguageModelStreamResponse
    ) -> LanguageModelStreamResponse:
        if "</tool_call>" == response.message.text.strip():
            _LOGGER.warning(
                "Response contains only <tool_call>. This is not allowed. Returning empty response."
            )
            await self._chat_service.modify_assistant_message_async(content="")
            response.message.text = ""

        return response
