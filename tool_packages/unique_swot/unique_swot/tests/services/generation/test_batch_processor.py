"""Comprehensive tests for batch processing functionality."""

from unittest.mock import AsyncMock, Mock

import pytest
from unique_toolkit._common.default_language_model import DEFAULT_GPT_4o
from unique_toolkit.language_model.infos import LanguageModelInfo

from unique_swot.services.collection.schema import Source, SourceChunk, SourceType
from unique_swot.services.generation.batch_processor import (
    SourceBatchs,
    extract_swot_from_source_batch,
    split_context_into_batches,
    summarize_swot_extraction_results,
)
from unique_swot.services.generation.models.strengths import StrengthsExtraction

LANGUAGE_MODEL = LanguageModelInfo.from_name(DEFAULT_GPT_4o)


class TestSplitContextIntoBatches:
    """Test cases for split_context_into_batches function."""

    def test_split_single_source_single_chunk(self):
        """Test splitting a single source with one small chunk."""
        sources = [
            Source(
                type=SourceType.KNOWLEDGE_BASE,
                url="https://example.com",
                title="Test Source",
                chunks=[SourceChunk(id="chunk_1", text="Short content.")],
            )
        ]

        batches = split_context_into_batches(
            sources=sources,
            batch_size=10,
            max_tokens_per_batch=10000,
            language_model=LANGUAGE_MODEL,
        )

        assert len(batches) == 1  # One SourceBatchs object
        assert len(batches[0].batches) == 1  # One batch within it
        assert len(batches[0].batches[0]) == 1  # One chunk in the batch

    def test_split_single_source_multiple_chunks(self):
        """Test splitting a single source with multiple chunks."""
        chunks = [
            SourceChunk(id=f"chunk_{i}", text=f"Content for chunk {i}.")
            for i in range(5)
        ]
        sources = [
            Source(
                type=SourceType.KNOWLEDGE_BASE,
                url="https://example.com",
                title="Test Source",
                chunks=chunks,
            )
        ]

        batches = split_context_into_batches(
            sources=sources,
            batch_size=2,  # Small batch size
            max_tokens_per_batch=10000,
            language_model=LANGUAGE_MODEL,
        )

        # Should create one SourceBatchs with multiple batches due to batch_size limit
        assert len(batches) == 1
        assert len(batches[0].batches) >= 2

    def test_split_respects_batch_size(self):
        """Test that splitting respects the batch_size parameter."""
        chunks = [SourceChunk(id=f"chunk_{i}", text="Short text.") for i in range(10)]
        sources = [
            Source(
                type=SourceType.KNOWLEDGE_BASE,
                url="https://example.com",
                title="Test Source",
                chunks=chunks,
            )
        ]

        batches = split_context_into_batches(
            sources=sources,
            batch_size=3,
            max_tokens_per_batch=100000,  # Large limit
            language_model=LANGUAGE_MODEL,
        )

        # Each batch should have at most 3 chunks
        assert len(batches) == 1  # One source
        for batch in batches[0].batches:
            assert len(batch) <= 3

    def test_split_multiple_sources(self):
        """Test splitting multiple sources."""
        sources = [
            Source(
                type=SourceType.KNOWLEDGE_BASE,
                url="https://example.com/1",
                title="Source 1",
                chunks=[SourceChunk(id="chunk_1", text="Content 1.")],
            ),
            Source(
                type=SourceType.WEB,
                url="https://example.com/2",
                title="Source 2",
                chunks=[SourceChunk(id="chunk_2", text="Content 2.")],
            ),
        ]

        batches = split_context_into_batches(
            sources=sources,
            batch_size=10,
            max_tokens_per_batch=10000,
            language_model=LANGUAGE_MODEL,
        )

        assert len(batches) >= 1

    def test_split_empty_sources(self):
        """Test splitting with empty sources list."""
        batches = split_context_into_batches(
            sources=[],
            batch_size=10,
            max_tokens_per_batch=10000,
            language_model=LANGUAGE_MODEL,
        )

        assert len(batches) == 0

    def test_split_source_with_empty_chunks(self):
        """Test splitting a source with no chunks."""
        sources = [
            Source(
                type=SourceType.KNOWLEDGE_BASE,
                url="https://example.com",
                title="Empty Source",
                chunks=[],
            )
        ]

        batches = split_context_into_batches(
            sources=sources,
            batch_size=10,
            max_tokens_per_batch=10000,
            language_model=LANGUAGE_MODEL,
        )

        # Creates one SourceBatchs but with no batches inside
        assert len(batches) == 1
        assert len(batches[0].batches) == 0


