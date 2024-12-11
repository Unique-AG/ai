import logging
from typing import Optional, cast

import unique_sdk

from unique_toolkit._common.validators import validate_required_parameters
from unique_toolkit.app.schemas import ChatEvent, MagicTableEvent
from unique_toolkit.content.schemas import ContentChunk
from unique_toolkit.language_model.infos import LanguageModelName
from unique_toolkit.language_model.schemas import (
    LanguageModelMessages,
    LanguageModelResponse,
    LanguageModelStreamResponse,
    LanguageModelTool,
)

logger = logging.getLogger(f"toolkit.{__name__}")


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

    DEFAULT_COMPLETE_TIMEOUT = 240_000
    DEFAULT_COMPLETE_TEMPERATURE = 0.0

    def complete(
        self,
        messages: LanguageModelMessages,
        model_name: LanguageModelName | str,
        temperature: float = DEFAULT_COMPLETE_TEMPERATURE,
        timeout: int = DEFAULT_COMPLETE_TIMEOUT,
        tools: Optional[list[LanguageModelTool]] = None,
    ):
        """
        Calls the completion endpoint synchronously without streaming the response.

        Args:
            messages (LanguageModelMessages): The LanguageModelMessages obj to complete.
            model_name (LanguageModelName | str): The model name.
            temperature (float): The temperature value. Defaults to 0.
            timeout (int): The timeout value in milliseconds. Defaults to 240_000.
            tools (Optional[list[LanguageModelTool]]): The tools to use. Defaults to None.

        Returns:
            LanguageModelResponse: The LanguageModelResponse object.
        """
        validate_required_parameters({"company_id": self.company_id})

        options = self._add_tools_to_options({}, tools)
        options["temperature"] = temperature
        messages = messages.model_dump(exclude_none=True)
        model = (
            model_name.name if isinstance(model_name, LanguageModelName) else model_name
        )

        try:
            response = unique_sdk.ChatCompletion.create(
                company_id=self.company_id,
                model=model,
                messages=cast(
                    list[unique_sdk.Integrated.ChatCompletionRequestMessage],
                    messages,
                ),
                timeout=timeout,
                options=options,  # type: ignore
            )
            return LanguageModelResponse(**response)
        except Exception as e:
            logger.error(f"Error completing: {e}")
            raise e

    @classmethod
    async def complete_async_util(
        cls,
        company_id: str,
        messages: LanguageModelMessages,
        model_name: LanguageModelName | str,
        temperature: float = DEFAULT_COMPLETE_TEMPERATURE,
        timeout: int = DEFAULT_COMPLETE_TIMEOUT,
        tools: Optional[list[LanguageModelTool]] = None,
    ) -> LanguageModelResponse:
        """
        Calls the completion endpoint asynchronously without streaming the response.

        This method sends a request to the completion endpoint using the provided messages, model name,
        temperature, timeout, and optional tools. It returns a `LanguageModelResponse` object containing
        the completed result.

        Args:
            company_id (str): The company ID associated with the request.
            messages (LanguageModelMessages): The messages to complete.
            model_name (LanguageModelName | str): The model name to use for the completion.
            temperature (float): The temperature setting for the completion. Defaults to 0.
            timeout (int): The timeout value in milliseconds for the request. Defaults to 240_000.
            tools (Optional[list[LanguageModelTool]]): Optional list of tools to include in the request.

        Returns:
            LanguageModelResponse: The response object containing the completed result.

        Raises:
            Exception: If an error occurs during the request, an exception is raised and logged.
        """
        options = cls._add_tools_to_options({}, tools)
        options["temperature"] = temperature
        messages = messages.model_dump(exclude_none=True, exclude={"tool_calls"})
        model = (
            model_name.name if isinstance(model_name, LanguageModelName) else model_name
        )
        try:
            response = await unique_sdk.ChatCompletion.create_async(
                company_id=company_id,
                model=model,
                messages=cast(
                    list[unique_sdk.Integrated.ChatCompletionRequestMessage],
                    messages,
                ),
                timeout=timeout,
                options=options,  # type: ignore
            )
            return LanguageModelResponse(**response)
        except Exception as e:
            logger.error(f"Error completing: {e}")  # type: ignore
            raise e

    async def complete_async(
        self,
        messages: LanguageModelMessages,
        model_name: LanguageModelName | str,
        temperature: float = DEFAULT_COMPLETE_TEMPERATURE,
        timeout: int = DEFAULT_COMPLETE_TIMEOUT,
        tools: Optional[list[LanguageModelTool]] = None,
    ) -> LanguageModelResponse:
        """
        Calls the completion endpoint asynchronously without streaming the response.

        This method utilizes the class method `complete_async_util` to perform the asynchronous completion
        request using the provided messages, model name, temperature, timeout, and optional tools. It
        returns a `LanguageModelResponse` object containing the result of the completion.

        Args:
            messages (LanguageModelMessages): The messages to complete.
            model_name (LanguageModelName | str): The model name to use for the completion.
            temperature (float): The temperature setting for the completion. Defaults to 0.0.
            timeout (int): The timeout value in milliseconds for the request. Defaults to 240,000.
            tools (Optional[list[LanguageModelTool]]): Optional list of tools to include in the request.

        Returns:
            LanguageModelResponse: The response object containing the completed result.

        Raises:
            Exception: If an error occurs during the completion request.
        """
        return await self.complete_async_util(
            company_id=self.company_id,
            messages=messages,
            model_name=model_name,
            temperature=temperature,
            timeout=timeout,
            tools=tools,
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
    ):
        """
        Streams a completion in the chat session synchronously.

        Args:
            messages (LanguageModelMessages): The LanguageModelMessages object to stream.
            content_chunks (list[ContentChunk]): The ContentChunks objects.
            model_name (LanguageModelName | str): The language model to use for the completion.
            debug_info (dict): The debug information. Defaults to {}.
            temperature (float): The temperature value. Defaults to 0.25.
            timeout (int): The timeout value in milliseconds. Defaults to 240_000.
            tools (Optional[list[LanguageModelTool]]): The tools to use. Defaults to None.
            start_text (Optional[str]): The start text. Defaults to None.

        Returns:
            The LanguageModelStreamResponse object once the stream has finished.
        """
        validate_required_parameters(
            {
                "company_id": self.company_id,
                "user_id": self.user_id,
                "assistant_message_id": self.assistant_message_id,
                "user_message_id": self.user_message_id,
                "chat_id": self.chat_id,
                "assistant_id": self.assistant_id,
            }
        )

        options = self._add_tools_to_options({}, tools)
        options["temperature"] = temperature
        search_context = self._to_search_context(content_chunks)
        messages = messages.model_dump(exclude_none=True, by_alias=True)
        model = (
            model_name.name if isinstance(model_name, LanguageModelName) else model_name
        )

        try:
            response = unique_sdk.Integrated.chat_stream_completion(
                user_id=self.user_id,
                company_id=self.company_id,
                assistantMessageId=self.assistant_message_id,
                userMessageId=self.user_message_id,
                messages=cast(
                    list[unique_sdk.Integrated.ChatCompletionRequestMessage],
                    messages,
                ),
                chatId=self.chat_id,
                searchContext=search_context,
                model=model,
                timeout=timeout,
                assistantId=self.assistant_id,
                debugInfo=debug_info,
                options=options,  # type: ignore
                startText=start_text,
            )
            return LanguageModelStreamResponse(**response)
        except Exception as e:
            logger.error(f"Error streaming completion: {e}")
            raise e

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
    ):
        """
        Streams a completion in the chat session asynchronously.

        Args:
            messages (LanguageModelMessages): The LanguageModelMessages object to stream.
            content_chunks (list[ContentChunk]): The content chunks.
            model_name (LanguageModelName | str): The language model to use for the completion.
            debug_info (dict): The debug information. Defaults to {}.
            temperature (float): The temperature value. Defaults to 0.25.
            timeout (int): The timeout value in milliseconds. Defaults to 240_000.
            tools (Optional[list[LanguageModelTool]]): The tools to use. Defaults to None.
            start_text (Optional[str]): The start text. Defaults to None.

        Returns:
            The LanguageModelStreamResponse object once the stream has finished.
        """
        validate_required_parameters(
            {
                "company_id": self.company_id,
                "user_id": self.user_id,
                "assistant_message_id": self.assistant_message_id,
                "user_message_id": self.user_message_id,
                "chat_id": self.chat_id,
                "assistant_id": self.assistant_id,
            }
        )

        options = self._add_tools_to_options({}, tools)
        options["temperature"] = temperature
        search_context = self._to_search_context(content_chunks)
        messages = messages.model_dump(exclude_none=True, by_alias=True)
        model = (
            model_name.name if isinstance(model_name, LanguageModelName) else model_name
        )

        try:
            response = await unique_sdk.Integrated.chat_stream_completion_async(
                user_id=self.user_id,
                company_id=self.company_id,
                assistantMessageId=self.assistant_message_id,
                userMessageId=self.user_message_id,
                messages=cast(
                    list[unique_sdk.Integrated.ChatCompletionRequestMessage],
                    messages,
                ),
                chatId=self.chat_id,
                searchContext=search_context,
                model=model,
                timeout=timeout,
                assistantId=self.assistant_id,
                debugInfo=debug_info,
                # TODO change or extend types in unique_sdk
                options=options,  # type: ignore
                startText=start_text,
            )
            return LanguageModelStreamResponse(**response)
        except Exception as e:
            logger.error(f"Error streaming completion: {e}")
            raise e

    @staticmethod
    def _to_search_context(chunks: list[ContentChunk]) -> dict | None:
        if not chunks:
            return None
        return [
            unique_sdk.Integrated.SearchResult(
                id=chunk.id,
                chunkId=chunk.chunk_id,
                key=chunk.key,
                title=chunk.title,
                url=chunk.url,
                startPage=chunk.start_page,
                endPage=chunk.end_page,
                order=chunk.order,
                object=chunk.object,
            )  # type: ignore
            for chunk in chunks
        ]

    @staticmethod
    def _add_tools_to_options(
        options: dict, tools: Optional[list[LanguageModelTool]]
    ) -> dict:
        if tools:
            options["tools"] = [
                {
                    "type": "function",
                    "function": tool.model_dump(exclude_none=True),
                }
                for tool in tools
            ]
        return options
