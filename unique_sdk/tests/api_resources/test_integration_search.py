import pytest
from unittest.mock import patch

from unique_sdk.api_resources._search import Search



@pytest.mark.integration
class TestSearch:
    def test_create_search(self, event):
        """Test creating a search request synchronously."""
        response = Search.create(
            user_id=event.user_id,
            company_id=event.company_id,
            chatId=event.chat_id,
            searchString="a",
            searchType="COMBINED",
            language="en",
            limit=10,
            page=1,
            chatOnly=False,
        )
        
        assert isinstance(response, list)
        if response:
            result = response[0]
            assert isinstance(result.id, str)
            assert isinstance(result.chunkId, str)
            assert isinstance(result.text, str)
            assert isinstance(result.createdAt, str)
            assert isinstance(result.updatedAt, str)
            assert isinstance(result.order, int)
            assert isinstance(result.startPage, int)
            assert isinstance(result.endPage, int)

    @pytest.mark.asyncio
    async def test_create_search_async(self, test_user_id, test_company_id):
        """Test creating a search request asynchronously."""
        response = await Search.create_async(
            user_id=test_user_id,
            company_id=test_company_id,
            chatId="test-chat-id-async",
            searchString="test query async",
            searchType="VECTOR",
            language="en",
            limit=5,
            page=1,
            chatOnly=True,
            scopeIds=["scope1"],
            metaDataFilter={"key": "value"},
            contentIds=["content1"]
        )
        
        assert isinstance(response, list)
        if response:
            result = response[0]
            assert isinstance(result.id, str)
            assert isinstance(result.chunkId, str)
            assert isinstance(result.text, str)
            assert isinstance(result.createdAt, str)
            assert isinstance(result.updatedAt, str)
            assert isinstance(result.order, int)
            assert isinstance(result.startPage, int)
            assert isinstance(result.endPage, int)

    def test_vector_search(self, test_user_id, test_company_id):
        """Test vector-based search."""
        response = Search.create(
            user_id=test_user_id,
            company_id=test_company_id,
            chatId="test-chat-id",
            searchString="vector search query",
            searchType="VECTOR",
            limit=10
        )
        
        assert isinstance(response, list)
        if response:
            assert all(hasattr(item, 'id') for item in response)
            assert all(hasattr(item, 'text') for item in response)

    def test_combined_search(self, test_user_id, test_company_id):
        """Test combined search approach."""
        response = Search.create(
            user_id=test_user_id,
            company_id=test_company_id,
            chatId="test-chat-id",
            searchString="combined search query",
            searchType="COMBINED",
            limit=10,
            reranker={"model": "test-model"}
        )
        
        assert isinstance(response, list)
        if response:
            assert all(hasattr(item, 'id') for item in response)
            assert all(hasattr(item, 'text') for item in response)