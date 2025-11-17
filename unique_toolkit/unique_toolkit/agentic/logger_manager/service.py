"""
Logger Service for Unique Agentic tools.

Target of the method is to extend the step tracking on all levels of the tool.
Therefore, the best way seems to expand the existing utils of deepsearch.
"""

from typing import Literal

from unique_toolkit.app.schemas import ChatEvent
from unique_toolkit.chat.schemas import (
    MessageLog,
    MessageLogDetails,
    MessageLogEvent,
    MessageLogStatus,
    MessageLogUncitedReferences,
)
from unique_toolkit.chat.service import ChatService
from unique_toolkit.content.schemas import ContentChunk, ContentReference

# Per-request counters for message log ordering - keyed by message_id
_request_counters: dict[str, int] = {}


class MessageStepLogger:
    """
    Logger class for tracking message steps in agentic tools.

    This class provides utilities for creating message log entries with proper
    ordering, references, and details. It extends the functionality from
    deepsearch utils to be usable across all agentic tools.
    """

    def __init__(self, chat_service: ChatService, event: ChatEvent) -> None:
        """
        Initialize the MessageStepLogger.

        Args:
            chat_service: ChatService instance for logging
            event: ChatEvent containing message and payload information
        """
        self._chat_service: ChatService = chat_service
        self._event: ChatEvent = event

    @classmethod
    def create_message_log_entry(
        cls,
        *,
        chat_service: ChatService,
        message_id: str,
        text: str | None = None,
        status: MessageLogStatus = MessageLogStatus.COMPLETED,
        details: MessageLogDetails | None = None,
        uncited_references: MessageLogUncitedReferences | None = None,
    ) -> MessageLog:
        """
        Create a message log entry with customizable details and references.

        Args:
            chat_service: ChatService instance for logging
            message_id: Message ID for the log entry
            text: Log message text (default: empty string)
            status: Log status (default: COMPLETED)
            details: Message details (default: empty)
            uncited_references: Uncited references (default: empty)

        The returns are for futre potential use cases using update.
        """
        # Use per-request incrementing counter for clean, predictable ordering
        order = MessageStepLogger.get_next_message_order(message_id=message_id)

        message_log: MessageLog = chat_service.create_message_log(
            message_id=message_id,
            text=text or "",
            status=status,
            order=order,
            details=details or MessageLogDetails(data=[]),
            uncited_references=uncited_references
            or MessageLogUncitedReferences(data=[]),
        )

        return message_log

    def write_message_log_text_message(self, *, text: str) -> MessageLog:
        """
        Write a simple text message for progress logging.

        Args:
            text: The text message to log
        """

        message_log = MessageStepLogger.create_message_log_entry(
            chat_service=self._chat_service,
            message_id=self._event.payload.assistant_message.id,
            text=text,
            status=MessageLogStatus.COMPLETED,
            details=MessageLogDetails(data=[]),
            uncited_references=MessageLogUncitedReferences(data=[]),
        )

        return message_log

    @staticmethod
    def get_next_message_order(*, message_id: str) -> int:
        """
        Get the next message log order number for a specific request.

        Each message_id (request) gets its own counter: 1, 2, 3, 4, ...
        This ensures proper ordering within each request while avoiding
        race conditions between concurrent requests.

        Args:
            message_id: The message ID to get the next order for

        Returns:
            Next order number for this specific request
        """
        if message_id not in _request_counters:
            _request_counters[message_id] = 0

        _request_counters[message_id] += 1
        return _request_counters[message_id]

    @staticmethod
    def define_reference_list(
        *,
        source: str,
        content_chunks: list[ContentChunk],
        data: list[ContentReference],
    ):
        """
        Create a reference list for web search content chunks.

        Since content keys are different than in web search, this method
        handles the internal search format.

        Args:
            source: The source identifier for the references
            content_chunks: List of ContentChunk objects to convert
            data: List of ContentReference objects to reference
        Returns:
            List of ContentReference objects
        """

        count = 0
        data: list[ContentReference] = []
        for content_chunk in content_chunks:
            content_url = content_chunk.url or ""

            if content_url != "":
                data.append(
                    ContentReference(
                        name=content_url or "",
                        sequence_number=count,
                        source=source,
                        url=content_url or "",
                        source_id=content_url or "",
                    )
                )

            count += 1

        return data

    @staticmethod
    def define_reference_list_for_internal(
        *,
        source: str,
        content_chunks: list[ContentChunk],
        data: list[ContentReference],
    ) -> list[ContentReference]:
        """
        Create a reference list for internal search content chunks.

        Since content keys are different than in web search, this method
        handles the internal search format.

        Args:
            source: The source identifier for the references
            content_chunks: List of ContentChunk objects to convert
            data: List of ContentReference objects to reference
        Returns:
            List of ContentReference objects
        """
        count = 0
        for content_chunk in content_chunks:
            reference_name: str
            if content_chunk.title is not None:
                reference_name = content_chunk.title
            else:
                reference_name = content_chunk.key or ""

            if reference_name != "":
                data.append(
                    ContentReference(
                        name=reference_name,
                        sequence_number=count,
                        source=source,
                        url="",
                        source_id=content_chunk.id,
                    )
                )

            count += 1

        return data

    def create_full_specific_message(
        self,
        *,
        query_list: list[str],
        search_type: Literal["WebSearch", "InternalSearch"],
        data: list[ContentReference],
    ) -> None:
        """
        Create a full message log entry with question, hits, and references.

        Args:
            message: The question/message text
            search_type: The type of search ("WebSearch" or "InternalSearch")
            data: List of ContentReference objects to reference
        """

        message = ""
        for entry in query_list:
            message += f"• {entry}\n"
        message = message.strip("\n")

        input_string = "**Web Search**"
        if search_type == "InternalSearch":
            input_string = "**Internal Search**"

        # Creating a new message log entry with the found hits.
        _ = self._chat_service.create_message_log(
            message_id=self._event.payload.assistant_message.id,
            text=f"{input_string}\n{message}\n",
            status=MessageLogStatus.COMPLETED,
            order=MessageStepLogger.get_next_message_order(
                message_id=self._event.payload.assistant_message.id
            ),
            details=MessageLogDetails(
                data=[MessageLogEvent(type=search_type, text="")]
            ),
            uncited_references=MessageLogUncitedReferences(data=data),
            references=data,
        )
