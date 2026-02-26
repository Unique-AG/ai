from unittest.mock import Mock

from unique_toolkit.content import ContentChunk

from unique_swot.services.citations import CitationManager
from unique_swot.services.report.config import RendererType


def _make_chunk(chunk_id="a", title="Test Doc", start_page=1, end_page=2):
    """Helper to create test ContentChunk."""
    return ContentChunk(
        id="content_1",
        chunk_id=f"chunk_{chunk_id}",
        title=title,
        key="doc.pdf",
        text="Some text",
        start_page=start_page,
        end_page=end_page,
        order=0,
    )


def test_add_citations_docx_format():
    """Test DOCX citation format with page numbers and document reference."""
    registry = Mock()
    registry.retrieve.return_value = _make_chunk()
    manager = CitationManager(content_chunk_registry=registry)

    processed = manager.map_citations_to_report(
        "**References:** [chunk_a]", RendererType.DOCX
    )

    assert "[chunk_a]" not in processed
    assert "p1" in processed or "p2" in processed  # Page numbers included
    assert manager.get_referenced_content_chunks() == [_make_chunk()]


def test_add_citations_chat_format():
    """Test Chat citation format with superscript numbers."""
    registry = Mock()
    registry.retrieve.return_value = _make_chunk()
    manager = CitationManager(content_chunk_registry=registry)

    processed = manager.map_citations_to_report("See ref [chunk_a]", RendererType.CHAT)

    assert "<sup>1</sup>" in processed
    assert "[chunk_a]" not in processed


def test_missing_chunk_uses_placeholder():
    """Test that missing chunks are replaced with [???] placeholder."""
    registry = Mock()
    registry.retrieve.return_value = None
    manager = CitationManager(content_chunk_registry=registry)

    processed = manager.map_citations_to_report(
        "See ref [chunk_missing]", RendererType.DOCX
    )

    assert "[???]" in processed
    assert "[chunk_missing]" not in processed


def test_duplicate_citations_reuse_same_reference():
    """Test that duplicate citations reuse the same formatted reference."""
    registry = Mock()
    registry.retrieve.return_value = _make_chunk()
    manager = CitationManager(content_chunk_registry=registry)

    processed = manager.map_citations_to_report(
        "First [chunk_a] and second [chunk_a]", RendererType.CHAT
    )

    # Both should use the same superscript
    assert processed.count("<sup>1</sup>") == 2
    # Only one chunk should be tracked
    assert len(manager.get_referenced_content_chunks()) == 1


def test_multiple_citations_sequential_numbering():
    """Test that multiple different citations get sequential numbers."""
    registry = Mock()
    registry.retrieve.side_effect = [_make_chunk("a"), _make_chunk("b")]
    manager = CitationManager(content_chunk_registry=registry)

    processed = manager.map_citations_to_report(
        "First [chunk_a] and second [chunk_b]", RendererType.CHAT
    )

    assert "<sup>1</sup>" in processed
    assert "<sup>2</sup>" in processed
    assert len(manager.get_referenced_content_chunks()) == 2


def test_get_references_builds_content_references():
    """Test that get_references creates proper ContentReference objects."""
    registry = Mock()
    registry.retrieve.return_value = _make_chunk()
    manager = CitationManager(content_chunk_registry=registry)
    manager.map_citations_to_report("See [chunk_a]", RendererType.CHAT)

    refs = manager.get_references("msg1")

    assert len(refs) == 1
    assert refs[0].message_id == "msg1"
    assert refs[0].sequence_number == 0
    assert refs[0].source == "SWOT-TOOL"
    assert "unique://content/" in refs[0].url


def test_get_citations_for_docx():
    """Test that get_citations_for_docx returns formatted citation list."""
    registry = Mock()
    registry.retrieve.side_effect = [
        _make_chunk("a", "Doc A"),
        _make_chunk("b", "Doc B"),
    ]
    manager = CitationManager(content_chunk_registry=registry)
    manager.map_citations_to_report("[chunk_a] and [chunk_b]", RendererType.DOCX)

    citations = manager.get_citations_for_docx()

    assert len(citations) == 2
    assert "[1] Doc A" in citations
    assert "[2] Doc B" in citations


def test_page_range_formatting():
    """Test that page ranges are formatted correctly."""
    registry = Mock()
    registry.retrieve.return_value = _make_chunk("a", "Test Doc", 5, 7)
    manager = CitationManager(content_chunk_registry=registry)

    processed = manager.map_citations_to_report("[chunk_a]", RendererType.DOCX)

    # Should include both page numbers
    assert "5" in processed
    assert "7" in processed


def test_single_page_formatting():
    """Test that single page citations are formatted correctly."""
    registry = Mock()
    registry.retrieve.return_value = _make_chunk("a", "Test Doc", 5, 5)
    manager = CitationManager(content_chunk_registry=registry)

    processed = manager.map_citations_to_report("[chunk_a]", RendererType.DOCX)

    assert "p5" in processed
