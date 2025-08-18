from datetime import datetime
from logging import Logger
from typing import Awaitable, Callable

from pydantic import BaseModel, Field

from unique_toolkit.app.schemas import ChatEvent


from unique_toolkit.chat.schemas import ChatMessage
from unique_toolkit.chat.service import ChatService
from unique_toolkit.content.schemas import Content
from unique_toolkit.content.service import ContentService
from unique_toolkit.language_model.builder import MessagesBuilder
from unique_toolkit.language_model.schemas import (
    LanguageModelAssistantMessage,
    LanguageModelFunction,
    LanguageModelMessage,
    LanguageModelMessageRole,
    LanguageModelToolMessage,
    LanguageModelUserMessage,
)

from unique_toolkit.tools.schemas import ToolCallResponse
from unique_toolkit.content.utils import count_tokens
from unique_toolkit.history_manager.utils import transform_chunks_to_string


class HistoryManagerConfig(BaseModel):
    """
    Manages the history of tool calls and conversation loops.

    This class is responsible for:
    - Storing and maintaining the history of tool call results and conversation messages.
    - Merging uploaded content with the conversation history for a unified view.
    - Limiting the history to fit within a configurable token window for efficient processing.
    - Providing methods to retrieve, manipulate, and append to the conversation history.
    - Handling post-processing steps to clean or modify the history as needed.

    Key Features:
    - Tool Call History: Tracks the results of tool calls and appends them to the conversation history.
    - Loop History: Maintains a record of conversation loops, including assistant and user messages.
    - History Merging: Combines uploaded files and chat messages into a cohesive history.
    - Token Window Management: Ensures the history stays within a specified token limit for optimal performance.
    - Post-Processing Support: Allows for custom transformations or cleanup of the conversation history.

    The HistoryManager serves as the backbone for managing and retrieving conversation history in a structured and efficient manner.
    """

    class ExperimentalFeatures(BaseModel):
        def __init__(self, full_sources_serialize_dump: bool = False):
            self.full_sources_serialize_dump = full_sources_serialize_dump

        full_sources_serialize_dump: bool = Field(
            default=False,
            description="If True, the sources will be serialized in full, otherwise only the content will be serialized.",
        )

    experimental_features: ExperimentalFeatures = Field(
        default=ExperimentalFeatures(),
        description="Experimental features for the history manager.",
    )

    max_history_tokens: int = Field(
        default=8000,
        ge=0,
        description="The maximum number of tokens to keep in the history.",
    )

    def __init__(
        self, full_sources_serialize_dump: bool = False, max_history_tokens: int = 8000
    ):
        self.experimental_features = HistoryManagerConfig.ExperimentalFeatures(
            full_sources_serialize_dump=full_sources_serialize_dump
        )
        self.max_history_tokens = max_history_tokens


