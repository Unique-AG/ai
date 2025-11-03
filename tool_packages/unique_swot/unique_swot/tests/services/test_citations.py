"""Comprehensive tests for citation management."""

from unittest.mock import Mock

import pytest
from unique_toolkit.content.schemas import ContentChunk

from unique_swot.services.citations import (
    CitationManager,
    _convert_content_chunk_to_content_reference,
    _get_pages,
)
from unique_swot.services.collection.registry import ContentChunkRegistry
from unique_swot.services.report.config import DocxRendererType


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
        assert citation_manager._inline_citations_map == {}
        assert citation_manager._content_chunks == []

    def test_add_citations_with_inline_and_consolidated(
        self, citation_manager, mock_registry, sample_content_chunk
    ):
        """Test processing report with both inline and consolidated citations."""
        report = """
- Strong brand [bullet_chunk_abc]
- Market leader [bullet_chunk_def]

**References:** [chunk_abc], [chunk_def]
"""
        processed = citation_manager.add_citations_to_report(
            report, DocxRendererType.DOCX
        )

        # Inline citations should be numbered
        assert "[1]" in processed
        assert "[2]" in processed

        # Original placeholders should be gone
        assert "[bullet_chunk_abc]" not in processed
        assert "[chunk_abc]" not in processed

        # Should have document title in consolidated references
        assert "Test Document" in processed

    def test_add_citations_chat_mode(
        self, citation_manager, mock_registry, sample_content_chunk
    ):
        """Test citations in chat mode with superscripts."""
        report = """
- Strong brand [bullet_chunk_abc]
- Market leader [bullet_chunk_def]

**References:** [chunk_abc], [chunk_def]
"""
        processed = citation_manager.add_citations_to_report(
            report, DocxRendererType.CHAT
        )

        # Inline citations should be numbered
        assert "[1]" in processed
        assert "[2]" in processed

        # Consolidated citations should have superscripts
        assert "<sup>" in processed

    def test_add_citations_duplicate_inline(
        self, citation_manager, mock_registry, sample_content_chunk
    ):
        """Test that duplicate inline citations reuse the same number."""
        report = """
- Point one [bullet_chunk_abc]
- Point two [bullet_chunk_abc]

**References:** [chunk_abc]
"""
        processed = citation_manager.add_citations_to_report(
            report, DocxRendererType.DOCX
        )

        # Both inline citations should have [1]
        assert processed.count("[1]") >= 2

    def test_add_citations_missing_chunk(self, citation_manager, mock_registry):
        """Test handling of missing chunks in registry."""
        mock_registry.retrieve.return_value = None

        report = "Content [bullet_chunk_missing]\n\n**References:** [chunk_missing]"

        processed = citation_manager.add_citations_to_report(
            report, DocxRendererType.DOCX
        )

        # Should have numbered inline citation
        assert "[1]" in processed

        # Consolidated citation should remain as placeholder (chunk not found)
        assert "[chunk_missing]" in processed

    def test_add_citations_no_citations(self, citation_manager):
        """Test processing report with no citations."""
        report = "This is a plain report without any citations."

        processed = citation_manager.add_citations_to_report(
            report, DocxRendererType.DOCX
        )

        assert processed == report
        assert citation_manager._citations_map == {}
        assert citation_manager._inline_citations_map == {}

    def test_add_citations_invalid_renderer_type(self, citation_manager):
        """Test that invalid renderer type raises error."""
        report = "Content [bullet_chunk_abc]"

        with pytest.raises(ValueError, match="Invalid renderer type"):
            citation_manager.add_citations_to_report(report, "invalid_type")  # type: ignore

    def test_citation_docx_format(
        self, citation_manager, mock_registry, sample_content_chunk
    ):
        """Test DOCX citation format includes title and pages."""
        report = "Content [bullet_chunk_abc]\n\n**References:** [chunk_abc]"

        processed = citation_manager.add_citations_to_report(
            report, DocxRendererType.DOCX
        )

        # Should include document title
        assert "Test Document" in processed

        # Should include page numbers
        assert "1" in processed  # start_page

    def test_citation_chat_format_superscripts(
        self, citation_manager, mock_registry, sample_content_chunk
    ):
        """Test Chat citation format uses superscripts."""
        report = "Content [bullet_chunk_abc]\n\n**References:** [chunk_abc]"

        processed = citation_manager.add_citations_to_report(
            report, DocxRendererType.CHAT
        )

        # Should have superscript tags
        assert "<sup>1</sup>" in processed

    def test_get_references(
        self, citation_manager, mock_registry, sample_content_chunk
    ):
        """Test getting content references."""
        report = "Content [bullet_chunk_abc]\n\n**References:** [chunk_abc]"
        citation_manager.add_citations_to_report(report, DocxRendererType.DOCX)

        references = citation_manager.get_references("message_123")

        assert len(references) == 1
        assert references[0].message_id == "message_123"
        assert references[0].sequence_number == 0
        assert references[0].source == "SWOT-TOOL"
        assert "Test Document" in references[0].name

    def test_get_referenced_content_chunks(
        self, citation_manager, mock_registry, sample_content_chunk
    ):
        """Test getting referenced content chunks."""
        report = """
Content [bullet_chunk_abc] and [bullet_chunk_def]

**References:** [chunk_abc], [chunk_def]
"""
        citation_manager.add_citations_to_report(report, DocxRendererType.DOCX)

        chunks = citation_manager.get_referenced_content_chunks()

        assert len(chunks) == 2
        assert all(isinstance(chunk, ContentChunk) for chunk in chunks)

    def test_citation_numbering_sequential(
        self, citation_manager, mock_registry, sample_content_chunk
    ):
        """Test that citations are numbered sequentially."""
        report = """
- First [bullet_chunk_a]
- Second [bullet_chunk_b]
- Third [bullet_chunk_c]

**References:** [chunk_a], [chunk_b], [chunk_c]
"""
        processed = citation_manager.add_citations_to_report(
            report, DocxRendererType.DOCX
        )

        # Should have sequential numbers
        assert "[1]" in processed
        assert "[2]" in processed
        assert "[3]" in processed

        # Numbers should appear in order
        pos_1 = processed.find("[1]")
        pos_2 = processed.find("[2]")
        pos_3 = processed.find("[3]")
        assert pos_1 < pos_2 < pos_3

    def test_citation_with_hyphens_in_id(
        self, citation_manager, mock_registry, sample_content_chunk
    ):
        """Test citations with hyphens in chunk IDs."""
        report = (
            "Content [bullet_chunk_abc-123-def]\n\n**References:** [chunk_abc-123-def]"
        )

        processed = citation_manager.add_citations_to_report(
            report, DocxRendererType.DOCX
        )

        assert "[1]" in processed
        assert "[bullet_chunk_abc-123-def]" not in processed

    def test_multiple_inline_references_same_chunk(
        self, citation_manager, mock_registry, sample_content_chunk
    ):
        """Test multiple inline references to the same chunk."""
        report = """
- Point A [bullet_chunk_abc]
- Point B [bullet_chunk_abc]
- Point C [bullet_chunk_abc]

**References:** [chunk_abc]
"""
        processed = citation_manager.add_citations_to_report(
            report, DocxRendererType.DOCX
        )

        # All three should reference [1]
        assert processed.count("[1]") >= 3


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
        assert result == "5"

    def test_get_pages_both_pages(self):
        """Test getting pages with both start and end."""
        result = _get_pages(5, 10)
        assert result == "5, 10"

    def test_get_pages_same_page(self):
        """Test getting pages when start and end are same."""
        result = _get_pages(7, 7)
        assert result == "7"
