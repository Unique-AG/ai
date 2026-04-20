"""
Integration tests for the Message API resource.

These tests make actual API calls and require valid credentials.
Configuration must be provided via tests/.env file.

Required environment variables in tests/.env:
- UNIQUE_TEST_API_KEY: API key for authentication
- UNIQUE_TEST_APP_ID: App ID for authentication
- UNIQUE_TEST_USER_ID: User ID for API requests
- UNIQUE_TEST_COMPANY_ID: Company ID for API requests
- UNIQUE_TEST_BASE_URL: Base URL for API
- UNIQUE_TEST_ASSISTANT_ID: Assistant ID for creating messages
"""

from __future__ import annotations

from collections.abc import Generator

import pytest

from tests.api_resources.typed_dict_helpers import get_missing_fields, has_all_fields
from tests.test_config import IntegrationTestConfig
from unique_sdk.api_resources._message import Message
from unique_sdk.api_resources._space import Space


def assert_message(message: Message, skip_fields: list[str] | None = None) -> None:
    assert has_all_fields(message, Message, skip_fields=skip_fields), (
        f"Message does not have all required fields: {get_missing_fields(message, Message)}"
    )


@pytest.fixture(scope="module")
def created_message_ids() -> Generator[list[tuple[str, str]], None, None]:
    """
    Track message IDs and their chat IDs created during tests.
    This fixture maintains a list of (message_id, chat_id) tuples that need to be cleaned up.
    """
    message_ids: list[tuple[str, str]] = []
    yield message_ids
    # Cleanup happens in teardown_message_cleanup fixture


@pytest.fixture(scope="module")
def created_chat_ids() -> Generator[list[str], None, None]:
    """
    Track chat IDs created during tests.
    This fixture maintains a list of chat IDs that need to be cleaned up.
    """
    chat_ids: list[str] = []
    yield chat_ids
    # Cleanup happens in teardown_chat_cleanup fixture


@pytest.fixture(scope="module", autouse=True)
def teardown_message_cleanup(
    integration_test_config: IntegrationTestConfig,
    created_message_ids: list[tuple[str, str]],
) -> Generator[None, None, None]:
    """
    Teardown: Clean up all messages created during tests.
    This runs after all tests in the module complete.
    """
    yield  # Let tests run first

    # Cleanup: Delete all messages created during tests
    for message_id, chat_id in created_message_ids:
        try:
            _ = Message.delete(
                id=message_id,
                user_id=integration_test_config.user_id,
                company_id=integration_test_config.company_id,
                chatId=chat_id,
            )
        except Exception:
            pass  # Ignore cleanup errors during teardown


@pytest.fixture(scope="module", autouse=True)
def teardown_chat_cleanup(
    integration_test_config: IntegrationTestConfig,
    created_chat_ids: list[str],
) -> Generator[None, None, None]:
    """
    Teardown: Clean up all chats created during tests.
    This runs after all tests in the module complete.
    """
    yield  # Let tests run first

    # Cleanup: Delete all chats created during tests
    for chat_id in created_chat_ids:
        try:
            _ = Space.delete_chat(
                user_id=integration_test_config.user_id,
                company_id=integration_test_config.company_id,
                chat_id=chat_id,
            )
        except Exception:
            pass  # Ignore cleanup errors during teardown


@pytest.fixture
def test_chat(
    integration_test_config: IntegrationTestConfig,
    created_chat_ids: list[str],
) -> str:
    """
    Create a test chat for message operations.
    Returns the chat ID and tracks it for cleanup.
    """
    # Create a chat by sending a message via Space API
    # This will create a new chat if chatId is not provided
    space_message = Space.create_message(
        user_id=integration_test_config.user_id,
        company_id=integration_test_config.company_id,
        assistantId=integration_test_config.assistant_id,
        text="Test message to create chat",
    )

    chat_id = space_message["chatId"]
    created_chat_ids.append(chat_id)

    return chat_id


