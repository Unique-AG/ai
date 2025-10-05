"""Integration tests for content operations using generated SDK."""

import pytest

import unique_toolkit.generated.generated_routes.public as unique_SDK
from unique_toolkit.generated.generated_routes.public.content.upsert.models import (
    Input,
    UpsertResponse,
)


@pytest.mark.integration
@pytest.mark.ai_generated
class TestContentCRUD:
    """Test content CRUD operations."""

    def test_content_upsert__creates_or_updates_content__successfully(
        self, request_context, integration_env, cleanup_items
    ):
        """
        Purpose: Verify content upsert operation works with generated SDK.
        Why: Content upsert is core functionality for document management.
        Setup: Request context from test.env.
        """
        # Arrange
        test_chat_id = integration_env.get("test_chat_id")
        if not test_chat_id:
            pytest.skip("TEST_CHAT_ID required for content tests")

        content_id = None

        test_input = Input(
            url="https://example.com/test",
            key="integration_test",
            title="Integration test content",
            mime_type="text/plain",
            byte_size=100,
            ingestion_config=None,
            metadata=None,
        )

        try:
            content_id = None
            # Act: Upsert content
            response = unique_SDK.content.upsert.Upsert.request(
                context=request_context,
                chat_id=test_chat_id,
                scope_id=None,
                input=test_input,
                store_internally=False,
                file_url=None,
            )
            # Assert
            assert isinstance(response, UpsertResponse)

            if response.id:
                cleanup_items.append(("content", response.id))

        finally:
            # Cleanup
            if content_id:
                try:
                    unique_SDK.content.contentId.Delete.request(
                        context=request_context,
                        content_id=content_id,
                    )
                except Exception:
                    pass

    def test_content_info__retrieves_content_details__successfully(
        self, request_context, integration_env
    ):
        """
        Purpose: Verify content info retrieval works.
        Why: Content metadata access is essential for content management.
        Setup: Request context and test data.
        """
        # Arrange
        content_ids = (
            [integration_env.get("test_content_id")]
            if integration_env.get("test_content_id")
            else []
        )
        test_chat_id = integration_env.get("test_chat_id")

        if not content_ids or not test_chat_id:
            pytest.skip("TEST_CONTENT_ID and TEST_CHAT_ID not set in test.env")

        # Act
        response = unique_SDK.content.info.GetContentInfo.request(
            context=request_context,
            content_id=content_ids[0],
            chat_id=test_chat_id,
            metadata_filter={},
            file_path="",
            take=1,
            skip=0,
        )

        # Assert
        assert response is not None

    def test_content_search__finds_content__by_query(
        self, request_context, integration_env
    ):
        """
        Purpose: Verify content search functionality.
        Why: Search is critical for content discovery.
        Setup: Request context and test chat ID.
        """
        # Arrange
        test_chat_id = integration_env.get("test_chat_id")
        if not test_chat_id:
            pytest.skip("TEST_CHAT_ID required")

        # Act
        response = unique_SDK.content.search.Search.request(
            context=request_context,
            query="test",
            chat_id=test_chat_id,
        )

        # Assert
        assert response is not None
