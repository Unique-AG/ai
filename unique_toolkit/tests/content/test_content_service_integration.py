import pytest

from unique_toolkit.content.schemas import Content, ContentChunk, ContentSearchType
from unique_toolkit.content.service import ContentService


@pytest.mark.usefixtures("chat_state")
class TestContentServiceIntegration:
    @pytest.fixture(autouse=True)
    def setup(self, chat_state):
        self.state = chat_state
        self.service = ContentService(chat_state)

    def test_search_content_chunks(self):
        result = self.service.search_content_chunks(
            search_string="test",
            search_type=ContentSearchType.COMBINED,
            limit=10,
        )

        assert isinstance(result, list)
        assert all(isinstance(chunk, ContentChunk) for chunk in result)
        assert len(result) > 0
        assert all(hasattr(chunk, "id") for chunk in result)
        assert all(hasattr(chunk, "text") for chunk in result)

    def test_search_contents(self):
        filter = [
            {
                "key": {
                    "equals": "test",
                },
                "ownerId": {
                    "equals": self.state.scope_ids[0],
                },
            },
        ]

        where = {
            "OR": filter,
        }
        result = self.service.search_contents(where=where)

        assert isinstance(result, list)
        assert all(isinstance(content, Content) for content in result)
        if len(result) > 0:
            assert all(hasattr(content, "id") for content in result)
            assert all(hasattr(content, "key") for content in result)
            assert all(hasattr(content, "chunks") for content in result)
            assert all(isinstance(content.chunks, list) for content in result)

    def test_error_handling(self):
        with pytest.raises(Exception):
            # This should raise an exception due to invalid search type
            self.service.search_content_chunks(
                search_string="test",
                search_type="invalid_type",  # type: ignore
                limit=10,
            )
