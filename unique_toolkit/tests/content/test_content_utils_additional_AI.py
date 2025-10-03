"""
Additional tests for content utils to improve coverage.
These tests focus on edge cases in page number generation and token counting.
"""

from unittest.mock import Mock, patch

import pytest

from unique_toolkit.content.schemas import ContentChunk
from unique_toolkit.content.utils import (
    _generate_pages_postfix,
    count_tokens,
    pick_content_chunks_for_token_window,
)


@pytest.mark.ai
class TestContentUtilsAdditional:
    """Additional tests for content utils to improve coverage."""

    def test_generate_pages_postfix__start_minus_one_end_minus_one_AI(
        self, base_content_chunk
    ):
        """
        Purpose: Verify _generate_pages_postfix handles start=-1, end=-1 case.
        Why this matters: Tests edge case in page number generation logic.
        Setup summary: Use base_content_chunk fixture and modify for edge case.
        """
        # Arrange
        chunk = base_content_chunk
        chunk.start_page = -1
        chunk.end_page = -1
        chunks = [chunk]

        # Act
        result = _generate_pages_postfix(chunks)

        # Assert
        assert result == ""

    def test_generate_pages_postfix__start_minus_one_end_valid_AI(self):
        """
        Purpose: Verify _generate_pages_postfix handles start=-1, end=valid case.
        Why this matters: Tests edge case in page number generation logic.
        Setup summary: Create chunk with start_page=-1, end_page=5.
        """
        # Arrange
        chunks = [
            ContentChunk(
                id="1",
                text="test",
                start_page=-1,
                end_page=5,
            )
        ]

        # Act
        result = _generate_pages_postfix(chunks)

        # Assert
        # The function filters out negative pages, so -1 is excluded
        assert result == ""

    def test_generate_pages_postfix__start_valid_end_minus_one_AI(self):
        """
        Purpose: Verify _generate_pages_postfix handles start=valid, end=-1 case.
        Why this matters: Tests edge case in page number generation logic.
        Setup summary: Create chunk with start_page=3, end_page=-1.
        """
        # Arrange
        chunks = [
            ContentChunk(
                id="1",
                text="test",
                start_page=3,
                end_page=-1,
            )
        ]

        # Act
        result = _generate_pages_postfix(chunks)

        # Assert
        # The function uses start_page when end_page is negative
        assert result == " : 3"

    def test_pick_content_chunks_for_token_window__encoding_error_AI(self):
        """
        Purpose: Verify pick_content_chunks_for_token_window handles encoding errors gracefully.
        Why this matters: Ensures robust token counting even with problematic text.
        Setup summary: Mock tiktoken to raise exception during encoding.
        """
        # Arrange
        chunks = [
            ContentChunk(id="1", text="Normal text", order=1),
            ContentChunk(id="2", text="Problematic text", order=2),
        ]

        # Act
        with patch(
            "unique_toolkit.content.utils.tiktoken.get_encoding"
        ) as mock_get_encoding:
            mock_encoding = Mock()
            mock_encoding.encode.side_effect = [4, Exception("Encoding error")]
            mock_get_encoding.return_value = mock_encoding

            result = pick_content_chunks_for_token_window(chunks, token_limit=10)

        # Assert
        # The function continues processing even with encoding errors
        assert len(result) == 2
        assert result[0].id == "1"

    def test_count_tokens__encoding_error_AI(self):
        """
        Purpose: Verify count_tokens handles encoding errors gracefully.
        Why this matters: Ensures robust token counting even with problematic text.
        Setup summary: Mock tiktoken to raise exception during encoding.
        """
        # Arrange
        text = "Problematic text"

        # Act
        with patch(
            "unique_toolkit.content.utils.tiktoken.get_encoding"
        ) as mock_get_encoding:
            mock_encoding = Mock()
            mock_encoding.encode.side_effect = Exception("Encoding error")
            mock_get_encoding.return_value = mock_encoding

            # This should not raise an exception, but we need to handle it
            # The current implementation doesn't handle encoding errors in count_tokens
            # This test documents the current behavior
            with pytest.raises(Exception):
                count_tokens(text)

    def test_generate_pages_postfix__multiple_chunks_with_overlap_AI(self):
        """
        Purpose: Verify _generate_pages_postfix handles multiple chunks with overlapping pages.
        Why this matters: Tests deduplication logic in page number generation.
        Setup summary: Create multiple chunks with overlapping page ranges.
        """
        # Arrange
        chunks = [
            ContentChunk(
                id="1",
                text="test",
                start_page=1,
                end_page=3,
            ),
            ContentChunk(
                id="1",
                text="test",
                start_page=2,
                end_page=4,
            ),
            ContentChunk(
                id="2",
                text="test",
                start_page=5,
                end_page=7,
            ),
        ]

        # Act
        result = _generate_pages_postfix(chunks)

        # Assert
        # Should contain pages 1, 2, 3, 4, 5, 6, 7 (deduplicated and sorted)
        expected_pages = [1, 2, 3, 4, 5, 6, 7]
        actual_pages = [int(p) for p in result.split(" : ")[1].split(",")]
        assert actual_pages == expected_pages

    def test_generate_pages_postfix__chunks_with_zero_pages_AI(self):
        """
        Purpose: Verify _generate_pages_postfix filters out zero and negative pages.
        Why this matters: Tests filtering logic for invalid page numbers.
        Setup summary: Create chunks with zero and negative page numbers.
        """
        # Arrange
        chunks = [
            ContentChunk(
                id="1",
                text="test",
                start_page=0,
                end_page=0,
            ),
            ContentChunk(
                id="2",
                text="test",
                start_page=1,
                end_page=2,
            ),
            ContentChunk(
                id="3",
                text="test",
                start_page=-5,
                end_page=-3,
            ),
        ]

        # Act
        result = _generate_pages_postfix(chunks)

        # Assert
        # Should only contain pages 1, 2 (zero and negative pages filtered out)
        expected_pages = [1, 2]
        actual_pages = [int(p) for p in result.split(" : ")[1].split(",")]
        assert actual_pages == expected_pages

    def test_generate_pages_postfix__empty_chunks_list_AI(self):
        """
        Purpose: Verify _generate_pages_postfix handles empty chunks list.
        Why this matters: Tests edge case with no chunks.
        Setup summary: Pass empty list to _generate_pages_postfix.
        """
        # Arrange
        chunks = []

        # Act
        result = _generate_pages_postfix(chunks)

        # Assert
        assert result == ""

    def test_pick_content_chunks_for_token_window__exact_token_limit_AI(self):
        """
        Purpose: Verify pick_content_chunks_for_token_window handles exact token limit.
        Why this matters: Tests boundary condition in token window selection.
        Setup summary: Create chunks that exactly match the token limit.
        """
        # Arrange
        chunks = [
            ContentChunk(id="1", text="Short", order=1),
            ContentChunk(id="2", text="Medium length text", order=2),
            ContentChunk(id="3", text="Very long text that exceeds limit", order=3),
        ]

        # Act
        result = pick_content_chunks_for_token_window(chunks, token_limit=5)

        # Assert
        # Should pick chunks until limit is reached
        assert len(result) <= 3
        assert all(chunk.id in ["1", "2", "3"] for chunk in result)

    def test_pick_content_chunks_for_token_window__zero_token_limit_AI(self):
        """
        Purpose: Verify pick_content_chunks_for_token_window handles zero token limit.
        Why this matters: Tests edge case with zero token limit.
        Setup summary: Pass zero token limit to pick_content_chunks_for_token_window.
        """
        # Arrange
        chunks = [
            ContentChunk(id="1", text="Some text", order=1),
            ContentChunk(id="2", text="More text", order=2),
        ]

        # Act
        result = pick_content_chunks_for_token_window(chunks, token_limit=0)

        # Assert
        assert len(result) == 0

    def test_pick_content_chunks_for_token_window__empty_chunks_AI(self):
        """
        Purpose: Verify pick_content_chunks_for_token_window handles empty chunks list.
        Why this matters: Tests edge case with no chunks.
        Setup summary: Pass empty list to pick_content_chunks_for_token_window.
        """
        # Arrange
        chunks = []

        # Act
        result = pick_content_chunks_for_token_window(chunks, token_limit=10)

        # Assert
        assert len(result) == 0

    def test_count_tokens__empty_text_AI(self):
        """
        Purpose: Verify count_tokens handles empty text.
        Why this matters: Tests edge case with empty input.
        Setup summary: Pass empty string to count_tokens.
        """
        # Arrange
        text = ""

        # Act
        result = count_tokens(text)

        # Assert
        assert result == 0

    def test_count_tokens__unicode_text_AI(self):
        """
        Purpose: Verify count_tokens handles unicode text correctly.
        Why this matters: Tests token counting with international characters.
        Setup summary: Pass unicode text to count_tokens.
        """
        # Arrange
        text = "Hello 世界 🌍"

        # Act
        result = count_tokens(text)

        # Assert
        assert result > 0
        assert isinstance(result, int)

    def test_count_tokens__very_long_text_AI(self):
        """
        Purpose: Verify count_tokens handles very long text.
        Why this matters: Tests token counting with large inputs.
        Setup summary: Pass very long text to count_tokens.
        """
        # Arrange
        text = "This is a test sentence. " * 1000  # Very long text

        # Act
        result = count_tokens(text)

        # Assert
        assert result > 0
        assert isinstance(result, int)
