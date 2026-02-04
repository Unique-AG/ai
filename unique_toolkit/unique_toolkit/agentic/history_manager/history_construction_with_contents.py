import base64
import json
import mimetypes
import re
from datetime import datetime
from enum import StrEnum

import numpy as np
import tiktoken
from pydantic import RootModel

from unique_toolkit._common.token.token_counting import (
    num_token_for_language_model_messages,
    num_tokens_per_language_model_message,
)
from unique_toolkit._common.utils import files as FileUtils
from unique_toolkit.app import ChatEventUserMessage
from unique_toolkit.chat.schemas import ChatMessage
from unique_toolkit.chat.schemas import ChatMessageRole as ChatRole
from unique_toolkit.chat.service import ChatService
from unique_toolkit.content.schemas import Content
from unique_toolkit.content.service import ContentService
from unique_toolkit.language_model import LanguageModelAssistantMessage, LanguageModelMessage, LanguageModelMessageRole
from unique_toolkit.language_model.infos import EncoderName
from unique_toolkit.language_model.reference import _preprocess_message
from unique_toolkit.language_model.schemas import LanguageModelMessages

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

def _get_last_message_by_role(
    messages: list[ChatMessage],
    role: ChatRole,
) -> ChatMessage | None:
    """Return the last message with the given role, or None if not found."""
    return next((msg for msg in reversed(messages) if msg.role == role), None)

def _construct_history_from_gpt_request(
    chat_service: ChatService,
) -> list[LanguageModelMessage]:
    chat_history = chat_service.get_full_history()

    if len(chat_history) == 0:
        return []

    last_assistant_message = _get_last_message_by_role(chat_history, ChatRole.ASSISTANT)
    last_user_message = _get_last_message_by_role(chat_history, ChatRole.USER)

    if not last_user_message or not last_user_message.gpt_request or not last_assistant_message:
        return []

    # Convert gpt_request messages to ChatMessage, excluding system messages
    history = [
        LanguageModelMessage(
            role=LanguageModelMessageRole(msg.get("role")),
            content=msg.get("content"),
        )
        for msg in last_user_message.gpt_request
        if msg.get("role") != ChatRole.SYSTEM
    ]

    return [*history, LanguageModelAssistantMessage(content=last_assistant_message.content)]

def _extract_cited_sources(messages: list[LanguageModelMessage]) -> set[int]:
    """Extract all cited source numbers from assistant messages.

    Scans the content of all assistant messages for citation patterns
    like [source1], [source2], etc. and returns the set of source numbers.

    Args:
        messages: List of chat messages to scan.

    Returns:
        A set of integers representing the cited source numbers.
    """
    cited_sources: set[int] = set()
    pattern = re.compile(r"\[source(\d+)\]", re.IGNORECASE)

    for message in messages:
        if message.role != ChatRole.ASSISTANT:
            continue

        if not isinstance(message.content, str):
            continue

        content = _preprocess_message(message.content)
        matches = pattern.findall(content)
        cited_sources.update(int(match) for match in matches)

    return cited_sources


def _build_source_id_mapping(messages: list[ChatMessage]) -> dict[int, int]:
    """Build a mapping from old source IDs to new sequential IDs.

    Scans tool messages in order and assigns new sequential IDs (starting from 1)
    based on the order sources appear.

    Args:
        messages: List of chat messages to scan.

    Returns:
        A dictionary mapping old source IDs to new sequential IDs.
    """
    old_to_new: dict[int, int] = {}
    next_id = 0

    for message in messages:
        if message.role != ChatRole.TOOL:
            continue

        if not message.content:
            continue

        try:
            content_data = json.loads(message.content)

            if not isinstance(content_data, list):
                if isinstance(content_data, dict) and "source_number" in content_data:
                    content_data = [content_data]
                else:
                    continue

            for item in content_data:
                source_num = item.get("source_number")
                if source_num is not None and source_num not in old_to_new:
                    old_to_new[source_num] = next_id
                    next_id += 1

        except (json.JSONDecodeError, TypeError):
            continue

    return old_to_new


