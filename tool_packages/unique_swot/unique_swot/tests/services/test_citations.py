"""Tests for citation management."""

from unittest.mock import Mock

import pytest
from unique_toolkit.content.schemas import ContentChunk

from unique_swot.services.citations import (
    CitationManager,
    _convert_content_chunk_to_content_reference,
    _get_pages,
)
from unique_swot.services.collection.registry import ContentChunkRegistry


class TestCitationManager:
    """Test cases for CitationManager class."""

    @pytest.fixture
    def mock_registry(self, sample_content_chunk):
        """Create a mock content chunk registry."""
        registry = Mock(spec=ContentChunkRegistry)
        registry.retrieve.return_value = sample_content_chunk
        return registry

    @pytest.fixture
    def citation_manager(self, mock_registry):
        """Create a CitationManager instance for testing."""
        return CitationManager(content_chunk_registry=mock_registry)

    def test_citation_manager_initialization(self, citation_manager):
        """Test CitationManager initialization."""
        assert citation_manager._citations_map == {}
        assert citation_manager._content_chunks == []

    def test_process_result_single_citation(
        self, citation_manager, mock_registry, sample_content_chunk
    ):
        """Test processing a report with a single citation."""
        report = "This is a report with [chunk_abc123] citation."

        processed = citation_manager.process_result(report)

        assert "[chunk_abc123]" not in processed
        assert "<sup>1</sup>" in processed
        mock_registry.retrieve.assert_called_once_with("chunk_abc123")

    def test_process_result_multiple_citations(
        self, citation_manager, mock_registry, sample_content_chunk
    ):
        """Test processing a report with multiple different citations."""
        report = "First [chunk_abc123] and second [chunk_def456] citations."

        processed = citation_manager.process_result(report)

        assert "[chunk_abc123]" not in processed
        assert "[chunk_def456]" not in processed
        assert "<sup>1</sup>" in processed
        assert "<sup>2</sup>" in processed

    def test_process_result_duplicate_citations(
        self, citation_manager, mock_registry, sample_content_chunk
    ):
        """Test processing a report with duplicate citations."""
        report = "First [chunk_abc123] and duplicate [chunk_abc123] citations."

        processed = citation_manager.process_result(report)

        # Both should be replaced with the same superscript
        assert processed.count("<sup>1</sup>") == 2
        assert "<sup>2</sup>" not in processed

    def test_process_result_missing_chunk(self, citation_manager, mock_registry):
        """Test processing a report with a citation that doesn't exist in registry."""
        mock_registry.retrieve.return_value = None
        report = "Report with missing [chunk_missing] citation."

        processed = citation_manager.process_result(report)

        # Should keep the original citation tag
        assert "[chunk_missing]" in processed
        assert "<sup>" not in processed

    def test_process_result_no_citations(self, citation_manager):
        """Test processing a report with no citations."""
        report = "This is a plain report without any citations."

        processed = citation_manager.process_result(report)

        assert processed == report
        assert citation_manager._citations_map == {}

    def test_process_result_citation_with_hyphens(
        self, citation_manager, mock_registry, sample_content_chunk
    ):
        """Test processing citations with hyphens in UUID."""
        report = "Citation with UUID [chunk_abc-123-def-456]."

        processed = citation_manager.process_result(report)

        assert "[chunk_abc-123-def-456]" not in processed
        assert "<sup>1</sup>" in processed

    def test_get_references(
        self, citation_manager, mock_registry, sample_content_chunk
    ):
        """Test getting content references."""
        report = "Report with [chunk_abc123] citation."
        citation_manager.process_result(report)

        references = citation_manager.get_references("message_123")

        assert len(references) == 1
        assert references[0].message_id == "message_123"
        assert references[0].sequence_number == 0
        assert references[0].source == "SWOT-TOOL"

    def test_get_referenced_content_chunks(
        self, citation_manager, mock_registry, sample_content_chunk
    ):
        """Test getting referenced content chunks."""
        report = "Report with [chunk_abc123] and [chunk_def456] citations."
        citation_manager.process_result(report)

        chunks = citation_manager.get_referenced_content_chunks()

        assert len(chunks) == 2

    def test_citation_numbering_order(
        self, citation_manager, mock_registry, sample_content_chunk
    ):
        """Test that citations are numbered in order of first appearance."""
        report = "First [chunk_aaa], then [chunk_bbb], then [chunk_aaa] again."

        processed = citation_manager.process_result(report)

        # First appearance of chunk_aaa should be <sup>1</sup>
        first_sup = processed.find("<sup>1</sup>")
        second_sup = processed.find("<sup>2</sup>")
        third_sup = processed.find("<sup>1</sup>", first_sup + 1)

        assert first_sup < second_sup < third_sup


class TestConvertContentChunkToContentReference:
    """Test cases for _convert_content_chunk_to_content_reference function."""

    def test_convert_with_pages(self, sample_content_chunk):
        """Test converting content chunk with page numbers."""
        reference = _convert_content_chunk_to_content_reference(
            "msg_123", 0, sample_content_chunk
        )

        assert reference.message_id == "msg_123"
        assert reference.sequence_number == 0
        assert reference.source == "SWOT-TOOL"
        assert reference.url == f"unique//content/{sample_content_chunk.id}"
        assert "Test Document" in reference.name
        assert "1" in reference.name  # start page

    def test_convert_without_title(self, sample_content_chunk):
        """Test converting content chunk without title."""
        chunk = ContentChunk(
            id="content_123",
            chunk_id="chunk_456",
            title=None,
            key="fallback.pdf",
            text="Content",
            start_page=None,
            end_page=None,
        )

        reference = _convert_content_chunk_to_content_reference("msg_123", 0, chunk)

        assert "fallback.pdf" in reference.name


class TestGetPages:
    """Test cases for _get_pages function."""

    def test_get_pages_both_none(self):
        """Test getting pages when both are None."""
        result = _get_pages(None, None)
        assert result == ""

    def test_get_pages_only_start(self):
        """Test getting pages with only start page."""
        result = _get_pages(5, None)
        assert result == ": 5"

    def test_get_pages_both_pages(self):
        """Test getting pages with both start and end."""
        result = _get_pages(5, 10)
        assert result == ": 5, 10"

    def test_get_pages_same_page(self):
        """Test getting pages when start and end are same."""
        result = _get_pages(7, 7)
        assert result == ": 7, 7"
