"""Integration tests for chunk operations using generated SDK."""

import pytest

import unique_toolkit.generated.generated_routes.public as unique_SDK


@pytest.mark.integration
@pytest.mark.ai_generated
class TestChunkOperations:
    """Test chunk creation operations."""

    def test_chunk_create__creates_single_chunk__successfully(
        self, request_context, integration_env
    ):
        """
        Purpose: Verify single chunk creation works with generated SDK.
        Why: Chunk creation is fundamental for content indexing.
        Setup: Request context and test chat ID.
        """
        # Arrange
        test_chat_id = integration_env.get("test_chat_id")
        if not test_chat_id:
            pytest.skip("TEST_CHAT_ID required for chunk tests")

        # Act
        response = unique_SDK.chunk.CreateChunk.request(
            context=request_context,
            chat_id=test_chat_id,
            text="Integration test chunk",
            embedding=[0.1] * 1536,  # Sample embedding vector
            metadata={"test": "integration"},
        )

        # Assert
        assert response is not None

    def test_chunk_create_many__creates_multiple_chunks__successfully(
        self, request_context, integration_env
    ):
        """
        Purpose: Verify batch chunk creation works.
        Why: Bulk operations are important for performance.
        Setup: Request context with multiple chunk data.
        """
        # Arrange
        test_chat_id = integration_env.get("test_chat_id")
        if not test_chat_id:
            pytest.skip("TEST_CHAT_ID required")

        # Act
        response = unique_SDK.chunk.createMany.CreateMany.request(
            context=request_context,
            chunks=[
                {
                    "chatId": test_chat_id,
                    "text": f"Test chunk {i}",
                    "embedding": [0.1] * 1536,
                    "metadata": {},
                }
                for i in range(3)
            ],
        )

        # Assert
        assert response is not None
