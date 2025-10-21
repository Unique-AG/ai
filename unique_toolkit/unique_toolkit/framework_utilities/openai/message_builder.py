import base64
import mimetypes
from collections.abc import Iterable
from pathlib import Path
from typing import Self, overload

from openai.types.chat.chat_completion_assistant_message_param import (
    Audio,
    ChatCompletionAssistantMessageParam,
    ContentArrayOfContentPart,
    FunctionCall,
)
from openai.types.chat.chat_completion_content_part_image_param import (
    ChatCompletionContentPartImageParam,
    ImageURL,
)
from openai.types.chat.chat_completion_content_part_param import (
    ChatCompletionContentPartParam,
)
from openai.types.chat.chat_completion_content_part_text_param import (
    ChatCompletionContentPartTextParam,
)
from openai.types.chat.chat_completion_developer_message_param import (
    ChatCompletionDeveloperMessageParam,
)
from openai.types.chat.chat_completion_function_message_param import (
    ChatCompletionFunctionMessageParam,
)
from openai.types.chat.chat_completion_message_param import ChatCompletionMessageParam
from openai.types.chat.chat_completion_message_tool_call_param import (
    ChatCompletionMessageToolCallParam,
)
from openai.types.chat.chat_completion_system_message_param import (
    ChatCompletionSystemMessageParam,
)
from openai.types.chat.chat_completion_tool_message_param import (
    ChatCompletionToolMessageParam,
)
from openai.types.chat.chat_completion_user_message_param import (
    ChatCompletionUserMessageParam,
)
from typing_extensions import Literal


class OpenAIUserMessageBuilder:
    def __init__(
        self,
    ) -> None:
        self._messages: list[ChatCompletionContentPartParam] = []

    def append_text(self, content: str) -> Self:
        part = ChatCompletionContentPartTextParam(
            type="text",
            text=content,
        )
        self._messages.append(part)
        return self

    @overload
    def append_image(
        self, *, url: str, detail: Literal["auto", "low", "high"] = "auto"
    ) -> Self: ...

    @overload
    def append_image(
        self, *, path: Path, detail: Literal["auto", "low", "high"] = "auto"
    ) -> Self: ...

    @overload
    def append_image(
        self,
        *,
        content: bytes,
        mime_type: str,
        detail: Literal["auto", "low", "high"] = "auto",
    ) -> Self: ...

    def append_image(
        self,
        *,
        url: str | None = None,
        path: Path | None = None,
        content: bytes | None = None,
        mime_type: str | None = None,
        detail: Literal["auto", "low", "high"] = "auto",
    ) -> Self:
        if url is None and path is None and (content is None or mime_type is None):
            raise ValueError("Either url or path must be provided")

        if path is not None:
            # Read image file and encode as base64 data URI
            image_data = path.read_bytes()
            base64_image = base64.b64encode(image_data).decode("utf-8")
            mime_type = mimetypes.guess_type(str(path))[0] or "image/jpeg"
            url = f"data:{mime_type};base64,{base64_image}"

        if content is not None and mime_type is not None:
            base64_image = base64.b64encode(content).decode("utf-8")
            url = f"data:{mime_type};base64,{base64_image}"

        image_url = ImageURL(url=url or "", detail=detail)
        part = ChatCompletionContentPartImageParam(
            type="image_url",
            image_url=image_url,
        )
        self._messages.append(part)
        return self

    @property
    def user_message(self) -> ChatCompletionUserMessageParam:
        return ChatCompletionUserMessageParam(
            content=self._messages,
            role="user",
        )

    @property
    def iterable_content(self) -> Iterable[ChatCompletionContentPartParam]:
        return self._messages


class OpenAIMessageBuilder:
    def __init__(
        self,
        messages: list[ChatCompletionMessageParam] | None = None,
    ) -> None:
        self._messages: list[ChatCompletionMessageParam] = []
        if messages:
            self._messages = messages

    @classmethod
    def from_messages(cls, messages: list[ChatCompletionMessageParam]) -> Self:
        builder = cls()
        builder._messages = messages.copy()
        return builder

    def append(self, message: ChatCompletionMessageParam):
        self._messages.append(message)

    def system_message_append(
        self,
        content: str | Iterable[ChatCompletionContentPartTextParam],
        name: str = "system",
    ) -> Self:
        self._messages.append(
            ChatCompletionSystemMessageParam(
                content=content,
                role="system",
            ),
        )
        return self

    def user_message_append(
        self,
        content: str | Iterable[ChatCompletionContentPartParam],
        name: str = "user",
    ) -> Self:
        self._messages.append(
            ChatCompletionUserMessageParam(
                content=content,
                role="user",
            ),
        )
        return self

    def assistant_message_append(
        self,
        content: str | Iterable[ContentArrayOfContentPart] | None = None,
        name: str = "assistant",
        audio: Audio | None = None,
        function_call: FunctionCall | None = None,
        refusal: str | None = None,
        tool_calls: Iterable[ChatCompletionMessageToolCallParam] | None = None,
    ) -> Self:
        self._messages.append(
            ChatCompletionAssistantMessageParam(
                content=content,
                role="assistant",
                audio=audio,
                function_call=function_call,
                refusal=refusal,
                tool_calls=tool_calls or [],
            ),
        )
        return self

    def developper_message_append(
        self,
        content: str | Iterable[ChatCompletionContentPartTextParam],
        name: str = "developer",
    ) -> Self:
        self._messages.append(
            ChatCompletionDeveloperMessageParam(
                content=content,
                role="developer",
            ),
        )
        return self

    def function_message_append(
        self,
        content: str | None,
        name: str = "function",
    ) -> Self:
        self._messages.append(
            ChatCompletionFunctionMessageParam(
                content=content,
                role="function",
                name=name,
            ),
        )
        return self

    def tool_message_append(
        self,
        content: str | Iterable[ChatCompletionContentPartTextParam],
        tool_call_id: str,
    ) -> Self:
        self._messages.append(
            ChatCompletionToolMessageParam(
                content=content,
                role="tool",
                tool_call_id=tool_call_id,
            ),
        )
        return self

    @property
    def messages(self) -> list[ChatCompletionMessageParam]:
        return self._messages
