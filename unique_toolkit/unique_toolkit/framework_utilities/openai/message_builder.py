from collections.abc import Iterable
from typing import Self

from openai.types.chat.chat_completion_assistant_message_param import (
    ChatCompletionAssistantMessageParam,
    ContentArrayOfContentPart,
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
from openai.types.chat.chat_completion_system_message_param import (
    ChatCompletionSystemMessageParam,
)
from openai.types.chat.chat_completion_tool_message_param import (
    ChatCompletionToolMessageParam,
)
from openai.types.chat.chat_completion_user_message_param import (
    ChatCompletionUserMessageParam,
)


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

    def append_system_message(
        self,
        content: str | Iterable[ChatCompletionContentPartTextParam],
        name: str = "user",
    ) -> Self:
        self._messages.append(
            ChatCompletionSystemMessageParam(
                content=content,
                role="system",
                name=name,
            ),
        )
        return self

    def append_user_message(
        self,
        content: str | Iterable[ChatCompletionContentPartParam],
        name: str = "user",
    ) -> Self:
        self._messages.append(
            ChatCompletionUserMessageParam(
                content=content,
                role="user",
                name=name,
            ),
        )
        return self

    def append_assistant_message(
        self,
        content: str | Iterable[ContentArrayOfContentPart],
        name: str = "assistant",
    ) -> Self:
        self._messages.append(
            ChatCompletionAssistantMessageParam(
                content=content,
                role="assistant",
                name=name,
            ),
        )
        return self

    def append_developper_message(
        self,
        content: str | Iterable[ChatCompletionContentPartTextParam],
        name: str = "developer",
    ) -> Self:
        self._messages.append(
            ChatCompletionDeveloperMessageParam(
                content=content,
                role="developer",
                name=name,
            ),
        )
        return self

    def append_function_message(
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

    def append_tool_message(
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
