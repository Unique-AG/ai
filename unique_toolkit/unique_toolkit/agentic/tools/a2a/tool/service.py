import asyncio
import contextlib
import json
import logging
import re
from datetime import datetime
from typing import cast, override

import unique_sdk
from pydantic import Field, TypeAdapter, create_model
from unique_sdk.utils.chat_in_space import send_message_and_wait_for_completion

from unique_toolkit._common.referencing import (
    get_all_ref_numbers,
    get_detection_pattern_for_ref,
    remove_all_refs,
    replace_ref_number,
)
from unique_toolkit._common.utils.jinja.render import render_template
from unique_toolkit.agentic.evaluation.schemas import EvaluationMetricName
from unique_toolkit.agentic.tools.a2a.response_watcher import SubAgentResponseWatcher
from unique_toolkit.agentic.tools.a2a.tool._memory import (
    get_sub_agent_short_term_memory_manager,
)
from unique_toolkit.agentic.tools.a2a.tool._schema import (
    SubAgentShortTermMemorySchema,
    SubAgentToolInput,
)
from unique_toolkit.agentic.tools.a2a.tool.config import (
    RegExpDetectedSystemReminderConfig,
    SubAgentSystemReminderType,
    SubAgentToolConfig,
)
from unique_toolkit.agentic.tools.factory import ToolFactory
from unique_toolkit.agentic.tools.schemas import ToolCallResponse
from unique_toolkit.agentic.tools.tool import Tool
from unique_toolkit.agentic.tools.tool_progress_reporter import (
    ProgressState,
    ToolProgressReporter,
)
from unique_toolkit.app import ChatEvent
from unique_toolkit.content import ContentChunk
from unique_toolkit.language_model import (
    LanguageModelFunction,
    LanguageModelToolDescription,
)

logger = logging.getLogger(__name__)

_ContentChunkList = TypeAdapter(list[ContentChunk])