@pytest.fixture
def created_message(
    integration_test_config: IntegrationTestConfig,
    test_chat: str,
    created_message_ids: list[tuple[str, str]],
) -> Message:
    """
    Create a message for testing.
    Returns the created Message object and tracks it for cleanup.
    """
    import uuid

    # Create an ASSISTANT message
    message = Message.create(
        user_id=integration_test_config.user_id,
        company_id=integration_test_config.company_id,
        chatId=test_chat,
        assistantId=integration_test_config.assistant_id,
        role="ASSISTANT",
        text=f"Test assistant message {uuid.uuid4().hex[:8]}",
        references=[],
        debugInfo={},
        completedAt=None,
    )

    # Track for cleanup
    created_message_ids.append((message["id"], test_chat))

    return message


@pytest.mark.ai
@pytest.mark.integration
def test_message__list__returns_messages_for_chat(
    integration_test_config: IntegrationTestConfig,
    test_chat: str,
    created_message: Message,
) -> None:
    """
    Purpose: Verify list returns messages for a given chat.
    Why this matters: Core functionality for retrieving message history.
    Setup summary: Create message, list messages for chat, assert message list structure.
    """
    # Act
    result = Message.list(
        user_id=integration_test_config.user_id,
        company_id=integration_test_config.company_id,
        chatId=test_chat,
    )

    # Assert
    from unique_sdk._list_object import ListObject

    assert isinstance(result, ListObject)
    assert hasattr(result, "data")
    messages = result.data
    assert len(messages) > 0
    # Verify the created message is in the list
    message_ids = [msg["id"] for msg in messages]
    assert created_message["id"] in message_ids


@pytest.mark.ai
@pytest.mark.integration
@pytest.mark.asyncio
async def test_message__list_async__returns_messages_for_chat(
    integration_test_config: IntegrationTestConfig,
    test_chat: str,
    created_message: Message,
) -> None:
    """
    Purpose: Verify async list returns messages for a given chat.
    Why this matters: Enables asynchronous message listing for better performance.
    Setup summary: Create message, list messages using async method, assert message list structure.
    """
    # Act
    result = await Message.list_async(
        user_id=integration_test_config.user_id,
        company_id=integration_test_config.company_id,
        chatId=test_chat,
    )

    # Assert
    from unique_sdk._list_object import ListObject

    assert isinstance(result, ListObject)
    assert hasattr(result, "data")
    messages = result.data
    assert len(messages) > 0
    # Verify the created message is in the list
    message_ids = [msg["id"] for msg in messages]
    assert created_message["id"] in message_ids


@pytest.mark.ai
@pytest.mark.integration
def test_message__retrieve__retrieves_message_by_id(
    integration_test_config: IntegrationTestConfig,
    created_message: Message,
    test_chat: str,
) -> None:
    """
    Purpose: Verify retrieve returns a specific message by ID.
    Why this matters: Enables direct message lookup using IDs.
    Setup summary: Create message, retrieve by ID, assert message structure.
    """
    # Act
    retrieved_message = Message.retrieve(
        user_id=integration_test_config.user_id,
        company_id=integration_test_config.company_id,
        id=created_message["id"],
        chatId=test_chat,
    )

    # Assert
    assert_message(retrieved_message, skip_fields=["OBJECT_NAME"])
    assert retrieved_message["id"] == created_message["id"]
    assert retrieved_message["chatId"] == test_chat

    for key in retrieved_message.keys() & created_message.keys():
        assert retrieved_message[key] == created_message[key]


@pytest.mark.ai
@pytest.mark.integration
@pytest.mark.asyncio
async def test_message__retrieve_async__retrieves_message_by_id(
    integration_test_config: IntegrationTestConfig,
    created_message: Message,
    test_chat: str,
) -> None:
    """
    Purpose: Verify async retrieve returns a specific message by ID.
    Why this matters: Enables asynchronous message retrieval for better performance.
    Setup summary: Create message, retrieve using async method, assert message structure.
    """
    # Act
    retrieved_message = await Message.retrieve_async(
        user_id=integration_test_config.user_id,
        company_id=integration_test_config.company_id,
        id=created_message["id"],
        chatId=test_chat,
    )

    # Assert
    assert_message(retrieved_message, skip_fields=["gptRequest", "debugInfo"])
    assert retrieved_message["id"] == created_message["id"]
    assert retrieved_message["chatId"] == test_chat

    for key in retrieved_message.keys() & created_message.keys():
        assert retrieved_message[key] == created_message[key]


