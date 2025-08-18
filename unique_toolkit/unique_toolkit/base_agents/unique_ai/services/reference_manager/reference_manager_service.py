import json
import logging


from unique_toolkit.app import ChatEventUserMessage
from unique_toolkit.chat.schemas import ChatMessageRole
from unique_toolkit.content.schemas import (
    ContentChunk,
)
from unique_toolkit.language_model.schemas import (
    LanguageModelAssistantMessage,
    LanguageModelMessages,
    LanguageModelSystemMessage,
    LanguageModelToolMessage,
    LanguageModelUserMessage,
)


from unique_ai.services.reference_manager.config import ReferenceManagerConfig
from unique_toolkit.unique_toolkit.base_agents.loop_agent.history_manager.utils import load_sources_from_string
from unique_toolkit.unique_toolkit.chat.service import ChatService
from unique_toolkit.unique_toolkit.tools.schemas import Source

logger = logging.getLogger(__name__)


class ReferenceManagerService:
    """Service for managing content chunk references in chat messages.

    This service provides functionality to:
    1. Store and manage references to content chunks
    2. Maintain a fixed-size queue of references
    3. Update reference numbers in chat messages
    4. Format chat history with proper reference handling
    5. Extract and update tool calls with proper reference mapping

    The service uses a persistent memory manager to store references between sessions.
    """

    def __init__(
        self,
        chat_service: ChatService,
        chat_id: str,
        config: ReferenceManagerConfig = ReferenceManagerConfig(),
        chat_user_message: ChatEventUserMessage | None = None,
    ):
        """Initialize the ReferenceManagerService.

        Args:
            content_service: Service for content operations
            chat_id: Chat ID for this session
            config: Configuration settings for the reference manager
        """
        # Config and services
        self.config = config
        self.chat_id = chat_id
        self.tools_to_include = self.config.tool_names_to_include
        self._chat_service = chat_service

        # Required data
        self.chat_history = self._chat_service.get_full_history()

        # We only work with the latest GPT request and add the reply assistant message to the gpt_request
        # This is assumed to be the message after the one containing the gpt_request
        self.gpt_request: LanguageModelMessages = LanguageModelMessages([])

        idx_offset = len(self.chat_history)
        for message in self.chat_history[::-1]:
            if message.role == ChatMessageRole.USER and message.gpt_request:
                idx_offset -= 1
                self.gpt_request = LanguageModelMessages.load_messages_to_root(
                    message.gpt_request
                )
                break

        if len(self.gpt_request.root) != 0:
            if idx_offset != len(self.chat_history) - 1:
                logger.warning(
                    f"Only expected one message after the latest gpt_request. Including {len(self.chat_history) - idx_offset} messages"
                )
            # Add all messages after the latest gpt_request to the gpt_request
            for message in self.chat_history[idx_offset:]:
                match message.role:
                    case ChatMessageRole.ASSISTANT:
                        if message.tool_calls:
                            logger.error(
                                "Unexpected assistant message found in chat history with tool calls. Skipping it"
                            )
                            continue
                        self.gpt_request.root.append(
                            LanguageModelAssistantMessage(
                                content=message.original_content
                                or message.content
                                or "NO CONTENT FOUND",
                            )
                        )
                    case _:
                        logger.warning(
                            f"Unexpected message role {message.role} for message {message.id} in {message.chat_id} found in chat history after the latest gpt_request"
                        )

        self._chunks, self._history, self.chunk_sequence_number = (
            self._get_chunks_and_history(
                user_message=chat_user_message,
            )
        )

    def _get_chunks_and_history(
        self,
        user_message: ChatEventUserMessage | None,
    ) -> tuple[list[ContentChunk], LanguageModelMessages, int]:
        # 1. Get cited chunks source_ids
        refenced_ids = set()
        for message in self.chat_history:
            if (
                message.role == ChatMessageRole.ASSISTANT
                and message.references
            ):
                for reference in message.references:
                    refenced_ids.add(reference.source_id)

        # 2. Get actual tool call ids cited so we can filter out unused tool calls
        tool_call_ids_cited = set()
        for message in self.gpt_request:
            # Remove tool calls that are not include to not make model think we have bad tools
            if isinstance(message, LanguageModelToolMessage):
                if message.name in self.tools_to_include:
                    if not message.content or not isinstance(
                        message.content, str
                    ):
                        logger.warning(
                            f"Tool call {message.tool_call_id} has no content"
                        )
                        continue
                    sources = load_sources_from_string(message.content)
                    if not sources:
                        logger.warning(
                            f"Tool call {message.tool_call_id} has no sources"
                        )
                        continue
                    for source in sources:
                        if f"{source.id}_{source.chunk_id}" in refenced_ids:
                            tool_call_ids_cited.add(message.tool_call_id)
                            break

        # 3. Build the LLMMessages to be used in the next request and collect chunks
        chunk_sequence_number = 0
        chunks = []
        builder = LanguageModelMessages([]).builder()
        for message in self.gpt_request:
            # Remove tool calls that are not include to not make model think we have bad tools
            if isinstance(message, LanguageModelToolMessage):
                if (
                    message.name in self.tools_to_include
                    and message.tool_call_id in tool_call_ids_cited
                ):
                    if not message.content or not isinstance(
                        message.content, str
                    ):
                        logger.warning(
                            f"Tool call {message.tool_call_id} has no content"
                        )
                        continue

                    sources = load_sources_from_string(message.content)
                    filtered_sources: list[Source] = []

                    if not sources:
                        continue

                    for source in sources:
                        if (
                            f"{source.id}_{source.chunk_id}"
                            not in refenced_ids
                        ):
                            continue

                        source.source_number = chunk_sequence_number
                        chunks.append(
                            ContentChunk(
                                text=source.content,
                                order=source.order,
                                id=source.id,
                                chunk_id=source.chunk_id,
                                key=source.key,
                                url=source.url,
                            )
                        )
                        filtered_sources.append(source)
                        chunk_sequence_number += 1
                    message.content = json.dumps(
                        [x.model_dump() for x in filtered_sources]
                    )
                    builder.append(message)
            elif isinstance(message, LanguageModelAssistantMessage):
                if message.tool_calls:
                    filtered_tool_calls = [
                        tool_call
                        for tool_call in message.tool_calls
                        if (
                            tool_call.function.name in self.tools_to_include
                            and tool_call.id in tool_call_ids_cited
                        )
                    ]
                    if filtered_tool_calls:
                        message.tool_calls = filtered_tool_calls
                    else:
                        # Case where we don't cite any data from any tool calls. Here we remove the assistantmessage as it's not useful
                        logger.info(
                            "Removing message assistant tool_call message as it has no tool calls"
                        )
                        continue
                    builder.append(message)
                elif message.content:
                    builder.append(message)
                else:
                    logger.warning(
                        "Removing message assistant message as it has no content or tool calls"
                    )
                    continue
                # TODO: Try to remap citing numbers
            elif isinstance(message, LanguageModelSystemMessage):
                logger.info(
                    "Reference manager service is ignoring system message"
                )
            elif isinstance(message, LanguageModelUserMessage):
                builder.append(message)
            else:
                logger.warning(
                    "Unexpected message type in gpt_request ignoring"
                )

        if user_message:
            builder.user_message_append(user_message.text)

        gpt_request_messages = builder.build()

        return chunks, gpt_request_messages, chunk_sequence_number

    @property
    def chunks(self) -> list[ContentChunk]:
        return self._chunks

    @property
    def history(self) -> LanguageModelMessages:
        return self._history

    @property
    def tool_call_ids_protected_from_reduction(self) -> set[str]:
        return set(
            [
                tool_call.tool_call_id
                for tool_call in self._history
                if isinstance(tool_call, LanguageModelToolMessage)
            ]
        )
