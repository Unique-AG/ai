import base64
import logging
import mimetypes
from datetime import datetime
from enum import StrEnum

import numpy as np
from pydantic import RootModel

from unique_toolkit._common.token.token_counting import (
    num_tokens_per_language_model_message,
)
from unique_toolkit._common.utils import files as FileUtils
from unique_toolkit.app import ChatEventUserMessage
from unique_toolkit.chat.schemas import ChatMessage
from unique_toolkit.chat.schemas import ChatMessageRole as ChatRole
from unique_toolkit.chat.service import ChatService
from unique_toolkit.content.schemas import Content
from unique_toolkit.content.service import ContentService
from unique_toolkit.language_model import LanguageModelMessageRole as LLMRole
from unique_toolkit.language_model.infos import EncoderName, LanguageModelInfo
from unique_toolkit.language_model.schemas import (
    LanguageModelAssistantMessage,
    LanguageModelFunctionCall,
    LanguageModelMessage,
    LanguageModelMessageOptions,
    LanguageModelMessages,
    LanguageModelToolMessage,
)

logger = logging.getLogger(__name__)

# TODO: Test this once it moves into the unique toolkit

map_chat_llm_message_role = {
    ChatRole.USER: LLMRole.USER,
    ChatRole.ASSISTANT: LLMRole.ASSISTANT,
    ChatRole.SYSTEM: LLMRole.SYSTEM,
}


class ChatMessageWithContents(ChatMessage):
    contents: list[Content] = []


class ChatHistoryWithContent(RootModel):
    root: list[ChatMessageWithContents]

    @classmethod
    def from_chat_history_and_contents(
        cls,
        chat_history: list[ChatMessage],
        chat_contents: list[Content],
    ):
        combined = chat_contents + chat_history
        combined.sort(key=lambda x: x.created_at or datetime.min)

        grouped_elements = []
        content_container = []

        # Content is collected and added to the next chat message
        for c in combined:
            if isinstance(c, ChatMessage):
                grouped_elements.append(
                    ChatMessageWithContents(
                        contents=content_container.copy(),
                        **c.model_dump(),
                    ),
                )
                content_container.clear()
            else:
                content_container.append(c)

        return cls(root=grouped_elements)

    def __iter__(self):
        return iter(self.root)

    def __getitem__(self, item):
        return self.root[item]


def get_chat_history_with_contents(
    user_message: ChatEventUserMessage,
    chat_id: str,
    chat_history: list[ChatMessage],
    content_service: ContentService,
) -> ChatHistoryWithContent:
    last_user_message = ChatMessage(
        id=user_message.id,
        chat_id=chat_id,
        text=user_message.text,
        originalText=user_message.original_text,
        role=ChatRole.USER,
        gpt_request=None,
        created_at=datetime.fromisoformat(user_message.created_at),
    )
    if len(chat_history) > 0 and last_user_message.id == chat_history[-1].id:
        pass
    else:
        chat_history.append(last_user_message)

    chat_contents = content_service.search_contents(
        where={
            "ownerId": {
                "equals": chat_id,
            },
        },
    )

    return ChatHistoryWithContent.from_chat_history_and_contents(
        chat_history,
        chat_contents,
    )


def download_encoded_images(
    contents: list[Content],
    content_service: ContentService,
    chat_id: str,
) -> list[str]:
    base64_encoded_images = []
    for im in contents:
        if FileUtils.is_image_content(im.key):
            try:
                file_bytes = content_service.download_content_to_bytes(
                    content_id=im.id,
                    chat_id=chat_id,
                )

                mime_type, _ = mimetypes.guess_type(im.key)
                encoded_string = base64.b64encode(file_bytes).decode("utf-8")
                image_string = f"data:{mime_type};base64," + encoded_string
                base64_encoded_images.append(image_string)
            except Exception as e:
                print(e)
    return base64_encoded_images


class FileContentSerialization(StrEnum):
    NONE = "none"
    FILE_NAME = "file_name"


class ImageContentInclusion(StrEnum):
    NONE = "none"
    ALL = "all"


