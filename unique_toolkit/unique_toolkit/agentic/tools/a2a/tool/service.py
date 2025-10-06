import asyncio
import contextlib
import re
from typing import Protocol, override

import unique_sdk
from pydantic import Field, create_model
from unique_sdk.utils.chat_in_space import send_message_and_wait_for_completion

from unique_toolkit.agentic.evaluation.schemas import EvaluationMetricName
from unique_toolkit.agentic.tools.a2a.tool._memory import (
    get_sub_agent_short_term_memory_manager,
)
from unique_toolkit.agentic.tools.a2a.tool._schema import (
    SubAgentShortTermMemorySchema,
    SubAgentToolInput,
)
from unique_toolkit.agentic.tools.a2a.tool.config import (
    SubAgentToolConfig,
)
from unique_toolkit.agentic.tools.agent_chunks_hanlder import AgentChunksHandler
from unique_toolkit.agentic.tools.factory import ToolFactory
from unique_toolkit.agentic.tools.schemas import ToolCallResponse
from unique_toolkit.agentic.tools.tool import Tool
from unique_toolkit.agentic.tools.tool_progress_reporter import (
    ProgressState,
    ToolProgressReporter,
)
from unique_toolkit.app import ChatEvent
from unique_toolkit.language_model import (
    LanguageModelFunction,
    LanguageModelToolDescription,
)
from unique_toolkit.language_model.schemas import LanguageModelMessage


class SubAgentResponseSubscriber(Protocol):
    def notify_sub_agent_response(
        self,
        response: unique_sdk.Space.Message,
        sub_agent_assistant_id: str,
        sequence_number: int,
    ) -> None: ...

    """
    Notify the subscriber that a sub agent response has been received.
    Important: The subscriber should NOT modify the response in place.
    The sequence number is a 1-indexed counter that is incremented for each concurrent run of the same sub agent.
    """