class SubAgentTool(Tool[SubAgentToolConfig]):
    name: str = "SubAgentTool"

    def __init__(
        self,
        configuration: SubAgentToolConfig,
        event: ChatEvent,
        tool_progress_reporter: ToolProgressReporter | None = None,
        name: str = "SubAgentTool",
        display_name: str = "SubAgentTool",
        response_watcher: SubAgentResponseWatcher | None = None,
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
        self._should_run_evaluation = False

        self._response_watcher = response_watcher

        # Synchronization state
        self._sequence_number = 1
        self._lock = asyncio.Lock()

    @staticmethod
    def get_sub_agent_reference_format(
        name: str, sequence_number: int, reference_number: int
    ) -> str:
        return f"<sup><name>{name} {sequence_number}</name>{reference_number}</sup>"

    @staticmethod
    def get_sub_agent_reference_re(
        name: str, sequence_number: int, reference_number: int
    ) -> str:
        return rf"<sup>\s*<name>\s*{re.escape(name)}\s*{sequence_number}\s*</name>\s*{reference_number}\s*</sup>"

    @override
    def display_name(self) -> str:
        return self._display_name

    @override
    def tool_description(self) -> LanguageModelToolDescription:
        if self.config.tool_input_json_schema is not None:
            return LanguageModelToolDescription(
                name=self.name,
                description=self.config.tool_description,
                parameters=json.loads(self.config.tool_input_json_schema),
            )

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
        return self.config.tool_format_information_for_system_prompt

    @override
    def tool_description_for_user_prompt(self) -> str:
        return self.config.tool_description_for_user_prompt

    @override
    def tool_format_information_for_user_prompt(self) -> str:
        return self.config.tool_format_information_for_user_prompt

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
        if self.config.tool_input_json_schema is not None:
            tool_input = json.dumps(tool_call.arguments)
        else:
            tool_input = SubAgentToolInput.model_validate(
                tool_call.arguments
            ).user_message

        timestamp = datetime.now()

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
                message=tool_input,
                state=ProgressState.RUNNING,
            )

            # Check if there is a saved chat id in short term memory
            chat_id = await self._get_chat_id()

            response = await self._execute_and_handle_timeout(
                tool_user_message=tool_input,
                chat_id=chat_id,
                tool_call=tool_call,
            )

            self._should_run_evaluation |= (
                response["assessment"] is not None and len(response["assessment"]) > 0
            )  # Run evaluation if any sub agent returned an assessment

            self._notify_watcher(response, sequence_number, timestamp)

            if chat_id is None:
                await self._save_chat_id(response["chatId"])

            if response["text"] is None:
                raise ValueError("No response returned from sub agent")

            has_refs = False
            content = ""
            content_chunks = None
            if self.config.returns_content_chunks:
                content_chunks = _ContentChunkList.validate_json(response["text"])
            else:
                content, has_refs = self._prepare_response_references(
                    response=response["text"],
                    sequence_number=sequence_number,
                )

            await self._notify_progress(
                tool_call=tool_call,
                message=tool_input,
                state=ProgressState.FINISHED,
            )

            return ToolCallResponse(
                id=tool_call.id,
                name=tool_call.name,
                content=_format_response(
                    tool_name=self.name,
                    text=content,
                    system_reminders=self._get_system_reminders(
                        response, sequence_number, has_refs
                    ),
                ),
                content_chunks=content_chunks,
            )

    def _get_system_reminders(
        self, message: unique_sdk.Space.Message, sequence_number: int, has_refs: bool
    ) -> list[str]:
        has_refs = (
            self.config.use_sub_agent_references
            and message["references"] is not None
            and len(message["references"]) > 0
            and has_refs
            and not self.config.returns_content_chunks
        )
        reminders = []

        for reminder_config in self.config.system_reminders_config:
            render_kwargs = {}
            render_kwargs["display_name"] = self.display_name()
            render_kwargs["tool_name"] = self.name
            template = None

            if reminder_config.type == SubAgentSystemReminderType.FIXED:
                template = reminder_config.reminder
            elif (
                reminder_config.type == SubAgentSystemReminderType.REFERENCE
                and has_refs
            ):
                render_kwargs["tool_name"] = f"{self.name} {sequence_number}"
                template = reminder_config.reminder
            elif (
                reminder_config.type == SubAgentSystemReminderType.NO_REFERENCE
                and not has_refs
            ):
                render_kwargs["tool_name"] = f"{self.name} {sequence_number}"
                template = reminder_config.reminder
            elif (
                reminder_config.type == SubAgentSystemReminderType.REGEXP
                and message["text"] is not None
                and not self.config.returns_content_chunks
            ):
                reminder_config = cast(
                    RegExpDetectedSystemReminderConfig, reminder_config
                )
                if message["text"] is not None:
                    text_matches = [
                        match.group(0)
                        for match in reminder_config.regexp.finditer(message["text"])
                    ]
                    if len(text_matches) > 0:
                        template = reminder_config.reminder
                        render_kwargs["text_matches"] = text_matches

            if template is not None:
                reminders.append(render_template(template, **render_kwargs))

        return reminders

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

    def _prepare_response_references(
        self, response: str, sequence_number: int
    ) -> tuple[str, bool]:
        if not self.config.use_sub_agent_references:
            # Remove all references from the response
            response = remove_all_refs(response)
            return response, False

        replaced = False
        for ref_number in get_all_ref_numbers(response):
            reference = self.get_sub_agent_reference_format(
                name=self.name,
                sequence_number=sequence_number,
                reference_number=ref_number,
            )
            ref_pattern = get_detection_pattern_for_ref(ref_number)
            if re.search(ref_pattern, response) is not None:
                replaced = True
                response = replace_ref_number(
                    text=response, ref_number=ref_number, replacement=reference
                )

        return response, replaced

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

    def _notify_watcher(
        self,
        response: unique_sdk.Space.Message,
        sequence_number: int,
        timestamp: datetime,
    ) -> None:
        if self._response_watcher is not None:
            self._response_watcher.notify_response(
                assistant_id=self.config.assistant_id,
                name=self.name,
                sequence_number=sequence_number,
                response=response,
                timestamp=timestamp,
            )
        else:
            logger.warning(
                "No response watcher found for sub agent %s (assistant_id: %s)",
                self.name,
                self.config.assistant_id,
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
                tool_choices=self.config.forced_tools,
                max_wait=self.config.max_wait,
                stop_condition=self.config.stop_condition,
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


def _format_response(tool_name: str, text: str, system_reminders: list[str]) -> str:
    if len(system_reminders) == 0:
        return text

    reponse_key = f"{tool_name} response"
    response = {reponse_key: text, "SYSTEM_REMINDERS": system_reminders}

    return json.dumps(response, indent=2)


ToolFactory.register_tool(SubAgentTool, SubAgentToolConfig)
