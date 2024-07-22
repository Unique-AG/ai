import logging
from typing import Optional

import unique_sdk

from unique_toolkit.chat.state import ChatState
from unique_toolkit.content.schemas import ContentChunk
from unique_toolkit.language_model.infos import LanguageModelName
from unique_toolkit.language_model.schemas import (
    LanguageModelMessages,
    LanguageModelResponse,
)
from unique_toolkit.performance.async_wrapper import async_warning, to_async


class LanguageModelService:
    def __init__(self, state: ChatState, logger: Optional[logging.Logger] = None):
        self.state = state
        self.logger = logger or logging.getLogger(__name__)

    _DEFAULT_COMPLETE_TIMEOUT = 240000
    _DEFAULT_COMPLETE_STREAM_TIMEOUT = 100000
    _DEFAULT_COMPLETE_TEMPERATURE = 0.0
    _DEFAULT_COMPLETE_STREAM_TEMPERATURE = 0.25

    def complete(
        self,
        messages: LanguageModelMessages,
        model_name: LanguageModelName,
        temperature: Optional[float] = _DEFAULT_COMPLETE_TEMPERATURE,
        timeout: Optional[int] = _DEFAULT_COMPLETE_TIMEOUT,
    ):
        """
        Calls the completion endpoint synchronously without streaming the response.

        Args:
            messages (list[dict[str, str]]): The messages to complete.
            model_name (LanguageModelName): The model name.
            temperature (Optional[float]): The temperature value. Defaults to 0.
            timeout (Optional[int]): The timeout value in milliseconds. Defaults to 240000.

        Returns:
            LanguageModelResponse: The LanguageModelResponse object.
        """
        return self._trigger_complete(messages, model_name, temperature, timeout)

    @to_async
    @async_warning
    def async_complete(
        self,
        messages: LanguageModelMessages,
        model_name: LanguageModelName,
        temperature: Optional[float] = _DEFAULT_COMPLETE_TEMPERATURE,
        timeout: Optional[int] = _DEFAULT_COMPLETE_TIMEOUT,
    ):
        """
        Calls the completion endpoint asynchronously without streaming the response.

        Args:
            messages (list[LanugageModelMessage]): The messages to complete.
            model_name (LanguageModelName): The model name.
            temperature (Optional[float]): The temperature value. Defaults to 0.
            timeout (Optional[int]): The timeout value in milliseconds. Defaults to 240000.

        Returns:
            str: The completed message content.
        """
        return self._trigger_complete(
            messages,
            model_name,
            temperature,
            timeout,
        )

    def _trigger_complete(
        self,
        messages: LanguageModelMessages,
        model_name: LanguageModelName,
        temperature: float,
        timeout: int,
    ) -> LanguageModelResponse:
        result = unique_sdk.ChatCompletion.create(
            company_id=self.state.company_id,
            model=model_name.name,
            messages=messages.model_dump_json(exclude_none=True),
            timeout=timeout,
            temperature=temperature,
        )
        return LanguageModelResponse(**result)

    def stream_complete(
        self,
        messages: LanguageModelMessages,
        model_name: LanguageModelName,
        content_chunks: list[ContentChunk],
        debug_info: Optional[dict] = {},
        temperature: Optional[float] = _DEFAULT_COMPLETE_STREAM_TEMPERATURE,
        timeout: Optional[int] = _DEFAULT_COMPLETE_STREAM_TIMEOUT,
    ):
        """
        Streams a completion in the chat session synchronously.

        Args:
            messages (LanguageModelMessages): The LanguageModelMessages object to stream.
            content_chunks (list[ContentChunk]): The ContentChunks objects.
            model_name (LanguageModelName): The language model to use for the completion.
            debug_info (Optional[dict]): The debug information. Defaults to {}.
            temperature (Optional[float]): The temperature value. Defaults to 0.25.
            timeout (Optional[int]): The timeout value in milliseconds. Defaults to 100_000.

        Returns:
            A generator yielding streamed completion chunks.
        """
        return self._trigger_stream_complete(
            messages,
            content_chunks,
            model_name,
            debug_info,
            timeout,
            temperature,
        )

    @to_async
    @async_warning
    def async_stream_complete(
        self,
        messages: LanguageModelMessages,
        model_name: LanguageModelName,
        content_chunks: list[ContentChunk],
        debug_info: Optional[dict] = {},
        temperature: Optional[float] = _DEFAULT_COMPLETE_STREAM_TEMPERATURE,
        timeout: Optional[int] = _DEFAULT_COMPLETE_STREAM_TIMEOUT,
    ):
        """
        Streams a completion in the chat session asynchronously.

        Args:
            messages (LanguageModelMessages): The LanguageModelMessages object to stream.
            content_chunks (list[ContentChunk]): The content chunks.
            model_name (LanguageModelName): The language model to use for the completion.
            debug_info (Optional[dict]): The debug information. Defaults to {}.
            temperature (Optional[float]): The temperature value. Defaults to 0.25.
            timeout (Optional[int]): The timeout value in milliseconds. Defaults to 100_000.

        Returns:
            A generator yielding streamed completion chunks.
        """
        return self._trigger_stream_complete(
            messages,
            content_chunks,
            model_name,
            debug_info,
            timeout,
            temperature,
        )

    def _trigger_stream_complete(
        self,
        messages: LanguageModelMessages,
        model_name: LanguageModelName,
        content_chunks: list[ContentChunk],
        debug_info: dict,
        timeout: int,
        temperature: float,
    ):
        search_context = [
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
            )
            for chunk in content_chunks
        ]

        return unique_sdk.Integrated.chat_stream_completion(
            user_id=self.state.user_id,
            company_id=self.state.company_id,
            assistantMessageId=self.state.assistant_message_id,
            userMessageId=self.state.user_message_id,
            messages=messages.model_dump_json(exclude_none=True),
            chatId=self.state.chat_id,
            searchContext=search_context,
            model=model_name.name,
            timeout=timeout,
            temperature=temperature,
            assistantId=self.state.assistant_id,
            debugInfo=debug_info,
        )
