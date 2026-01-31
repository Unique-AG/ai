import base64
import mimetypes
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
from unique_toolkit.language_model import LanguageModelMessageRole as LLMRole
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
    from unique_toolkit.language_model import (
        LanguageModelFunctionCall,
        LanguageModelFunction
    )
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
                if c.role == ChatRole.USER and c.gpt_request is not None:
                    for gpt_request in c.gpt_request:
                        if gpt_request.get('tool_calls'):
                            tool_calls = [
                                LanguageModelFunction(**tool_call['function'])
                                for tool_call in gpt_request.get('tool_calls')
                            ]
                            builder.assistant_message_append(
                                content=gpt_request.get('content'),
                                tool_calls=tool_calls,
                            )
                        
                        
                        if gpt_request.get('name'):
                            builder.tool_message_append(
                                name=gpt_request.get('name'),
                                tool_call_id=gpt_request.get('tool_call_id'),
                                content=gpt_request.get('content'),
                            )
        else:
            builder.message_append(
                role=map_chat_llm_message_role[c.role],
                content=text,
            )
            if c.role == ChatRole.USER and c.gpt_request is not None:
                for gpt_request in c.gpt_request:
                    if gpt_request.get('tool_calls'):
                        tool_calls = [
                            LanguageModelFunction(
                                id=tool_call.get('id'),
                                name=tool_call.get('function', {}).get('name'),
                                arguments=tool_call.get('function', {}).get('arguments'),
                            )
                            for tool_call in gpt_request.get('tool_calls')
                        ]
                        builder.assistant_message_append(
                            content=gpt_request.get('content'),
                            tool_calls=tool_calls,
                        )
                        
                        
                    if gpt_request.get('name') and gpt_request.get('role') == 'tool':
                        builder.tool_message_append(
                            name=gpt_request.get('name'),
                            tool_call_id=gpt_request.get('tool_call_id'),
                            content=gpt_request.get('content'),
                        )
                # builder.assistant_message_append(
                #     content=c.gpt_request[-1].get('content'),
                #     # tool_calls=c.gpt_request[-2].get('tool_calls'),
                # )
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
