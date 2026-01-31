import json
from logging import Logger
from typing import Awaitable, Callable

import tiktoken
from pydantic import BaseModel

from unique_toolkit._common.token.token_counting import (
    num_token_for_language_model_messages,
)
from unique_toolkit._common.validators import LMI
from unique_toolkit.agentic.history_manager.history_construction_with_contents import (
    FileContentSerialization,
    get_full_history_with_contents,
)
from unique_toolkit.agentic.reference_manager.reference_manager import ReferenceManager
from unique_toolkit.app.schemas import ChatEvent
from unique_toolkit.chat.service import ChatService
from unique_toolkit.content.schemas import ContentChunk
from unique_toolkit.content.service import ContentService
from unique_toolkit.language_model.schemas import (
    LanguageModelAssistantMessage,
    LanguageModelMessage,
    LanguageModelMessageRole,
    LanguageModelMessages,
    LanguageModelSystemMessage,
    LanguageModelToolMessage,
    LanguageModelUserMessage,
)

MAX_INPUT_TOKENS_SAFETY_PERCENTAGE = (
    0.1  # 10% safety margin for input tokens we need 10% less does not work.
)
SAFETY_MARGIN_FOR_AGGRESSIVE_REDUCTION = 0.9


class SourceReductionResult(BaseModel):
    message: LanguageModelToolMessage
    reduced_chunks: list[ContentChunk]
    chunk_offset: int
    source_offset: int

    class Config:
        arbitrary_types_allowed = True


