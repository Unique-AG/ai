from typing import Any, Self

from unique_toolkit.language_model import (
    LanguageModelAssistantMessage,
    LanguageModelFunction,
    LanguageModelFunctionCall,
    LanguageModelMessage,
    LanguageModelMessageRole,
    LanguageModelMessages,
    LanguageModelSystemMessage,
    LanguageModelToolMessage,
    LanguageModelUserMessage,
)


class MessagesBuilder:
    def __init__(self):
        self.messages: list[LanguageModelMessage] = []

    def append(self, message: LanguageModelMessage) -> Self:
        self.messages.append(message)
        return self

    def message_append(self, role: LanguageModelMessageRole, content: str):
        message = LanguageModelMessage(role=role, content=content)
        self.messages.append(message)
        return self

    def system_message_append(self, content: str) -> Self:
        """Appends a system message to the messages list."""
        message = LanguageModelSystemMessage(content=content)
        self.messages.append(message)
        return self  # Return self to allow method chaining

    def user_message_append(self, content: str) -> Self:
        """Appends a user message to the messages list."""
        message = LanguageModelUserMessage(content=content)
        self.messages.append(message)
        return self  # Return self to allow method chaining

    def image_message_append(
        self,
        content: str,
        images: list[str],
        role: LanguageModelMessageRole = LanguageModelMessageRole.USER,
    ) -> Self:
        final_content: list[dict[str, Any]] = [{"type": "text", "text": content}]
        final_content.extend(
            [
                {
                    "type": "image_url",
                    "imageUrl": {"url": image},
                }
                for image in images
            ],
        )

        message = LanguageModelMessage(
            role=role,
            content=final_content,
        )
        self.messages.append(message)
        return self

    def assistant_message_append(
        self,
        content: str,
        tool_calls: list[LanguageModelFunction] | None = None,
    ) -> Self:
        """Appends an assistant message to the messages list."""
        message = LanguageModelAssistantMessage(content=content)
        if tool_calls:
            message.tool_calls = [
                LanguageModelFunctionCall(
                    id=tool_call.id,
                    type="function",
                    function=tool_call,
                )
                for tool_call in tool_calls
            ]
        self.messages.append(message)
        return self

    def tool_message_append(self, name: str, tool_call_id: str, content: str) -> Self:
        """Appends a tool message to the messages list."""
        message = LanguageModelToolMessage(
            name=name,
            tool_call_id=tool_call_id,
            content=content,
        )
        self.messages.append(message)
        return self

    def build(self, reset: bool = True) -> LanguageModelMessages:
        """Returns the list of messages and resets the builder"""
        messages = LanguageModelMessages(root=self.messages)
        if reset:
            self.messages = []
        return messages

    def model_dump(self, **kwargs):
        """Dumps the LanguageModelMessages model"""
        return self.build().model_dump(**kwargs)
