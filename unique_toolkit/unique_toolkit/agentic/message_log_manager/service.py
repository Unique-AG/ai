"""
Logger Service for Unique Agentic tools.

Target of the method is to extend the step tracking on all levels of the tool.
"""

from collections import defaultdict
from logging import getLogger

from unique_toolkit.chat.schemas import (
    MessageLogDetails,
    MessageLogStatus,
    MessageLogUncitedReferences,
)
from unique_toolkit.chat.service import ChatService
from unique_toolkit.content.schemas import ContentReference

_LOGGER = getLogger(__name__)

# Per-request counters for message log ordering - keyed by message_id
# This is a mandatory global variable since we have in the system a bug which makes it impossible to use it as a proper class variable.
_request_counters = defaultdict(int)


class MessageStepLogger:
    """
    Logger class for tracking message steps in agentic tools.

    This class provides utilities for creating message log entries with proper
    ordering, references, and details.
    """

    def __init__(self, chat_service: ChatService) -> None:
        """
        Initialize the MessageStepLogger.

        Args:
            chat_service: ChatService instance for logging
        """
        self._chat_service: ChatService = chat_service

    def _get_next_message_order(self, *, message_id: str) -> int:
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

        _request_counters[message_id] += 1
        return _request_counters[message_id]

    def create_message_log_entry(
        self,
        *,
        text: str,
        details: MessageLogDetails | None = None,
        references: list[ContentReference],
    ) -> None:
        """
        Create a full message log entry with question, hits, and references.

        Args:
            text: The prepared string for the message log entry
            details: Some formal details about the message log entry
            references: List of ContentReference objects to reference
        """

        # Creating a new message log entry with the found hits.
        if not self._chat_service._assistant_message_id:
            _LOGGER.warning(
                "Assistant message id is not set. Skipping message log entry creation."
            )
            return

        _ = self._chat_service.create_message_log(
            message_id=self._chat_service._assistant_message_id,
            text=text,
            status=MessageLogStatus.COMPLETED,
            order=self._get_next_message_order(
                message_id=self._chat_service._assistant_message_id
            ),
            details=details or MessageLogDetails(data=[]),
            uncited_references=MessageLogUncitedReferences(data=references),
            references=[],
        )