class HistoryManager:
    _tool_call_result_history: list[ToolCallResponse] = []
    _loop_history: list[LanguageModelMessage] = []
    _source_enumerator = 0

    def __init__(
        self,
        logger: Logger,
        event: ChatEvent,
        config: HistoryManagerConfig,
    ):
        self.config = config
        self.logger = logger
        self.event = event
        self.chat_service = ChatService(event)
        self.content_service = ContentService.from_event(event)

    def has_no_loop_messages(self) -> bool:
        return len(self._loop_history) == 0

    def add_tool_call_results(self, tool_call_results: list[ToolCallResponse]):
        for tool_response in tool_call_results:
            if not tool_response.successful:
                self._loop_history.append(
                    LanguageModelToolMessage(
                        name=tool_response.name,
                        tool_call_id=tool_response.id,
                        content=f"Tool call {tool_response.name} failed with error: {tool_response.error_message}",
                    )
                )
                continue
            self._append_tool_call_result_to_history(tool_response)

    def _append_tool_call_result_to_history(
        self,
        tool_response: ToolCallResponse,
    ) -> None:
        tool_call_result_for_history = self._get_tool_call_result_for_loop_history(
            tool_response=tool_response
        )
        self._loop_history.append(tool_call_result_for_history)

    def _get_tool_call_result_for_loop_history(
        self,
        tool_response: ToolCallResponse,
    ) -> LanguageModelMessage:
        self.logger.debug(
            f"Appending tool call result to history: {tool_response.name}"
        )

        content_chunks = (
            tool_response.content_chunks or []
        )  # it can be that the tool response does not have content chunks

        # Transform content chunks into sources to be appended to tool result
        sources = transform_chunks_to_string(
            content_chunks,
            self._source_enumerator,
            None,  # Use None for SourceFormatConfig
            self.config.experimental_features.full_sources_serialize_dump,
        )

        self._source_enumerator += len(
            sources
        )  # To make sure all sources have unique source numbers

        # Append the result to the history
        return LanguageModelToolMessage(
            content=sources,
            tool_call_id=tool_response.id,  # type: ignore
            name=tool_response.name,
        )

    def _append_tool_calls_to_history(
        self, tool_calls: list[LanguageModelFunction]
    ) -> None:
        self._loop_history.append(
            LanguageModelAssistantMessage.from_functions(tool_calls=tool_calls)
        )

    def add_assistant_message(self, message: LanguageModelAssistantMessage) -> None:
        self._loop_history.append(message)

    async def get_history(
        self,
        postprocessing_step: Callable[
            [list[LanguageModelMessage]], list[LanguageModelMessage]
        ]
        | None = None,
    ) -> list[LanguageModelMessage]:
        """
        Get the history of the conversation. The function will retrieve a subset of the full history based on the configuration.

        Returns:
            list[LanguageModelMessage]: The history
        """
        # Get uploaded files
        uploaded_files = self.content_service.search_content_on_chat(
            chat_id=self.chat_service.chat_id
        )
        # Get all message history
        full_history = await self.chat_service.get_full_history_async()

        merged_history = self._merge_history_and_uploads(full_history, uploaded_files)

        if postprocessing_step is not None:
            merged_history = postprocessing_step(merged_history)

        limited_history = self._limit_to_token_window(
            merged_history, self.config.max_history_tokens
        )

        # Add current user message if not already in history
        # we grab it fresh from the db so it must contain all the messages this code is not needed anymore below currently it's left in for explainability
        # current_user_msg = LanguageModelUserMessage(
        #     content=self.event.payload.user_message.text
        # )
        # if not any(
        #     msg.role == LanguageModelMessageRole.USER
        #     and msg.content == current_user_msg.content
        #     for msg in complete_history
        # ):
        #     complete_history.append(current_user_msg)

        # # Add final assistant response - this should be available when this method is called
        # if (
        #     hasattr(self, "loop_response")
        #     and self.loop_response
        #     and self.loop_response.message.text
        # ):
        #     complete_history.append(
        #         LanguageModelAssistantMessage(
        #             content=self.loop_response.message.text
        #         )
        #     )
        # else:
        #     self.logger.warning(
        #         "Called get_complete_conversation_history_after_streaming_no_tool_calls but no loop_response.message.text is available"
        #     )

        return limited_history

    def _merge_history_and_uploads(
        self, history: list[ChatMessage], uploads: list[Content]
    ) -> list[LanguageModelMessage]:
        # Assert that all content have a created_at
        content_with_created_at = [content for content in uploads if content.created_at]
        sorted_history = sorted(
            history + content_with_created_at,
            key=lambda x: x.created_at or datetime.min,
        )

        msg_builder = MessagesBuilder()
        for msg in sorted_history:
            if isinstance(msg, Content):
                msg_builder.user_message_append(
                    f"Uploaded file: {msg.key}, ContentId: {msg.id}"
                )
            else:
                msg_builder.messages.append(
                    LanguageModelMessage(
                        role=LanguageModelMessageRole(msg.role),
                        content=msg.content,
                    )
                )
        return msg_builder.messages

    def _limit_to_token_window(
        self, messages: list[LanguageModelMessage], token_limit: int
    ) -> list[LanguageModelMessage]:
        selected_messages = []
        token_count = 0
        for msg in messages[::-1]:
            msg_token_count = count_tokens(str(msg.content))
            if token_count + msg_token_count > token_limit:
                break
            selected_messages.append(msg)
            token_count += msg_token_count
        return selected_messages[::-1]

    async def remove_post_processing_manipulations(
        self, remove_from_text: Callable[[str], Awaitable[str]]
    ) -> list[LanguageModelMessage]:
        messages = await self.get_history()
        for message in messages:
            if isinstance(message.content, str):
                message.content = await remove_from_text(message.content)
            else:
                self.logger.warning(
                    f"Skipping message with unsupported content type: {type(message.content)}"
                )
        return messages
