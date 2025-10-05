"""Integration tests for space operations using generated SDK."""

import pytest

import unique_toolkit.generated.generated_routes.public as unique_SDK


@pytest.mark.integration
@pytest.mark.ai_generated
class TestSpaceOperations:
    """Test space and chat operations."""

    def test_space_chat__creates_chat__successfully(
        self, request_context, cleanup_items
    ):
        """
        Purpose: Verify space chat creation works.
        Why: Chat creation is foundational for conversation management.
        Setup: Request context with chat configuration.
        """
        # Arrange
        chat_id = None

        try:
            # Act: Create chat
            response = unique_SDK.space.chat.chatId.CreateChat.request(
                context=request_context,
                name="Integration Test Chat",
                description="Created by integration tests",
            )

            # Assert
            assert response is not None
            chat_id = response.id if hasattr(response, "id") else response.get("id")

            if chat_id:
                cleanup_items.append(("chat", chat_id))

        finally:
            # Cleanup
            if chat_id:
                try:
                    unique_SDK.space.chat.chatId.DeleteChat.request(
                        context=request_context,
                        chat_id=chat_id,
                    )
                except Exception:
                    pass

    def test_space_messages_latest__retrieves_latest_messages__successfully(
        self, request_context, integration_env
    ):
        """
        Purpose: Verify retrieving latest messages from chat works.
        Why: Latest message access is common use case.
        Setup: Request context and test chat ID.
        """
        # Arrange
        test_chat_id = integration_env.get("test_chat_id")
        if not test_chat_id:
            pytest.skip("TEST_CHAT_ID required")

        # Act
        response = unique_SDK.space.chatId.messages.latest.GetLatestMessages.request(
            context=request_context,
            chat_id=test_chat_id,
            limit=10,
        )

        # Assert
        assert response is not None

    def test_space_message_create__creates_space_message__successfully(
        self, request_context, integration_env, cleanup_items
    ):
        """
        Purpose: Verify space message creation works.
        Why: Message posting is fundamental chat operation.
        Setup: Request context and test chat ID.
        """
        # Arrange
        test_chat_id = integration_env.get("test_chat_id")
        if not test_chat_id:
            pytest.skip("TEST_CHAT_ID required")

        message_id = None

        try:
            # Act
            response = unique_SDK.space.message.CreateSpaceMessage.request(
                context=request_context,
                chat_id=test_chat_id,
                content="Integration test message",
                role="user",
            )

            # Assert
            assert response is not None
            message_id = response.id if hasattr(response, "id") else response.get("id")

            if message_id:
                cleanup_items.append(("space_message", message_id))

        finally:
            # Cleanup (if delete endpoint exists)
            pass
