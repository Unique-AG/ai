import logging
from typing import Optional

import unique_sdk

from unique_toolkit._common._base_service import BaseService
from unique_toolkit.app.schemas import ChatEvent
from unique_toolkit.chat.functions import (
    construct_message_create_params,
    construct_message_modify_params,
    get_full_history,
    get_full_history_async,
    get_selection_from_history,
)
from unique_toolkit.chat.schemas import ChatMessage
from unique_toolkit.content.schemas import ContentReference


class ChatService(BaseService):
    """
    Provides all functionalities to manage the chat session.

    Attributes:
        event (Event): The Event object.
        logger (Optional[logging.Logger]): The logger. Defaults to None.
    """

    def __init__(self, event: ChatEvent, logger: Optional[logging.Logger] = None):
        super().__init__(event, logger)

    DEFAULT_PERCENT_OF_MAX_TOKENS = 0.15
    DEFAULT_MAX_MESSAGES = 4

    async def update_debug_info_async(self, debug_info: dict):
        """
        Updates the debug information for the chat session.

        Args:
            debug_info (dict): The new debug information.
        """
        params = construct_message_modify_params(
            event_user_id=self.event.user_id,
            event_company_id=self.event.company_id,
            event_payload_assistant_message_id=self.event.payload.assistant_message.id,
            event_payload_chat_id=self.event.payload.chat_id,
            event_payload_user_message_id=self.event.payload.user_message.id,
            event_payload_user_message_text=self.event.payload.user_message.text,
            assistant=False,
            debug_info=debug_info,
        )
        try:
            await unique_sdk.Message.modify_async(**params)
        except Exception as e:
            self.logger.error(f"Failed to update debug info: {e}")
            raise e

    def update_debug_info(self, debug_info: dict):
        """
        Updates the debug information for the chat session.

        Args:
            debug_info (dict): The new debug information.
        """
        params = construct_message_modify_params(
            event_user_id=self.event.user_id,
            event_company_id=self.event.company_id,
            event_payload_assistant_message_id=self.event.payload.assistant_message.id,
            event_payload_chat_id=self.event.payload.chat_id,
            event_payload_user_message_id=self.event.payload.user_message.id,
            event_payload_user_message_text=self.event.payload.user_message.text,
            assistant=False,
            debug_info=debug_info,
        )
        try:
            unique_sdk.Message.modify(**params)
        except Exception as e:
            self.logger.error(f"Failed to update debug info: {e}")
            raise e

    def modify_user_message(
        self,
        content: str,
        references: Optional[list[ContentReference]] = None,
        debug_info: Optional[dict] = None,
        message_id: Optional[str] = None,
        set_completed_at: Optional[bool] = False,
    ) -> ChatMessage:
        """
        Modifies a message in the chat session synchronously.

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
        try:
            params = construct_message_modify_params(
                event_user_id=self.event.user_id,
                event_company_id=self.event.company_id,
                event_payload_assistant_message_id=self.event.payload.assistant_message.id,
                event_payload_chat_id=self.event.payload.chat_id,
                event_payload_user_message_id=self.event.payload.user_message.id,
                event_payload_user_message_text=self.event.payload.user_message.text,
                assistant=False,
                content=content,
                references=references,
                debug_info=debug_info,
                message_id=message_id,
                set_completed_at=set_completed_at,
            )
            message = unique_sdk.Message.modify(**params)
        except Exception as e:
            self.logger.error(f"Failed to modify user message: {e}")
            raise e
        return ChatMessage(**message)

    async def modify_user_message_async(
        self,
        content: str,
        references: list[ContentReference] = [],
        debug_info: dict = {},
        message_id: Optional[str] = None,
        set_completed_at: Optional[bool] = False,
    ) -> ChatMessage:
        """
        Modifies a message in the chat session asynchronously.

        Args:
            content (str): The new content for the message.
            message_id (str, optional): The message ID. Defaults to None, then the ChatState user message id is used.
            references (list[ContentReference]): list of ContentReference objects. Defaults to None.
            debug_info (Optional[dict[str, Any]]], optional): Debug information. Defaults to None.
            set_completed_at (Optional[bool]): Whether to set the completedAt field with the current date time. Defaults to False.

        Returns:
            ChatMessage: The modified message.

        Raises:
            Exception: If the modification fails.
        """
        try:
            params = construct_message_modify_params(
                event_user_id=self.event.user_id,
                event_company_id=self.event.company_id,
                event_payload_assistant_message_id=self.event.payload.assistant_message.id,
                event_payload_chat_id=self.event.payload.chat_id,
                event_payload_user_message_id=self.event.payload.user_message.id,
                event_payload_user_message_text=self.event.payload.user_message.text,
                assistant=False,
                content=content,
                references=references,
                debug_info=debug_info,
                message_id=message_id,
                set_completed_at=set_completed_at,
            )
            message = await unique_sdk.Message.modify_async(**params)
        except Exception as e:
            self.logger.error(f"Failed to modify user message: {e}")
            raise e
        return ChatMessage(**message)

    def modify_assistant_message(
        self,
        content: str | None = None,
        original_content: str | None = None,
        references: list[ContentReference] = [],
        debug_info: dict = {},
        message_id: Optional[str] = None,
        set_completed_at: Optional[bool] = False,
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
        try:
            params = construct_message_modify_params(
                event_user_id=self.event.user_id,
                event_company_id=self.event.company_id,
                event_payload_assistant_message_id=self.event.payload.assistant_message.id,
                event_payload_chat_id=self.event.payload.chat_id,
                event_payload_user_message_id=self.event.payload.user_message.id,
                event_payload_user_message_text=self.event.payload.user_message.text,
                assistant=True,
                content=content,
                original_content=original_content,
                references=references,
                debug_info=debug_info,
                message_id=message_id,
                set_completed_at=set_completed_at,
            )
            message = unique_sdk.Message.modify(**params)
        except Exception as e:
            self.logger.error(f"Failed to modify assistant message: {e}")
            raise e
        return ChatMessage(**message)

    async def modify_assistant_message_async(
        self,
        content: str | None = None,
        original_content: str | None = None,
        references: list[ContentReference] = [],
        debug_info: dict = {},
        message_id: Optional[str] = None,
        set_completed_at: Optional[bool] = False,
    ) -> ChatMessage:
        """
        Modifies a message in the chat session asynchronously.

        Args:
            content (str, optional): The new content for the message.
            original_content (str, optional): The original content for the message.
            message_id (str, optional): The message ID. Defaults to None, then the ChatState assistant message id is used.
            references (list[ContentReference]): list of ContentReference objects. Defaults to None.
            debug_info (Optional[dict[str, Any]]], optional): Debug information. Defaults to None.
            set_completed_at (Optional[bool]): Whether to set the completedAt field with the current date time. Defaults to False.

        Returns:
            ChatMessage: The modified message.

        Raises:
            Exception: If the modification fails.
        """
        try:
            params = construct_message_modify_params(
                event_user_id=self.event.user_id,
                event_company_id=self.event.company_id,
                event_payload_assistant_message_id=self.event.payload.assistant_message.id,
                event_payload_chat_id=self.event.payload.chat_id,
                event_payload_user_message_id=self.event.payload.user_message.id,
                event_payload_user_message_text=self.event.payload.user_message.text,
                assistant=True,
                content=content,
                original_content=original_content,
                references=references,
                debug_info=debug_info,
                message_id=message_id,
                set_completed_at=set_completed_at,
            )
            message = await unique_sdk.Message.modify_async(**params)
        except Exception as e:
            self.logger.error(f"Failed to modify assistant message: {e}")
            raise e
        return ChatMessage(**message)

    def get_full_history(self) -> list[ChatMessage]:
        """
        Loads the full chat history for the chat session synchronously.

        Returns:
            list[ChatMessage]: The full chat history.

        Raises:
            Exception: If the loading fails.
        """
        return get_full_history(
            event_user_id=self.event.user_id,
            event_company_id=self.event.company_id,
            event_payload_chat_id=self.event.payload.chat_id,
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
            event_user_id=self.event.user_id,
            event_company_id=self.event.company_id,
            event_payload_chat_id=self.event.payload.chat_id,
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
            event_user_id=self.event.user_id,
            event_company_id=self.event.company_id,
            event_payload_chat_id=self.event.payload.chat_id,
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
            event_user_id=self.event.user_id,
            event_company_id=self.event.company_id,
            event_payload_chat_id=self.event.payload.chat_id,
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
        if original_content is None:
            original_content = content

        try:
            params = construct_message_create_params(
                event_user_id=self.event.user_id,
                event_company_id=self.event.company_id,
                event_payload_chat_id=self.event.payload.chat_id,
                event_payload_assistant_id=self.event.payload.assistant_id,
                content=content,
                original_content=original_content,
                references=references,
                debug_info=debug_info,
                set_completed_at=set_completed_at,
            )

            message = unique_sdk.Message.create(**params)
        except Exception as e:
            self.logger.error(f"Failed to create assistant message: {e}")
            raise e
        return ChatMessage(**message)

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
        if original_content is None:
            original_content = content

        try:
            params = construct_message_create_params(
                event_user_id=self.event.user_id,
                event_company_id=self.event.company_id,
                event_payload_chat_id=self.event.payload.chat_id,
                event_payload_assistant_id=self.event.payload.assistant_id,
                content=content,
                original_content=original_content,
                references=references,
                debug_info=debug_info,
                set_completed_at=set_completed_at,
            )

            message = await unique_sdk.Message.create_async(**params)
        except Exception as e:
            self.logger.error(f"Failed to create assistant message: {e}")
            raise e
        return ChatMessage(**message)
