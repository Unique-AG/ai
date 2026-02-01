import base64
import json
import mimetypes
import re
from datetime import datetime
from enum import StrEnum
from typing import Any, Iterable

import numpy as np
import tiktoken
from pydantic import BaseModel, RootModel

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
)
from unique_toolkit.language_model import (
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


class ToolSource(BaseModel):
    source_number: int
    content: str


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


def _extract_referenced_source_numbers(text: str | None) -> set[int]:
    """Extract source ids referenced in text like [source0], [source1]."""
    # Pattern for [sourceN] where N is the source id (e.g. [source0], [source1])
    SOURCE_REF_PATTERN = re.compile(r"\[source(\d+)\]", re.IGNORECASE)
    if not text:
        return set()
    return {int(m) for m in SOURCE_REF_PATTERN.findall(text)}


def _parse_tool_sources(tool_content: str) -> list[ToolSource]:
    try:
        raw = json.loads(tool_content)
    except (TypeError, json.JSONDecodeError):
        return []

    if isinstance(raw, dict):
        raw = [raw]

    if not isinstance(raw, list):
        return []

    sources: list[ToolSource] = []
    for item in raw:
        if isinstance(item, dict):
            source = ToolSource(**item)
            if source:
                sources.append(source)
    return sources


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

    sources = _parse_tool_sources(tool_content)
    if not sources:
        return tool_content

    trimmed = [
        source.model_dump() for source in sources if source.source_number in referenced
    ]

    return json.dumps(trimmed) if trimmed else "No relevant sources found."


def _last_gpt_request(
    items: Iterable[dict[str, Any]],
    predicate,
) -> dict[str, Any] | None:
    return next((item for item in reversed(list(items)) if predicate(item)), None)


def _last_assistant_with_tool_calls(
    items: Iterable[dict[str, Any]],
) -> dict[str, Any] | None:
    return _last_gpt_request(items, lambda i: bool(i.get("tool_calls")))


def _last_tool_call_content(
    items: Iterable[dict[str, Any]],
) -> dict[str, Any] | None:
    return _last_gpt_request(
        items, lambda i: i.get("role") == ChatRole.TOOL and i.get("name")
    )


def _append_last_tool_calls_and_tool_message(
    builder,
    gpt_request: list[dict[str, Any]],
    original_content_from_next: str | None = None,
) -> None:
    """Append only the last assistant (with tool_calls) and last tool message.
    Ensures idempotency: only one assistant_message_append and one
    tool_message_append per gpt_request list on each iteration of grouped_elements.
    When trimming tool content to used sources, uses original_content_from_next
    (the original_content of the next item in grouped_elements) when provided.
    """
    assistant_tool_calls = _last_assistant_with_tool_calls(gpt_request)
    tool_calls_content = _last_tool_call_content(gpt_request)

    if assistant_tool_calls:
        builder.assistant_message_append(
            content=assistant_tool_calls.get("content"),
            tool_calls=[
                LanguageModelFunction.from_tool_call(tc)
                for tc in assistant_tool_calls.get("tool_calls", [])
            ],
        )

    if tool_calls_content:
        builder.tool_message_append(
            name=tool_calls_content.get("name"),
            tool_call_id=tool_calls_content.get("tool_call_id"),
            content=_trim_tool_content_to_used_sources(
                original_content_from_next,
                tool_calls_content.get("content"),
            ),
        )


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
