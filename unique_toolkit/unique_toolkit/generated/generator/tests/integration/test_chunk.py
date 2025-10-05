"""Integration tests for chunk operations using generated SDK."""

import pytest

import unique_toolkit.generated.generated_routes.public as unique_SDK
from unique_toolkit.generated.generated_routes.public.chunk.models import Input


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
        test_content_id: str = integration_env.get("test_content_id")
        if not test_chat_id or not test_content_id:
            pytest.skip("TEST_CHAT_ID and TEST_CONTENT_ID required for chunk tests")

        test_input = Input(
            text="Integration test chunk",
            start_page=None,
            end_page=None,
        )
        # Act
        response = unique_SDK.chunk.Create.request(
            context=request_context,
            content_id=test_content_id,
            chat_id=test_chat_id,
            input=test_input,
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
        test_content_id: str = integration_env.get("test_content_id")
        test_chat_id: str = integration_env.get("test_chat_id")

        if not test_chat_id or not test_content_id:
            pytest.skip("TEST_CHAT_ID and TEST_CONTENT_ID required")

        # Act
        response = unique_SDK.chunk.createMany.CreateMany.request(
            context=request_context,
            input=["Test chunk 1", "Test chunk 2", "Test chunk 3"],
            content_id=test_content_id,
            chat_id=test_chat_id,
        )

        # Assert
        assert response is not None