class SubAgentTool(Tool[SubAgentToolConfig]):
    name: str = "SubAgentTool"

    def __init__(
        self,
        configuration: SubAgentToolConfig,
        event: ChatEvent,
        tool_progress_reporter: ToolProgressReporter | None = None,
        name: str = "SubAgentTool",
        display_name: str = "SubAgentTool",
    ):
        super().__init__(configuration, event, tool_progress_reporter)
        self._user_id = event.user_id
        self._company_id = event.company_id

        self.name = name
        self._display_name = display_name

        self._short_term_memory_manager = get_sub_agent_short_term_memory_manager(
            company_id=self._company_id,
            user_id=self._user_id,
            chat_id=event.payload.chat_id,
            assistant_id=self.config.assistant_id,
        )
        self._subscribers: list[SubAgentResponseSubscriber] = []
        self._should_run_evaluation = False

        # Synchronization state
        self._sequence_number = 1
        self._lock = asyncio.Lock()

    @staticmethod
    def get_sub_agent_reference_format(
        name: str, sequence_number: int, reference_number: int
    ) -> str:
        return f"<sup><name>{name} {sequence_number}</name>{reference_number}</sup>"

    def subscribe(self, subscriber: SubAgentResponseSubscriber) -> None:
        self._subscribers.append(subscriber)

    @override
    def display_name(self) -> str:
        return self._display_name

    @override
    def tool_description(self) -> LanguageModelToolDescription:
        tool_input_model_with_description = create_model(
            "SubAgentToolInput",
            user_message=(
                str,
                Field(description=self.config.param_description_sub_agent_user_message),
            ),
        )

        return LanguageModelToolDescription(
            name=self.name,
            description=self.config.tool_description,
            parameters=tool_input_model_with_description,
        )

    @override
    def tool_description_for_system_prompt(self) -> str:
        return self.config.tool_description_for_system_prompt

    @override
    def tool_format_information_for_system_prompt(self) -> str:
        return self.config.tool_format_information_for_system_prompt.format(
            name=self.name
        )

    @override
    def tool_description_for_user_prompt(self) -> str:
        return self.config.tool_description_for_user_prompt

    @override
    def tool_format_information_for_user_prompt(self) -> str:
        return self.config.tool_format_information_for_user_prompt.format(
            name=self.name
        )

    @override
    def evaluation_check_list(self) -> list[EvaluationMetricName]:
        return [EvaluationMetricName.SUB_AGENT] if self._should_run_evaluation else []

    @override
    def get_evaluation_checks_based_on_tool_response(
        self,
        tool_response: ToolCallResponse,
    ) -> list[EvaluationMetricName]:
        return []

    @override
    async def run(self, tool_call: LanguageModelFunction) -> ToolCallResponse:
        tool_input = SubAgentToolInput.model_validate(tool_call.arguments)

        if self._lock.locked():
            await self._notify_progress(
                tool_call=tool_call,
                message=f"Waiting for another run of `{self.display_name()}` to finish",
                state=ProgressState.STARTED,
            )

        # When reusing the chat id, executing the sub agent in parrallel leads to race conditions and undefined behavior.
        # To avoid this, we use a lock to serialize the execution of the same sub agent.
        context = self._lock if self.config.reuse_chat else contextlib.nullcontext()

        async with context:
            sequence_number = self._sequence_number
            self._sequence_number += 1

            await self._notify_progress(
                tool_call=tool_call,
                message=tool_input.user_message,
                state=ProgressState.RUNNING,
            )

            # Check if there is a saved chat id in short term memory
            chat_id = await self._get_chat_id()

            response = await self._execute_and_handle_timeout(
                tool_user_message=tool_input.user_message,
                chat_id=chat_id,
                tool_call=tool_call,
            )

            self._should_run_evaluation |= (
                response["assessment"] is not None and len(response["assessment"]) > 0
            )  # Run evaluation if any sub agent returned an assessment

            self._notify_subscribers(response, sequence_number)

            if chat_id is None:
                await self._save_chat_id(response["chatId"])

            if response["text"] is None:
                raise ValueError("No response returned from sub agent")

            response_text_with_references = self._prepare_response_references(
                response=response["text"],
                sequence_number=sequence_number,
            )

            await self._notify_progress(
                tool_call=tool_call,
                message=tool_input.user_message,
                state=ProgressState.FINISHED,
            )

            return ToolCallResponse(
                id=tool_call.id,  # type: ignore
                name=tool_call.name,
                content=response_text_with_references,
            )

    @override
    def get_tool_call_result_for_loop_history(
        self,
        tool_response: ToolCallResponse,
        agent_chunks_handler: AgentChunksHandler,
    ) -> LanguageModelMessage: ...  # Empty as method is deprecated

    async def _get_chat_id(self) -> str | None:
        if not self.config.reuse_chat:
            return None

        if self.config.chat_id is not None:
            return self.config.chat_id

        # Check if there is a saved chat id in short term memory
        short_term_memory = await self._short_term_memory_manager.load_async()

        if short_term_memory is not None:
            return short_term_memory.chat_id

        return None

    def _prepare_response_references(self, response: str, sequence_number: int) -> str:
        for ref_number in re.findall(r"<sup>(\d+)</sup>", response):
            reference = self.get_sub_agent_reference_format(
                name=self.name,
                sequence_number=sequence_number,
                reference_number=ref_number,
            )
            response = response.replace(f"<sup>{ref_number}</sup>", reference)
        return response

    async def _save_chat_id(self, chat_id: str) -> None:
        if not self.config.reuse_chat:
            return

        await self._short_term_memory_manager.save_async(
            SubAgentShortTermMemorySchema(chat_id=chat_id)
        )

    async def _notify_progress(
        self,
        tool_call: LanguageModelFunction,
        message: str,
        state: ProgressState,
    ) -> None:
        if self.tool_progress_reporter is not None:
            await self.tool_progress_reporter.notify_from_tool_call(
                tool_call=tool_call,
                name=self._display_name,
                message=message,
                state=state,
            )

    def _notify_subscribers(
        self, response: unique_sdk.Space.Message, sequence_number: int
    ) -> None:
        for subsciber in self._subscribers:
            subsciber.notify_sub_agent_response(
                sub_agent_assistant_id=self.config.assistant_id,
                response=response,
                sequence_number=sequence_number,
            )

    async def _execute_and_handle_timeout(
        self,
        tool_user_message: str,
        chat_id: str | None,
        tool_call: LanguageModelFunction,
    ) -> unique_sdk.Space.Message:
        try:
            return await send_message_and_wait_for_completion(
                user_id=self._user_id,
                assistant_id=self.config.assistant_id,
                company_id=self._company_id,
                text=tool_user_message,
                chat_id=chat_id,
                poll_interval=self.config.poll_interval,
                max_wait=self.config.max_wait,
                stop_condition="completedAt",
            )
        except TimeoutError as e:
            await self._notify_progress(
                tool_call=tool_call,
                message="Timeout while waiting for response from sub agent.",
                state=ProgressState.FAILED,
            )

            raise TimeoutError(
                "Timeout while waiting for response from sub agent. The user should consider increasing the max wait time.",
            ) from e


ToolFactory.register_tool(SubAgentTool, SubAgentToolConfig)
