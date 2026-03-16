from __future__ import annotations

import base64
import logging
import mimetypes
from datetime import datetime
from enum import StrEnum
from itertools import groupby
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from unique_toolkit.language_model.builder import MessagesBuilder

import numpy as np
from pydantic import RootModel

from unique_toolkit._common.token.token_counting import (
    num_tokens_per_language_model_message,
)
from unique_toolkit._common.utils import files as FileUtils
from unique_toolkit.app import ChatEventUserMessage
from unique_toolkit.chat.schemas import ChatMessage, ChatMessageTool
from unique_toolkit.chat.schemas import ChatMessageRole as ChatRole
from unique_toolkit.chat.service import ChatService
from unique_toolkit.content.schemas import Content
from unique_toolkit.content.service import ContentService
from unique_toolkit.language_model import LanguageModelMessageRole as LLMRole
from unique_toolkit.language_model.infos import EncoderName, LanguageModelInfo
from unique_toolkit.language_model.schemas import (
    LanguageModelAssistantMessage,
    LanguageModelFunction,
    LanguageModelMessages,
    LanguageModelToolMessage,
)

_LOGGER = logging.getLogger(__name__)

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


def _append_element_to_builder(
    builder: MessagesBuilder,
    c: ChatMessageWithContents,
    text: str,
    include_images: ImageContentInclusion,
    file_content_serialization_type: FileContentSerialization,
    content_service: ContentService,
    chat_id: str,
) -> None:
    if len(c.contents) > 0:
        file_contents = [co for co in c.contents if FileUtils.is_file_content(co.key)]
        image_contents = [co for co in c.contents if FileUtils.is_image_content(co.key)]
        content = (
            text
            + "\n\n"
            + file_content_serialization(
                file_contents,
                file_content_serialization_type,
            )
        ).strip()
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
        # LanguageModelUserMessage has no field original_text
        text = c.original_text if c.original_text else c.content
        if text is None:
            if c.role == ChatRole.USER:
                raise ValueError(
                    "Content or original_text of LanguageModelMessages should exist.",
                )
            text = ""
        _append_element_to_builder(
            builder=builder,
            c=c,
            text=text,
            include_images=include_images,
            file_content_serialization_type=file_content_serialization_type,
            content_service=content_service,
            chat_id=chat_id,
        )
    return builder.build()


def get_full_history_with_contents_and_tool_calls(
    user_message: ChatEventUserMessage,
    chat_id: str,
    chat_service: ChatService,
    content_service: ContentService,
    include_images: ImageContentInclusion = ImageContentInclusion.ALL,
    file_content_serialization_type: FileContentSerialization = FileContentSerialization.FILE_NAME,
) -> LanguageModelMessages:
    """Build the full LLM message history, including persisted tool call rounds."""
    chat_history = chat_service.get_full_history()

    assistant_message_ids = [
        msg.id for msg in chat_history if msg.role == ChatRole.ASSISTANT and msg.id
    ]
    tool_calls_by_message: dict[str, list[ChatMessageTool]] = {}
    if assistant_message_ids:
        try:
            all_tool_calls = chat_service.get_message_tools(
                message_ids=assistant_message_ids,
            )
            for tc in all_tool_calls:
                if tc.message_id:
                    tool_calls_by_message.setdefault(tc.message_id, []).append(tc)
        except Exception:
            _LOGGER.warning(
                "Failed to batch-load tool calls, falling back to empty", exc_info=True
            )

    grouped_elements = get_chat_history_with_contents(
        user_message=user_message,
        chat_id=chat_id,
        chat_history=chat_history,
        content_service=content_service,
    )

    builder = LanguageModelMessages([]).builder()
    for c in grouped_elements:
        text = c.original_text if c.original_text else c.content
        if text is None:
            if c.role == ChatRole.USER:
                raise ValueError(
                    "Content or original_text of LanguageModelMessages should exist.",
                )
            text = ""

        if c.role == ChatRole.ASSISTANT and c.id and c.id in tool_calls_by_message:
            tc_records = sorted(
                tool_calls_by_message[c.id],
                key=lambda tc: (tc.round_index, tc.sequence_index),
            )
            if tc_records:
                for _round, round_group in groupby(
                    tc_records, key=lambda tc: tc.round_index
                ):
                    round_tcs = list(round_group)
                    # Only include tool calls that have a response; without a
                    # matching LanguageModelToolMessage the assistant message
                    # would reference a tool_call_id that never gets a reply,
                    # which LLM APIs (e.g. OpenAI) reject.
                    round_tcs_with_response = [
                        tc
                        for tc in round_tcs
                        if tc.response and tc.response.content is not None
                    ]
                    if not round_tcs_with_response:
                        continue
                    # Build LanguageModelFunction objects first so we can read
                    # back the post-validator id: the randomize_id validator
                    # replaces an empty string with a UUID, and we must use
                    # the same id in the LanguageModelToolMessage so the
                    # tool_call_id references match.
                    fns = [
                        LanguageModelFunction(
                            id=tc.external_tool_call_id,
                            name=tc.function_name,
                            arguments=tc.arguments,
                        )
                        for tc in round_tcs_with_response
                    ]
                    builder.messages.append(
                        LanguageModelAssistantMessage.from_functions(tool_calls=fns)
                    )
                    for fn, tc in zip(fns, round_tcs_with_response):
                        builder.messages.append(
                            LanguageModelToolMessage(
                                tool_call_id=fn.id,
                                content=tc.response.content,  # type: ignore[union-attr]
                                name=tc.function_name,
                            )
                        )

        # Drop empty assistant messages that had tool calls.
        # When a turn consists only of tool-call rounds (e.g. the loop was
        # cancelled before producing a final prose response), the DB message
        # ends up with text == "". The full turn is already captured by the
        # interleaved ASSISTANT(tool_calls) + TOOL messages emitted above, so
        # appending an empty ASSISTANT message here would waste tokens and can
        # be misread by LLM APIs as a conversation boundary.
        # Note: get_full_history_with_contents does NOT drop this message — it
        # has no tool-call context and treats the empty message as benign.
        had_tool_calls = (
            c.role == ChatRole.ASSISTANT
            and c.id is not None
            and c.id in tool_calls_by_message
        )
        if had_tool_calls and not text:
            continue

        _append_element_to_builder(
            builder=builder,
            c=c,
            text=text,
            include_images=include_images,
            file_content_serialization_type=file_content_serialization_type,
            content_service=content_service,
            chat_id=chat_id,
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
