import logging
import re
from typing import Optional, overload

from unique_toolkit._common.validate_required_values import validate_required_values
from unique_toolkit.app.schemas import ChatEvent, Event, MagicTableEvent
from unique_toolkit.chat.constants import (
    DEFAULT_MAX_MESSAGES,
    DEFAULT_PERCENT_OF_MAX_TOKENS,
    DOMAIN_NAME,
)
from unique_toolkit.chat.functions import (
    create_message,
    create_message_async,
    list_messages,
    list_messages_async,
    modify_message,
    modify_message_async,
    update_message_debug_info,
    update_message_debug_info_async,
)
from unique_toolkit.chat.schemas import ChatMessage, ChatMessageRole
from unique_toolkit.chat.utils import pick_messages_in_reverse_for_token_window
from unique_toolkit.content.schemas import ContentReference

logger = logging.getLogger(f"toolkit.{DOMAIN_NAME}.{__name__}")


class ChatService:
    """
    Provides all functionalities to manage the chat session.

    Attributes:
        company_id (str): The company ID.
        user_id (Optional[str]): The user ID.
        assistant_message_id (Optional[str]): The assistant message ID.
        user_message_id (Optional[str]): The user message ID.
        chat_id (Optional[str]): The chat ID.
        assistant_id (Optional[str]): The assistant ID.
    """

    @overload
    def __init__(self, event: Event): ...

    @overload
    def __init__(self, event: ChatEvent): ...

    @overload
    def __init__(self, event: MagicTableEvent): ...

    def __init__(
        self,
        event: ChatEvent | MagicTableEvent | Event,
    ):
        if isinstance(event, (ChatEvent, Event)):
            self.company_id = event.company_id
            self.user_id = event.user_id
            self.assistant_message_id = event.payload.assistant_message.id
            self.user_message_id = event.payload.user_message.id
            self.user_message_text = event.payload.user_message.text
            self.chat_id = event.payload.chat_id
            self.assistant_id = event.payload.assistant_id
        elif isinstance(event, MagicTableEvent):
            self.company_id = event.company_id
            self.user_id = event.user_id
            self.assistant_message_id = None
            self.user_message_id = None
            self.chat_id = None
            self.assistant_id = None

    async def update_debug_info_async(self, debug_info: dict) -> None:
        """Updates the debug information for the chat session asynchronously."""
        [user_id, company_id, message_id, chat_id] = validate_required_values(
            [self.user_id, self.company_id, self.user_message_id, self.chat_id]
        )
        await update_message_debug_info_async(
            user_id=user_id,
            company_id=company_id,
            message_id=message_id,
            chat_id=chat_id,
            debug_info=debug_info,
        )

    def update_debug_info(self, debug_info: dict) -> None:
        """Updates the debug information for the chat session synchronously."""
        [user_id, company_id, message_id, chat_id] = validate_required_values(
            [self.user_id, self.company_id, self.user_message_id, self.chat_id]
        )
        update_message_debug_info(
            user_id=user_id,
            company_id=company_id,
            message_id=message_id,
            chat_id=chat_id,
            debug_info=debug_info,
        )

    def modify_user_message(
        self,
        content: str,
        references: Optional[list[ContentReference]] = None,
        debug_info: Optional[dict] = None,
        message_id: Optional[str] = None,
        set_completed_at: bool = False,
    ) -> ChatMessage:
        """Modifies a user message synchronously."""
        [user_id, company_id, chat_id, user_message_id, user_message_text] = (
            validate_required_values(
                [
                    self.user_id,
                    self.company_id,
                    self.chat_id,
                    self.user_message_id,
                    self.user_message_text,
                ]
            )
        )
        return modify_message(
            user_id=user_id,
            company_id=company_id,
            message_id=message_id or user_message_id,
            chat_id=chat_id,
            content=content or user_message_text,
            references=references,
            debug_info=debug_info,
            set_completed_at=set_completed_at,
        )

    async def modify_user_message_async(
        self,
        content: str,
        references: list[ContentReference] = [],
        debug_info: dict = {},
        message_id: Optional[str] = None,
        set_completed_at: bool = False,
    ) -> ChatMessage:
        """Modifies a user message asynchronously."""
        [user_id, company_id, chat_id, user_message_id, user_message_text] = (
            validate_required_values(
                [
                    self.user_id,
                    self.company_id,
                    self.chat_id,
                    self.user_message_id,
                    self.user_message_text,
                ]
            )
        )
        return await modify_message_async(
            user_id=user_id,
            company_id=company_id,
            message_id=message_id or user_message_id,
            chat_id=chat_id,
            content=content or user_message_text,
            references=references,
            debug_info=debug_info,
            set_completed_at=set_completed_at,
        )

    def modify_assistant_message(
        self,
        content: str | None = None,
        original_content: str | None = None,
        references: list[ContentReference] = [],
        debug_info: dict = {},
        message_id: Optional[str] = None,
        set_completed_at: bool = False,
    ) -> ChatMessage:
        """Modifies an assistant message synchronously."""
        [user_id, company_id, chat_id, assistant_message_id] = validate_required_values(
            [self.user_id, self.company_id, self.chat_id, self.assistant_message_id]
        )
        return modify_message(
            user_id=user_id,
            company_id=company_id,
            message_id=message_id or assistant_message_id,
            chat_id=chat_id,
            content=content,
            original_content=original_content,
            references=references,
            debug_info=debug_info,
            set_completed_at=set_completed_at,
        )

    async def modify_assistant_message_async(
        self,
        content: str | None = None,
        original_content: str | None = None,
        references: list[ContentReference] = [],
        debug_info: dict = {},
        message_id: Optional[str] = None,
        set_completed_at: bool = False,
    ) -> ChatMessage:
        """Modifies an assistant message asynchronously."""
        [user_id, company_id, chat_id, assistant_message_id] = validate_required_values(
            [self.user_id, self.company_id, self.chat_id, self.assistant_message_id]
        )
        return await modify_message_async(
            user_id=user_id,
            company_id=company_id,
            message_id=message_id or assistant_message_id,
            chat_id=chat_id,
            content=content,
            original_content=original_content,
            references=references,
            debug_info=debug_info,
            set_completed_at=set_completed_at,
        )

    def create_assistant_message(
        self,
        content: str,
        original_content: str | None = None,
        references: list[ContentReference] = [],
        debug_info: dict = {},
        set_completed_at: bool = False,
    ) -> ChatMessage:
        """Creates an assistant message synchronously."""
        [user_id, company_id, chat_id, assistant_id] = validate_required_values(
            [self.user_id, self.company_id, self.chat_id, self.assistant_id]
        )
        return create_message(
            user_id=user_id,
            company_id=company_id,
            chat_id=chat_id,
            assistant_id=assistant_id,
            role=ChatMessageRole.ASSISTANT,
            content=content,
            original_content=original_content,
            references=references,
            debug_info=debug_info,
            set_completed_at=set_completed_at,
        )

    async def create_assistant_message_async(
        self,
        content: str,
        original_content: str | None = None,
        references: list[ContentReference] = [],
        debug_info: dict = {},
        set_completed_at: bool = False,
    ) -> ChatMessage:
        """Creates an assistant message asynchronously."""
        [user_id, company_id, chat_id, assistant_id] = validate_required_values(
            [self.user_id, self.company_id, self.chat_id, self.assistant_id]
        )
        return await create_message_async(
            user_id=user_id,
            company_id=company_id,
            chat_id=chat_id,
            assistant_id=assistant_id,
            role=ChatMessageRole.ASSISTANT,
            content=content,
            original_content=original_content,
            references=references,
            debug_info=debug_info,
            set_completed_at=set_completed_at,
        )

    def get_full_history(self) -> list[ChatMessage]:
        """Gets the full chat history synchronously."""
        [user_id, company_id, chat_id] = validate_required_values(
            [self.user_id, self.company_id, self.chat_id]
        )
        return list_messages(
            user_id=user_id,
            company_id=company_id,
            chat_id=chat_id,
        )

    async def get_full_history_async(self) -> list[ChatMessage]:
        """Gets the full chat history asynchronously."""
        [user_id, company_id, chat_id] = validate_required_values(
            [self.user_id, self.company_id, self.chat_id]
        )
        return await list_messages_async(
            user_id=user_id,
            company_id=company_id,
            chat_id=chat_id,
        )

    def get_full_and_selected_history(
        self,
        token_limit: int,
        percent_of_max_tokens: float = DEFAULT_PERCENT_OF_MAX_TOKENS,
        max_messages: int = DEFAULT_MAX_MESSAGES,
    ) -> tuple[list[ChatMessage], list[ChatMessage]]:
        """Gets both full and selected chat history synchronously."""
        full_history = self.get_full_history()
        selected_history = self._get_selection_from_history(
            full_history=full_history,
            max_tokens=int(round(token_limit * percent_of_max_tokens)),
            max_messages=max_messages,
        )
        return full_history, selected_history

    async def get_full_and_selected_history_async(
        self,
        token_limit: int,
        percent_of_max_tokens: float = DEFAULT_PERCENT_OF_MAX_TOKENS,
        max_messages: int = DEFAULT_MAX_MESSAGES,
    ) -> tuple[list[ChatMessage], list[ChatMessage]]:
        """Gets both full and selected chat history asynchronously."""
        full_history = await self.get_full_history_async()
        selected_history = self._get_selection_from_history(
            full_history=full_history,
            max_tokens=int(round(token_limit * percent_of_max_tokens)),
            max_messages=max_messages,
        )
        return full_history, selected_history

    def _get_selection_from_history(
        self,
        full_history: list[ChatMessage],
        max_tokens: int,
        max_messages: int = DEFAULT_MAX_MESSAGES,
    ) -> list[ChatMessage]:
        """Gets a selection of messages from the chat history."""
        messages = full_history[-max_messages:]
        filtered_messages = [m for m in messages if m.content]
        mapped_messages = []

        for m in filtered_messages:
            m.content = re.sub(r"<sup>\d+</sup>", "", m.content)
            m.role = (
                ChatMessageRole.ASSISTANT
                if m.role == ChatMessageRole.ASSISTANT
                else ChatMessageRole.USER
            )
            mapped_messages.append(m)

        return pick_messages_in_reverse_for_token_window(
            messages=mapped_messages,
            limit=max_tokens,
            logger=logger,
        )