class LoopTokenReducer:
    def __init__(
        self,
        logger: Logger,
        event: ChatEvent,
        max_history_tokens: int,
        has_uploaded_content_config: bool,
        reference_manager: ReferenceManager,
        language_model: LMI,
    ):
        self._max_history_tokens = max_history_tokens
        self._has_uploaded_content_config = has_uploaded_content_config
        self._logger = logger
        self._reference_manager = reference_manager
        self._language_model = language_model
        self._encoder = self._get_encoder(language_model)
        self._chat_service = ChatService(event)
        self._content_service = ContentService.from_event(event)
        self._user_message = event.payload.user_message
        self._chat_id = event.payload.chat_id
        self._effective_token_limit = int(
            self._language_model.token_limits.token_limit_input
            * (1 - MAX_INPUT_TOKENS_SAFETY_PERCENTAGE)
        )

    def _get_encoder(self, language_model: LMI) -> tiktoken.Encoding:
        name = language_model.encoder_name or "cl100k_base"
        return tiktoken.get_encoding(name)

    async def get_history_for_model_call(
        self,
        original_user_message: str,
        rendered_user_message_string: str,
        rendered_system_message_string: str,
        loop_history: list[LanguageModelMessage],
        remove_from_text: Callable[[str], Awaitable[str]],
    ) -> LanguageModelMessages:
        """Compose the system and user messages for the plan execution step, which is evaluating if any further tool calls are required."""

        history_from_db = await self._prep_db_history(
            original_user_message,
            rendered_user_message_string,
            rendered_system_message_string,
            remove_from_text,
        )

        messages = self._construct_history(
            history_from_db,
            loop_history,
        )

        token_count = self._count_message_tokens(messages)
        self._log_token_usage(token_count)

        while self._exceeds_token_limit(token_count):
            token_count_before_reduction = token_count
            loop_history = self._handle_token_limit_exceeded(loop_history, token_count)
            messages = self._construct_history(
                history_from_db,
                loop_history,
            )
            token_count = self._count_message_tokens(messages)
            self._log_token_usage(token_count)
            token_count_after_reduction = token_count
            if token_count_after_reduction >= token_count_before_reduction:
                break

        token_count = self._count_message_tokens(messages)
        self._logger.info(
            f"Final token count after reduction: {token_count} of model_capacity {self._language_model.token_limits.token_limit_input}"
        )

        return messages

    def _exceeds_token_limit(self, token_count: int) -> bool:
        """Check if token count exceeds the maximum allowed limit and if at least one tool call has more than one source."""
        # At least one tool call should have more than one chunk as answer
        has_multiple_chunks_for_a_tool_call = any(
            len(chunks) > 1
            for chunks in self._reference_manager.get_chunks_of_all_tools()
        )
        # TODO: This is not fully correct at the moment as the token_count
        # include system_prompt and user question already
        # TODO: There is a problem if we exceed but only have one chunk per tool call
        exceeds_limit = token_count > self._effective_token_limit

        return has_multiple_chunks_for_a_tool_call and exceeds_limit

    def _count_message_tokens(self, messages: LanguageModelMessages) -> int:
        """Count tokens in messages using the configured encoding model."""
        return num_token_for_language_model_messages(
            messages=messages,
            encode=self._encoder.encode,
        )

    def _log_token_usage(self, token_count: int) -> None:
        """Log token usage and update debug info."""
        self._logger.info(f"Token messages: {token_count}")
        # self.agent_debug_info.add("token_messages", token_count)

    async def _prep_db_history(
        self,
        original_user_message: str,
        rendered_user_message_string: str,
        rendered_system_message_string: str,
        remove_from_text: Callable[[str], Awaitable[str]],
    ) -> list[LanguageModelMessage]:
        history_from_db = await self.get_history_from_db(remove_from_text)
        history_from_db = self._replace_user_message(
            history_from_db, original_user_message, rendered_user_message_string
        )
        system_message = LanguageModelSystemMessage(
            content=rendered_system_message_string
        )
        return [system_message] + history_from_db

    def _construct_history(
        self,
        history_from_db: list[LanguageModelMessage],
        loop_history: list[LanguageModelMessage],
    ) -> LanguageModelMessages:
        constructed_history = LanguageModelMessages(
            history_from_db + loop_history,
        )

        return constructed_history

    def _handle_token_limit_exceeded(
        self, loop_history: list[LanguageModelMessage], token_count: int
    ) -> list[LanguageModelMessage]:
        """Handle case where token limit is exceeded by reducing sources in tool responses."""
        overshoot_factor = (
            token_count / self._effective_token_limit
            if self._effective_token_limit > 0
            else 1.0
        )
        self._logger.warning(
            f"Length of messages exceeds limit of {self._effective_token_limit} tokens "
            f"(overshoot factor: {overshoot_factor:.2f}x). Reducing number of sources per tool call.",
        )

        return self._reduce_message_length_by_reducing_sources_in_tool_response(
            loop_history, overshoot_factor
        )

    def _replace_user_message(
        self,
        history: list[LanguageModelMessage],
        original_user_message: str,
        rendered_user_message_string: str,
    ) -> list[LanguageModelMessage]:
        """
        Replaces the original user message in the history with the rendered user message string.
        """
        if history[-1].role == LanguageModelMessageRole.USER:
            m = history[-1]

            if isinstance(m.content, list):
                # Replace the last text element but be careful not to delete data added when merging with contents
                for t in reversed(m.content):
                    field = t.get("type", "")
                    if field == "text" and isinstance(field, dict):
                        inner_field = field.get("text", "")
                        if isinstance(inner_field, str):
                            added_to_message_by_history = inner_field.replace(
                                original_user_message,
                                "",
                            )
                            t["text"] = (
                                rendered_user_message_string
                                + added_to_message_by_history
                            )
                        break
            elif m.content:
                added_to_message_by_history = m.content.replace(
                    original_user_message, ""
                )
                m.content = rendered_user_message_string + added_to_message_by_history
        else:
            history = history + [
                LanguageModelUserMessage(content=rendered_user_message_string),
            ]
        return history

    async def get_history_from_db(
        self, remove_from_text: Callable[[str], Awaitable[str]] | None = None
    ) -> list[LanguageModelMessage]:
        """
        Get the history of the conversation. The function will retrieve a subset of the full history based on the configuration.

        Returns:
            list[LanguageModelMessage]: The history
        """
        full_history = get_full_history_with_contents(
            user_message=self._user_message,
            chat_id=self._chat_id,
            chat_service=self._chat_service,
            content_service=self._content_service,
            file_content_serialization_type=(
                FileContentSerialization.NONE
                if self._has_uploaded_content_config
                else FileContentSerialization.FILE_NAME
            ),
        )
        # if remove_from_text is not None:
        #     full_history.root = await self._clean_messages(
        #         full_history.root, remove_from_text
        #     )

        limited_history_messages = self._limit_to_token_window(
            full_history.root, self._max_history_tokens
        )

        if len(limited_history_messages) == 0:
            limited_history_messages = full_history.root[-1:]

        self._logger.info(
            f"Reduced history to {len(limited_history_messages)} messages from {len(full_history.root)}",
        )

        return self.ensure_last_message_is_user_message(limited_history_messages)

    def _limit_to_token_window(
        self, messages: list[LanguageModelMessage], token_limit: int
    ) -> list[LanguageModelMessage]:
        selected_messages = []
        token_count = 0
        for msg in messages[::-1]:
            msg_token_count = self._count_message_tokens(
                LanguageModelMessages(root=[msg])
            )
            if token_count + msg_token_count > token_limit:
                break
            selected_messages.append(msg)
            token_count += msg_token_count
        return selected_messages[::-1]

    async def _clean_messages(
        self,
        messages: list[
            LanguageModelMessage
            | LanguageModelToolMessage
            | LanguageModelAssistantMessage
            | LanguageModelSystemMessage
            | LanguageModelUserMessage
        ],
        remove_from_text: Callable[[str], Awaitable[str]],
    ) -> list[LanguageModelMessage]:
        for message in messages:
            if isinstance(message.content, str):
                message.content = await remove_from_text(message.content)
            else:
                self._logger.warning(
                    f"Skipping message with unsupported content type: {type(message.content)}"
                )
        return messages

    def ensure_last_message_is_user_message(self, limited_history_messages):
        """
        As the token limit can be reached in the middle of a gpt_request,
        we move forward to the next user message,to avoid confusing messages for the LLM
        """
        idx = 0
        for idx, message in enumerate(limited_history_messages):
            if message.role == LanguageModelMessageRole.USER:
                break

        # FIXME: This might reduce the history by a lot if we have a lot of tool calls / references in the history. Could make sense to summarize the messages and include
        # FIXME: We should remove chunks no longer in history from handler
        return limited_history_messages[idx:]

    def _reduce_message_length_by_reducing_sources_in_tool_response(
        self,
        history: list[LanguageModelMessage],
        overshoot_factor: float,
    ) -> list[LanguageModelMessage]:
        """
        Reduce the message length by removing sources from each tool call based on overshoot.

        The number of chunks to keep per tool call is calculated as:
        chunks_to_keep = num_sources / (overshoot_factor * SAFETY_MARGIN_FOR_AGGRESSIVE_REDUCTION)

        This ensures more aggressive reduction when we're significantly over the limit.
        Using SAFETY_MARGIN_FOR_AGGRESSIVE_REDUCTION factor provides a safety margin to avoid over-reduction.
        E.g., if overshoot_factor = 2 (2x over limit), keep 1/1.5 = 2/3 of chunks.
        Always keeps at least 1 chunk.
        """
        history_reduced: list[LanguageModelMessage] = []
        content_chunks_reduced: list[ContentChunk] = []
        chunk_offset = 0
        source_offset = 0

        for message in history:
            if self._should_reduce_message(message):
                result = self._reduce_sources_in_tool_message(
                    message,  # type: ignore
                    chunk_offset,
                    source_offset,
                    overshoot_factor,
                )
                content_chunks_reduced.extend(result.reduced_chunks)
                history_reduced.append(result.message)
                chunk_offset = result.chunk_offset
                source_offset = result.source_offset
            else:
                history_reduced.append(message)

        self._reference_manager.replace(chunks=content_chunks_reduced)
        return history_reduced

    def _should_reduce_message(self, message: LanguageModelMessage) -> bool:
        """Determine if a message should have its sources reduced."""
        return message.role == LanguageModelMessageRole.TOOL and isinstance(
            message, LanguageModelToolMessage
        )

    def _reduce_sources_in_tool_message(
        self,
        message: LanguageModelToolMessage,
        chunk_offset: int,
        source_offset: int,
        overshoot_factor: float,
    ) -> SourceReductionResult:
        """
        Reduce the sources in the tool message based on overshoot factor.

        Chunks to keep = num_sources / (overshoot_factor * SAFETY_MARGIN_FOR_AGGRESSIVE_REDUCTION)
        This ensures fewer chunks are kept when overshoot is larger.
        E.g., if overshoot_factor = 2 (2x over limit), keep 1/1.5 = 2/3 of chunks
        Always keeps at least 1 chunk.
        """
        tool_chunks = self._reference_manager.get_chunks_of_tool(message.tool_call_id)
        num_sources = len(tool_chunks)

        if num_sources == 0:
            return SourceReductionResult(
                message=message,
                reduced_chunks=[],
                chunk_offset=chunk_offset,
                source_offset=source_offset,
            )

        # Calculate how many chunks to keep based on overshoot
        # Use SAFETY_MARGIN_FOR_AGGRESSIVE_REDUCTION safety margin for aggressive reduction, but only when overshoot is
        # significant enough (>= ~1.33). Otherwise, the margin would prevent reduction.
        divisor = (
            overshoot_factor * SAFETY_MARGIN_FOR_AGGRESSIVE_REDUCTION
            if overshoot_factor * SAFETY_MARGIN_FOR_AGGRESSIVE_REDUCTION
            >= 1.2  # Skip safety margin for small overshoots (e.g., 1.03) to avoid tiny reduction steps
            else overshoot_factor
        )
        chunks_to_keep = max(1, int(num_sources // divisor))

        # Reduce chunks
        if chunks_to_keep >= num_sources:
            # No reduction needed for this tool call
            reduced_chunks = tool_chunks
            content_chunks_reduced = self._reference_manager.get_chunks()[
                chunk_offset : chunk_offset + num_sources
            ]
        else:
            reduced_chunks = tool_chunks[:chunks_to_keep]
            content_chunks_reduced = self._reference_manager.get_chunks()[
                chunk_offset : chunk_offset + chunks_to_keep
            ]
            self._reference_manager.replace_chunks_of_tool(
                message.tool_call_id, reduced_chunks
            )

        # Create new message with reduced sources
        new_message = self._create_tool_call_message_with_reduced_sources(
            message=message,
            content_chunks=reduced_chunks,
            source_offset=source_offset,
        )

        return SourceReductionResult(
            message=new_message,
            reduced_chunks=content_chunks_reduced,
            chunk_offset=chunk_offset + num_sources,
            source_offset=source_offset + len(reduced_chunks),
        )

    def _create_tool_call_message_with_reduced_sources(
        self,
        message: LanguageModelToolMessage,
        content_chunks: list[ContentChunk] | None = None,
        source_offset: int = 0,
    ) -> LanguageModelToolMessage:
        # Handle special case for TableSearch tool
        if message.name == "TableSearch":
            return self._create_reduced_table_search_message(
                message, content_chunks, source_offset
            )

        # Handle empty content case
        if not content_chunks:
            return self._create_reduced_empty_sources_message(message)

        # Handle standard content chunks
        return self._create_reduced_standard_sources_message(
            message, content_chunks, source_offset
        )

    def _create_reduced_table_search_message(
        self,
        message: LanguageModelToolMessage,
        content_chunks: list[ContentChunk] | None,
        source_offset: int,
    ) -> LanguageModelToolMessage:
        """
        Create a message for TableSearch tool.

        Note: TableSearch content consists of a single result with SQL results,
        not content chunks.
        """
        if not content_chunks:
            content = message.content
        else:
            if isinstance(message.content, str):
                content_dict = json.loads(message.content)
            elif isinstance(message.content, dict):
                content_dict = message.content
            else:
                raise ValueError(f"Unexpected content type: {type(message.content)}")

            content = json.dumps(
                {
                    "source_number": source_offset,
                    "content": content_dict.get("content"),
                }
            )

        return LanguageModelToolMessage(
            content=content,
            tool_call_id=message.tool_call_id,
            name=message.name,
        )

    def _create_reduced_empty_sources_message(
        self,
        message: LanguageModelToolMessage,
    ) -> LanguageModelToolMessage:
        """Create a message when no content chunks are available."""
        return LanguageModelToolMessage(
            content="No relevant sources found.",
            tool_call_id=message.tool_call_id,
            name=message.name,
        )

    def _create_reduced_standard_sources_message(
        self,
        message: LanguageModelToolMessage,
        content_chunks: list[ContentChunk],
        source_offset: int,
    ) -> LanguageModelToolMessage:
        """Create a message with standard content chunks."""
        sources = [
            {
                "source_number": source_offset + i,
                "content": chunk.text,
            }
            for i, chunk in enumerate(content_chunks)
        ]

        return LanguageModelToolMessage(
            content=json.dumps(sources),
            tool_call_id=message.tool_call_id,
            name=message.name,
        )
