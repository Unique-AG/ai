import logging
from typing import Optional

from unique_toolkit.app.schemas import ChatEvent, Event
from unique_toolkit.chat.constants import (
    DEFAULT_MAX_MESSAGES,
    DEFAULT_PERCENT_OF_MAX_TOKENS,
    DOMAIN_NAME,
)
from unique_toolkit.chat.functions import (
    create_message,
    create_message_async,
    get_full_history,
    get_full_history_async,
    get_selection_from_history,
    modify_message,
    modify_message_async,
)
from unique_toolkit.chat.schemas import ChatMessage, ChatMessageRole
from unique_toolkit.content.schemas import ContentReference

logger = logging.getLogger(f"toolkit.{DOMAIN_NAME}.{__name__}")


class ChatService:
    """
    Provides all functionalities to manage the chat session.

    Attributes:
        event (Event | ChatEvent): The Event object.
        logger (Optional[logging.Logger]): The logger. Defaults to None.
    """

    def __init__(self, event: ChatEvent | Event):
        self.event = event
        self.company_id = event.company_id
        self.user_id = event.user_id
        self.assistant_message_id = event.payload.assistant_message.id
        self.user_message_id = event.payload.user_message.id
        self.chat_id = event.payload.chat_id
        self.assistant_id = event.payload.assistant_id
        self.user_message_text = event.payload.user_message.text

    async def update_debug_info_async(self, debug_info: dict):
        """
        Updates the debug information for the chat session.

        Args:
            debug_info (dict): The new debug information.
        """

        return await modify_message_async(
            user_id=self.user_id,
            company_id=self.company_id,
            assistant_message_id=self.assistant_message_id,
            chat_id=self.chat_id,
            user_message_id=self.user_message_id,
            user_message_text=self.user_message_text,
            assistant=False,
            debug_info=debug_info,
        )

    def update_debug_info(self, debug_info: dict):
        """
        Updates the debug information for the chat session.

        Args:
            debug_info (dict): The new debug information.
        """

        return modify_message(
            user_id=self.user_id,
            company_id=self.company_id,
            assistant_message_id=self.assistant_message_id,
            chat_id=self.chat_id,
            user_message_id=self.user_message_id,
            user_message_text=self.user_message_text,
            assistant=False,
            debug_info=debug_info,
        )

    def modify_user_message(
        self,
        content: str,
        references: list[ContentReference] = [],
        debug_info: dict = {},
        message_id: str | None = None,
        set_completed_at: bool | None = False,
    ) -> ChatMessage:
        """
        Modifies a user message in the chat session synchronously.

        Args:
            content (str): The new content for the message.
            references (list[ContentReference]): list of ContentReference objects. Defaults to [].
            debug_info (dict[str, Any]]]): Debug information. Defaults to {}.
            message_id (str, optional): The message ID. Defaults to None, then the ChatState user message id is used.
            set_completed_at (Optional[bool]): Whether to set the completedAt field with the current date time. Defaults to False.

        Returns:
            ChatMessage: The modified message.

        Raises:
            Exception: If the modification fails.
        """
        return modify_message(
            user_id=self.user_id,
            company_id=self.company_id,
            assistant_message_id=self.assistant_message_id,
            chat_id=self.chat_id,
            user_message_id=self.user_message_id,
            user_message_text=self.user_message_text,
            assistant=False,
            content=content,
            references=references,
            debug_info=debug_info,
            message_id=message_id,
            set_completed_at=set_completed_at or False,
        )

    async def modify_user_message_async(
        self,
        content: str,
        references: list[ContentReference] = [],
        debug_info: dict = {},
        message_id: str | None = None,
        set_completed_at: bool | None = False,
    ) -> ChatMessage:
        """
        Modifies a message in the chat session asynchronously.

        Args:
            content (str): The new content for the message.
            message_id (str, optional): The message ID. Defaults to None, then the ChatState user message id is used.
            references (list[ContentReference]): list of ContentReference objects. Defaults to None.
            debug_info (dict[str, Any]]]): Debug information. Defaults to {}.
            set_completed_at (bool, optional): Whether to set the completedAt field with the current date time. Defaults to False.

        Returns:
            ChatMessage: The modified message.

        Raises:
            Exception: If the modification fails.
        """
        return await modify_message_async(
            user_id=self.user_id,
            company_id=self.company_id,
            assistant_message_id=self.assistant_message_id,
            chat_id=self.chat_id,
            user_message_id=self.user_message_id,
            user_message_text=self.user_message_text,
            assistant=False,
            content=content,
            references=references,
            debug_info=debug_info,
            message_id=message_id,
            set_completed_at=set_completed_at or False,
        )

    def modify_assistant_message(
        self,
        content: str | None = None,
        original_content: str | None = None,
        references: list[ContentReference] = [],
        debug_info: dict = {},
        message_id: str | None = None,
        set_completed_at: bool | None = False,
    ) -> ChatMessage:
        """
        Modifies a message in the chat session synchronously.

        Args:
            content (str, optional): The new content for the message.
            original_content (str, optional): The original content for the message.
            references (list[ContentReference]): list of ContentReference objects. Defaults to [].
            debug_info (dict[str, Any]]]): Debug information. Defaults to {}.
            message_id (Optional[str]): The message ID. Defaults to None.
            set_completed_at (Optional[bool]): Whether to set the completedAt field with the current date time. Defaults to False.

        Returns:
            ChatMessage: The modified message.

        Raises:
            Exception: If the modification fails.
        """
        return modify_message(
            user_id=self.user_id,
            company_id=self.company_id,
            assistant_message_id=self.assistant_message_id,
            chat_id=self.chat_id,
            user_message_id=self.user_message_id,
            user_message_text=self.user_message_text,
            assistant=True,
            content=content,
            original_content=original_content,
            references=references,
            debug_info=debug_info,
            message_id=message_id,
            set_completed_at=set_completed_at or False,
        )

    async def modify_assistant_message_async(
        self,
        content: str | None = None,
        original_content: str | None = None,
        references: list[ContentReference] = [],
        debug_info: dict = {},
        message_id: str | None = None,
        set_completed_at: bool | None = False,
    ) -> ChatMessage:
        """
        Modifies a message in the chat session asynchronously.

        Args:
            content (str, optional): The new content for the message.
            original_content (str, optional): The original content for the message.
            message_id (str, optional): The message ID. Defaults to None, then the ChatState assistant message id is used.
            references (list[ContentReference]): list of ContentReference objects. Defaults to None.
            debug_info (dict[str, Any]], optional): Debug information. Defaults to None.
            set_completed_at (bool, optional): Whether to set the completedAt field with the current date time. Defaults to False.

        Returns:
            ChatMessage: The modified message.

        Raises:
            Exception: If the modification fails.
        """

        return await modify_message_async(
            user_id=self.user_id,
            company_id=self.company_id,
            assistant_message_id=self.assistant_message_id,
            chat_id=self.chat_id,
            user_message_id=self.user_message_id,
            user_message_text=self.user_message_text,
            assistant=True,
            content=content,
            original_content=original_content,
            references=references,
            debug_info=debug_info,
            message_id=message_id,
            set_completed_at=set_completed_at or False,
        )

    def get_full_history(self) -> list[ChatMessage]:
        """
        Loads the full chat history for the chat session synchronously.

        Returns:
            list[ChatMessage]: The full chat history.

        Raises:
            Exception: If the loading fails.
        """
        return get_full_history(
            event_user_id=self.user_id,
            event_company_id=self.company_id,
            event_payload_chat_id=self.chat_id,
        )

    async def get_full_history_async(self) -> list[ChatMessage]:
        """
        Loads the full chat history for the chat session asynchronously.

        Returns:
            list[ChatMessage]: The full chat history.

        Raises:
            Exception: If the loading fails.
        """
        return await get_full_history_async(
            event_user_id=self.user_id,
            event_company_id=self.company_id,
            event_payload_chat_id=self.chat_id,
        )

    def get_full_and_selected_history(
        self,
        token_limit: int,
        percent_of_max_tokens: float = DEFAULT_PERCENT_OF_MAX_TOKENS,
        max_messages: int = DEFAULT_MAX_MESSAGES,
    ) -> tuple[list[ChatMessage], list[ChatMessage]]:
        """
        Loads the chat history for the chat session synchronously.

        Args:
            token_limit (int): The maximum number of tokens to load.
            percent_of_max_tokens (float): The percentage of the maximum tokens to load. Defaults to 0.15.
            max_messages (int): The maximum number of messages to load. Defaults to 4.

        Returns:
            tuple[list[ChatMessage], list[ChatMessage]]: The selected and full chat history.

        Raises:
            Exception: If the loading fails.
        """
        full_history = get_full_history(
            event_user_id=self.user_id,
            event_company_id=self.company_id,
            event_payload_chat_id=self.chat_id,
        )
        selected_history = get_selection_from_history(
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
        """
        Loads the chat history for the chat session asynchronously.

        Args:
            token_limit (int): The maximum number of tokens to load.
            percent_of_max_tokens (float): The percentage of the maximum tokens to load. Defaults to 0.15.
            max_messages (int): The maximum number of messages to load. Defaults to 4.

        Returns:
            tuple[list[ChatMessage], list[ChatMessage]]: The selected and full chat history.

        Raises:
            Exception: If the loading fails.
        """
        full_history = await get_full_history_async(
            event_user_id=self.user_id,
            event_company_id=self.company_id,
            event_payload_chat_id=self.chat_id,
        )
        selected_history = get_selection_from_history(
            full_history=full_history,
            max_tokens=int(round(token_limit * percent_of_max_tokens)),
            max_messages=max_messages,
        )

        return full_history, selected_history

    def create_assistant_message(
        self,
        content: str,
        original_content: str | None = None,
        references: list[ContentReference] = [],
        debug_info: dict = {},
        set_completed_at: Optional[bool] = False,
    ):
        """
        Creates a message in the chat session synchronously.

        Args:
            content (str): The content for the message.
            original_content (str, optional): The original content for the message.
            references (list[ContentReference]): list of ContentReference objects. Defaults to None.
            debug_info (dict[str, Any]]): Debug information. Defaults to None.
            set_completed_at (Optional[bool]): Whether to set the completedAt field with the current date time. Defaults to False.

        Returns:
            ChatMessage: The created message.

        Raises:
            Exception: If the creation fails.
        """
        return create_message(
            user_id=self.user_id,
            company_id=self.company_id,
            chat_id=self.chat_id,
            assistant_id=self.assistant_id,
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
        set_completed_at: Optional[bool] = False,
    ):
        """
        Creates a message in the chat session asynchronously.

        Args:
            content (str): The content for the message.
            original_content (str, optional): The original content for the message.
            references (list[ContentReference]): list of references. Defaults to None.
            debug_info (dict[str, Any]]): Debug information. Defaults to None.
            set_completed_at (Optional[bool]): Whether to set the completedAt field with the current date time. Defaults to False.

        Returns:
            ChatMessage: The created message.

        Raises:
            Exception: If the creation fails.
        """

        return await create_message_async(
            user_id=self.user_id,
            company_id=self.company_id,
            chat_id=self.chat_id,
            assistant_id=self.assistant_id,
            role=ChatMessageRole.ASSISTANT,
            content=content,
            original_content=original_content,
            references=references,
            debug_info=debug_info,
            set_completed_at=set_completed_at,
        )
