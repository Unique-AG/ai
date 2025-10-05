"""Integration tests for message operations using generated SDK."""

import pytest

import unique_toolkit.generated.generated_routes.public as unique_SDK
from unique_toolkit.generated.generated_routes.public.messages.models import Role


@pytest.mark.integration
@pytest.mark.ai_generated
class TestMessageOperations:
    """Test message operations with generated SDK."""

    def test_message_create__creates_message__successfully(
        self, request_context, integration_env, cleanup_items
    ):
        """
        Purpose: Verify message creation works with generated SDK.
        Why: Message creation is core SDK functionality.
        Setup: Chat ID from test.env, request context.
        """
        # Arrange
        test_chat_id = integration_env.get("test_chat_id")
        test_assistant_id = integration_env.get("test_assistant_id")

        if not test_chat_id or not test_assistant_id:
            pytest.skip("TEST_CHAT_ID and TEST_ASSISTANT_ID required in test.env")

        # Act
        response = unique_SDK.messages.Create.request(
            context=request_context,
            chat_id=test_chat_id,
            assistant_id=test_assistant_id,
            original_text="Integration test message",
            role=Role.user,
            references=[],
            gpt_request={},
            debug_info={"test": "integration"},
            completed_at=None,
        )

        # Assert
        assert response is not None
        assert hasattr(response, "id") or (
            isinstance(response, dict) and "id" in response
        )

        # Track for potential cleanup
        message_id = response.id if hasattr(response, "id") else response.get("id")
        if message_id:
            cleanup_items.append(("message", message_id))

    def test_messages_find_all__retrieves_messages__for_chat(
        self, request_context, integration_env
    ):
        """
        Purpose: Verify message list retrieval with query parameters.
        Why: Query parameter handling is important SDK feature.
        Setup: Existing chat ID from test.env.
        """
        # Arrange
        test_chat_id = integration_env.get("test_chat_id")
        if not test_chat_id:
            pytest.skip("TEST_CHAT_ID required in test.env")

        # Act
        response = unique_SDK.messages.FindAll.request(
            context=request_context,
            chat_id=test_chat_id,
        )

        # Assert
        assert response is not None
        # Response should be a list or have data attribute
        if hasattr(response, "data"):
            assert isinstance(response.data, list)
        elif isinstance(response, dict):
            assert "data" in response
            assert isinstance(response["data"], list)


@pytest.mark.integration
@pytest.mark.ai_generated
class TestMessageCRUD:
    """Test complete message lifecycle."""

    def test_message_lifecycle__create_read_delete__works_correctly(
        self, request_context, integration_env
    ):
        """
        Purpose: Verify complete message CRUD cycle with generated SDK.
        Why: End-to-end workflow validation ensures SDK usability.
        Setup: Chat and assistant IDs from test.env.
        """
        # Arrange
        test_chat_id = integration_env.get("test_chat_id")
        test_assistant_id = integration_env.get("test_assistant_id")

        if not test_chat_id or not test_assistant_id:
            pytest.skip("TEST_CHAT_ID and TEST_ASSISTANT_ID required")

        message_id = None

        try:
            # Act 1: Create message
            create_response = unique_SDK.messages.Create.request(
                context=request_context,
                chat_id=test_chat_id,
                assistant_id=test_assistant_id,
                original_text="CRUD test message",
                role=Role.user,
                references=[],
                gpt_request={},
                debug_info={},
                completed_at=None,
            )

            # Assert: Creation succeeded
            assert create_response is not None
            message_id = (
                create_response.id
                if hasattr(create_response, "id")
                else create_response.get("id")
            )
            assert message_id is not None

            # Act 2: Retrieve message
            get_response = unique_SDK.messages.id.FindOne.request(
                context=request_context,
                id=message_id,
            )

            # Assert: Retrieved successfully
            assert get_response is not None
            retrieved_id = (
                get_response.id
                if hasattr(get_response, "id")
                else get_response.get("id")
            )
            assert retrieved_id == message_id

            # Act 3: Update message (if update endpoint exists)
            # Act 4: Delete message
            delete_response = unique_SDK.messages.id.Delete.request(
                context=request_context,
                id=message_id,
            )

            # Assert: Deletion succeeded
            assert delete_response is not None
            message_id = None  # Cleared after successful deletion

        finally:
            # Cleanup: Delete if still exists
            if message_id:
                try:
                    unique_SDK.messages.id.Delete.request(
                        context=request_context,
                        id=message_id,
                    )
                except Exception:
                    pass  # Already deleted or doesn't exist
