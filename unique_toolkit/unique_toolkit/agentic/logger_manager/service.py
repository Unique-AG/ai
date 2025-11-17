"""
Logger Service for Unique Agentic tools.

Target of the method is to extend the step tracking on all levels of the tool.
"""

from unique_toolkit.app.schemas import ChatEvent
from unique_toolkit.chat.schemas import (
    MessageLogDetails,
    MessageLogStatus,
    MessageLogUncitedReferences,
)
from unique_toolkit.chat.service import ChatService
from unique_toolkit.content.schemas import ContentReference

# Per-request counters for message log ordering - keyed by message_id
_request_counters: dict[str, int] = {}


class MessageStepLogger:
    """
    Logger class for tracking message steps in agentic tools.

    This class provides utilities for creating message log entries with proper
    ordering, references, and details.
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

    def create_message_log_entry(
        self,
        *,
        text: str,
        details: MessageLogDetails | None = None,
        data: list[ContentReference],
    ) -> None:
        """
        Create a full message log entry with question, hits, and references.

        Args:
            text: The prepared string for the message log entry
            details: Some formal details about the message log entry
            data: List of ContentReference objects to reference
        """

        # Creating a new message log entry with the found hits.
        _ = self._chat_service.create_message_log(
            message_id=self._event.payload.assistant_message.id,
            text=text,
            status=MessageLogStatus.COMPLETED,
            order=MessageStepLogger.get_next_message_order(
                message_id=self._event.payload.assistant_message.id
            ),
            details=details or MessageLogDetails(data=[]),
            uncited_references=MessageLogUncitedReferences(data=data),
            references=data,
        )
