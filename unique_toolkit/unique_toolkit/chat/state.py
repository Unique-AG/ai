from dataclasses import dataclass
from typing import Self

from unique_toolkit.event.schema import Event


@dataclass
class ChatState:
    """
    Represents the state of the chat session.

    Attributes:
        company_id (str): The company ID.
        user_id (str): The user ID.
        chat_id (str): The chat ID.
        scope_ids (list[str] | None): The scope IDs.
        chat_only (bool): The chat only flag.
        user_message_text (str): The user message text.
        user_message_id (str): The user message ID.
        assistant_message_id (str): The assistant message ID.
    """

    company_id: str
    user_id: str
    assistant_id: str
    chat_id: str
    scope_ids: list[str] | None = None
    chat_only: bool = False
    user_message_text: str = ""
    user_message_id: str = ""
    assistant_message_id: str = ""
    module_name: str = ""


    @classmethod
    def from_event(cls, event: Event) -> Self:
        """
        Creates a ChatState instance from the Event.

        Args:
            event (Event): The Event object.

        Returns:
            ChatManager: The ChatManager instance.
        """
        config = event.payload.configuration

        scope_ids = config.get("scopeIds") or None
        chat_only = config.get("scopeToChatOnUpload", False)
        return cls(
            user_id=event.user_id,
            chat_id=event.payload.chat_id,
            company_id=event.company_id,
            assistant_id=event.payload.assistant_id,
            scope_ids=scope_ids,
            chat_only=chat_only,
            user_message_text=event.payload.user_message.text,
            user_message_id=event.payload.user_message.id,
            assistant_message_id=event.payload.assistant_message.id,
            module_name=event.payload.name
        )