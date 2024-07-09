import unique_sdk
from unique_sdk.utils.chat_history import load_history

from unique_toolkit.performance.async_wrapper import to_async

from .state import ChatState


class ChatService:
    """
    Provides all functionalities to manage the chat session.

    Attributes:
        state (ChatState): The chat state.
    """

    def __init__(self, state: ChatState):
        self.state = state

    def modify_assistant_message(
        self,
        *,
        text: str,
        references: list = [],
        debug_info: dict = {},
    ) -> None:
        """
        Modifies a message in the chat session synchronously.

        Args:
            text (str): The new text for the message.
            references (Optional[list[dict[str, Any]]], optional): list of references. Defaults to None.
            debug_info (Optional[dict[str, Any]]], optional): Debug information. Defaults to None.
        """
        self._trigger_modify_assistant_message(text, references, debug_info)

    @to_async
    def async_modify_assistant_message(
        self,
        *,
        text: str,
        references: list = [],
        debug_info: dict = {},
    ) -> None:
        """
        Modifies a message in the chat session asynchronously.

        Args:
            text (str): The new text for the message.
            references (Optional[list[dict[str, Any]]], optional): list of references. Defaults to None.
            debug_info (Optional[dict[str, Any]]], optional): Debug information. Defaults to None.
        """
        self._trigger_modify_assistant_message(text, references, debug_info)

    def get_history(
        self,
        *,
        max_tokens: int,
        percent_of_max_tokens: float,
        max_messages: int,
    ):
        """
        Loads the chat history for the chat session synchronously.

        Args:
            max_tokens (int): The maximum number of tokens to load.
            percent_of_max_tokens (float): The percentage of the maximum tokens to load.
            max_messages (int): The maximum number of messages to load.

        Returns:
            list[dict[str, Any]]: The chat history.
        """
        return self._trigger_load_history(
            max_tokens, percent_of_max_tokens, max_messages
        )

    @to_async
    def async_get_history(
        self,
        *,
        max_tokens: int,
        percent_of_max_tokens: float,
        max_messages: int,
    ):
        """
        Loads the chat history for the chat session asynchronously.

        Args:
            max_tokens (int): The maximum number of tokens to load.
            percent_of_max_tokens (float): The percentage of the maximum tokens to load.
            max_messages (int): The maximum number of messages to load.

        Returns:
            list[dict[str, Any]]: The chat history.
        """
        return self._trigger_load_history(
            max_tokens, percent_of_max_tokens, max_messages
        )

    def create_assistant_message(
        self,
        *,
        text: str,
        references: list = [],
        debug_info: dict = {},
    ):
        """
        Creates a message in the chat session synchronously.

        Args:
            text (str): The text for the message.
            references (Optional[list[dict[str, Any]]], optional): list of references. Defaults to None.
            debug_info (Optional[dict[str, Any]]], optional): Debug information. Defaults to None.
        """
        return self._trigger_create_assistant_message(text, references, debug_info)

    @to_async
    def async_create_assistant_message(
        self,
        *,
        text: str,
        references: list = [],
        debug_info: dict = {},
    ):
        """
        Creates a message in the chat session asynchronously.

        Args:
            text (str): The text for the message.
            references (Optional[list[dict[str, Any]]], optional): list of references. Defaults to None.
            debug_info (Optional[dict[str, Any]]], optional): Debug information. Defaults to None.
        """
        return self._trigger_create_assistant_message(text, references, debug_info)

    def _trigger_modify_assistant_message(
        self,
        text: str,
        references: list = [],
        debug_info: dict = {},
    ) -> None:
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
        max_tokens: int,
        percent_of_max_tokens: float,
        max_messages: int,
    ):
        return load_history(
            self.state.user_id,
            self.state.company_id,
            self.state.chat_id,
            max_tokens,
            percent_of_max_tokens,
            max_messages,
        )

    # TODO throws error at the moment
    def _trigger_create_assistant_message(
        self,
        text: str,
        references: list = [],
        debug_info: dict = {},
    ):
        return unique_sdk.Message.create(
            user_id=self.state.user_id,
            company_id=self.state.company_id,
            chatId=self.state.chat_id,
            assistantId=self.state.assistant_id,
            text=text,
            role="ASSISTANT",
            references=references,
            debugInfo=debug_info,
        )
