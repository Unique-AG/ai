from unique_toolkit.language_model.builder import MessagesBuilder
from unique_toolkit.language_model.schemas import (
    LanguageModelAssistantMessage,
    LanguageModelFunction,
    LanguageModelMessages,
    LanguageModelSystemMessage,
    LanguageModelToolMessage,
    LanguageModelUserMessage,
)


def test_system_message_append():
    builder = MessagesBuilder()
    builder.system_message_append("This is a system message.")
    assert len(builder.messages) == 1
    assert isinstance(builder.messages[0], LanguageModelSystemMessage)
    assert builder.messages[0].content == "This is a system message."


def test_user_message_append():
    builder = MessagesBuilder()
    builder.user_message_append("This is a user message.")
    assert len(builder.messages) == 1
    assert isinstance(builder.messages[0], LanguageModelUserMessage)
    assert builder.messages[0].content == "This is a user message."


def test_assistant_message_append():
    builder = MessagesBuilder()
    builder.assistant_message_append("This is an assistant message.")
    assert len(builder.messages) == 1
    assert isinstance(builder.messages[0], LanguageModelAssistantMessage)
    assert builder.messages[0].content == "This is an assistant message."


def test_tool_message_append():
    builder = MessagesBuilder()
    builder.tool_message_append("ToolName", "1234", "This is a tool message.")
    assert len(builder.messages) == 1
    assert isinstance(builder.messages[0], LanguageModelToolMessage)
    assert builder.messages[0].name == "ToolName"
    assert builder.messages[0].tool_call_id == "1234"
    assert builder.messages[0].content == "This is a tool message."


def test_build():
    builder = MessagesBuilder()
    builder.system_message_append("System message")
    builder.user_message_append("User message")
    messages = builder.build()
    assert isinstance(messages, LanguageModelMessages)
    assert len(messages.root) == 2  # Should contain both messages
    assert messages.root[0].content == "System message"
    assert messages.root[1].content == "User message"
    assert len(builder.messages) == 0  # Builder should reset after build


def test_model_dump():
    builder = MessagesBuilder()
    builder.system_message_append("System message")
    dump = builder.model_dump(mode="json")
    assert isinstance(dump, list)
    assert isinstance(dump[0], dict)
    assert dump[0]["role"] == "system"
    assert dump[0]["content"] == "System message"


def test_assistant_message_append_with_tool_calls():
    builder = MessagesBuilder()
    tool_calls = [
        LanguageModelFunction(
            name="weather",
            arguments={
                "query": "current weather in Zurich",
                "language": "English",
                "time_sensitive_query": {
                    "query": "current weather in Zurich March 2025",
                    "time_sensitive_flag": True,
                },
            },
        ),
        LanguageModelFunction(
            name="weather",
            arguments='{"query": "current weather in Zurich", "language": "English", "time_sensitive_query": {"query": "current weather in Zurich March 2025", "time_sensitive_flag": true}}',
        ),
    ]
    builder.assistant_message_append(
        "This is an assistant message with tools.", tool_calls
    )

    assert len(builder.messages) == 1
    assert isinstance(builder.messages[0], LanguageModelAssistantMessage)
    assert builder.messages[0].content == "This is an assistant message with tools."

    # Verify tool calls were properly added
    assert builder.messages[0].tool_calls is not None
    assert len(builder.messages[0].tool_calls) == 2

    # Check first tool call
    assert builder.messages[0].tool_calls[0].function.name == "weather"
    assert builder.messages[0].tool_calls[0].function.arguments == {
        "query": "current weather in Zurich",
        "language": "English",
        "time_sensitive_query": {
            "query": "current weather in Zurich March 2025",
            "time_sensitive_flag": True,
        },
    }

    # Check second tool call
    assert builder.messages[0].tool_calls[1].function.name == "weather"
    assert builder.messages[0].tool_calls[0].function.arguments == {
        "query": "current weather in Zurich",
        "language": "English",
        "time_sensitive_query": {
            "query": "current weather in Zurich March 2025",
            "time_sensitive_flag": True,
        },
    }
