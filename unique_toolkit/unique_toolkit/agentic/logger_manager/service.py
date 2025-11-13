"""
Logger Service for Unique Agentic tools.

Target of the method is to extend the step tracking on all levels of the tool.
Therefore, the best way seems to expand the existing utils of deepsearch.
"""
from typing import Literal

from unique_toolkit.app.schemas import ChatEvent
from unique_toolkit.chat.schemas import (
    MessageLogDetails,
    MessageLogStatus,
    MessageLogUncitedReferences,
    MessageLogEvent,
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

    @staticmethod
    def create_message_log_entry(
        chat_service: ChatService,
        message_id: str,
        text: str | None = None,
        status: MessageLogStatus = MessageLogStatus.COMPLETED,
        details: MessageLogDetails | None = None,
        uncited_references: MessageLogUncitedReferences | None = None,
    ) -> None:
        """
        Create a message log entry with customizable details and references.

        Args:
            chat_service: ChatService instance for logging
            message_id: Message ID for the log entry
            text: Log message text (default: empty string)
            status: Log status (default: COMPLETED)
            details: Message details (default: empty)
            uncited_references: Uncited references (default: empty)
        """
        # Use per-request incrementing counter for clean, predictable ordering
        order = MessageStepLogger.get_next_message_order(message_id)

        _ = chat_service.create_message_log(
            message_id=message_id,
            text=text or "",
            status=status,
            order=order,
            details=details or MessageLogDetails(data=[]),
            uncited_references=uncited_references or MessageLogUncitedReferences(data=[]),
        )

    def write_message_log_text_message(self, text: str) -> None:
        """
        Write a simple text message for progress logging.

        Args:
            text: The text message to log
        """
        MessageStepLogger.create_message_log_entry(
            self._chat_service,
            self._event.payload.assistant_message.id,
            text,
            MessageLogStatus.COMPLETED,
            details=MessageLogDetails(data=[]),
            uncited_references=MessageLogUncitedReferences(data=[]),
        )

    @staticmethod
    def get_next_message_order(message_id: str) -> int:
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
    def define_reference_list(source : str,content_chunks : list[ContentChunk]):

        count = 0
        data: list[ContentReference] = []
        for content_chunk in content_chunks:
            count +=1
            data.append(              
                    ContentReference(
                            name=content_chunk.url or "",
                            sequence_number = count,
                            source=source,
                            url=content_chunk.url or "",
                            source_id=content_chunk.url or "")
                            )
            
        return data

    @staticmethod
    def define_reference_list_for_internal(
        source: str, content_chunks: list[ContentChunk]
    ) -> list[ContentReference]:
        """
        Create a reference list for internal search content chunks.

        Since content keys are different than in web search, this method
        handles the internal search format.

        Args:
            source: The source identifier for the references
            content_chunks: List of ContentChunk objects to convert

        Returns:
            List of ContentReference objects
        """
        count = 0
        data = []
        for content_chunk in content_chunks:
            count += 1

            reference_name: str
            if content_chunk.title is not None:
                reference_name = content_chunk.title
            else:
                reference_name = content_chunk.key or ""

            data.append(
                ContentReference(
                    name=reference_name,
                    sequence_number=count,
                    source=source,
                    url="",
                    source_id=content_chunk.id,
                )
            )

        return data

    def create_full_specific_message(
        self,
        message: str,
        source: str,
        search_type: Literal["WebSearch", "InternalSearch"],
        content_chunks: list[ContentChunk],
    ) -> None:
        """
        Create a full message log entry with question, hits, and references.

        Args:
            message: The question/message text
            source: The source identifier ('internal' or other)
            search_type: The type of search ("WebSearch" or "InternalSearch")
            content_chunks: List of content chunks to reference

        Note:
            This function is in test mode and not yet fully used in many DS projects.
        """
        if source == "internal":
            data = MessageStepLogger.define_reference_list_for_internal(
                source, content_chunks
            )
        else:
            data = MessageStepLogger.define_reference_list(source, content_chunks)

        _ = self._chat_service.create_message_log(
            message_id=self._event.payload.assistant_message.id,
            text=f"**Question asked**\n{message}\n**Found hits**",
            status=MessageLogStatus.COMPLETED,
            details=MessageLogDetails(data=[MessageLogEvent(type=search_type, text="")]),
            order=MessageStepLogger.get_next_message_order(
                self._event.payload.assistant_message.id
            ),
            uncited_references=MessageLogUncitedReferences(data=data),
        )
