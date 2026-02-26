import asyncio
import contextlib
import json
import logging
import re
from datetime import datetime
from typing import cast, override

import unique_sdk
from pydantic import Field, TypeAdapter, create_model
from unique_sdk.api_resources._space import Space
from unique_sdk.utils.chat_in_space import send_message_and_wait_for_completion

from unique_toolkit._common.referencing import (
    get_all_ref_numbers,
    get_detection_pattern_for_ref,
    replace_ref_number,
)
from unique_toolkit._common.utils.jinja.render import render_template
from unique_toolkit.agentic.evaluation.schemas import EvaluationMetricName
from unique_toolkit.agentic.feature_flags import feature_flags
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
    SystemReminderConfigType,
)
from unique_toolkit.agentic.tools.factory import ToolFactory
from unique_toolkit.agentic.tools.schemas import ToolCallResponse
from unique_toolkit.agentic.tools.tool import Tool
from unique_toolkit.agentic.tools.tool_progress_reporter import (
    ProgressState,
    ToolProgressReporter,
)
from unique_toolkit.app import ChatEvent
from unique_toolkit.chat.schemas import MessageLog, MessageLogStatus
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
        active_message_log: MessageLog | None = None

        try:
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

                active_message_log = self._create_or_update_message_log(
                    progress_message="_Waiting for another run of this sub agent to finish_",
                    active_message_log=active_message_log,
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

                active_message_log = self._create_or_update_message_log(
                    progress_message=f"_Executing sub agent with input: {tool_input}_",
                    active_message_log=active_message_log,
                )

                # Check if there is a saved chat id in short term memory
                chat_id = await self._get_chat_id()

                response = await self._execute_and_handle_timeout(
                    tool_user_message=tool_input,
                    chat_id=chat_id,
                    tool_call=tool_call,
                    active_message_log=active_message_log,
                )

                self._should_run_evaluation |= (
                    response["assessment"] is not None
                    and len(response["assessment"]) > 0
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
                    has_refs = (
                        self.config.use_sub_agent_references
                        and _response_has_refs(response)
                    )
                    content = response["text"]
                    if has_refs:
                        refs = response["references"]
                        assert refs is not None  # Checked in _response_has_refs
                        content = _prepare_sub_agent_response_refs(
                            response=content,
                            name=self.name,
                            sequence_number=sequence_number,
                            refs=refs,
                        )
                        content = _remove_extra_refs(content, refs=refs)
                    else:
                        content = _remove_extra_refs(content, refs=[])

                system_reminders = []
                if not self.config.returns_content_chunks:
                    system_reminders = _get_sub_agent_system_reminders(
                        response=response["text"],
                        configs=self.config.system_reminders_config,
                        name=self.name,
                        display_name=self.display_name(),
                        sequence_number=sequence_number,
                        has_refs=has_refs,
                    )

                await self._notify_progress(
                    tool_call=tool_call,
                    message=tool_input,
                    state=ProgressState.FINISHED,
                )

                # Update message log entry to completed
                active_message_log = self._create_or_update_message_log(
                    progress_message=f"_Completed sub agent with input: {tool_input}_",
                    status=MessageLogStatus.COMPLETED,
                    active_message_log=active_message_log,
                )

                return ToolCallResponse(
                    id=tool_call.id,
                    name=tool_call.name,
                    content=_format_response(
                        tool_name=self.name,
                        text=content,
                        system_reminders=system_reminders,
                    ),
                    content_chunks=content_chunks,
                )
        except TimeoutError as e:
            raise e
        except Exception as e:
            await self._notify_progress(
                tool_call=tool_call,
                message="Error while running sub agent",
                state=ProgressState.FAILED,
            )
            active_message_log = self._create_or_update_message_log(
                progress_message="_Error while running sub agent_",
                status=MessageLogStatus.FAILED,
                active_message_log=active_message_log,
            )
            raise e

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
        if (
            self.tool_progress_reporter is not None
            and not feature_flags.enable_new_answers_ui_un_14411.is_enabled(
                self._company_id
            )
        ):
            await self.tool_progress_reporter.notify_from_tool_call(
                tool_call=tool_call,
                name=self._display_name,
                message=message,
                state=state,
            )

    def _create_or_update_message_log(
        self,
        *,
        progress_message: str | None = None,
        status: MessageLogStatus = MessageLogStatus.RUNNING,
        active_message_log: MessageLog | None = None,
    ) -> MessageLog | None:
        return self._message_step_logger.create_or_update_message_log(
            active_message_log=active_message_log,
            header=self._display_name,
            progress_message=progress_message,
            status=status,
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
        active_message_log: MessageLog | None = None,
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
                correlation=Space.Correlation(
                    parentMessageId=self._chat_service._assistant_message_id,
                    parentChatId=self._event.payload.chat_id,
                    parentAssistantId=self.config.assistant_id,
                ),
            )
        except TimeoutError as e:
            await self._notify_progress(
                tool_call=tool_call,
                message="Timeout while waiting for response from sub agent.",
                state=ProgressState.FAILED,
            )
            active_message_log = self._create_or_update_message_log(
                progress_message="_Timeout while waiting for response from sub agent_",
                status=MessageLogStatus.FAILED,
                active_message_log=active_message_log,
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


def _response_has_refs(response: unique_sdk.Space.Message) -> bool:
    if (
        response["text"] is None
        or response["references"] is None
        or len(response["references"]) == 0
    ):
        return False

    for ref in response["references"]:
        if (
            re.search(
                get_detection_pattern_for_ref(ref["sequenceNumber"]), response["text"]
            )
            is not None
        ):
            return True

    return False


def _remove_extra_refs(response: str, refs: list[unique_sdk.Space.Reference]) -> str:
    text_ref_numbers = set(get_all_ref_numbers(response))
    extra_ref_numbers = text_ref_numbers - set(ref["sequenceNumber"] for ref in refs)

    for ref_num in extra_ref_numbers:
        response = get_detection_pattern_for_ref(ref_num).sub("", response)

    return response


def _prepare_sub_agent_response_refs(
    response: str,
    name: str,
    sequence_number: int,
    refs: list[unique_sdk.Space.Reference],
) -> str:
    for ref in refs:
        ref_number = ref["sequenceNumber"]
        reference = SubAgentTool.get_sub_agent_reference_format(
            name=name, sequence_number=sequence_number, reference_number=ref_number
        )
        response = replace_ref_number(
            text=response, ref_number=ref_number, replacement=reference
        )

    return response


def _get_sub_agent_system_reminders(
    response: str,
    configs: list[SystemReminderConfigType],
    name: str,
    display_name: str,
    sequence_number: int,
    has_refs: bool,
) -> list[str]:
    reminders = []

    for reminder_config in configs:
        render_kwargs = {}
        render_kwargs["display_name"] = display_name
        render_kwargs["tool_name"] = name
        template = None

        if reminder_config.type == SubAgentSystemReminderType.FIXED:
            template = reminder_config.reminder
        elif (
            reminder_config.type == SubAgentSystemReminderType.REFERENCE and has_refs
        ) or (
            reminder_config.type == SubAgentSystemReminderType.NO_REFERENCE
            and not has_refs
        ):
            render_kwargs["tool_name"] = f"{name} {sequence_number}"
            template = reminder_config.reminder
        elif reminder_config.type == SubAgentSystemReminderType.REGEXP:
            reminder_config = cast(RegExpDetectedSystemReminderConfig, reminder_config)
            text_matches = [
                match.group(0) for match in reminder_config.regexp.finditer(response)
            ]
            if len(text_matches) > 0:
                template = reminder_config.reminder
                render_kwargs["text_matches"] = text_matches

        if template is not None:
            reminders.append(render_template(template, **render_kwargs))

    return reminders


ToolFactory.register_tool(SubAgentTool, SubAgentToolConfig)
