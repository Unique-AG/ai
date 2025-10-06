import pytest

from unique_web_search.services.content_processing import WebPageChunk
from unique_web_search.utils import query_params_to_human_string


class TestQueryParamsToHumanString:
    """Test cases for query_params_to_human_string function."""

    def test_query_without_date_restrict(self):
        """Test query conversion without date restriction."""
        result = query_params_to_human_string("Python tutorials", None)
        assert result == "Python tutorials"

    def test_query_with_single_day(self):
        """Test query conversion with single day restriction."""
        result = query_params_to_human_string("Python tutorials", "d1")
        assert result == "Python tutorials (For the last 1 day)"

    def test_query_with_multiple_days(self):
        """Test query conversion with multiple days restriction."""
        result = query_params_to_human_string("Python tutorials", "d7")
        assert result == "Python tutorials (For the last 7 days)"

    def test_query_with_single_week(self):
        """Test query conversion with single week restriction."""
        result = query_params_to_human_string("Python tutorials", "w1")
        assert result == "Python tutorials (For the last 1 week)"

    def test_query_with_multiple_weeks(self):
        """Test query conversion with multiple weeks restriction."""
        result = query_params_to_human_string("Python tutorials", "w2")
        assert result == "Python tutorials (For the last 2 weeks)"

    def test_query_with_single_month(self):
        """Test query conversion with single month restriction."""
        result = query_params_to_human_string("Python tutorials", "m1")
        assert result == "Python tutorials (For the last 1 month)"

    def test_query_with_multiple_months(self):
        """Test query conversion with multiple months restriction."""
        result = query_params_to_human_string("Python tutorials", "m6")
        assert result == "Python tutorials (For the last 6 months)"

    def test_query_with_single_year(self):
        """Test query conversion with single year restriction."""
        result = query_params_to_human_string("Python tutorials", "y1")
        assert result == "Python tutorials (For the last 1 year)"

    def test_query_with_multiple_years(self):
        """Test query conversion with multiple years restriction."""
        result = query_params_to_human_string("Python tutorials", "y2")
        assert result == "Python tutorials (For the last 2 years)"

    def test_query_with_invalid_date_restrict(self):
        """Test query conversion with invalid date restriction format."""
        result = query_params_to_human_string("Python tutorials", "invalid")
        assert result == "Python tutorials (For the last invalid)"


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
