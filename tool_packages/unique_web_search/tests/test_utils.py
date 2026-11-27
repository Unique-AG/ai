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


class TestShorten:
    @pytest.mark.ai
    def test_shorten__cuts_at_the_last_whole_word__and_marks_the_cut(self) -> None:
        from unique_web_search.services.helpers import shorten

        assert shorten("alpha beta gamma delta", 12) == "alpha beta…"
        assert shorten("short", 100) == "short"

    @pytest.mark.ai
    @pytest.mark.parametrize(
        ("text", "expected"),
        [
            (" " * 501, "…"),
            ("x" * 600, "x" * 500 + "…"),
            ("A " + "b" * 498 + " next", "A " + "b" * 498 + "…"),
        ],
        ids=["only-whitespace", "no-word-break", "word-ends-at-limit"],
    )
    def test_shorten__cuts_at_the_limit__when_there_is_no_word_break(
        self, text: str, expected: str
    ) -> None:
        from unique_web_search.services.helpers import shorten

        assert shorten(text, 500) == expected
