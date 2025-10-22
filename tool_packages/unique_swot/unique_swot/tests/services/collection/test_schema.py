"""Tests for collection schemas."""

import pytest
from pydantic import ValidationError

from unique_swot.services.collection.schema import (
    Source,
    SourceChunk,
    SourceType,
)


class TestSourceType:
    """Test cases for SourceType enum."""

    def test_source_type_values(self):
        """Test that SourceType has expected values."""
        assert SourceType.WEB_SEARCH == "web_search"
        assert SourceType.INTERNAL_DOCUMENT == "internal_document"
        assert SourceType.EARNINGS_CALL == "earnings_call"

    def test_source_type_from_string(self):
        """Test creating SourceType from string."""
        assert SourceType("web_search") == SourceType.WEB_SEARCH
        assert SourceType("internal_document") == SourceType.INTERNAL_DOCUMENT
        assert SourceType("earnings_call") == SourceType.EARNINGS_CALL


class TestSourceChunk:
    """Test cases for SourceChunk class."""

    def test_source_chunk_creation(self):
        """Test creating a SourceChunk."""
        chunk = SourceChunk(
            id="chunk_123",
            text="This is the chunk content.",
        )

        assert chunk.id == "chunk_123"
        assert chunk.text == "This is the chunk content."

    def test_source_chunk_validation(self):
        """Test SourceChunk validation."""
        # Should require id and text
        with pytest.raises(ValidationError):
            SourceChunk(id="chunk_123")

        with pytest.raises(ValidationError):
            SourceChunk(text="Some text")


class TestSource:
    """Test cases for Source class."""

    def test_source_creation_internal_document(self):
        """Test creating a Source with internal document type."""
        source = Source(
            type=SourceType.INTERNAL_DOCUMENT,
            url="https://example.com/doc.pdf",
            title="Internal Report",
            chunks=[
                SourceChunk(id="chunk_1", text="Content 1"),
                SourceChunk(id="chunk_2", text="Content 2"),
            ],
        )

        assert source.type == SourceType.INTERNAL_DOCUMENT
        assert source.url == "https://example.com/doc.pdf"
        assert source.title == "Internal Report"
        assert len(source.chunks) == 2

    def test_source_creation_web_search(self):
        """Test creating a Source with web search type."""
        source = Source(
            type=SourceType.WEB_SEARCH,
            url="https://example.com/article",
            title="Web Article",
            chunks=[SourceChunk(id="chunk_1", text="Web content")],
        )

        assert source.type == SourceType.WEB_SEARCH
        assert source.url == "https://example.com/article"

    def test_source_creation_earnings_call(self):
        """Test creating a Source with earnings call type."""
        source = Source(
            type=SourceType.EARNINGS_CALL,
            url="https://example.com/transcript",
            title="Q4 2024 Earnings Call",
            chunks=[SourceChunk(id="chunk_1", text="Transcript content")],
        )

        assert source.type == SourceType.EARNINGS_CALL

    def test_source_with_no_url(self):
        """Test creating a Source without URL."""
        source = Source(
            type=SourceType.INTERNAL_DOCUMENT,
            url=None,
            title="Local Document",
            chunks=[SourceChunk(id="chunk_1", text="Content")],
        )

        assert source.url is None
        assert source.title == "Local Document"

    def test_source_with_empty_chunks(self):
        """Test creating a Source with empty chunks list."""
        source = Source(
            type=SourceType.WEB_SEARCH,
            url="https://example.com",
            title="Empty Source",
            chunks=[],
        )

        assert len(source.chunks) == 0

    def test_source_validation(self):
        """Test Source validation."""
        # Should require type, title, and chunks
        with pytest.raises(ValidationError):
            Source(
                url="https://example.com",
                title="Title",
                chunks=[],
            )

    def test_source_serialization(self):
        """Test Source serialization."""
        source = Source(
            type=SourceType.INTERNAL_DOCUMENT,
            url="https://example.com/doc",
            title="Test Doc",
            chunks=[SourceChunk(id="chunk_1", text="Content")],
        )

        source_dict = source.model_dump()

        assert source_dict["type"] == "internal_document"
        assert source_dict["title"] == "Test Doc"
        assert len(source_dict["chunks"]) == 1

        # Recreate from dict
        source_restored = Source.model_validate(source_dict)
        assert source_restored.type == source.type
        assert source_restored.title == source.title

    def test_source_with_multiple_chunks(self):
        """Test Source with multiple chunks."""
        chunks = [SourceChunk(id=f"chunk_{i}", text=f"Content {i}") for i in range(10)]

        source = Source(
            type=SourceType.WEB_SEARCH,
            url="https://example.com",
            title="Multi-chunk Source",
            chunks=chunks,
        )

        assert len(source.chunks) == 10
        assert source.chunks[0].id == "chunk_0"
        assert source.chunks[9].id == "chunk_9"
