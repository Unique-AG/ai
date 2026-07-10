import pytest

from unique_web_search.schema import WebPageChunk


class TestWebPageChunk:
    """Test WebPageChunk functionality."""

    def test_web_page_chunk_creation(self):
        """Test creating a WebPageChunk."""
        chunk = WebPageChunk(
            url="https://example.com/test",
            display_link="example.com",
            title="Test Article",
            snippet="This is a test article",
            content="Full content of the test article",
            order="1",
        )

        assert chunk.url == "https://example.com/test"
        assert chunk.display_link == "example.com"
        assert chunk.title == "Test Article"
        assert chunk.snippet == "This is a test article"
        assert chunk.content == "Full content of the test article"
        assert chunk.order == "1"

    def test_web_page_chunk_to_content_chunk(self):
        """Test converting WebPageChunk to ContentChunk."""
        chunk = WebPageChunk(
            url="https://example.com/test",
            display_link="example.com",
            title="Test Article",
            snippet="This is a test article",
            content="Full content of the test article",
            order="1",
        )

        content_chunk = chunk.to_content_chunk()

        assert content_chunk.url == "https://example.com/test"
        assert content_chunk.text == "Full content of the test article"
        assert content_chunk.order == 1
        assert "example.com" in content_chunk.id
        assert "Test Article" in content_chunk.id


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
