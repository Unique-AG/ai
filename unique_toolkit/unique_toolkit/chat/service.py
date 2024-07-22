import logging
from typing import Optional

import unique_sdk
from unique_sdk.utils.chat_history import load_history

from unique_toolkit.chat.schemas import ChatMessage, ChatMessageRole
from unique_toolkit.chat.state import ChatState
from unique_toolkit.performance.async_wrapper import async_warning, to_async


class ChatService:
    """
    Provides all functionalities to manage the chat session.

    Attributes:
        state (ChatState): The chat state.
        logger (Optional[logging.Logger]): The logger. Defaults to None.
    """

    def __init__(self, state: ChatState, logger: Optional[logging.Logger] = None):
        self.state = state
        self.logger = logger or logging.getLogger(__name__)

    def modify_assistant_message(
        self,
        text: str,
        message_id: Optional[str] = None,
        # TODO add type for references
        references: Optional[list] = [],
        debug_info: Optional[dict] = {},
    ) -> None:
        """
        Modifies a message in the chat session synchronously.

        Args:
            text (str): The new text for the message.
            message_id (Optional[str]): The message ID. Defaults to None.
            references (Optional[list[dict[str, Any]]], optional): list of references. Defaults to [].
            debug_info (Optional[dict[str, Any]]], optional): Debug information. Defaults to {}.
        """
        self._trigger_modify_assistant_message(text, message_id, references, debug_info)

    @to_async
    @async_warning
    def async_modify_assistant_message(
        self,
        text: str,
        message_id: Optional[str] = None,
        references: Optional[list] = [],
        debug_info: Optional[dict] = {},
    ) -> None:
        """
        Modifies a message in the chat session asynchronously.

        Args:
            text (str): The new text for the message.
            message_id (str, optional): The message ID. Defaults to None, then the ChatState assistant message id is used.
            references (Optional[list[dict[str, Any]]], optional): list of references. Defaults to None.
            debug_info (Optional[dict[str, Any]]], optional): Debug information. Defaults to None.
        """
        self._trigger_modify_assistant_message(
            text,
            message_id,
            references,
            debug_info,
        )

    def get_history(
        self,
        token_limit: int,
        percent_of_max_tokens: float,
        max_messages: int,
    ):
        """
        Loads the chat history for the chat session synchronously.

        Args:
            token_limit (int): The maximum number of tokens to load.
            percent_of_max_tokens (float): The percentage of the maximum tokens to load.
            max_messages (int): The maximum number of messages to load.

        Returns:
            list[dict[str, Any]]: The chat history.
        """
        return self._trigger_load_history(
            token_limit,
            percent_of_max_tokens,
            max_messages,
        )

    @to_async
    @async_warning
    def async_get_history(
        self,
        token_limit: int,
        percent_of_max_tokens: float,
        max_messages: int,
    ):
        """
        Loads the chat history for the chat session asynchronously.

        Args:
            token_limit (int): The maximum number of tokens to load.
            percent_of_max_tokens (float): The percentage of the maximum tokens to load.
            max_messages (int): The maximum number of messages to load.

        Returns:
            list[dict[str, Any]]: The chat history.
        """
        return self._trigger_load_history(
            token_limit,
            percent_of_max_tokens,
            max_messages,
        )

    def create_assistant_message(
        self,
        text: str,
        references: Optional[list] = [],
        debug_info: Optional[dict] = {},
    ):
        """
        Creates a message in the chat session synchronously.

        Args:
            text (str): The text for the message.
            references (Optional[list[dict[str, Any]]], optional): list of references. Defaults to None.
            debug_info (Optional[dict[str, Any]]], optional): Debug information. Defaults to None.
        """
        return self._trigger_create_assistant_message(
            text,
            references,
            debug_info,
        )

    @to_async
    @async_warning
    def async_create_assistant_message(
        self,
        text: str,
        references: Optional[list] = [],
        debug_info: Optional[dict] = {},
    ):
        """
        Creates a message in the chat session asynchronously.

        Args:
            text (str): The text for the message.
            references (Optional[list[dict[str, Any]]], optional): list of references. Defaults to None.
            debug_info (Optional[dict[str, Any]]], optional): Debug information. Defaults to None.
        """
        return self._trigger_create_assistant_message(
            text,
            references,
            debug_info,
        )

    def _trigger_modify_assistant_message(
        self,
        text: str,
        message_id: Optional[str],
        references: list,
        debug_info: dict,
    ) -> None:
        message_id = message_id or self.state.assistant_message_id
        unique_sdk.Message.modify(
            user_id=self.state.user_id,
            company_id=self.state.company_id,
            id=self.state.assistant_message_id,
            chatId=self.state.chat_id,
            text=text,
            references=references or [],
            debugInfo=debug_info or {},
        )

    def _trigger_load_history(
        self,
        token_limit: int,
        percent_of_max_tokens: float,
        max_messages: int,
    ) -> tuple[list[ChatMessage], list[ChatMessage]]:
        return load_history(
            self.state.user_id,
            self.state.company_id,
            self.state.chat_id,
            token_limit,
            percent_of_max_tokens,
            max_messages,
        )

    def _trigger_create_assistant_message(
        self,
        text: str,
        references: list,
        debug_info: dict,
    ) -> ChatMessage:
        return unique_sdk.Message.create(
            user_id=self.state.user_id,
            company_id=self.state.company_id,
            chatId=self.state.chat_id,
            assistantId=self.state.assistant_id,
            text=text,
            role=ChatMessageRole.name,
            references=references,
            debugInfo=debug_info,
        )
