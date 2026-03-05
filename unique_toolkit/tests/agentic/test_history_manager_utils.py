import json

import pytest

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
        metadata=ContentMetadata(key="file.docx", mime_type="application/vnd.openxmlformats"),
    )
    assert _chunk_is_pdf(chunk) is False


# --- transform_chunks_to_string ---


def test_transform_chunks__empty_list():
    result_str, sources = transform_chunks_to_string([], 0)
    assert result_str == "No relevant sources found."
    assert sources == []


def test_transform_chunks__pdf_chunk_includes_content_id_when_flag_enabled():
    chunks = [
        ContentChunk(id="cont_abc123", text="PDF content", key="report.pdf"),
    ]

    result_str, sources = transform_chunks_to_string(
        chunks, 0, include_content_id_for_pdf_chunks=True
    )

    assert len(sources) == 1
    assert sources[0]["content_id"] == "cont_abc123"
    assert sources[0]["content"] == "PDF content"
    parsed = json.loads(result_str)
    assert parsed[0]["content_id"] == "cont_abc123"


def test_transform_chunks__pdf_chunk_excludes_content_id_when_flag_disabled():
    chunks = [
        ContentChunk(id="cont_abc123", text="PDF content", key="report.pdf"),
    ]

    _, sources = transform_chunks_to_string(chunks, 0)

    assert len(sources) == 1
    assert "content_id" not in sources[0]


def test_transform_chunks__non_pdf_chunk_excludes_content_id():
    chunks = [
        ContentChunk(id="cont_abc123", text="Word content", key="document.docx"),
    ]

    result_str, sources = transform_chunks_to_string(
        chunks, 0, include_content_id_for_pdf_chunks=True
    )

    assert len(sources) == 1
    assert "content_id" not in sources[0]
    assert sources[0]["content"] == "Word content"


def test_transform_chunks__mixed_pdf_and_non_pdf():
    chunks = [
        ContentChunk(id="cont_pdf1", text="PDF text", key="report.pdf"),
        ContentChunk(id="cont_doc1", text="Doc text", key="notes.docx"),
        ContentChunk(id="cont_pdf2", text="PDF text 2", key="invoice.pdf : 1,2"),
    ]

    _, sources = transform_chunks_to_string(
        chunks, 10, include_content_id_for_pdf_chunks=True
    )

    assert sources[0]["content_id"] == "cont_pdf1"
    assert sources[0]["source_number"] == 10
    assert "content_id" not in sources[1]
    assert sources[1]["source_number"] == 11
    assert sources[2]["content_id"] == "cont_pdf2"
    assert sources[2]["source_number"] == 12


def test_transform_chunks__pdf_without_id_excludes_content_id():
    chunks = [
        ContentChunk(id="", text="No ID PDF", key="report.pdf"),
    ]

    _, sources = transform_chunks_to_string(
        chunks, 0, include_content_id_for_pdf_chunks=True
    )

    assert "content_id" not in sources[0]
