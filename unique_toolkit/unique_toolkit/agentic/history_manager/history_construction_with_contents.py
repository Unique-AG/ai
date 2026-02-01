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
    num_tokens_per_language_model_message,
)
from unique_toolkit._common.utils import files as FileUtils
from unique_toolkit.app import ChatEventUserMessage
from unique_toolkit.chat.schemas import ChatMessage
from unique_toolkit.chat.schemas import ChatMessageRole as ChatRole
from unique_toolkit.chat.service import ChatService
from unique_toolkit.content.schemas import Content
from unique_toolkit.content.service import ContentService
from unique_toolkit.language_model import (
    LanguageModelFunction,
    LanguageModelMessageRole as LLMRole,
)
from unique_toolkit.language_model.infos import EncoderName
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


# Pattern for [sourceN] where N is the source id (e.g. [source0], [source1])
_SOURCE_REF_PATTERN = re.compile(r"\[source(\d+)\]", re.IGNORECASE)


def _extract_referenced_source_numbers(text: str | None) -> set[int]:
    """Extract source ids referenced in text like [source0], [source1]."""
    if not text:
        return set()
    return {int(m) for m in _SOURCE_REF_PATTERN.findall(text)}


def _trim_tool_content_to_used_sources(
    original_content: str | None,
    tool_content: str | None,
) -> str:
    """Keep only sources that are referenced in original_content.

    original_content uses citations like [source0], [source1].
    tool_content is a JSON string: list of {source_number: id, content: "..."}.
    Returns trimmed JSON string with only referenced sources.
    """
    if not tool_content or not tool_content.strip():
        return tool_content or ""
    referenced = _extract_referenced_source_numbers(original_content)
    if not referenced:
        return tool_content
    try:
        data = json.loads(tool_content)
    except (json.JSONDecodeError, TypeError):
        return tool_content
    def _source_num_in_refs(item: dict) -> bool:
        sn = item.get("source_number")
        if sn is None:
            return False
        try:
            return int(sn) in referenced
        except (TypeError, ValueError):
            return False

    if isinstance(data, list):
        trimmed = [
            item
            for item in data
            if isinstance(item, dict) and _source_num_in_refs(item)
        ]
        return json.dumps(trimmed) if trimmed else "No relevant sources found."
    if isinstance(data, dict) and _source_num_in_refs(data):
        return tool_content
    if isinstance(data, dict):
        return "No relevant sources found."
    return tool_content


def _append_last_tool_calls_and_tool_message(
    builder,
    gpt_request: list,
    original_content_from_next: str | None = None,
) -> None:
    """Append only the last assistant (with tool_calls) and last tool message.

    Ensures idempotency: only one assistant_message_append and one
    tool_message_append per gpt_request list on each iteration of grouped_elements.

    When trimming tool content to used sources, uses original_content_from_next
    (the original_content of the next item in grouped_elements) when provided.
    """
    last_assistant_with_tool_calls = None
    last_tool_message = None
    for item in gpt_request:
        if item.get("tool_calls"):
            last_assistant_with_tool_calls = item
        if item.get("name") and item.get("role") == "tool":
            last_tool_message = item
    if last_assistant_with_tool_calls is not None:
        tool_calls = [
            LanguageModelFunction.from_tool_call(tc)
            for tc in last_assistant_with_tool_calls.get("tool_calls", [])
        ]
        builder.assistant_message_append(
            content=last_assistant_with_tool_calls.get("content"),
            tool_calls=tool_calls,
        )
    if last_tool_message is not None:
        tool_content = last_tool_message.get("content")
        trimmed_content = _trim_tool_content_to_used_sources(
            original_content=original_content_from_next,
            tool_content=tool_content,
        )
        builder.tool_message_append(
            name=last_tool_message.get("name"),
            tool_call_id=last_tool_message.get("tool_call_id"),
            content=trimmed_content,
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


def get_full_history_with_contents_with_tools(
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
    for i, c in enumerate(grouped_elements):
        # LanguageModelUserMessage has not field original content
        text = c.original_content if c.original_content else c.content
        if text is None:
            if c.role == ChatRole.USER:
                raise ValueError(
                    "Content or original_content of LanguageModelMessages should exist.",
                )
            text = ""
        # When there's gpt_request, use original_content of the next grouped_elements item for trimming sources
        next_c = grouped_elements[i + 1] if i + 1 < len(grouped_elements.root) else None
        original_content_from_next = (
            (next_c.original_content or next_c.content) if next_c else None
        )
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
                if c.role == ChatRole.USER and c.gpt_request is not None:
                    _append_last_tool_calls_and_tool_message(
                        builder=builder,
                        gpt_request=c.gpt_request,
                        original_content_from_next=original_content_from_next,
                    )
        else:
            builder.message_append(
                role=map_chat_llm_message_role[c.role],
                content=text,
            )
            if c.role == ChatRole.USER and c.gpt_request is not None:
                _append_last_tool_calls_and_tool_message(
                    builder=builder,
                    gpt_request=c.gpt_request,
                    original_content_from_next=original_content_from_next,
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
