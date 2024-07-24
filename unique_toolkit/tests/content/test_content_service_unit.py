from unittest.mock import patch

import pytest
import unique_sdk

from unique_toolkit.chat.state import ChatState
from unique_toolkit.content.schemas import Content, ContentChunk, ContentSearchType
from unique_toolkit.content.service import ContentService


class TestContentServiceUnit:
    @pytest.fixture(autouse=True)
    def setup(self):
        self.chat_state = ChatState(
            user_id="test_user",
            company_id="test_company",
            assistant_id="test_assistant",
            chat_id="test_chat",
        )
        self.service = ContentService(self.chat_state)

    def test_search_content_chunks(self):
        with patch.object(unique_sdk.Search, "create") as mock_create:
            mock_create.return_value = [
                {
                    "id": "1",
                    "text": "Test chunk",
                    "startPage": 1,
                    "endPage": 1,
                    "order": 1,
                }
            ]

            result = self.service.search_content_chunks(
                search_string="test",
                search_type=ContentSearchType.COMBINED,
                limit=10,
                scope_ids=["scope1", "scope2"],
            )

            assert isinstance(result, list)
            assert all(isinstance(chunk, ContentChunk) for chunk in result)
            assert len(result) == 1
            assert result[0].id == "1"
            assert result[0].text == "Test chunk"

            mock_create.assert_called_once_with(
                user_id="test_user",
                company_id="test_company",
                chatId="test_chat",
                searchString="test",
                searchType="COMBINED",
                scopeIds=["scope1", "scope2"],
                limit=10,
                chatOnly=False,
            )

    def test_search_contents(self):
        with patch.object(unique_sdk.Content, "search") as mock_search:
            mock_search.return_value = [
                {
                    "id": "1",
                    "key": "test_key",
                    "title": "Test Content",
                    "url": "http://test.com",
                    "chunks": [
                        {
                            "id": "chunk1",
                            "text": "Test chunk",
                            "startPage": 1,
                            "endPage": 1,
                            "order": 1,
                        }
                    ],
                }
            ]

            result = self.service.search_contents(where={"key": "test_key"})

            assert isinstance(result, list)
            assert all(isinstance(content, Content) for content in result)
            assert len(result) == 1
            assert result[0].id == "1"
            assert result[0].key == "test_key"
            assert len(result[0].chunks) == 1
            assert result[0].chunks[0].id == "chunk1"

            mock_search.assert_called_once_with(
                user_id="test_user",
                company_id="test_company",
                chatId="test_chat",
                where={"key": "test_key"},
            )

    def test_error_handling_search_content_chunks(self):
        with patch.object(
            unique_sdk.Search, "create", side_effect=Exception("API Error")
        ):
            with pytest.raises(Exception, match="API Error"):
                self.service.search_content_chunks(
                    "test", ContentSearchType.COMBINED, 10, None
                )

    def test_error_handling_search_contents(self):
        with patch.object(
            unique_sdk.Content, "search", side_effect=Exception("API Error")
        ):
            with pytest.raises(Exception, match="API Error"):
                self.service.search_contents({"key": "test_key"})