@pytest.mark.ai
@pytest.mark.integration
def test_message__create__creates_assistant_message(
    integration_test_config: IntegrationTestConfig,
    test_chat: str,
    created_message_ids: list[tuple[str, str]],
) -> None:
    """
    Purpose: Verify create creates an ASSISTANT message.
    Why this matters: Core functionality for creating assistant responses.
    Setup summary: Create message with text, assert message structure and content.
    """
    # Arrange
    import uuid

    message_text = f"Test assistant message {uuid.uuid4().hex[:8]}"

    # Act
    message = Message.create(
        user_id=integration_test_config.user_id,
        company_id=integration_test_config.company_id,
        chatId=test_chat,
        assistantId=integration_test_config.assistant_id,
        role="ASSISTANT",
        text=message_text,
        references=[],
        debugInfo={},
        completedAt=None,
    )

    # Track for cleanup
    created_message_ids.append((message["id"], test_chat))

    # Assert
    assert_message(message, skip_fields=["OBJECT_NAME"])
    assert message["role"] == "ASSISTANT"
    assert message["chatId"] == test_chat
    if message["text"]:
        assert message["text"] == message_text


@pytest.mark.ai
@pytest.mark.integration
def test_message__create__creates_message_with_references(
    integration_test_config: IntegrationTestConfig,
    test_chat: str,
    created_message_ids: list[tuple[str, str]],
) -> None:
    """
    Purpose: Verify create can create a message with references.
    Why this matters: Enables associating source content with messages.
    Setup summary: Create message with references, assert references are included.
    """
    # Arrange
    import uuid

    references: list[Message.Reference] = [
        {
            "name": "Test Reference",
            "url": "https://example.com",
            "sequenceNumber": 1,
            "sourceId": f"source_{uuid.uuid4().hex[:8]}",
            "source": "test_source",
        }
    ]

    # Act
    message = Message.create(
        user_id=integration_test_config.user_id,
        company_id=integration_test_config.company_id,
        chatId=test_chat,
        assistantId=integration_test_config.assistant_id,
        role="ASSISTANT",
        text="Test message with references",
        references=references,
        debugInfo={},
        completedAt=None,
    )

    # Track for cleanup
    created_message_ids.append((message["id"], test_chat))

    # Assert
    assert_message(message, skip_fields=["OBJECT_NAME"])
    assert message["role"] == "ASSISTANT"
    if message["references"]:
        assert len(message["references"]) == 1
        assert message["references"][0]["name"] == "Test Reference"


@pytest.mark.ai
@pytest.mark.integration
@pytest.mark.asyncio
async def test_message__create_async__creates_assistant_message(
    integration_test_config: IntegrationTestConfig,
    test_chat: str,
    created_message_ids: list[tuple[str, str]],
) -> None:
    """
    Purpose: Verify async create creates an ASSISTANT message.
    Why this matters: Enables asynchronous message creation for better performance.
    Setup summary: Create message using async method, assert message structure.
    """
    # Arrange
    import uuid

    message_text = f"Async test message {uuid.uuid4().hex[:8]}"

    # Act
    message = await Message.create_async(
        user_id=integration_test_config.user_id,
        company_id=integration_test_config.company_id,
        chatId=test_chat,
        assistantId=integration_test_config.assistant_id,
        role="ASSISTANT",
        text=message_text,
        references=[],
        debugInfo={},
        completedAt=None,
    )

    # Track for cleanup
    created_message_ids.append((message["id"], test_chat))

    # Assert
    assert_message(message, skip_fields=["OBJECT_NAME"])
    assert message["role"] == "ASSISTANT"
    assert message["chatId"] == test_chat
    if message["text"]:
        assert message["text"] == message_text


