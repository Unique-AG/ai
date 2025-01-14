from unique_toolkit.language_model import (
    LanguageModelAssistantMessage,
    LanguageModelMessage,
    LanguageModelMessages,
    LanguageModelSystemMessage,
    LanguageModelToolMessage,
    LanguageModelUserMessage,
)


class MessagesBuilder:
    def __init__(self):
        self.messages: list[LanguageModelMessage] = []

    def system_message_append(self, content):
        """Appends a user message to the messages list."""
        message = LanguageModelSystemMessage(content=content)
        self.messages.append(message)
        return self  # Return self to allow method chaining

    def user_message_append(self, content):
        """Appends a user message to the messages list."""
        message = LanguageModelUserMessage(content=content)
        self.messages.append(message)
        return self  # Return self to allow method chaining

    def assistant_message_append(self, content):
        """Appends an assistant message to the messages list."""
        message = LanguageModelAssistantMessage(content=content)
        self.messages.append(message)
        return self  # Return self to allow method chaining

    def tool_message_append(self, name: str, tool_call_id: str, content: str):
        """Appends a tool message to the messages list."""
        message = LanguageModelToolMessage(
            name=name, tool_call_id=tool_call_id, content=content
        )
        self.messages.append(message)
        return self  # Return self to allow method chaining

    def build(self, reset: bool = True) -> LanguageModelMessages:
        """Returns the list of messages and resets the builder"""
        messages = LanguageModelMessages(root=self.messages)
        if reset:
            self.messages = []
        return messages

    def model_dump(self, **kwargs):
        """Dumps the LanguageModelMessages model"""
        return self.build().model_dump(**kwargs)
