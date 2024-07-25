import logging
from typing import Optional, cast

import unique_sdk

from unique_toolkit.app.performance.async_wrapper import async_warning, to_async
from unique_toolkit.chat.state import ChatState
from unique_toolkit.content.schemas import ContentChunk
from unique_toolkit.language_model.infos import LanguageModelName
from unique_toolkit.language_model.schemas import (
    LanguageModelMessages,
    LanguageModelResponse,
    LanguageModelStreamResponse,
    LanguageModelTool,
)


class LanguageModelService:
    def __init__(self, state: ChatState, logger: Optional[logging.Logger] = None):
        self.state = state
        self.logger = logger or logging.getLogger(__name__)

    _DEFAULT_COMPLETE_TIMEOUT = 240_000
    _DEFAULT_COMPLETE_TEMPERATURE = 0.0

    def complete(
        self,
        messages: LanguageModelMessages,
        model_name: LanguageModelName,
        temperature: float = _DEFAULT_COMPLETE_TEMPERATURE,
        timeout: int = _DEFAULT_COMPLETE_TIMEOUT,
        tools: Optional[list[LanguageModelTool]] = None,
    ):
        """
        Calls the completion endpoint synchronously without streaming the response.

        Args:
            messages (LanguageModelMessages): The LanguageModelMessages obj to complete.
            model_name (LanguageModelName): The model name.
            temperature (float): The temperature value. Defaults to 0.
            timeout (int): The timeout value in milliseconds. Defaults to 240_000.
            tools (Optional[list[LanguageModelTool]]): The tools to use. Defaults to None.

        Returns:
            LanguageModelResponse: The LanguageModelResponse object.
        """
        return self._trigger_complete(
            messages=messages,
            model_name=model_name,
            temperature=temperature,
            timeout=timeout,
            tools=tools,
        )

    @to_async
    @async_warning
    def async_complete(
        self,
        messages: LanguageModelMessages,
        model_name: LanguageModelName,
        temperature: float = _DEFAULT_COMPLETE_TEMPERATURE,
        timeout: int = _DEFAULT_COMPLETE_TIMEOUT,
        tools: Optional[list[LanguageModelTool]] = None,
    ):
        """
        Calls the completion endpoint asynchronously without streaming the response.

        Args:
            messages (LanguageModelMessages): The messages to complete.
            model_name (LanguageModelName): The model name.
            temperature (float): The temperature value. Defaults to 0.
            timeout (int): The timeout value in milliseconds. Defaults to 240_000.
            tools (Optional[list[LanguageModelTool]]): The tools to use. Defaults to None.

        Returns:
            str: The completed message content.
        """
        return self._trigger_complete(
            messages=messages,
            model_name=model_name,
            temperature=temperature,
            timeout=timeout,
            tools=tools,
        )

    def _trigger_complete(
        self,
        messages: LanguageModelMessages,
        model_name: LanguageModelName,
        temperature: float,
        timeout: int,
        tools: Optional[list[LanguageModelTool]] = None,
    ) -> LanguageModelResponse:
        options = self._add_tools_to_options({}, tools)
        messages = messages.model_dump(exclude_none=True)
        try:
            response = unique_sdk.ChatCompletion.create(
                company_id=self.state.company_id,
                # TODO change or extend types in unique_sdk
                model=model_name.name,  # type: ignore
                messages=cast(
                    list[unique_sdk.Integrated.ChatCompletionRequestMessage],
                    messages,
                ),
                timeout=timeout,
                temperature=temperature,
                options=options,  # type: ignore
            )
        except Exception as e:
            self.logger.error(f"Error completing: {e}")
            raise e

        return LanguageModelResponse(**response)

    def stream_complete(
        self,
        messages: LanguageModelMessages,
        model_name: LanguageModelName,
        content_chunks: list[ContentChunk] = [],
        debug_info: dict = {},
        temperature: float = _DEFAULT_COMPLETE_TEMPERATURE,
        timeout: int = _DEFAULT_COMPLETE_TIMEOUT,
        tools: Optional[list[LanguageModelTool]] = None,
        start_text: Optional[str] = None,
    ):
        """
        Streams a completion in the chat session synchronously.

        Args:
            messages (LanguageModelMessages): The LanguageModelMessages object to stream.
            content_chunks (list[ContentChunk]): The ContentChunks objects.
            model_name (LanguageModelName): The language model to use for the completion.
            debug_info (dict): The debug information. Defaults to {}.
            temperature (float): The temperature value. Defaults to 0.25.
            timeout (int): The timeout value in milliseconds. Defaults to 240_000.
            tools (Optional[list[LanguageModelTool]]): The tools to use. Defaults to None.
            start_text (Optional[str]): The start text. Defaults to None.

        Returns:
            The LanguageModelStreamResponse object once the stream has finished.
        """
        return self._trigger_stream_complete(
            messages=messages,
            content_chunks=content_chunks,
            model_name=model_name,
            debug_info=debug_info,
            timeout=timeout,
            temperature=temperature,
            tools=tools,
            start_text=start_text,
        )

    @to_async
    @async_warning
    def async_stream_complete(
        self,
        messages: LanguageModelMessages,
        model_name: LanguageModelName,
        content_chunks: list[ContentChunk] = [],
        debug_info: dict = {},
        temperature: float = _DEFAULT_COMPLETE_TEMPERATURE,
        timeout: int = _DEFAULT_COMPLETE_TIMEOUT,
        tools: Optional[list[LanguageModelTool]] = None,
        start_text: Optional[str] = None,
    ):
        """
        Streams a completion in the chat session asynchronously.

        Args:
            messages (LanguageModelMessages): The LanguageModelMessages object to stream.
            content_chunks (list[ContentChunk]): The content chunks.
            model_name (LanguageModelName): The language model to use for the completion.
            debug_info (dict): The debug information. Defaults to {}.
            temperature (float): The temperature value. Defaults to 0.25.
            timeout (int): The timeout value in milliseconds. Defaults to 240_000.
            tools (Optional[list[LanguageModelTool]]): The tools to use. Defaults to None.
            start_text (Optional[str]): The start text. Defaults to None.

        Returns:
            The LanguageModelStreamResponse object once the stream has finished.
        """
        return self._trigger_stream_complete(
            messages=messages,
            content_chunks=content_chunks,
            model_name=model_name,
            debug_info=debug_info,
            timeout=timeout,
            temperature=temperature,
            tools=tools,
            start_text=start_text,
        )

    def _trigger_stream_complete(
        self,
        messages: LanguageModelMessages,
        model_name: LanguageModelName,
        content_chunks: list[ContentChunk],
        debug_info: dict,
        timeout: int,
        temperature: float,
        tools: Optional[list[LanguageModelTool]] = None,
        start_text: Optional[str] = None,
    ) -> LanguageModelStreamResponse:
        options = self._add_tools_to_options({}, tools)
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
            )  # type: ignore
            for chunk in content_chunks
        ]

        messages = messages.model_dump(exclude_none=True)

        try:
            response = unique_sdk.Integrated.chat_stream_completion(
                user_id=self.state.user_id,
                company_id=self.state.company_id,
                assistantMessageId=self.state.assistant_message_id,  # type: ignore
                userMessageId=self.state.user_message_id,  # type: ignore
                messages=cast(
                    list[unique_sdk.Integrated.ChatCompletionRequestMessage],
                    messages,
                ),
                chatId=self.state.chat_id,
                searchContext=search_context,
                # TODO change or extend types in unique_sdk
                model=model_name.name,  # type: ignore
                timeout=timeout,
                temperature=temperature,
                assistantId=self.state.assistant_id,
                debugInfo=debug_info,
                options=options,  # type: ignore
                startText=start_text,
            )
        except Exception as e:
            self.logger.error(f"Error streaming completion: {e}")
            raise e

        return LanguageModelStreamResponse(**response)

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