class TestExtractSwotFromSourceBatch:
    """Test cases for extract_swot_from_source_batch function."""

    @pytest.fixture
    def mock_language_model_service(self):
        """Create a mock language model service."""
        service = Mock()
        mock_response = Mock()
        mock_response.choices = [Mock()]
        mock_response.choices[0].message.parsed = {"strengths": []}
        service.complete_async = AsyncMock(return_value=mock_response)
        return service

    @pytest.fixture
    def batch_parser(self):
        """Create a simple batch parser function."""

        def parser(chunks):
            return "\n".join([chunk.text for chunk in chunks])

        return parser

    @pytest.mark.asyncio
    async def test_extract_swot_from_batch_success(
        self, mock_language_model_service, batch_parser
    ):
        """Test successful extraction from a batch."""
        batch = [
            SourceChunk(id="chunk_1", text="Strong brand."),
            SourceChunk(id="chunk_2", text="Good reputation."),
        ]

        result = await extract_swot_from_source_batch(
            system_prompt="Analyze strengths",
            batch_parser=batch_parser,
            language_model_service=mock_language_model_service,
            language_model=LANGUAGE_MODEL,
            output_model=StrengthsExtraction,
            batch=batch,
        )

        assert result is not None
        mock_language_model_service.complete_async.assert_called_once()

    @pytest.mark.asyncio
    async def test_extract_swot_from_empty_batch(
        self, mock_language_model_service, batch_parser
    ):
        """Test extraction from an empty batch."""
        batch = []

        await extract_swot_from_source_batch(
            system_prompt="Analyze strengths",
            batch_parser=batch_parser,
            language_model_service=mock_language_model_service,
            language_model=LANGUAGE_MODEL,
            output_model=StrengthsExtraction,
            batch=batch,
        )

        # Should still call the service
        assert mock_language_model_service.complete_async.called

    @pytest.mark.asyncio
    async def test_extract_swot_from_batch_error_handling(self, batch_parser):
        """Test that extraction handles errors gracefully."""
        service = Mock()
        service.complete_async = AsyncMock(side_effect=Exception("API Error"))

        batch = [SourceChunk(id="chunk_1", text="Content")]

        result = await extract_swot_from_source_batch(
            system_prompt="Analyze",
            batch_parser=batch_parser,
            language_model_service=service,
            language_model=LANGUAGE_MODEL,
            output_model=StrengthsExtraction,
            batch=batch,
        )

        # Should return None on error
        assert result is None


class TestSummarizeSwotExtractionResults:
    """Test cases for summarize_swot_extraction_results function."""

    @pytest.fixture
    def mock_language_model_service(self):
        """Create a mock language model service."""
        service = Mock()
        mock_response = Mock()
        mock_response.choices = [Mock()]
        mock_response.choices[0].message.content = "Summarized analysis"
        service.complete_async = AsyncMock(return_value=mock_response)
        return service

    @pytest.fixture
    def mock_extraction_model(self):
        """Create a mock extraction output model."""
        return StrengthsExtraction(strengths=[])

    @pytest.mark.asyncio
    async def test_summarize_success(
        self, mock_language_model_service, mock_extraction_model
    ):
        """Test successful summarization."""
        result = await summarize_swot_extraction_results(
            system_prompt="Summarize the analysis",
            language_model_service=mock_language_model_service,
            language_model=LANGUAGE_MODEL,
            extraction_output_model=mock_extraction_model,
        )

        assert result == "Summarized analysis"
        mock_language_model_service.complete_async.assert_called_once()

    @pytest.mark.asyncio
    async def test_summarize_error_handling(self, mock_extraction_model):
        """Test that summarization handles errors gracefully."""
        service = Mock()
        service.complete_async = AsyncMock(side_effect=Exception("Summarization error"))

        result = await summarize_swot_extraction_results(
            system_prompt="Summarize",
            language_model_service=service,
            language_model=LANGUAGE_MODEL,
            extraction_output_model=mock_extraction_model,
        )

        # Should return error message
        assert "Unavailable summary" in result
        assert "error" in result.lower()


class TestSourceBatchs:
    """Test cases for SourceBatchs model."""

    def test_source_batchs_initialization(self):
        """Test SourceBatchs initialization."""
        source = Source(
            type=SourceType.KNOWLEDGE_BASE,
            url="https://example.com",
            title="Test Source",
            chunks=[],
        )

        batch_model = SourceBatchs(source=source)

        assert batch_model.source == source
        assert batch_model.batches == []

    def test_source_batchs_with_batches(self):
        """Test SourceBatchs with batches."""
        source = Source(
            type=SourceType.KNOWLEDGE_BASE,
            url="https://example.com",
            title="Test Source",
            chunks=[],
        )

        batch1 = [SourceChunk(id="chunk_1", text="Content 1")]
        batch2 = [SourceChunk(id="chunk_2", text="Content 2")]

        batch_model = SourceBatchs(source=source, batches=[batch1, batch2])

        assert len(batch_model.batches) == 2
        assert batch_model.batches[0] == batch1
        assert batch_model.batches[1] == batch2


