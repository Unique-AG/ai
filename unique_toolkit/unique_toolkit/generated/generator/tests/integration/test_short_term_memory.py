"""Integration tests for short-term memory operations using generated SDK."""

import pytest

import unique_toolkit.generated.generated_routes.public as unique_SDK


@pytest.mark.integration
@pytest.mark.ai_generated
class TestShortTermMemory:
    """Test short-term memory operations."""

    def test_short_term_memory_create__stores_memory__successfully(
        self, request_context, integration_env, cleanup_items
    ):
        """
        Purpose: Verify short-term memory creation works.
        Why: Memory storage is critical for context retention.
        Setup: Request context and test chat ID.
        """
        # Arrange
        test_chat_id = integration_env.get("test_chat_id")
        if not test_chat_id:
            pytest.skip("TEST_CHAT_ID required")

        memory_id = None

        try:
            # Act: Create memory
            response = unique_SDK.short_term_memory.Create.request(
                context=request_context,
                chat_id=test_chat_id,
                key="integration_test_key",
                value={"test": "data", "timestamp": "2024-10-05"},
            )

            # Assert
            assert response is not None
            memory_id = response.id if hasattr(response, "id") else response.get("id")

            if memory_id:
                cleanup_items.append(("memory", memory_id))

        finally:
            if memory_id:
                try:
                    unique_SDK.short_term_memory.Delete.request(
                        context=request_context,
                        id=memory_id,
                    )
                except Exception:
                    pass

    def test_short_term_memory_find_latest__retrieves_latest_memory__successfully(
        self, request_context, integration_env
    ):
        """
        Purpose: Verify finding latest memory by key works.
        Why: Latest memory retrieval is common use case.
        Setup: Request context and test chat ID.
        """
        # Arrange
        test_chat_id = integration_env.get("test_chat_id")
        if not test_chat_id:
            pytest.skip("TEST_CHAT_ID required")

        # Act
        response = unique_SDK.short_term_memory.find_latest.FindLatest.request(
            context=request_context,
            chat_id=test_chat_id,
            key="test_key",
        )

        # Assert
        assert response is not None
