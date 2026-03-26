import json

from unique_toolkit.agentic.history_manager.utils import (
    _chunk_is_pdf,
    transform_chunks_to_string,
)
from unique_toolkit.content.schemas import ContentChunk, ContentMetadata

# --- _chunk_is_pdf ---


def test_chunk_is_pdf__by_mime_type():
    chunk = ContentChunk(
        id="cont_abc",
        text="some text",
        metadata=ContentMetadata(key="file.pdf", mime_type="application/pdf"),
    )
    assert _chunk_is_pdf(chunk) is True


def test_chunk_is_pdf__by_key_extension():
    chunk = ContentChunk(id="cont_abc", text="text", key="report.pdf")
    assert _chunk_is_pdf(chunk) is True


def test_chunk_is_pdf__by_key_with_page_postfix():
    chunk = ContentChunk(id="cont_abc", text="text", key="report.pdf : 5,6,7")
    assert _chunk_is_pdf(chunk) is True


def test_chunk_is_pdf__case_insensitive():
    chunk = ContentChunk(id="cont_abc", text="text", key="Report.PDF")
    assert _chunk_is_pdf(chunk) is True


def test_chunk_is_pdf__non_pdf_key():
    chunk = ContentChunk(id="cont_abc", text="text", key="document.docx")
    assert _chunk_is_pdf(chunk) is False


def test_chunk_is_pdf__no_key_no_metadata():
    chunk = ContentChunk(id="cont_abc", text="text")
    assert _chunk_is_pdf(chunk) is False


def test_chunk_is_pdf__non_pdf_mime_type():
    chunk = ContentChunk(
        id="cont_abc",
        text="text",
        key="file.docx",
        metadata=ContentMetadata(
            key="file.docx", mime_type="application/vnd.openxmlformats"
        ),
    )
    assert _chunk_is_pdf(chunk) is False
