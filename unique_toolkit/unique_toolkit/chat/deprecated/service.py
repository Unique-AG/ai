from typing_extensions import deprecated

from unique_toolkit.app.schemas import ChatEvent, Correlation, Event
from unique_toolkit.chat.functions import (
    modify_message,
)


class ChatServiceDeprecated:
    def __init__(
        self,
        event: ChatEvent | Event,
        content_scope_chat_id: str | None = None,
    ):
        """Initialize the chat service from an event.

        Message operations use the event's chat and message ids. Content and
        search operations use the content-scope chat: when correlation is
        present (e.g. subagent), this is the parent chat so uploaded files
        from the primary session are accessible.

        Args:
            event: The chat event (e.g. from the webhook payload).
            content_scope_chat_id: Optional chat id for content/search scope.
                If None and event.payload.correlation is set, uses
                correlation.parent_chat_id; otherwise uses event.payload.chat_id.
        """
        self._event = event
        self._company_id: str = event.company_id
        self._user_id: str = event.user_id
        self._assistant_message_id: str = event.payload.assistant_message.id
        self._user_message_id: str = event.payload.user_message.id
        self._chat_id: str = event.payload.chat_id
        self._assistant_id: str = event.payload.assistant_id
        self._user_message_text: str = event.payload.user_message.text
        if content_scope_chat_id is not None:
            self._content_scope_chat_id: str = content_scope_chat_id
        else:
            correlation = event.payload.correlation
            if correlation is not None:
                self._content_scope_chat_id = correlation.parent_chat_id
            else:
                self._content_scope_chat_id = event.payload.chat_id

    @classmethod
    def from_chat_event(cls, event: ChatEvent | Event) -> "ChatServiceDeprecated":
        """Create a chat service from an event.

        When the event has a correlation (e.g. subagent run), delegates to
        from_correlation so content scope is the parent chat. Otherwise
        returns an instance with content scope equal to the event's chat.

        Args:
            event: The chat event.

        Returns:
            ChatServiceDeprecated: Instance configured for this event (and
                parent chat content scope when correlation is present).
        """
        correlation = event.payload.correlation
        if correlation is not None:
            return cls.from_correlation(
                correlation,
                event,
            )
        return cls(event)

    @classmethod
    def from_correlation(
        cls,
        correlation: Correlation,
        event: ChatEvent | Event,
    ) -> "ChatServiceDeprecated":
        """Create a chat service for a subagent using parent chat for content.

        Use when the event has correlation (e.g. subagent). Message operations
        use the current (subagent) chat; content and search use the parent chat
        so files uploaded in the primary session are accessible.

        Args:
            correlation: Parent chat/message/assistant ids.
            event: The subagent's chat event.

        Returns:
            ChatServiceDeprecated: Instance with content_scope_chat_id set to
                correlation.parent_chat_id.
        """
        return cls(event, content_scope_chat_id=correlation.parent_chat_id)

    @property
    @deprecated(
        "The event property is deprecated and will be removed in a future version.",
    )
    def event(self) -> Event | ChatEvent:
        """Get the event object (deprecated).

        Returns:
            Event | BaseEvent | None: The event object.

        """
        return self._event

    @property
    @deprecated(
        "The company_id property is deprecated and will be removed in a future version.",
    )
    def company_id(self) -> str:
        """Get the company identifier (deprecated).

        Returns:
            str | None: The company identifier.

        """
        return self._company_id

    @company_id.setter
    @deprecated(
        "The company_id setter is deprecated and will be removed in a future version.",
    )
    def company_id(self, value: str) -> None:
        """Set the company identifier (deprecated).

        Args:
            value (str | None): The company identifier.

        """
        self._company_id = value

    @property
    @deprecated(
        "The user_id property is deprecated and will be removed in a future version.",
    )
    def user_id(self) -> str:
        """Get the user identifier (deprecated).

        Returns:
            str | None: The user identifier.

        """
        return self._user_id

    @user_id.setter
    @deprecated(
        "The user_id setter is deprecated and will be removed in a future version.",
    )
    def user_id(self, value: str) -> None:
        """Set the user identifier (deprecated).

        Args:
            value (str | None): The user identifier.

        """
        self._user_id = value

    @property
    @deprecated(
        "The assistant_message_id property is deprecated and will be removed in a future version.",
    )
    def assistant_message_id(self) -> str:
        """Get the assistant message identifier (deprecated).

        Returns:
            str | None: The assistant message identifier.

        """
        return self._assistant_message_id

    @assistant_message_id.setter
    @deprecated(
        "The assistant_message_id setter is deprecated and will be removed in a future version.",
    )
    def assistant_message_id(self, value: str) -> None:
        """Set the assistant message identifier (deprecated).

        Args:
            value (str | None): The assistant message identifier.

        """
        self._assistant_message_id = value

    @property
    @deprecated(
        "The user_message_id property is deprecated and will be removed in a future version.",
    )
    def user_message_id(self) -> str:
        """Get the user message identifier (deprecated).

        Returns:
            str | None: The user message identifier.

        """
        return self._user_message_id

    @user_message_id.setter
    @deprecated(
        "The user_message_id setter is deprecated and will be removed in a future version.",
    )
    def user_message_id(self, value: str) -> None:
        """Set the user message identifier (deprecated).

        Args:
            value (str | None): The user message identifier.

        """
        self._user_message_id = value

    @property
    @deprecated(
        "The chat_id property is deprecated and will be removed in a future version.",
    )
    def chat_id(self) -> str:
        """Get the chat identifier (deprecated).

        Returns:
            str | None: The chat identifier.

        """
        return self._chat_id

    @chat_id.setter
    @deprecated(
        "The chat_id setter is deprecated and will be removed in a future version.",
    )
    def chat_id(self, value: str) -> None:
        """Set the chat identifier (deprecated).

        Args:
            value (str | None): The chat identifier.

        """
        self._chat_id = value

    @property
    @deprecated(
        "The assistant_id property is deprecated and will be removed in a future version.",
    )
    def assistant_id(self) -> str:
        """Get the assistant identifier (deprecated).

        Returns:
            str | None: The assistant identifier.

        """
        return self._assistant_id

    @assistant_id.setter
    @deprecated(
        "The assistant_id setter is deprecated and will be removed in a future version.",
    )
    def assistant_id(self, value: str) -> None:
        """Set the assistant identifier (deprecated).

        Args:
            value (str | None): The assistant identifier.

        """
        self._assistant_id = value

    @property
    @deprecated(
        "The user_message_text property is deprecated and will be removed in a future version.",
    )
    def user_message_text(self) -> str:
        """Get the user message text (deprecated).

        Returns:
            str | None: The user message text.

        """
        return self._user_message_text

    @user_message_text.setter
    @deprecated(
        "The user_message_text setter is deprecated and will be removed in a future version.",
    )
    def user_message_text(self, value: str) -> None:
        """Set the user message text (deprecated).

        Args:
            value (str | None): The user message text.

        """
        self._user_message_text = value

    @deprecated("Use `replace_debug_info`")
    def update_debug_info(self, debug_info: dict):
        """Updates the debug information for the chat session.

        Args:
            debug_info (dict): The new debug information.

        """
        return modify_message(
            user_id=self._user_id,
            company_id=self._company_id,
            assistant_message_id=self._assistant_message_id,
            chat_id=self._chat_id,
            user_message_id=self._user_message_id,
            user_message_text=self._user_message_text,
            assistant=False,
            debug_info=debug_info,
        )