def _reorder_source_ids(messages: list[LanguageModelMessage]) -> list[LanguageModelMessage]:
    """Reorder source IDs to be sequential starting from 1.

    Updates source_number fields in tool messages and [sourceN] references
    in assistant messages to use new sequential IDs based on the order
    sources appear in tool messages.
    """
    old_to_new = _build_source_id_mapping(messages)

    if not old_to_new:
        return messages

    for message in messages:
        if message.role == ChatRole.TOOL and message.content:
            try:
                if not isinstance(message.content, str):
                    continue
                content_data = json.loads(message.content)

                if not isinstance(content_data, list):
                    if isinstance(content_data, dict) and "source_number" in content_data:
                        content_data = [content_data]
                    else:
                        continue

                for item in content_data:
                    old_source = item.get("source_number")
                    if old_source is not None and old_source in old_to_new:
                        item["source_number"] = old_to_new[old_source]

                message.content = json.dumps(content_data)

            except (json.JSONDecodeError, TypeError):
                continue

        elif message.role == ChatRole.ASSISTANT and message.content:
            # Replace [sourceN] patterns with new IDs
            def replace_source(match: re.Match) -> str:
                old_id = int(match.group(1))
                new_id = old_to_new.get(old_id, old_id)
                if new_id is None: # If the source number is not found, return an empty string. This references al
                    return ""
                return f"[source{new_id}]"

            if not isinstance(message.content, str):
                continue
            message.content = re.sub(
                r"\[source(\d+)\]",
                replace_source,
                message.content,
                flags=re.IGNORECASE,
            )

    return messages


def _remove_uncited_sources_from_tool_messages(
    messages: list[LanguageModelMessage],
    cited_sources: set[int],
) -> list[LanguageModelMessage]:
    """Remove uncited sources from tool messages with InternalSearch format.

    Goes through all messages with role 'tool' and checks if the content
    follows the InternalSearch format (JSON array with source_number entries).
    If so, keeps only the dicts where source_number is in cited_sources.
    """
    for message in messages:
        if message.role != ChatRole.TOOL:
            continue

        if not message.content:
            continue

        try:
            if not isinstance(message.content, str):
                continue
            content_data = json.loads(message.content)

            # Check if it's a list of dicts with source_number keys
            if not isinstance(content_data, list):
                if not isinstance(content_data, dict) or "source_number" not in content_data:
                    continue
                content_data = [content_data]

            # Filter to keep only cited sources
            filtered_data = [
                item for item in content_data
                if item.get("source_number") in cited_sources
            ]

            message.content = json.dumps(filtered_data)

        except (json.JSONDecodeError, TypeError):
            # Content is not valid JSON, skip this message
            continue

    return messages

def _count_message_tokens(messages: LanguageModelMessages) -> int:
        """Count tokens in messages using the configured encoding model."""
        return num_token_for_language_model_messages(
            messages=messages,
            encode=tiktoken.get_encoding("cl100k_base").encode, # TODO: Make this configurable
        )
        
def _limit_to_token_window(
    messages: list[LanguageModelMessage], token_limit: int
) -> list[LanguageModelMessage]:
    selected_messages = []
    token_count = 0
    for msg in messages[::-1]:
        msg_token_count = _count_message_tokens(
            messages=LanguageModelMessages(root=[msg])
        )
        if token_count + msg_token_count > token_limit:
            break
        selected_messages.append(msg)
        token_count += msg_token_count
    return selected_messages[::-1]

def get_full_history_with_tool_calls(
    chat_service: ChatService,
    token_limit: int,
) -> list[LanguageModelMessage]:
    # Construct full history from gpt request
    history = _construct_history_from_gpt_request(chat_service)

    if len(history) == 0:
        return []

    # Clean up sources from last assistant message.
    if history[-1].role == ChatRole.ASSISTANT and isinstance(history[-1].content, str):
        history[-1].content = _preprocess_message(history[-1].content)

    # Extract cited sources from assistant messages
    cited_sources = _extract_cited_sources(history)

    # Remove uncited sources from tool messages
    history = _remove_uncited_sources_from_tool_messages(history, cited_sources)

    # Limit to token window
    history = _limit_to_token_window(history, token_limit)

    # Reorder source ids starting from 0
    history = _reorder_source_ids(history)

    return history


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
    encoding_name: EncoderName = EncoderName.O200K_BASE,
) -> LanguageModelMessages:
    encoder = tiktoken.get_encoding(encoding_name)
    token_per_message_reversed = num_tokens_per_language_model_message(
        messages,
        encode=encoder.encode,
    )

    to_take: list[bool] = (np.cumsum(token_per_message_reversed) < token_limit).tolist()
    to_take.reverse()

    return LanguageModelMessages(
        root=[m for m, tt in zip(messages, to_take, strict=False) if tt],
    )