def file_content_serialization(
    file_contents: list[Content],
    file_content_serialization: FileContentSerialization,
) -> str:
    match file_content_serialization:
        case FileContentSerialization.NONE:
            return ""
        case FileContentSerialization.FILE_NAME:
            file_names = [
                f"- Uploaded file: {f.key} at {f.created_at}" for f in file_contents
            ]
            return "\n".join(
                [
                    "Files Uploaded to Chat can be accessed by internal search tool if available:\n",
                ]
                + file_names,
            )


def get_full_history_with_contents(
    user_message: ChatEventUserMessage,
    chat_id: str,
    chat_service: ChatService,
    content_service: ContentService,
    include_images: ImageContentInclusion = ImageContentInclusion.ALL,
    file_content_serialization_type: FileContentSerialization = FileContentSerialization.FILE_NAME,
) -> LanguageModelMessages:
    grouped_elements = get_chat_history_with_contents(
        user_message=user_message,
        chat_id=chat_id,
        chat_history=chat_service.get_full_history(),
        content_service=content_service,
    )

    builder = LanguageModelMessages([]).builder()
    for c in grouped_elements:
        # LanguageModelUserMessage has not field original content
        text = c.original_content if c.original_content else c.content
        if text is None:
            if c.role == ChatRole.USER:
                raise ValueError(
                    "Content or original_content of LanguageModelMessages should exist.",
                )
            text = ""

        if len(c.contents) > 0:
            file_contents = [
                co for co in c.contents if FileUtils.is_file_content(co.key)
            ]
            image_contents = [
                co for co in c.contents if FileUtils.is_image_content(co.key)
            ]

            content = (
                text
                + "\n\n"
                + file_content_serialization(
                    file_contents,
                    file_content_serialization_type,
                )
            )
            content = content.strip()

            if include_images and len(image_contents) > 0:
                builder.image_message_append(
                    content=content,
                    images=download_encoded_images(
                        contents=image_contents,
                        content_service=content_service,
                        chat_id=chat_id,
                    ),
                    role=map_chat_llm_message_role[c.role],
                )
            else:
                builder.message_append(
                    role=map_chat_llm_message_role[c.role],
                    content=content,
                )
        else:
            builder.message_append(
                role=map_chat_llm_message_role[c.role],
                content=text,
            )
    return builder.build()


def _segment_gpt_request_into_turns(
    gpt_request: list[dict],
) -> list[list[dict]]:
    """Segment a gpt_request message array into per-turn groups.

    Each turn starts with a user message. System messages are skipped.
    Returns a list of turn segments, where each segment is a list of
    message dicts belonging to that turn.
    """
    turns: list[list[dict]] = []
    current_turn: list[dict] = []

    for msg in gpt_request:
        if msg.get("role") == "system":
            continue
        if msg.get("role") == "user" and current_turn:
            turns.append(current_turn)
            current_turn = []
        current_turn.append(msg)

    if current_turn:
        turns.append(current_turn)

    return turns


def _extract_tool_messages_per_turn(
    gpt_request: list[dict],
) -> list[list[dict]]:
    """Extract intermediate tool-related messages for each turn in a gpt_request.

    For each turn, returns the messages between the user message and the
    final assistant response — i.e. intermediate assistant messages (with
    tool_calls) and tool response messages.

    For non-last turns, the final element is the concluding assistant message
    (which is already in the DB), so it is excluded.
    For the last turn, there is no concluding assistant response in the
    gpt_request (it was the LLM output), so all messages after the user
    message are included.
    """
    turns = _segment_gpt_request_into_turns(gpt_request)

    result: list[list[dict]] = []
    for i, turn in enumerate(turns):
        is_last_turn = i == len(turns) - 1
        if is_last_turn:
            result.append(turn[1:] if len(turn) > 1 else [])
        else:
            result.append(turn[1:-1] if len(turn) > 2 else [])

    return result