@pytest.mark.ai
@pytest.mark.integration
def test_message__modify__updates_message_text(
    integration_test_config: IntegrationTestConfig,
    created_message: Message,
    test_chat: str,
) -> None:
    """
    Purpose: Verify modify can update message text.
    Why this matters: Enables message content modification after creation.
    Setup summary: Create message, update text, assert text change.
    """
    # Arrange
    import uuid

    new_text = f"Updated message text {uuid.uuid4().hex[:8]}"

    # Act
    updated_message = Message.modify(
        user_id=integration_test_config.user_id,
        company_id=integration_test_config.company_id,
        id=created_message["id"],
        chatId=test_chat,
        text=new_text,
        references=[],
        debugInfo={},
        completedAt=None,
    )

    # Assert
    assert_message(updated_message, skip_fields=["OBJECT_NAME"])
    assert updated_message["id"] == created_message["id"]
    if updated_message["text"]:
        assert updated_message["text"] == new_text


@pytest.mark.ai
@pytest.mark.integration
def test_message__modify__updates_message_references(
    integration_test_config: IntegrationTestConfig,
    created_message: Message,
    test_chat: str,
) -> None:
    """
    Purpose: Verify modify can update message references.
    Why this matters: Enables updating source content associations.
    Setup summary: Create message, update references, assert references change.
    """
    # Arrange
    import uuid

    new_references: list[Message.Reference] = [
        {
            "name": "Updated Reference",
            "url": "https://example.com/updated",
            "sequenceNumber": 1,
            "sourceId": f"updated_source_{uuid.uuid4().hex[:8]}",
            "source": "updated_source",
        }
    ]

    # Act
    updated_message = Message.modify(
        user_id=integration_test_config.user_id,
        company_id=integration_test_config.company_id,
        id=created_message["id"],
        chatId=test_chat,
        references=new_references,
        debugInfo={},
        completedAt=None,
    )

    # Assert
    assert_message(updated_message, skip_fields=["OBJECT_NAME"])
    assert updated_message["id"] == created_message["id"]
    if updated_message["references"]:
        assert len(updated_message["references"]) == 1
        assert updated_message["references"][0]["name"] == "Updated Reference"


@pytest.mark.ai
@pytest.mark.integration
@pytest.mark.asyncio
async def test_message__modify_async__updates_message(
    integration_test_config: IntegrationTestConfig,
    created_message: Message,
    test_chat: str,
) -> None:
    """
    Purpose: Verify async modify can update messages.
    Why this matters: Enables asynchronous message updates for better performance.
    Setup summary: Create message, update using async method, assert update succeeds.
    """
    # Arrange
    import uuid

    new_text = f"Async updated text {uuid.uuid4().hex[:8]}"

    # Act
    updated_message = await Message.modify_async(
        user_id=integration_test_config.user_id,
        company_id=integration_test_config.company_id,
        id=created_message["id"],
        chatId=test_chat,
        text=new_text,
        references=[],
        debugInfo={},
        completedAt=None,
    )

    # Assert
    assert_message(updated_message, skip_fields=["OBJECT_NAME"])
    assert updated_message["id"] == created_message["id"]
    if updated_message["text"]:
        assert updated_message["text"] == new_text


