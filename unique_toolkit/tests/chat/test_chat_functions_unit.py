from unittest.mock import patch

import pytest
import unique_sdk

from unique_toolkit.chat.functions import (
    ChatMessage,
    ChatMessageRole,
    create_message,
    create_message_async,
    filter_valid_messages,
    get_full_history,
    get_selection_from_history,
    list_messages_async,
    map_references,
    modify_message,
    modify_message_async,
    pick_messages_in_reverse_for_token_window,
    stream_complete_to_chat,
    stream_complete_to_chat_async,
)
from unique_toolkit.content.schemas import ContentReference
from unique_toolkit.language_model.infos import LanguageModelName
from unique_toolkit.language_model.schemas import LanguageModelMessages


@pytest.fixture
def mock_sdk():
    with patch("unique_toolkit.chat.functions.unique_sdk") as mock:
        yield mock


@pytest.fixture
def sample_message_data():
    return {
        "user_id": "user123",
        "company_id": "company123",
        "chat_id": "chat123",
        "assistant_id": "assistant123",
        "content": "Hello world",
        "role": ChatMessageRole.USER,
        "id": "msg123",
        "references": [],
        "debugInfo": None,
    }


def test_modify_message(mock_sdk, sample_message_data):
    # Setup
    mock_sdk.Message.modify.return_value = sample_message_data

    # Execute
    result = modify_message(
        user_id="user123",
        company_id="company123",
        assistant_message_id="asst123",
        chat_id="chat123",
        user_message_id="user123",
        user_message_text="Hello",
        assistant=True,
        content="Modified content",
    )

    # Assert
    assert isinstance(result, ChatMessage)
    mock_sdk.Message.modify.assert_called_once()
    assert result.content == "Hello world"


def test_create_message(mock_sdk, sample_message_data):
    # Setup
    mock_sdk.Message.create.return_value = sample_message_data

    # Execute
    result = create_message(
        user_id="user123",
        company_id="company123",
        chat_id="chat123",
        assistant_id="assistant123",
        role=ChatMessageRole.USER,
        content="Hello world",
    )

    # Assert
    assert isinstance(result, ChatMessage)
    mock_sdk.Message.create.assert_called_once()
    assert result.content == "Hello world"


def test_get_full_history(mock_sdk):
    # Setup
    mock_messages = {
        "data": [
            {
                "text": "Message 1",
                "role": "USER",
                "id": "msg1",
                "content": "Message 1",
                "object": None,
                "debug_info": {},
                "chatId": "chat123",
            },
            {
                "text": "Message 2",
                "role": "ASSISTANT",
                "id": "msg2",
                "content": "Message 2",
                "object": None,
                "debug_info": {},
                "chatId": "chat123",
            },
            {
                "text": "[SYSTEM] System message",
                "role": "SYSTEM",
                "id": "msg3",
                "content": "[SYSTEM] System message",
                "object": None,
                "debug_info": {},
                "chatId": "chat123",
            },
        ]
    }
    mock_sdk.Message.list.return_value = mock_messages

    # Execute
    result = get_full_history("user123", "company123", "chat123")

    # Assert
    assert len(result) == 1  # Only first message should remain after filtering
    assert all(isinstance(msg, ChatMessage) for msg in result)


def test_get_selection_from_history():
    # Setup
    messages = [
        ChatMessage(
            id="1",
            role=ChatMessageRole.USER,
            text="Short message 1",
            chat_id="chat123",
        ),
        ChatMessage(
            id="2",
            role=ChatMessageRole.ASSISTANT,
            text="Short message 2",
            chat_id="chat123",
        ),
        ChatMessage(
            id="3",
            role=ChatMessageRole.USER,
            text="Short message 3",
            chat_id="chat123",
        ),
    ]

    # Execute
    result = get_selection_from_history(messages, max_tokens=100)

    # Assert
    assert len(result) > 0
    assert all(isinstance(msg, ChatMessage) for msg in result)
    assert result[-1].content == "Short message 3"  # Last message should be preserved


@pytest.mark.asyncio
async def test_modify_message_async(mock_sdk, sample_message_data):
    # Setup
    async def async_return():
        return sample_message_data

    mock_sdk.Message.modify_async.return_value = async_return()

    # Execute
    result = await modify_message_async(
        user_id="user123",
        company_id="company123",
        assistant_message_id="asst123",
        chat_id="chat123",
        user_message_id="user123",
        user_message_text="Hello",
        assistant=True,
        content="Modified content",
    )

    # Assert
    assert isinstance(result, ChatMessage)
    mock_sdk.Message.modify_async.assert_called_once()
    assert result.content == "Hello world"


def test_modify_message_with_references(mock_sdk, sample_message_data):
    # Setup
    mock_sdk.Message.modify.return_value = sample_message_data
    references = [
        ContentReference(
            id="ref123",
            message_id="msg123",
            name="Test Doc",
            url="http://example.com",
            sequence_number=1,
            source_id="src123",
            source="web",
        )
    ]

    # Execute
    result = modify_message(
        user_id="user123",
        company_id="company123",
        assistant_message_id="asst123",
        chat_id="chat123",
        user_message_id="user123",
        user_message_text="Hello",
        assistant=True,
        content="Modified content",
        references=references,
    )

    # Assert
    assert isinstance(result, ChatMessage)
    mock_sdk.Message.modify.assert_called_once()
    call_kwargs = mock_sdk.Message.modify.call_args[1]
    assert "references" in call_kwargs
    assert isinstance(call_kwargs["references"], list)


