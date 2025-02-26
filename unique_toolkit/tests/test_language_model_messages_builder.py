from unique_toolkit.language_model import (
    LanguageModelMessageRole,
    LanguageModelMessages,
)


def test_existing_messages_builder():
    """Test creating a builder from existing messages."""
    # Create initial messages
    initial_builder = LanguageModelMessages([]).builder()
    initial_messages = (
        initial_builder.system_message_append("You are a helpful assistant.")
        .user_message_append("Hello!")
        .build()
    )

    # Create a builder from existing messages
    builder = initial_messages.builder()

    # Add more messages
    updated_messages = (
        builder.assistant_message_append("How can I help you today?")
        .user_message_append("Tell me about Python.")
        .build()
    )

    # Verify the messages
    assert len(updated_messages.root) == 4
    assert updated_messages.root[0].role == LanguageModelMessageRole.SYSTEM
    assert updated_messages.root[0].content == "You are a helpful assistant."
    assert updated_messages.root[1].role == LanguageModelMessageRole.USER
    assert updated_messages.root[1].content == "Hello!"
    assert updated_messages.root[2].role == LanguageModelMessageRole.ASSISTANT
    assert updated_messages.root[2].content == "How can I help you today?"
    assert updated_messages.root[3].role == LanguageModelMessageRole.USER
    assert updated_messages.root[3].content == "Tell me about Python."

    # Verify original messages are unchanged
    assert len(initial_messages.root) == 2


def test_tool_message():
    """Test adding tool messages."""
    builder = LanguageModelMessages([]).builder()

    messages = (
        builder.system_message_append("You are a helpful assistant.")
        .user_message_append("What's the weather?")
        .assistant_message_append("I'll check the weather for you.")
        .tool_message_append(
            name="get_weather",
            tool_call_id="call_123",
            content='{"temperature": 72, "condition": "sunny"}',
        )
        .build()
    )

    # Verify the tool message
    assert len(messages.root) == 4
    assert messages.root[3].role == LanguageModelMessageRole.TOOL
    assert messages.root[3].name == "get_weather"
    assert messages.root[3].tool_call_id == "call_123"
    assert messages.root[3].content == '{"temperature": 72, "condition": "sunny"}'


def test_image_message():
    """Test adding image messages."""
    builder = LanguageModelMessages([]).builder()

    messages = builder.image_message_append(
        content="What's in this image?", images=["https://example.com/image.jpg"]
    ).build()

    # Verify the image message
    assert len(messages.root) == 1
    assert messages.root[0].role == LanguageModelMessageRole.USER
    assert isinstance(messages.root[0].content, list)
    assert messages.root[0].content[0]["type"] == "text"
    assert messages.root[0].content[0]["text"] == "What's in this image?"
    assert messages.root[0].content[1]["type"] == "image_url"
    assert (
        messages.root[0].content[1]["imageUrl"]["url"]
        == "https://example.com/image.jpg"
    )
