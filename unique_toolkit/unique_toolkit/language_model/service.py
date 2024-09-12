import logging
from typing import Optional, cast

import unique_sdk

from unique_toolkit._common._base_service import BaseService
from unique_toolkit.app.schemas import Event
from unique_toolkit.content.schemas import ContentChunk
from unique_toolkit.language_model.infos import LanguageModelName
from unique_toolkit.language_model.schemas import (
    LanguageModelMessages,
    LanguageModelResponse,
    LanguageModelStreamResponse,
    LanguageModelTool,
)


class LanguageModelService(BaseService):
    """
    Provides methods to interact with the Language Model by generating responses.

    Attributes:
        event (Event): The Event object.
        logger (Optional[logging.Logger]): The logger object. Defaults to None.
    """

    def __init__(self, event: Event, logger: Optional[logging.Logger] = None):
        super().__init__(event, logger)

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
        options = self._add_tools_to_options({}, tools)
        messages = messages.model_dump(exclude_none=True)
        model = (
            model_name.name if isinstance(model_name, LanguageModelName) else model_name
        )

        try:
            response = unique_sdk.ChatCompletion.create(
                company_id=self.event.company_id,
                # TODO change or extend types in unique_sdk
                model=model,
                messages=cast(
                    list[unique_sdk.Integrated.ChatCompletionRequestMessage],
                    messages,
                ),
                timeout=timeout,
                temperature=temperature,
                options=options,  # type: ignore
            )
            return LanguageModelResponse(**response)
        except Exception as e:
            self.logger.error(f"Error completing: {e}")
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
        logger: Optional[logging.Logger] = logging.getLogger(__name__),
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
            logger (Optional[logging.Logger], optional): The logger used to log errors. Defaults to the logger for the current module.

        Returns:
            LanguageModelResponse: The response object containing the completed result.

        Raises:
            Exception: If an error occurs during the request, an exception is raised and logged.
        """
        options = cls._add_tools_to_options({}, tools)
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
                temperature=temperature,
                options=options,  # type: ignore
            )
            return LanguageModelResponse(**response)
        except Exception as e:
            logger.error(f"Error completing: {e}")
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
            company_id=self.event.company_id,
            messages=messages,
            model_name=model_name,
            temperature=temperature,
            timeout=timeout,
            tools=tools,
            logger=self.logger,
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
        options = self._add_tools_to_options({}, tools)
        search_context = self._to_search_context(content_chunks)
        messages = messages.model_dump(exclude_none=True)
        model = (
            model_name.name if isinstance(model_name, LanguageModelName) else model_name
        )

        try:
            response = unique_sdk.Integrated.chat_stream_completion(
                user_id=self.event.user_id,
                company_id=self.event.company_id,
                assistantMessageId=self.event.payload.assistant_message.id,
                userMessageId=self.event.payload.user_message.id,
                messages=cast(
                    list[unique_sdk.Integrated.ChatCompletionRequestMessage],
                    messages,
                ),
                chatId=self.event.payload.chat_id,
                searchContext=search_context,
                # TODO change or extend types in unique_sdk
                model=model,
                timeout=timeout,
                temperature=temperature,
                assistantId=self.event.payload.assistant_id,
                debugInfo=debug_info,
                options=options,  # type: ignore
                startText=start_text,
            )
            return LanguageModelStreamResponse(**response)
        except Exception as e:
            self.logger.error(f"Error streaming completion: {e}")
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

        options = self._add_tools_to_options({}, tools)
        search_context = self._to_search_context(content_chunks)
        messages = messages.model_dump(exclude_none=True, exclude=["tool_calls"])
        model = (
            model_name.name if isinstance(model_name, LanguageModelName) else model_name
        )

        try:
            response = await unique_sdk.Integrated.chat_stream_completion_async(
                user_id=self.event.user_id,
                company_id=self.event.company_id,
                assistantMessageId=self.event.payload.assistant_message.id,
                userMessageId=self.event.payload.user_message.id,
                messages=cast(
                    list[unique_sdk.Integrated.ChatCompletionRequestMessage],
                    messages,
                ),
                chatId=self.event.payload.chat_id,
                searchContext=search_context,
                model=model,
                timeout=timeout,
                temperature=temperature,
                assistantId=self.event.payload.assistant_id,
                debugInfo=debug_info,
                # TODO change or extend types in unique_sdk
                options=options,  # type: ignore
                startText=start_text,
            )
            return LanguageModelStreamResponse(**response)
        except Exception as e:
            self.logger.error(f"Error streaming completion: {e}")
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
