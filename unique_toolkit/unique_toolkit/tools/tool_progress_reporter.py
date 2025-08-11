import re
from datetime import datetime
from enum import Enum
from functools import wraps
from typing import Protocol

from pydantic import BaseModel
from unique_toolkit.chat.service import ChatService
from unique_toolkit.content.schemas import ContentReference
from unique_toolkit.language_model.schemas import (
    LanguageModelFunction,
    LanguageModelStreamResponse,
)

ARROW = "&#8594;&nbsp;"
DUMMY_REFERENCE_PLACEHOLDER = "<sup></sup>"


class ProgressState(Enum):
    STARTED = "⚪"
    RUNNING = "🟡"
    FAILED = "🔴"
    FINISHED = "🟢"


class ToolExecutionStatus(BaseModel):
    name: str
    message: str
    state: ProgressState
    references: list[ContentReference] = []
    timestamp: datetime = datetime.now()


class ToolProgressReporter:
    def __init__(self, chat_service: ChatService):
        self.chat_service = chat_service
        self.tool_statuses: dict[str, ToolExecutionStatus] = {}
        self._progress_start_text = ""
        self._requires_new_assistant_message = False

    @property
    def requires_new_assistant_message(self):
        return self._requires_new_assistant_message

    @requires_new_assistant_message.setter
    def requires_new_assistant_message(self, value: bool):
        self._requires_new_assistant_message = value

    @property
    def tool_statuses_is_empty(self):
        return len(self.tool_statuses) == 0

    def empty_tool_statuses_if_stream_has_text(
        self, stream_response: LanguageModelStreamResponse
    ):
        if stream_response.message.text:
            self.tool_statuses = {}

    async def notify_from_tool_call(
        self,
        tool_call: LanguageModelFunction,
        name: str,
        message: str,
        state: ProgressState,
        references: list[ContentReference] = [],
        requires_new_assistant_message: bool = False,
    ):
        """
        Notifies about a tool call execution status and updates the assistant message.

        Args:
            tool_call (LanguageModelFunction): The tool call being executed
            name (str): Name of the tool being executed
            message (str): Status message to display
            state (ProgressState): Current execution state of the tool
            references (list[ContentReference], optional): List of content references. Defaults to [].
            requires_new_assistant_message (bool, optional): Whether a new assistant message is needed when tool call is finished.
            Defaults to False. If yes, the agentic steps will remain in chat history and will be overwritten by the stream response.

        Raises:
            AssertionError: If tool_call.id is None
        """
        assert tool_call.id is not None
        self.tool_statuses[tool_call.id] = ToolExecutionStatus(
            name=name,
            message=message,
            state=state,
            references=references,
        )
        self.requires_new_assistant_message = (
            self.requires_new_assistant_message or requires_new_assistant_message
        )
        await self.publish()

    async def publish(self):
        messages = []
        all_references = []
        for item in sorted(self.tool_statuses.values(), key=lambda x: x.timestamp):
            references = item.references
            start_number = len(all_references) + 1
            message = self._replace_placeholders(item.message, start_number)
            references = self._correct_reference_sequence(references, start_number)
            all_references.extend(references)

            messages.append(f"{ARROW}**{item.name} {item.state.value}**: {message}")

        await self.chat_service.modify_assistant_message_async(
            content=self._progress_start_text + "\n\n" + "\n\n".join(messages),
            references=all_references,
        )

    @staticmethod
    def _replace_placeholders(message: str, start_number: int = 1) -> str:
        counter = start_number

        def replace_match(match):
            nonlocal counter
            result = f"<sup>{counter}</sup>"
            counter += 1
            return result

        return re.sub(r"<sup></sup>", replace_match, message)

    @staticmethod
    def _correct_reference_sequence(
        references: list[ContentReference], start_number: int = 1
    ) -> list[ContentReference]:
        for i, reference in enumerate(references, start_number):
            reference.sequence_number = i
        return references


class ToolWithToolProgressReporter(Protocol):
    tool_progress_reporter: ToolProgressReporter


def track_tool_progress(
    message: str,
    on_start_state: ProgressState = ProgressState.RUNNING,
    on_success_state: ProgressState = ProgressState.RUNNING,
    on_success_message: str | None = None,
    on_error_message: str = "Unexpected error occurred",
    requires_new_assistant_message: bool = False,
):
    """
    Decorator to add progress reporting and status tracking steps to tool functions. Can be used with async and sync functions.

    Args:
        name (str): Display name for the tool progress status
        message (str): Message to show during tool execution
        on_error_message (str, optional): Message to show if tool execution fails. Defaults to empty string.
        on_success_state (ProgressState, optional): State to set after successful execution. Defaults to RUNNING.
        requires_new_assistant_message (bool, optional): Whether to create a new assistant message. Defaults to False.

    The decorator will:
    1. Show a RUNNING status when the tool starts executing
    2. Update the status to on_success_state if execution succeeds
    3. Update the status to FAILED if execution fails
    4. Include any references from the tool result in the status update if the result has a 'references' attribute or item.
    5. Create a new assistant message if requires_new_assistant_message is True

    The decorated function must be a method of a class that implements ToolWithToolProgressReporter.
    """

    def decorator(func):
        @wraps(func)  # Preserve the original function's metadata
        async def async_wrapper(
            self: ToolWithToolProgressReporter,
            tool_call: LanguageModelFunction,
            notification_tool_name: str,
            *args,
            **kwargs,
        ):
            try:
                # Start status
                await self.tool_progress_reporter.notify_from_tool_call(
                    tool_call=tool_call,
                    name=notification_tool_name,
                    message=message,
                    state=on_start_state,
                )

                # Execute the tool function
                result = await func(
                    self, tool_call, notification_tool_name, *args, **kwargs
                )

                # Success status
                await self.tool_progress_reporter.notify_from_tool_call(
                    tool_call=tool_call,
                    name=notification_tool_name,
                    message=on_success_message or message,
                    state=on_success_state,
                    references=_get_references_from_results(result),
                    requires_new_assistant_message=requires_new_assistant_message,
                )
                return result

            except Exception as e:
                # Failure status
                await self.tool_progress_reporter.notify_from_tool_call(
                    tool_call=tool_call,
                    name=notification_tool_name,
                    message=on_error_message,
                    state=ProgressState.FAILED,
                    requires_new_assistant_message=requires_new_assistant_message,
                )
                raise e

        return async_wrapper

    return decorator


def _get_references_from_results(result):
    if isinstance(result, dict):
        return result.get("references", [])
    return getattr(result, "references", [])