def _convert_raw_messages_to_typed(
    raw_messages: list[dict],
) -> list[LanguageModelMessageOptions]:
    """Convert raw gpt_request message dicts to typed LanguageModelMessage objects.

    Handles assistant messages (with tool_calls) and tool response messages,
    defaulting missing fields gracefully.
    """
    converted: list[LanguageModelMessageOptions] = []
    for msg in raw_messages:
        role = msg.get("role", "")
        try:
            if role == "assistant":
                tool_calls = None
                if msg.get("tool_calls"):
                    tool_calls = [
                        LanguageModelFunctionCall(**tc)
                        for tc in msg["tool_calls"]
                    ]
                converted.append(
                    LanguageModelAssistantMessage(
                        content=msg.get("content"),
                        tool_calls=tool_calls,
                    )
                )
            elif role == "tool":
                converted.append(
                    LanguageModelToolMessage(
                        content=msg.get("content"),
                        tool_call_id=msg.get("tool_call_id", ""),
                        name=msg.get("name", "unknown"),
                    )
                )
            else:
                converted.append(
                    LanguageModelMessage(
                        role=LLMRole(role),
                        content=msg.get("content"),
                    )
                )
        except Exception:
            logger.warning(
                "Failed to convert gpt_request message, skipping: %s",
                msg,
                exc_info=True,
            )
    return converted


def _interleave_tool_messages(
    enriched_history: LanguageModelMessages,
    tool_messages_per_turn: list[list[dict]],
) -> LanguageModelMessages:
    """Splice intermediate tool messages into the enriched history.

    The enriched history is a flat list of [user, assistant, user, assistant, ...].
    For each user message, the corresponding turn's tool messages are inserted
    right after it (and before the following assistant message).
    """
    result: list[LanguageModelMessageOptions] = []
    turn_idx = 0

    for msg in enriched_history:
        result.append(msg)
        if msg.role == LLMRole.USER and turn_idx < len(tool_messages_per_turn):
            typed_tool_msgs = _convert_raw_messages_to_typed(
                tool_messages_per_turn[turn_idx]
            )
            result.extend(typed_tool_msgs)
            turn_idx += 1

    return LanguageModelMessages(root=result)


def get_full_history_with_contents_and_tool_calls(
    user_message: ChatEventUserMessage,
    chat_id: str,
    chat_service: ChatService,
    content_service: ContentService,
    include_images: ImageContentInclusion = ImageContentInclusion.ALL,
    file_content_serialization_type: FileContentSerialization = FileContentSerialization.FILE_NAME,
) -> LanguageModelMessages:
    """Build the full conversation history with content enrichment AND tool call messages.

    Combines the enriched DB history (user/assistant messages with file and
    image metadata) with the intermediate tool interaction messages extracted
    from the gpt_request field on previous user messages.

    Falls back to plain enriched history if no gpt_request is available.
    """
    enriched_history = get_full_history_with_contents(
        user_message=user_message,
        chat_id=chat_id,
        chat_service=chat_service,
        content_service=content_service,
        include_images=include_images,
        file_content_serialization_type=file_content_serialization_type,
    )

    chat_history = chat_service.get_full_history()

    last_user_with_gpt_request = next(
        (
            m
            for m in reversed(chat_history)
            if m.role == ChatRole.USER and m.gpt_request
        ),
        None,
    )

    if not last_user_with_gpt_request or not last_user_with_gpt_request.gpt_request:
        return enriched_history

    tool_messages_per_turn = _extract_tool_messages_per_turn(
        last_user_with_gpt_request.gpt_request
    )

    return _interleave_tool_messages(enriched_history, tool_messages_per_turn)


def get_full_history_as_llm_messages(
    chat_service: ChatService,
) -> LanguageModelMessages:
    chat_history = chat_service.get_full_history()

    map_chat_llm_message_role = {
        ChatRole.USER: LLMRole.USER,
        ChatRole.ASSISTANT: LLMRole.ASSISTANT,
    }

    builder = LanguageModelMessages([]).builder()
    for c in chat_history:
        builder.message_append(
            role=map_chat_llm_message_role[c.role],
            content=c.content or "",
        )
    return builder.build()


def limit_to_token_window(
    messages: LanguageModelMessages,
    token_limit: int,
    model_info: LanguageModelInfo | None = None,
    encoding_name: EncoderName = EncoderName.O200K_BASE,
) -> LanguageModelMessages:
    if model_info is not None:
        encode = model_info.get_encoder()
    else:
        encode = encoding_name.get_encoder()

    token_per_message_reversed = num_tokens_per_language_model_message(
        messages,
        encode=encode,
    )

    to_take: list[bool] = (np.cumsum(token_per_message_reversed) < token_limit).tolist()
    to_take.reverse()

    return LanguageModelMessages(
        root=[m for m, tt in zip(messages, to_take, strict=False) if tt],
    )
