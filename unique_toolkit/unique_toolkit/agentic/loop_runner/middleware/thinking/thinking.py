import logging
from typing import Unpack

from pydantic import BaseModel

from unique_toolkit import ChatService, LanguageModelMessages
from unique_toolkit._common.pydantic_helpers import get_configuration_dict
from unique_toolkit.agentic.history_manager.history_manager import HistoryManager
from unique_toolkit.agentic.loop_runner._stream_handler_utils import stream_response
from unique_toolkit.agentic.loop_runner.base import LoopRunner, _LoopRunnerKwargs
from unique_toolkit.agentic.loop_runner.middleware.thinking.think_tool import (
    ThinkToolConfig,
    get_think_tool,
)
from unique_toolkit.agentic.tools.schemas import ToolCallResponse
from unique_toolkit.agentic.tools.tool_manager import ToolManager
from unique_toolkit.agentic.tools.utils import failsafe_async
from unique_toolkit.chat.service import LanguageModelStreamResponse
from unique_toolkit.language_model import (
    LanguageModelAssistantMessage,
    LanguageModelFunction,
    LanguageModelMessage,
    LanguageModelToolMessage,
)

logger = logging.getLogger(__name__)


class ThinkingConfig(BaseModel):
    model_config = get_configuration_dict()

    think_tool_config: ThinkToolConfig = ThinkToolConfig()


class ThinkingMiddleware(LoopRunner):
    def __init__(
        self,
        *,
        loop_runner: LoopRunner,
        config: ThinkingConfig,
        tool_manager: ToolManager,
        chat_service: ChatService,
        history_manager: HistoryManager | None = None,
    ) -> None:
        self._config = config
        self._loop_runner = loop_runner
        self._history_manager = history_manager
        self._tool_manager = tool_manager
        self._chat_service = chat_service

    def _create_tool_call_response(
        self, tool_call: LanguageModelFunction
    ) -> tuple[ToolCallResponse, LanguageModelToolMessage]:
        return ToolCallResponse(
            content="No tool call response (this is normal).",
            id=tool_call.id,
            name=tool_call.name,
        ), LanguageModelToolMessage(
            content="No tool call response (this is normal).",
            tool_call_id=tool_call.id,
            name=tool_call.name,
        )

    def _get_think_step_messages(
        self, response: LanguageModelStreamResponse
    ) -> list[LanguageModelMessage] | None:
        if not response.tool_calls:
            logger.error("Model did not output any tool calls.")
            return None

        tool_call_names = set(tool_call.name for tool_call in response.tool_calls)
        expected_tool_call_names = {self._config.think_tool_config.tool_name}
        if tool_call_names != expected_tool_call_names:
            logger.error(
                "Incorrect thinking tool calls found %s",
                tool_call_names - expected_tool_call_names,
            )
            return None

        if self._history_manager is not None:
            self._history_manager._append_tool_calls_to_history(
                tool_calls=response.tool_calls
            )

        messages = []
        messages.append(LanguageModelAssistantMessage.from_stream_response(response))

        for tool_call in response.tool_calls:
            tool_call_response, tool_call_message = self._create_tool_call_response(
                tool_call
            )
            messages.append(tool_call_message)
            if self._history_manager is not None:
                self._history_manager._append_tool_call_result_to_history(
                    tool_call_response
                )

        return messages

    @failsafe_async(failure_return_value=None, logger=logger)
    async def _run_think_step(
        self, **kwargs: Unpack[_LoopRunnerKwargs]
    ) -> list[LanguageModelMessage] | None:
        think_tool = get_think_tool(self._config.think_tool_config)
        forced_tool = self._tool_manager.get_forced_tool_call(think_tool.name)
        tools = kwargs.get("tools", [])
        response = await stream_response(
            loop_runner_kwargs=kwargs,
            tools=tools + [think_tool],
            tool_choice=forced_tool,
        )

        messages = self._get_think_step_messages(response)

        return messages

    async def __call__(
        self, **kwargs: Unpack[_LoopRunnerKwargs]
    ) -> LanguageModelStreamResponse:
        messages = await self._run_think_step(**kwargs)

        if messages is None:
            logger.info("Error executing think step, proceeding without thinking step")
            return await self._loop_runner(**kwargs)

        kwargs["messages"] = LanguageModelMessages(kwargs["messages"].root + messages)
        return await self._loop_runner(**kwargs)
