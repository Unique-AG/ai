import logging
from typing import Optional

from typing_extensions import deprecated

from unique_toolkit._common.validate_required_values import validate_required_values
from unique_toolkit.app.schemas import ChatEvent, Event, MagicTableEvent
from unique_toolkit.content.schemas import ContentChunk
from unique_toolkit.language_model import DOMAIN_NAME
from unique_toolkit.language_model.constants import (
    DEFAULT_COMPLETE_TEMPERATURE,
    DEFAULT_COMPLETE_TIMEOUT,
)
from unique_toolkit.language_model.functions import (
    complete,
    complete_async,
    stream_complete,
    stream_complete_async,
)
from unique_toolkit.language_model.infos import LanguageModelName
from unique_toolkit.language_model.schemas import (
    LanguageModelMessages,
    LanguageModelResponse,
    LanguageModelStreamResponse,
    LanguageModelTool,
)

logger = logging.getLogger(f"toolkit.{DOMAIN_NAME}.{__name__}")


class LanguageModelService:
    """
    Provides methods to interact with the Language Model by generating responses.

    Attributes:
        company_id (str): The company ID.
        user_id (Optional[str]): The user ID.
        assistant_message_id (Optional[str]): The assistant message ID.
        user_message_id (Optional[str]): The user message ID.
        chat_id (Optional[str]): The chat ID.
        assistant_id (Optional[str]): The assistant ID.
    """

    def __init__(
        self,
        company_id: str,
        user_id: Optional[str] = None,
        assistant_message_id: Optional[str] = None,
        user_message_id: Optional[str] = None,
        chat_id: Optional[str] = None,
        assistant_id: Optional[str] = None,
    ):
        self.company_id = company_id
        self.user_id = user_id
        self.assistant_message_id = assistant_message_id
        self.user_message_id = user_message_id
        self.chat_id = chat_id
        self.assistant_id = assistant_id

    @deprecated(
        "Use `from_chat_event` or `from_magic_table_event` instead. This method will be removed in the next major version."
    )
    @classmethod
    def from_event(cls, event: Event) -> "LanguageModelService":
        """
        Creates a LanguageModelService instance from an event.

        Args:
            event (Event): The chat event containing necessary information.

        Returns:
            LanguageModelService: A new instance initialized with event data.
        """
        return cls(
            company_id=event.company_id,
            user_id=event.user_id,
            assistant_message_id=event.payload.assistant_message.id,
            user_message_id=event.payload.user_message.id,
            chat_id=event.payload.chat_id,
            assistant_id=event.payload.assistant_id,
        )

    @classmethod
    def from_chat_event(cls, event: ChatEvent) -> "LanguageModelService":
        """
        Creates a LanguageModelService instance from a chat event.

        Args:
            event (Event): The chat event containing necessary information.

        Returns:
            LanguageModelService: A new instance initialized with event data.
        """
        return cls(
            company_id=event.company_id,
            user_id=event.user_id,
            assistant_message_id=event.payload.assistant_message.id,
            user_message_id=event.payload.user_message.id,
            chat_id=event.payload.chat_id,
            assistant_id=event.payload.assistant_id,
        )

    @classmethod
    def from_magic_table_event(cls, event: MagicTableEvent) -> "LanguageModelService":
        return cls(
            company_id=event.company_id,
            user_id=event.user_id,
        )

    @classmethod
    def from_properties(
        cls,
        company_id: str,
        user_id: Optional[str] = None,
        assistant_message_id: Optional[str] = None,
        user_message_id: Optional[str] = None,
        chat_id: Optional[str] = None,
        assistant_id: Optional[str] = None,
    ) -> "LanguageModelService":
        return cls(
            company_id=company_id,
            user_id=user_id,
            assistant_message_id=assistant_message_id,
            user_message_id=user_message_id,
            chat_id=chat_id,
            assistant_id=assistant_id,
        )

    def complete(
        self,
        messages: LanguageModelMessages,
        model_name: LanguageModelName | str,
        temperature: float = DEFAULT_COMPLETE_TEMPERATURE,
        timeout: int = DEFAULT_COMPLETE_TIMEOUT,
        tools: Optional[list[LanguageModelTool]] = None,
        other_options: Optional[dict] = None,
    ) -> LanguageModelResponse:
        """
        Calls the completion endpoint synchronously without streaming the response.
        """
        [company_id] = validate_required_values([self.company_id])

        return complete(
            company_id=company_id,
            messages=messages,
            model_name=model_name,
            temperature=temperature,
            timeout=timeout,
            tools=tools,
            other_options=other_options,
        )

    async def complete_async(
        self,
        messages: LanguageModelMessages,
        model_name: LanguageModelName | str,
        temperature: float = DEFAULT_COMPLETE_TEMPERATURE,
        timeout: int = DEFAULT_COMPLETE_TIMEOUT,
        tools: Optional[list[LanguageModelTool]] = None,
        other_options: Optional[dict] = None,
    ) -> LanguageModelResponse:
        """
        Calls the completion endpoint asynchronously without streaming the response.
        """
        [company_id] = validate_required_values([self.company_id])

        return await complete_async(
            company_id=company_id,
            messages=messages,
            model_name=model_name,
            temperature=temperature,
            timeout=timeout,
            tools=tools,
            other_options=other_options,
        )

    def stream_complete(
        self,
        messages: LanguageModelMessages,
        model_name: LanguageModelName | str,
        content_chunks: list[ContentChunk] = [],
        debug_info: dict = {},
        temperature: float = DEFAULT_COMPLETE_TEMPERATURE,
        timeout: int = DEFAULT_COMPLETE_TIMEOUT,
        tools: Optional[list[LanguageModelTool]] = None,
        start_text: Optional[str] = None,
        other_options: Optional[dict] = None,
    ) -> LanguageModelStreamResponse:
        """
        Streams a completion in the chat session synchronously.
        """
        [
            company_id,
            user_id,
            assistant_message_id,
            user_message_id,
            chat_id,
            assistant_id,
        ] = validate_required_values(
            [
                self.company_id,
                self.user_id,
                self.assistant_message_id,
                self.user_message_id,
                self.chat_id,
                self.assistant_id,
            ]
        )

        return stream_complete(
            company_id=company_id,
            user_id=user_id,
            assistant_message_id=assistant_message_id,
            user_message_id=user_message_id,
            chat_id=chat_id,
            assistant_id=assistant_id,
            messages=messages,
            model_name=model_name,
            content_chunks=content_chunks,
            debug_info=debug_info,
            temperature=temperature,
            timeout=timeout,
            tools=tools,
            start_text=start_text,
            other_options=other_options,
        )

    async def stream_complete_async(
        self,
        messages: LanguageModelMessages,
        model_name: LanguageModelName | str,
        content_chunks: list[ContentChunk] = [],
        debug_info: dict = {},
        temperature: float = DEFAULT_COMPLETE_TEMPERATURE,
        timeout: int = DEFAULT_COMPLETE_TIMEOUT,
        tools: Optional[list[LanguageModelTool]] = None,
        start_text: Optional[str] = None,
        other_options: Optional[dict] = None,
    ) -> LanguageModelStreamResponse:
        """
        Streams a completion in the chat session asynchronously.
        """

        [
            company_id,
            user_id,
            assistant_message_id,
            user_message_id,
            chat_id,
            assistant_id,
        ] = validate_required_values(
            [
                self.company_id,
                self.user_id,
                self.assistant_message_id,
                self.user_message_id,
                self.chat_id,
                self.assistant_id,
            ]
        )

        return await stream_complete_async(
            company_id=company_id,
            user_id=user_id,
            assistant_message_id=assistant_message_id,
            user_message_id=user_message_id,
            chat_id=chat_id,
            assistant_id=assistant_id,
            messages=messages,
            model_name=model_name,
            content_chunks=content_chunks,
            debug_info=debug_info,
            temperature=temperature,
            timeout=timeout,
            tools=tools,
            start_text=start_text,
            other_options=other_options,
        )
