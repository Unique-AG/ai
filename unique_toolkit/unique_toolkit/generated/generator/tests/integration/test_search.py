"""Integration tests for search operations using generated SDK."""

import pytest

import unique_toolkit.generated.generated_routes.public as unique_SDK


@pytest.mark.integration
@pytest.mark.ai_generated
class TestSearchOperations:
    """Test search functionality with generated SDK."""

    def test_search_search__executes_search__successfully(
        self, request_context, integration_env
    ):
        """
        Purpose: Verify search operation works with generated SDK.
        Why: Search is a key feature requiring proper request handling.
        Setup: Request context from test.env.
        """
        # Arrange
        test_chat_id = integration_env.get("test_chat_id")
        if not test_chat_id:
            pytest.skip("TEST_CHAT_ID required for search tests")

        search_query = {
            "query": "test search",
            "chat_id": test_chat_id,
            "limit": 10,
        }

        # Act
        response = unique_SDK.search.search.Search.request(
            context=request_context,
            **search_query,
        )

        # Assert
        assert response is not None
        # Response should have results or be empty list
        if hasattr(response, "results"):
            assert isinstance(response.results, list)
        elif isinstance(response, dict):
            assert "results" in response or "data" in response

    def test_search_string__performs_string_search__successfully(
        self, request_context, integration_env
    ):
        """
        Purpose: Verify search-string endpoint works with generated SDK.
        Why: Alternative search method needs validation.
        Setup: Request context and test chat ID.
        """
        # Arrange
        test_chat_id = integration_env.get("test_chat_id")
        if not test_chat_id:
            pytest.skip("TEST_CHAT_ID required")

        # Act
        response = unique_SDK.search.search_string.SearchString.request(
            context=request_context,
            search_string="integration test",
            chat_id=test_chat_id,
        )

        # Assert
        assert response is not None
