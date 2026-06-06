"""Tests for InternalSearchMessageLogger.log_chunks and related methods."""

from unittest.mock import AsyncMock, MagicMock

import pytest
from unique_toolkit.content.schemas import ContentChunk, ContentMetadata

from unique_internal_search.services.message_log import InternalSearchMessageLogger


@pytest.fixture
def mock_message_step_logger() -> MagicMock:
    logger = MagicMock()
    logger.create_or_update_message_log_async = AsyncMock(return_value=MagicMock())
    return logger


@pytest.fixture
def message_logger(mock_message_step_logger: MagicMock) -> InternalSearchMessageLogger:
    return InternalSearchMessageLogger(
        message_step_logger=mock_message_step_logger,
        tool_display_name="Internal Search",
    )


@pytest.fixture
def sample_chunk() -> ContentChunk:
    return ContentChunk(
        id="cont_abcdefghijklmnopqrstuv",
        chunk_id="chunk_123",
        key="doc1.pdf",
        text="Sample chunk text",
        order=1,
        start_page=1,
        end_page=2,
        metadata=ContentMetadata(key="doc1.pdf", mime_type="application/pdf"),
    )


class TestLogChunks:
    @pytest.mark.ai
    @pytest.mark.asyncio
    async def test_log_chunks__returns_list__with_internal_chunks(
        self,
        message_logger: InternalSearchMessageLogger,
        mock_message_step_logger: MagicMock,
        sample_chunk: ContentChunk,
    ) -> None:
        """
        Purpose: Verify log_chunks creates references for internal search chunks.
        Why this matters: References link log entries to internal document sources.
        """
        await message_logger.log_chunks([sample_chunk])

        assert len(message_logger._references) == 1
        mock_message_step_logger.create_or_update_message_log_async.assert_called_once()

    @pytest.mark.ai
    @pytest.mark.asyncio
    async def test_log_chunks__sets_sequence_number__for_first_chunk(
        self,
        message_logger: InternalSearchMessageLogger,
        sample_chunk: ContentChunk,
    ) -> None:
        """
        Purpose: Verify sequence_number starts at 0 for the first chunk.
        Why this matters: Sequence numbers control display order in the UI.
        """
        await message_logger.log_chunks([sample_chunk])

        assert message_logger._references[0].sequence_number == 0

    @pytest.mark.ai
    @pytest.mark.asyncio
    async def test_log_chunks__sets_source_id__from_chunk_id(
        self,
        message_logger: InternalSearchMessageLogger,
        sample_chunk: ContentChunk,
    ) -> None:
        """
        Purpose: Verify source_id is taken from the chunk's ID field.
        Why this matters: source_id is used to look up the original document.
        """
        await message_logger.log_chunks([sample_chunk])

        assert message_logger._references[0].source_id == sample_chunk.id

    @pytest.mark.ai
    @pytest.mark.asyncio
    async def test_log_chunks__sets_source__to_internal(
        self,
        message_logger: InternalSearchMessageLogger,
        sample_chunk: ContentChunk,
    ) -> None:
        """
        Purpose: Verify source field is "internal" for internal search references.
        Why this matters: source field distinguishes internal from web search results in the UI.
        """
        await message_logger.log_chunks([sample_chunk])

        assert message_logger._references[0].source == "internal"

    @pytest.mark.ai
    @pytest.mark.asyncio
    async def test_log_chunks__sets_name__from_chunk_key_when_no_title(
        self,
        message_logger: InternalSearchMessageLogger,
    ) -> None:
        """
        Purpose: Verify name falls back to key when title is absent.
        Why this matters: Users see the name in the message log; it should always be meaningful.
        """
        chunk = ContentChunk(
            id="cont_123",
            chunk_id="chunk_1",
            key="fallback.pdf",
            text="text",
            order=1,
            metadata=ContentMetadata(key="fallback.pdf", mime_type="application/pdf"),
        )

        await message_logger.log_chunks([chunk])

        assert message_logger._references[0].name == "fallback.pdf"

    @pytest.mark.ai
    @pytest.mark.asyncio
    async def test_log_chunks__sets_name__from_chunk_title_when_available(
        self,
        message_logger: InternalSearchMessageLogger,
    ) -> None:
        """
        Purpose: Verify name is taken from title when it is present.
        Why this matters: Title is the preferred human-readable display name.
        """
        chunk = ContentChunk(
            id="cont_456",
            chunk_id="chunk_2",
            key="file.pdf",
            title="My Document Title",
            text="text",
            order=1,
            metadata=ContentMetadata(
                key="file.pdf",
                title="My Document Title",
                mime_type="application/pdf",
            ),
        )

        await message_logger.log_chunks([chunk])

        assert message_logger._references[0].name == "My Document Title"

    @pytest.mark.ai
    @pytest.mark.asyncio
    async def test_log_chunks__sets_unique_url__for_internal_chunks(
        self,
        message_logger: InternalSearchMessageLogger,
        sample_chunk: ContentChunk,
    ) -> None:
        """
        Purpose: Verify URL is built as unique://content/<chunk_id>.
        Why this matters: The frontend uses this URL scheme to open the source document.
        """
        await message_logger.log_chunks([sample_chunk])

        assert (
            message_logger._references[0].url == f"unique://content/{sample_chunk.id}"
        )

    @pytest.mark.ai
    @pytest.mark.asyncio
    async def test_log_chunks__increments_sequence_number__for_multiple_chunks(
        self,
        message_logger: InternalSearchMessageLogger,
    ) -> None:
        """
        Purpose: Verify sequence numbers are assigned consecutively across multiple chunks.
        Why this matters: Out-of-order sequence numbers would scramble the source list in the UI.
        """
        chunks = [
            ContentChunk(
                id=f"cont_{i}",
                chunk_id=f"chunk_{i}",
                text="text",
                order=i,
                metadata=ContentMetadata(
                    key=f"doc{i}.pdf", mime_type="application/pdf"
                ),
            )
            for i in range(3)
        ]

        await message_logger.log_chunks(chunks)

        assert [r.sequence_number for r in message_logger._references] == [0, 1, 2]

    @pytest.mark.ai
    @pytest.mark.asyncio
    async def test_log_chunks__includes_chunks__with_empty_name(
        self,
        message_logger: InternalSearchMessageLogger,
    ) -> None:
        """
        Purpose: Verify chunks without title or key produce a reference with an empty name.
        Why this matters: Missing metadata should not drop the source from the log.
        """
        chunk_with_name = ContentChunk(
            id="cont_named",
            chunk_id="chunk_named",
            key="doc1.pdf",
            text="text",
            order=1,
            metadata=ContentMetadata(key="doc1.pdf", mime_type="application/pdf"),
        )
        chunk_no_name = ContentChunk(
            id="cont_unnamed",
            chunk_id="chunk_unnamed",
            text="text",
            order=2,
            metadata=ContentMetadata(key="", mime_type="application/pdf"),
        )

        await message_logger.log_chunks([chunk_with_name, chunk_no_name])

        assert len(message_logger._references) == 2
        assert message_logger._references[0].name == "doc1.pdf"
        assert message_logger._references[1].name == ""