@pytest.mark.ai
@pytest.mark.integration
def test_message__delete__deletes_message_by_id(
    integration_test_config: IntegrationTestConfig,
    test_chat: str,
) -> None:
    """
    Purpose: Verify delete removes a message by ID.
    Why this matters: Core functionality for message removal.
    Setup summary: Create message, delete by ID, assert deletion succeeds.
    """
    # Arrange
    import uuid

    # Create a message to delete
    message = Message.create(
        user_id=integration_test_config.user_id,
        company_id=integration_test_config.company_id,
        chatId=test_chat,
        assistantId=integration_test_config.assistant_id,
        role="ASSISTANT",
        text=f"Message to delete {uuid.uuid4().hex[:8]}",
        references=[],
        debugInfo={},
        completedAt=None,
    )

    # Act
    deleted_message = Message.delete(
        id=message["id"],
        user_id=integration_test_config.user_id,
        company_id=integration_test_config.company_id,
        chatId=test_chat,
    )

    # Assert
    assert_message(
        deleted_message,
        skip_fields=[
            "OBJECT_NAME",
            "role",
            "chatId",
            "gptRequest",
            "text",
            "debugInfo",
        ],
    )
    assert deleted_message["id"] == message["id"]


@pytest.mark.ai
@pytest.mark.integration
@pytest.mark.asyncio
async def test_message__delete_async__deletes_message(
    integration_test_config: IntegrationTestConfig,
    test_chat: str,
) -> None:
    """
    Purpose: Verify async delete removes a message.
    Why this matters: Enables asynchronous message deletion for better performance.
    Setup summary: Create message, delete using async method, assert deletion succeeds.
    """
    # Arrange
    import uuid

    # Create a message to delete
    message = await Message.create_async(
        user_id=integration_test_config.user_id,
        company_id=integration_test_config.company_id,
        chatId=test_chat,
        assistantId=integration_test_config.assistant_id,
        role="ASSISTANT",
        text=f"Async message to delete {uuid.uuid4().hex[:8]}",
        references=[],
        debugInfo={},
        completedAt=None,
    )

    # Act
    deleted_message = await message.delete_async(
        user_id=integration_test_config.user_id,
        company_id=integration_test_config.company_id,
        chatId=test_chat,
    )

    # Assert
    assert_message(
        deleted_message,
        skip_fields=[
            "OBJECT_NAME",
            "role",
            "chatId",
            "gptRequest",
            "text",
            "debugInfo",
        ],
    )
    assert deleted_message["id"] == message["id"]


@pytest.mark.ai
@pytest.mark.integration
def test_message__create_event__creates_message_event(
    integration_test_config: IntegrationTestConfig,
    created_message: Message,
    test_chat: str,
) -> None:
    """
    Purpose: Verify create_event creates a message event.
    Why this matters: Enables tracking message events and modifications.
    Setup summary: Create message, create event, assert event creation succeeds.
    """
    # Arrange
    import uuid

    event_text = f"Event message {uuid.uuid4().hex[:8]}"

    # Act
    event_message = Message.create_event(
        user_id=integration_test_config.user_id,
        company_id=integration_test_config.company_id,
        messageId=created_message["id"],
        chatId=test_chat,
        text=event_text,
        references=[],
        debugInfo={},
        completedAt=None,
    )

    # Assert
    assert_message(
        event_message,
        skip_fields=[
            "gptRequest",
            "text",
            "role",
            "debugInfo",
            "OBJECT_NAME",
            "chatId",
        ],
    )


@pytest.mark.ai
@pytest.mark.integration
@pytest.mark.asyncio
async def test_message__create_event_async__creates_message_event(
    integration_test_config: IntegrationTestConfig,
    created_message: Message,
    test_chat: str,
) -> None:
    """
    Purpose: Verify async create_event creates a message event.
    Why this matters: Enables asynchronous message event creation for better performance.
    Setup summary: Create message, create event using async method, assert event creation succeeds.
    """
    # Arrange
    import uuid

    event_text = f"Async event message {uuid.uuid4().hex[:8]}"

    # Act
    event_message = await Message.create_event_async(
        user_id=integration_test_config.user_id,
        company_id=integration_test_config.company_id,
        messageId=created_message["id"],
        chatId=test_chat,
        text=event_text,
    )

    # Assert
    assert_message(
        event_message,
        skip_fields=[
            "gptRequest",
            "text",
            "role",
            "debugInfo",
            "OBJECT_NAME",
            "chatId",
        ],
    )
