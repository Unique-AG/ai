import logging
import re
from typing import Optional

import unique_sdk
from unique_sdk._list_object import ListObject

from unique_toolkit._common._base_service import BaseService
from unique_toolkit.chat.schemas import ChatMessage, ChatMessageRole
from unique_toolkit.chat.state import ChatState
from unique_toolkit.content.schemas import ContentReference
from unique_toolkit.content.utils import count_tokens


class ChatService(BaseService):
    """
    Provides all functionalities to manage the chat session.

    Attributes:
        state (ChatState): The chat state.
        logger (Optional[logging.Logger]): The logger. Defaults to None.
    """

    def __init__(self, state: ChatState, logger: Optional[logging.Logger] = None):
        super().__init__(state, logger)

    DEFAULT_PERCENT_OF_MAX_TOKENS = 0.15
    DEFAULT_MAX_MESSAGES = 4

    def modify_assistant_message(
        self,
        content: str,
        references: list[ContentReference] = [],
        debug_info: dict = {},
        message_id: Optional[str] = None,
    ) -> ChatMessage:
        """
        Modifies a message in the chat session synchronously.

        Args:
            content (str): The new content for the message.
            references (list[ContentReference]): list of ContentReference objects. Defaults to [].
            debug_info (dict[str, Any]]]): Debug information. Defaults to {}.
            message_id (Optional[str]): The message ID. Defaults to None.

        Returns:
            ChatMessage: The modified message.

        Raises:
            Exception: If the modification fails.
        """
        message_id = message_id or self.state.assistant_message_id

        try:
            message = unique_sdk.Message.modify(
                user_id=self.state.user_id,
                company_id=self.state.company_id,
                id=message_id,  # type: ignore
                chatId=self.state.chat_id,
                text=content,
                references=self._map_references(references),  # type: ignore
                debugInfo=debug_info or {},
            )
        except Exception as e:
            self.logger.error(f"Failed to modify assistant message: {e}")
            raise e
        return ChatMessage(**message)

    async def modify_assistant_message_async(
        self,
        content: str,
        references: list[ContentReference] = [],
        debug_info: dict = {},
        message_id: Optional[str] = None,
    ) -> ChatMessage:
        """
        Modifies a message in the chat session asynchronously.

        Args:
            content (str): The new content for the message.
            message_id (str, optional): The message ID. Defaults to None, then the ChatState assistant message id is used.
            references (list[ContentReference]): list of ContentReference objects. Defaults to None.
            debug_info (Optional[dict[str, Any]]], optional): Debug information. Defaults to None.

        Returns:
            ChatMessage: The modified message.

        Raises:
            Exception: If the modification fails.
        """
        message_id = message_id or self.state.assistant_message_id

        try:
            message = await unique_sdk.Message.modify_async(
                user_id=self.state.user_id,
                company_id=self.state.company_id,
                id=message_id,  # type: ignore
                chatId=self.state.chat_id,
                text=content,
                references=self._map_references(references),  # type: ignore
                debugInfo=debug_info or {},
            )
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
        return self._get_full_history()

    async def get_full_history_async(self) -> list[ChatMessage]:
        """
        Loads the full chat history for the chat session asynchronously.

        Returns:
            list[ChatMessage]: The full chat history.

        Raises:
            Exception: If the loading fails.
        """
        return await self._get_full_history_async()

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
        full_history = self._get_full_history()
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
        full_history = await self._get_full_history_async()
        selected_history = self._get_selection_from_history(
            full_history=full_history,
            max_tokens=int(round(token_limit * percent_of_max_tokens)),
            max_messages=max_messages,
        )

        return full_history, selected_history

    def create_assistant_message(
        self,
        content: str,
        references: list[ContentReference] = [],
        debug_info: dict = {},
    ):
        """
        Creates a message in the chat session synchronously.

        Args:
            content (str): The content for the message.
            references (list[ContentReference]): list of ContentReference objects. Defaults to None.
            debug_info (dict[str, Any]]): Debug information. Defaults to None.

        Returns:
            ChatMessage: The created message.

        Raises:
            Exception: If the creation fails.
        """

        try:
            message = unique_sdk.Message.create(
                user_id=self.state.user_id,
                company_id=self.state.company_id,
                chatId=self.state.chat_id,
                assistantId=self.state.assistant_id,
                text=content,
                role=ChatMessageRole.ASSISTANT.name,
                references=self._map_references(references),  # type: ignore
                debugInfo=debug_info,
            )
        except Exception as e:
            self.logger.error(f"Failed to create assistant message: {e}")
            raise e
        return ChatMessage(**message)

    async def create_assistant_message_async(
        self,
        content: str,
        references: list[ContentReference] = [],
        debug_info: dict = {},
    ):
        """
        Creates a message in the chat session asynchronously.

        Args:
            content (str): The content for the message.
            references (list[ContentReference]): list of references. Defaults to None.
            debug_info (dict[str, Any]]): Debug information. Defaults to None.

        Returns:
            ChatMessage: The created message.

        Raises:
            Exception: If the creation fails.
        """
        try:
            message = await unique_sdk.Message.create_async(
                user_id=self.state.user_id,
                company_id=self.state.company_id,
                chatId=self.state.chat_id,
                assistantId=self.state.assistant_id,
                text=content,
                role=ChatMessageRole.ASSISTANT.name,
                references=self._map_references(references),  # type: ignore
                debugInfo=debug_info,
            )
        except Exception as e:
            self.logger.error(f"Failed to create assistant message: {e}")
            raise e
        return ChatMessage(**message)

    @staticmethod
    def _map_references(references: list[ContentReference]):
        return [
            {
                "name": ref.name,
                "url": ref.url,
                "sequenceNumber": ref.sequence_number,
                "sourceId": ref.source_id,
                "source": ref.source,
            }
            for ref in references
        ]

    def _get_full_history(self):
        messages = self._trigger_list_messages(self.state.chat_id)
        messages = self._filter_valid_messages(messages)

        return self._map_to_chat_messages(messages)

    async def _get_full_history_async(self):
        messages = await self._trigger_list_messages_async(self.state.chat_id)
        messages = self._filter_valid_messages(messages)

        return self._map_to_chat_messages(messages)

    @staticmethod
    def _filter_valid_messages(messages: ListObject[unique_sdk.Message]):
        SYSTEM_MESSAGE_PREFIX = "[SYSTEM] "

        # Remove the last two messages
        messages = messages["data"][:-2]  # type: ignore
        filtered_messages = []
        for message in messages:
            if message["text"] is None:
                continue
            elif SYSTEM_MESSAGE_PREFIX in message["text"]:
                continue
            else:
                filtered_messages.append(message)

        return filtered_messages

    def _trigger_list_messages(self, chat_id: str):
        try:
            messages = unique_sdk.Message.list(
                user_id=self.state.user_id,
                company_id=self.state.company_id,
                chatId=chat_id,
            )
            return messages
        except Exception as e:
            self.logger.error(f"Failed to list chat history: {e}")
            raise e

    async def _trigger_list_messages_async(self, chat_id: str):
        try:
            messages = await unique_sdk.Message.list_async(
                user_id=self.state.user_id,
                company_id=self.state.company_id,
                chatId=chat_id,
            )
            return messages
        except Exception as e:
            self.logger.error(f"Failed to list chat history: {e}")
            raise e

    @staticmethod
    def _map_to_chat_messages(messages: list[dict]):
        return [ChatMessage(**msg) for msg in messages]

    def _get_selection_from_history(
        self,
        full_history: list[ChatMessage],
        max_tokens: int,
        max_messages=4,
    ):
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

        return self._pick_messages_in_reverse_for_token_window(
            messages=mapped_messages,
            limit=max_tokens,
        )

    def _pick_messages_in_reverse_for_token_window(
        self,
        messages: list[ChatMessage],
        limit: int,
    ) -> list[ChatMessage]:
        if len(messages) < 1 or limit < 1:
            return []

        last_index = len(messages) - 1
        token_count = count_tokens(messages[last_index].content)
        while token_count > limit:
            self.logger.debug(
                f"Limit too low for the initial message. Last message TokenCount {token_count} available tokens {limit} - cutting message in half until it fits"
            )
            content = messages[last_index].content
            messages[last_index].content = content[: len(content) // 2] + "..."
            token_count = count_tokens(messages[last_index].content)

        while token_count <= limit and last_index > 0:
            token_count = count_tokens(
                "".join([msg.content for msg in messages[:last_index]])
            )
            if token_count <= limit:
                last_index -= 1

        last_index = max(0, last_index)
        return messages[last_index:]