@pytest.mark.asyncio
async def test_create_message_async(mock_sdk, sample_message_data):
    # Setup
    async def async_return():
        return sample_message_data

    mock_sdk.Message.create_async.return_value = async_return()

    # Execute
    result = await create_message_async(
        user_id="user123",
        company_id="company123",
        chat_id="chat123",
        assistant_id="assistant123",
        role=ChatMessageRole.ASSISTANT,
        content="Hello world",
    )

    # Assert
    assert isinstance(result, ChatMessage)
    mock_sdk.Message.create_async.assert_called_once()
    assert result.content == "Hello world"


def test_map_references():
    # Setup
    references = [
        ContentReference(
            id="ref123",
            message_id="msg123",
            name="Test Doc",
            url="http://example.com",
            sequence_number=1,
            source_id="src123",
            source="web",
        )
    ]

    # Execute
    result = map_references(references)

    # Assert
    assert isinstance(result, list)
    assert len(result) == 1
    assert result[0]["name"] == "Test Doc"
    assert result[0]["url"] == "http://example.com"
    assert result[0]["sequenceNumber"] == 1
    assert result[0]["sourceId"] == "src123"
    assert result[0]["source"] == "web"


@pytest.mark.asyncio
async def test_list_messages_async(mock_sdk):
    # Setup
    mock_messages = {
        "data": [
            {
                "text": "Message 1",
                "role": "USER",
                "id": "msg1",
                "content": "Message 1",
                "object": None,
                "debug_info": {},
            }
        ]
    }

    async def async_return():
        return mock_messages

    mock_sdk.Message.list_async.return_value = async_return()

    # Execute
    result = await list_messages_async("user123", "company123", "chat123")

    # Assert
    mock_sdk.Message.list_async.assert_called_once_with(
        user_id="user123", company_id="company123", chatId="chat123"
    )
    assert result == mock_messages


def test_filter_valid_messages():
    # Setup
    messages = {
        "data": [
            {"text": "Valid message 1", "role": "USER", "id": "msg1"},
            {
                "text": None,
                "role": "USER",
                "id": "msg2",
            },  # Should be filtered out because text is None
            {
                "text": "[SYSTEM] System message",  # Should be filtered out because role is SYSTEM
                "role": "SYSTEM",
                "id": "msg3",
            },
            {
                "text": "Invalid message 3",
                "role": "USER",
                "id": "msg4",
            },  # Should be filtered out because last two messages are from the same user
            {
                "text": "Invalid message 5",
                "role": "ASSISTANT",
                "id": "msg5",
            },  # Should be filtered out because last two messages are from the same user
        ]
    }

    # Execute
    result = filter_valid_messages(messages)  # type: ignore

    # Assert
    assert len(result) == 1
    assert result[0]["text"] == "Valid message 1"


def test_pick_messages_in_reverse_for_token_window():
    # Setup
    messages = [
        ChatMessage(
            id="1",
            role=ChatMessageRole.USER,
            text="Short message 1",
            chat_id="chat123",
        ),
        ChatMessage(
            id="2",
            role=ChatMessageRole.ASSISTANT,
            text="Short message 2",
            chat_id="chat123",
        ),
        ChatMessage(
            id="3",
            role=ChatMessageRole.USER,
            text="A very long message that should exceed the token limit " * 10,
            chat_id="chat123",
        ),
    ]

    # Execute
    result = pick_messages_in_reverse_for_token_window(messages, limit=50)

    # Assert
    assert len(result) > 0
    assert result[-1].content
    assert result[-1].content.endswith("...")  # Verify message was truncated


def test_pick_messages_in_reverse_for_token_window_empty():
    # Test edge cases
    assert pick_messages_in_reverse_for_token_window([], 100) == []
    assert (
        pick_messages_in_reverse_for_token_window(
            [
                ChatMessage(
                    id="1", role=ChatMessageRole.USER, text="test", chat_id="chat123"
                )
            ],
            0,
        )
        == []
    )


@patch.object(unique_sdk.Integrated, "chat_stream_completion")
def test_stream_complete_basic(mock_stream):
    mock_stream.return_value = {
        "message": {
            "id": "test_message",
            "previousMessageId": "test_previous_message",
            "role": "ASSISTANT",
            "text": "Streamed response",
            "originalText": "Streamed response original",
        }
    }

    messages = LanguageModelMessages([])
    result = stream_complete_to_chat(
        company_id="test_company",
        user_id="test_user",
        assistant_message_id="test_assistant_msg",
        user_message_id="test_user_msg",
        chat_id="test_chat",
        assistant_id="test_assistant",
        messages=messages,
        model_name=LanguageModelName.AZURE_GPT_4_0613,
    )

    assert result.message.text == "Streamed response"
    mock_stream.assert_called_once()


@pytest.mark.asyncio
@patch.object(unique_sdk.Integrated, "chat_stream_completion_async")
async def test_stream_complete_async_basic(mock_stream):
    mock_stream.return_value = {
        "message": {
            "id": "test_message",
            "previousMessageId": "test_previous_message",
            "role": "ASSISTANT",
            "text": "Streamed response",
            "originalText": "Streamed response original",
        }
    }

    messages = LanguageModelMessages([])
    result = await stream_complete_to_chat_async(
        company_id="test_company",
        user_id="test_user",
        assistant_message_id="test_assistant_msg",
        user_message_id="test_user_msg",
        chat_id="test_chat",
        assistant_id="test_assistant",
        messages=messages,
        model_name=LanguageModelName.AZURE_GPT_4_0613,
    )

    assert result.message.text == "Streamed response"
    mock_stream.assert_called_once()
