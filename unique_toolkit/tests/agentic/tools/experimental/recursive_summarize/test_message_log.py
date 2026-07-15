"""Tests for RecursiveSummarizeMessageLogger."""

from unittest.mock import AsyncMock, MagicMock

import pytest

from unique_toolkit.agentic.tools.experimental.recursive_summarize.message_log import (
    RecursiveSummarizeMessageLogger,
    build_cited_reference_chunks,
    build_reference_chunks,
    content_to_reference,
    representative_chunk,
)
from unique_toolkit.content.schemas import Content, ContentChunk, ContentMetadata


@pytest.fixture
def mock_message_step_logger() -> MagicMock:
    logger = MagicMock()
    logger.create_or_update_message_log_async = AsyncMock(return_value=MagicMock())
    return logger


@pytest.fixture
def message_logger(
    mock_message_step_logger: MagicMock,
) -> RecursiveSummarizeMessageLogger:
    return RecursiveSummarizeMessageLogger(
        message_step_logger=mock_message_step_logger,
        tool_display_name="Summarize",
    )


@pytest.fixture
def sample_content() -> Content:
    return Content(
        id="cont_abcdefghijklmnopqrstuv",
        key="report.pdf",
        title="Annual Report",
        chunks=[
            ContentChunk(
                id="cont_abcdefghijklmnopqrstuv",
                chunk_id="chunk_123",
                key="report.pdf",
                text="Sample chunk text",
                order=1,
                metadata=ContentMetadata(key="report.pdf", mime_type="application/pdf"),
            )
        ],
    )


class TestRecursiveSummarizeMessageLogger:
    @pytest.mark.ai
    @pytest.mark.asyncio
    async def test_log_task__adds_task_detail(
        self,
        message_logger: RecursiveSummarizeMessageLogger,
        mock_message_step_logger: MagicMock,
    ) -> None:
        await message_logger.log_task("Summarize the uploaded document")

        assert message_logger._details.data is not None
        assert len(message_logger._details.data) == 1
        assert message_logger._details.data[0].text == "Summarize the uploaded document"
        mock_message_step_logger.create_or_update_message_log_async.assert_called_once()

    @pytest.mark.ai
    @pytest.mark.asyncio
    async def test_log_contents__adds_document_reference(
        self,
        message_logger: RecursiveSummarizeMessageLogger,
        sample_content: Content,
    ) -> None:
        await message_logger.log_contents([sample_content])

        assert len(message_logger._references) == 1
        assert message_logger._references[0].name == "report.pdf"


class TestContentToReference:
    @pytest.mark.ai
    def test_content_to_reference__uses_first_chunk_when_present(
        self, sample_content: Content
    ) -> None:
        reference = content_to_reference(sample_content, sequence_number=0)

        assert reference.source_id == "cont_abcdefghijklmnopqrstuv_chunk_123"
        assert reference.name == "report.pdf"

    @pytest.mark.ai
    def test_content_to_reference__falls_back_to_content_metadata(self) -> None:
        content = Content(
            id="cont_abcdefghijklmnopqrstuv",
            key="notes.txt",
            title="Meeting Notes",
        )

        reference = content_to_reference(content, sequence_number=0)

        assert reference.name == "Meeting Notes"
        assert reference.source_id == "cont_abcdefghijklmnopqrstuv"


class TestBuildReferenceChunks:
    @pytest.mark.ai
    def test_build_reference_chunks__returns_one_stub_per_content(
        self, sample_content: Content
    ) -> None:
        sample_content.chunks[0].start_page = 3
        sample_content.chunks[0].end_page = 3
        second_chunk = sample_content.chunks[0].model_copy(
            deep=True,
            update={"chunk_id": "chunk_456", "order": 2, "text": "Another page"},
        )
        sample_content.chunks.append(second_chunk)

        chunks = build_reference_chunks([sample_content])

        assert len(chunks) == 1
        assert chunks[0].text == ""
        assert chunks[0].chunk_id == "chunk_123"


class TestBuildCitedReferenceChunks:
    @pytest.mark.ai
    def test_build_cited_reference_chunks__preserves_order_and_text(
        self, sample_content: Content
    ) -> None:
        first = sample_content.chunks[0]
        second = first.model_copy(
            deep=True,
            update={"chunk_id": "chunk_456", "order": 2, "text": "Second passage"},
        )

        chunks = build_cited_reference_chunks([second, first])

        assert [chunk.chunk_id for chunk in chunks] == ["chunk_456", "chunk_123"]
        assert chunks[0].text == "Second passage"
        assert chunks[1].text == "Sample chunk text"

    @pytest.mark.ai
    def test_build_cited_reference_chunks__appends_page_postfix_per_chunk(
        self, sample_content: Content
    ) -> None:
        page3 = sample_content.chunks[0].model_copy(
            deep=True,
            update={"title": "Annual Report", "start_page": 3, "end_page": 3},
        )
        page9 = sample_content.chunks[0].model_copy(
            deep=True,
            update={
                "title": "Annual Report",
                "chunk_id": "chunk_456",
                "start_page": 9,
                "end_page": 9,
            },
        )

        chunks = build_cited_reference_chunks([page3, page9])

        # node-chat names the reference from title ?? key; the page must ride along
        # so the frontend can deep-link, and distinct pages must yield distinct names.
        assert chunks[0].key == "report.pdf : 3"
        assert chunks[0].title == "Annual Report : 3"
        assert chunks[1].key == "report.pdf : 9"
        assert chunks[1].title == "Annual Report : 9"

    @pytest.mark.ai
    def test_build_cited_reference_chunks__postfixes_key_when_title_absent(
        self, sample_content: Content
    ) -> None:
        chunk = sample_content.chunks[0].model_copy(
            deep=True, update={"start_page": 7, "end_page": 7}
        )

        chunks = build_cited_reference_chunks([chunk])

        assert chunks[0].title is None
        assert chunks[0].key == "report.pdf : 7"

    @pytest.mark.ai
    def test_build_cited_reference_chunks__no_postfix_without_pages(
        self, sample_content: Content
    ) -> None:
        chunk = sample_content.chunks[0].model_copy(
            deep=True, update={"start_page": None, "end_page": None}
        )

        chunks = build_cited_reference_chunks([chunk])

        assert chunks[0].key == "report.pdf"

    @pytest.mark.ai
    def test_build_cited_reference_chunks__does_not_mutate_input(
        self, sample_content: Content
    ) -> None:
        chunk = sample_content.chunks[0].model_copy(
            deep=True, update={"start_page": 5, "end_page": 5}
        )

        build_cited_reference_chunks([chunk])

        assert chunk.key == "report.pdf"


class TestRepresentativeChunk:
    @pytest.mark.ai
    def test_representative_chunk__synthesizes_chunk_when_no_ingested_chunks(
        self,
    ) -> None:
        content = Content(
            id="cont_abcdefghijklmnopqrstuv",
            key="notes.txt",
            title="Meeting Notes",
        )

        chunk = representative_chunk(content)

        assert chunk is not None
        assert chunk.id == "cont_abcdefghijklmnopqrstuv"
        assert chunk.key == "notes.txt"
