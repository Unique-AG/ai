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
        user_message_text (str): The user message text.
        user_message_id (str): The user message ID.
        assistant_message_id (str): The assistant message ID.
    """

    company_id: str
    user_id: str
    assistant_id: str = ""
    chat_id: str = ""
    user_message_text: str = ""
    user_message_id: str = ""
    assistant_message_id: str = ""

    @classmethod
    def from_event(cls, event: Event) -> Self:
        """
        Creates a ChatState instance from an event dictionary.

        Args:
            event (dict): The event dictionary.

        Returns:
            ChatState: The ChatState instance.
        """
        # Chat only flag
        return cls(
            user_id=event.user_id,
            chat_id=event.payload.chat_id,
            company_id=event.company_id,
            user_message_text=event.payload.user_message.text,
            user_message_id=event.payload.user_message.id,
            assistant_message_id=event.payload.assistant_message.id,
        )
