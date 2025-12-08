from unittest.mock import Mock

from unique_toolkit.content.schemas import ContentChunk

from unique_swot.services.citations import CitationManager
from unique_swot.services.report import DocxRendererType


def _make_chunk():
    return ContentChunk(
        id="content_1",
        chunk_id="chunk_a",
        title="Test Doc",
        key="doc.pdf",
        text="Some text",
        start_page=1,
        end_page=2,
    )


def test_add_citations_docx_and_track_chunks():
    registry = Mock()
    registry.retrieve.return_value = _make_chunk()
    manager = CitationManager(content_chunk_registry=registry)

    processed = manager.add_citations_to_report(
        "**References:** [chunk_a]", DocxRendererType.DOCX
    )

    assert "[chunk_a]" not in processed
    assert "p1" in processed
    assert manager.get_referenced_content_chunks() == [_make_chunk()]


def test_add_citations_chat_format():
    registry = Mock()
    registry.retrieve.return_value = _make_chunk()
    manager = CitationManager(content_chunk_registry=registry)

    processed = manager.add_citations_to_report(
        "See ref [chunk_a]", DocxRendererType.CHAT
    )

    assert "<sup>1</sup>" in processed
    assert "[chunk_a]" not in processed


def test_missing_chunk_uses_placeholder():
    registry = Mock()
    registry.retrieve.return_value = None
    manager = CitationManager(content_chunk_registry=registry)

    processed = manager.add_citations_to_report(
        "See ref [chunk_missing]", DocxRendererType.DOCX
    )

    assert "[???]" in processed


def test_get_references_builds_content_references():
    registry = Mock()
    registry.retrieve.return_value = _make_chunk()
    manager = CitationManager(content_chunk_registry=registry)
    manager.add_citations_to_report("See [chunk_a]", DocxRendererType.CHAT)

    refs = manager.get_references("msg1")

    assert refs[0].message_id == "msg1"
    assert refs[0].sequence_number == 0
    assert refs[0].source == "SWOT-TOOL"
