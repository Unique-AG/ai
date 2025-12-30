"""
Logger Service for Unique Agentic tools.

Target of the method is to extend the step tracking on all levels of the tool.
"""

from collections import defaultdict
from logging import getLogger

from unique_toolkit.chat.schemas import (
    MessageLog,
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
        status: MessageLogStatus = MessageLogStatus.COMPLETED,
        details: MessageLogDetails | None = None,
        references: list[ContentReference] = [],
    ) -> MessageLog | None:
        """
        Create a full message log entry with question, hits, and references.
        The created message log entry is returned. If the message log entry is not created, None is returned.
        """
        if not self._chat_service._assistant_message_id:
            _LOGGER.warning(
                "Assistant message id is not set. Skipping message log entry creation."
            )
            return
        return self._chat_service.create_message_log(
            message_id=self._chat_service._assistant_message_id,
            text=text,
            status=status,
            order=self._get_next_message_order(
                message_id=self._chat_service._assistant_message_id
            ),
            details=details or MessageLogDetails(data=[]),
            uncited_references=MessageLogUncitedReferences(data=references),
            references=[],
        )

    def update_message_log_entry(
        self,
        *,
        message_log: MessageLog,
        text: str | None = None,
        status: MessageLogStatus,
        details: MessageLogDetails | None = None,
        references: list[ContentReference] = [],
    ) -> MessageLog | None:
        """
        Update a message log entry with a new status.
        The updated message log entry is returned. If the message log entry is not updated, None is returned.
        """
        if message_log.message_log_id is None:
            _LOGGER.warning(
                "Message log id is not set. Skipping message log entry update."
            )
            return
        return self._chat_service.update_message_log(
            message_log_id=message_log.message_log_id,
            order=message_log.order,
            text=text,
            status=status,
            details=details or MessageLogDetails(data=[]),
            uncited_references=MessageLogUncitedReferences(data=references),
            references=[],
        )

    def create_or_update_message_log(
        self,
        *,
        active_message_log: MessageLog | None,
        header: str,
        progress_message: str | None = None,
        status: MessageLogStatus,
        details: MessageLogDetails | None = None,
        references: list[ContentReference] | None = None,
    ) -> MessageLog | None:
        """
        Create a new message log entry or update an existing one.

        This is a convenience method that handles the common pattern of:
        - Creating a new message log if active_message_log is None
        - Updating the existing message log otherwise

        Args:
            active_message_log: The current active message log, or None if none exists
            header: The header to show in bold (e.g., "Internal Search", "Web Search")
            progress_message: Optional progress message to append after the display name
            status: The status of the message log
            details: Optional message log details
            references: Optional list of content references

        Returns:
            The created or updated MessageLog, or None if the operation failed
        """
        text = (
            f"**{header}**\n{progress_message}"
            if progress_message is not None
            else f"**{header}**"
        )

        if references is None:
            references = []

        if active_message_log is None:
            return self.create_message_log_entry(
                text=text,
                details=details,
                references=references,
                status=status,
            )
        else:
            return self.update_message_log_entry(
                message_log=active_message_log,
                text=text,
                status=status,
                details=details,
                references=references,
            )