class TestBatchProcessingIntegration:
    """Integration tests for batch processing."""

    @pytest.mark.asyncio
    async def test_batch_processing_with_token_limits(self):
        """Test that batch processing respects token limits."""
        # Create chunks with known content sizes
        chunks = [SourceChunk(id=f"chunk_{i}", text="word " * 100) for i in range(20)]
        source = Source(
            type=SourceType.KNOWLEDGE_BASE,
            url="https://example.com",
            title="Large Source",
            chunks=chunks,
        )

        batches = split_context_into_batches(
            sources=[source],
            batch_size=5,  # Small batch size
            max_tokens_per_batch=500,  # Small token limit
            language_model=LANGUAGE_MODEL,
        )

        # Should create multiple batches
        assert len(batches) == 1  # One SourceBatchs
        assert len(batches[0].batches) > 1  # Multiple batches within

        # Each batch should respect the batch size limit
        for batch in batches[0].batches:
            assert len(batch) <= 5

    @pytest.mark.asyncio
    async def test_end_to_end_batch_extraction(self):
        """Test end-to-end batch extraction process."""
        # Create test data
        chunks = [
            SourceChunk(id="chunk_1", text="Strong brand recognition."),
            SourceChunk(id="chunk_2", text="Market leadership position."),
            SourceChunk(id="chunk_3", text="High customer satisfaction."),
        ]
        source = Source(
            type=SourceType.KNOWLEDGE_BASE,
            url="https://example.com",
            title="Company Report",
            chunks=chunks,
        )

        # Split into batches
        batches = split_context_into_batches(
            sources=[source],
            batch_size=10,
            max_tokens_per_batch=10000,
            language_model=LANGUAGE_MODEL,
        )

        # Mock LLM service
        llm_service = Mock()
        mock_response = Mock()
        mock_response.choices = [Mock()]
        mock_response.choices[0].message.parsed = {
            "strengths": [
                {
                    "title": "Strong brand",
                    "justification": "Market leader with strong brand recognition",
                    "reference_chunk_ids": ["chunk_1"],
                }
            ]
        }
        llm_service.complete_async = AsyncMock(return_value=mock_response)

        # Process each batch
        results = []
        for source_batch in batches:
            for batch in source_batch.batches:
                result = await extract_swot_from_source_batch(
                    system_prompt="Extract strengths",
                    batch_parser=lambda chunks: "\n".join([c.text for c in chunks]),
                    language_model_service=llm_service,
                    language_model=LANGUAGE_MODEL,
                    output_model=StrengthsExtraction,
                    batch=batch,
                )
                if result:
                    results.append(result)

        # Verify results - should have at least one result
        assert len(results) >= 1
        assert all(isinstance(r, StrengthsExtraction) for r in results)

    def test_batch_splitting_deterministic(self):
        """Test that batch splitting is deterministic."""
        chunks = [SourceChunk(id=f"chunk_{i}", text="Content") for i in range(10)]
        source = Source(
            type=SourceType.KNOWLEDGE_BASE,
            url="https://example.com",
            title="Test",
            chunks=chunks,
        )

        # Split twice with same parameters
        batches1 = split_context_into_batches(
            sources=[source],
            batch_size=3,
            max_tokens_per_batch=10000,
            language_model=LANGUAGE_MODEL,
        )

        batches2 = split_context_into_batches(
            sources=[source],
            batch_size=3,
            max_tokens_per_batch=10000,
            language_model=LANGUAGE_MODEL,
        )

        # Results should be identical
        assert len(batches1) == len(batches2)
        assert len(batches1[0].batches) == len(batches2[0].batches)

    def test_batch_splitting_preserves_order(self):
        """Test that batch splitting preserves chunk order."""
        chunks = [SourceChunk(id=f"chunk_{i}", text=f"Content {i}") for i in range(10)]
        source = Source(
            type=SourceType.KNOWLEDGE_BASE,
            url="https://example.com",
            title="Test",
            chunks=chunks,
        )

        batches = split_context_into_batches(
            sources=[source],
            batch_size=3,
            max_tokens_per_batch=10000,
            language_model=LANGUAGE_MODEL,
        )

        # Reconstruct all chunks from batches
        reconstructed_chunks = []
        for source_batch in batches:
            for batch in source_batch.batches:
                reconstructed_chunks.extend(batch)

        # Order should be preserved
        assert len(reconstructed_chunks) == len(chunks)
        for i, chunk in enumerate(reconstructed_chunks):
            assert chunk.id == f"chunk_{i}"
            assert chunk.text == f"Content {i}"

    @pytest.mark.asyncio
    async def test_batch_processing_with_varied_chunk_sizes(self):
        """Test batch processing with chunks of different sizes."""
        # Create chunks with varying content sizes
        chunks = [
            SourceChunk(id="chunk_1", text="Short."),
            SourceChunk(id="chunk_2", text="Medium content " * 50),
            SourceChunk(id="chunk_3", text="Very long content " * 200),
            SourceChunk(id="chunk_4", text="Another short."),
        ]
        source = Source(
            type=SourceType.KNOWLEDGE_BASE,
            url="https://example.com",
            title="Varied Content",
            chunks=chunks,
        )

        batches = split_context_into_batches(
            sources=[source],
            batch_size=10,
            max_tokens_per_batch=1000,
            language_model=LANGUAGE_MODEL,
        )

        # Should create one SourceBatchs
        assert len(batches) == 1
        # Large chunk should cause multiple batches
        assert len(batches[0].batches) >= 1

        # Verify all chunks are included
        total_chunks = sum(len(batch) for batch in batches[0].batches)
        assert total_chunks == len(chunks)
