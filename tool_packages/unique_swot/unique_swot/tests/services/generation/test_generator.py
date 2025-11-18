"""Comprehensive tests for SWOT generation pipeline."""

from unittest.mock import AsyncMock, Mock

import pytest
from unique_toolkit._common.default_language_model import DEFAULT_GPT_4o
from unique_toolkit.language_model.infos import LanguageModelInfo

from unique_swot.services.collection.schema import Source, SourceChunk, SourceType
from unique_swot.services.generation import SWOTComponent
from unique_swot.services.generation.config import ReportGenerationConfig
from unique_swot.services.generation.contexts import (
    ReportGenerationContext,
    ReportSummarizationContext,
)
from unique_swot.services.generation.generator import (
    extract_swot_from_sources,
    modify_report,
    summarize_swot_extraction,
)
from unique_swot.services.generation.models.strengths import StrengthsExtraction

LANGUAGE_MODEL = LanguageModelInfo.from_name(DEFAULT_GPT_4o)


class TestExtractSwotFromSources:
    """Test cases for extract_swot_from_sources function."""

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
    def mock_notifier(self):
        """Create a mock notifier."""
        notifier = Mock()
        notifier.notify = Mock()
        notifier.update_progress = Mock()
        return notifier

    @pytest.fixture
    def batch_parser(self):
        """Create a batch parser function."""

        def parser(chunks):
            return "\n".join([chunk.text for chunk in chunks])

        return parser

    @pytest.fixture
    def generation_context(self, sample_sources):
        """Create a generation context."""
        return ReportGenerationContext(
            component=SWOTComponent.STRENGTHS,
            sources=sample_sources,
            extraction_system_prompt="Extract strengths from the sources",
            extraction_output_model=StrengthsExtraction,
            company_name="Test Company",
        )

    @pytest.fixture
    def generation_config(self):
        """Create a generation configuration."""
        return ReportGenerationConfig(
            extraction_batch_size=10,
            max_tokens_per_extraction_batch=5000,
            language_model=LANGUAGE_MODEL,
        )

    @pytest.mark.asyncio
    async def test_extract_swot_from_sources_success(
        self,
        generation_context,
        generation_config,
        mock_language_model_service,
        mock_notifier,
        batch_parser,
    ):
        """Test successful extraction from sources."""
        result = await extract_swot_from_sources(
            context=generation_context,
            configuration=generation_config,
            language_model_service=mock_language_model_service,
            notifier=mock_notifier,
            batch_parser=batch_parser,
        )

        # Verify result is of correct type
        assert isinstance(result, StrengthsExtraction)

        # Verify notifier was called
        assert mock_notifier.notify.called
        assert mock_notifier.update_progress.called

        # Verify LLM service was called
        assert mock_language_model_service.complete_async.called

    @pytest.mark.asyncio
    async def test_extract_swot_from_empty_sources(
        self,
        generation_config,
        mock_language_model_service,
        mock_notifier,
        batch_parser,
    ):
        """Test extraction with empty sources list."""
        empty_context = ReportGenerationContext(
            component=SWOTComponent.STRENGTHS,
            sources=[],
            extraction_system_prompt="Extract strengths",
            extraction_output_model=StrengthsExtraction,
            company_name="Test Company",
        )

        result = await extract_swot_from_sources(
            context=empty_context,
            configuration=generation_config,
            language_model_service=mock_language_model_service,
            notifier=mock_notifier,
            batch_parser=batch_parser,
        )

        # Should return empty extraction
        assert isinstance(result, StrengthsExtraction)

        # LLM should not be called for empty sources
        assert not mock_language_model_service.complete_async.called

    @pytest.mark.asyncio
    async def test_extract_swot_progress_tracking(
        self,
        generation_context,
        generation_config,
        mock_language_model_service,
        mock_notifier,
        batch_parser,
    ):
        """Test that progress is tracked during extraction."""
        await extract_swot_from_sources(
            context=generation_context,
            configuration=generation_config,
            language_model_service=mock_language_model_service,
            notifier=mock_notifier,
            batch_parser=batch_parser,
        )

        # Verify progress updates were called
        assert mock_notifier.update_progress.called
        update_calls = mock_notifier.update_progress.call_count
        assert update_calls > 0

        # Verify notify was called for start and completion
        notify_calls = mock_notifier.notify.call_args_list
        assert len(notify_calls) >= 2  # At least start and end

    @pytest.mark.asyncio
    async def test_extract_swot_notification_messages(
        self,
        generation_context,
        generation_config,
        mock_language_model_service,
        mock_notifier,
        batch_parser,
    ):
        """Test notification messages during extraction."""
        await extract_swot_from_sources(
            context=generation_context,
            configuration=generation_config,
            language_model_service=mock_language_model_service,
            notifier=mock_notifier,
            batch_parser=batch_parser,
        )

        # Check notification content
        notify_calls = mock_notifier.notify.call_args_list
        assert len(notify_calls) > 0

        # First notification should mention the component
        first_call = notify_calls[0]
        assert "strengths" in str(first_call).lower() or "Strengths" in str(first_call)

    @pytest.mark.asyncio
    async def test_extract_swot_with_large_sources(
        self,
        generation_config,
        mock_language_model_service,
        mock_notifier,
        batch_parser,
    ):
        """Test extraction with many chunks that require batching."""
        # Create a source with many chunks
        large_chunks = [
            SourceChunk(id=f"chunk_{i}", text=f"Content {i} " * 100) for i in range(50)
        ]
        large_source = Source(
            type=SourceType.KNOWLEDGE_BASE,
            url="https://example.com/large",
            title="Large Source",
            chunks=large_chunks,
        )

        large_context = ReportGenerationContext(
            component=SWOTComponent.STRENGTHS,
            sources=[large_source],
            extraction_system_prompt="Extract strengths",
            extraction_output_model=StrengthsExtraction,
            company_name="Test Company",
        )

        result = await extract_swot_from_sources(
            context=large_context,
            configuration=generation_config,
            language_model_service=mock_language_model_service,
            notifier=mock_notifier,
            batch_parser=batch_parser,
        )

        # Should handle large source successfully
        assert isinstance(result, StrengthsExtraction)

        # Should make multiple LLM calls due to batching
        assert mock_language_model_service.complete_async.call_count >= 1

    @pytest.mark.asyncio
    async def test_extract_swot_handles_failed_batches(
        self,
        generation_context,
        generation_config,
        mock_notifier,
        batch_parser,
    ):
        """Test that extraction continues when some batches fail."""
        service = Mock()
        # First call succeeds, second fails, third succeeds
        service.complete_async = AsyncMock(
            side_effect=[
                Mock(choices=[Mock(message=Mock(parsed={"strengths": []}))]),
                Exception("Batch failed"),
                Mock(choices=[Mock(message=Mock(parsed={"strengths": []}))]),
            ]
        )

        result = await extract_swot_from_sources(
            context=generation_context,
            configuration=generation_config,
            language_model_service=service,
            notifier=mock_notifier,
            batch_parser=batch_parser,
        )

        # Should still return a result
        assert isinstance(result, StrengthsExtraction)


class TestSummarizeSwotExtraction:
    """Test cases for summarize_swot_extraction function."""

    @pytest.fixture
    def mock_language_model_service(self):
        """Create a mock language model service."""
        service = Mock()
        mock_response = Mock()
        mock_response.choices = [Mock()]
        mock_response.choices[0].message.content = "Summarized strengths analysis"
        service.complete_async = AsyncMock(return_value=mock_response)
        return service

    @pytest.fixture
    def mock_notifier(self):
        """Create a mock notifier."""
        notifier = Mock()
        notifier.notify = Mock()
        return notifier

    @pytest.fixture
    def summarization_context(self):
        """Create a summarization context."""
        extraction_results = StrengthsExtraction(strengths=[])
        return ReportSummarizationContext(
            component=SWOTComponent.STRENGTHS,
            summarization_system_prompt="Summarize the extracted strengths",
            extraction_results=extraction_results,
            company_name="Test Company",
        )

    @pytest.fixture
    def generation_config(self):
        """Create a generation configuration."""
        return ReportGenerationConfig(
            language_model=LANGUAGE_MODEL,
        )

    @pytest.mark.asyncio
    async def test_summarize_swot_extraction_success(
        self,
        summarization_context,
        generation_config,
        mock_language_model_service,
        mock_notifier,
    ):
        """Test successful summarization."""
        result = await summarize_swot_extraction(
            context=summarization_context,
            configuration=generation_config,
            language_model_service=mock_language_model_service,
            notifier=mock_notifier,
        )

        # Verify result is a string
        assert isinstance(result, str)
        assert result == "Summarized strengths analysis"

        # Verify LLM was called
        mock_language_model_service.complete_async.assert_called_once()

        # Verify notifier was called
        assert mock_notifier.notify.call_count == 2  # Start and complete

    @pytest.mark.asyncio
    async def test_summarize_swot_extraction_with_data(
        self,
        generation_config,
        mock_language_model_service,
        mock_notifier,
    ):
        """Test summarization with actual extraction data."""
        from unique_swot.services.generation.models.strengths import StrengthItem

        extraction_results = StrengthsExtraction(
            strengths=[
                StrengthItem(
                    title="Strong brand",
                    justification="Market leader with strong brand recognition",
                    reference_chunk_ids=["chunk_1"],
                ),
                StrengthItem(
                    title="Quality products",
                    justification="High customer satisfaction scores",
                    reference_chunk_ids=["chunk_2"],
                ),
            ]
        )
        context = ReportSummarizationContext(
            component=SWOTComponent.STRENGTHS,
            summarization_system_prompt="Summarize",
            extraction_results=extraction_results,
            company_name="Test Company",
        )

        _ = await summarize_swot_extraction(
            context=context,
            configuration=generation_config,
            language_model_service=mock_language_model_service,
            notifier=mock_notifier,
        )

        # Verify LLM was called with serialized data
        call_args = mock_language_model_service.complete_async.call_args
        messages = call_args[1]["messages"]

        # User message should contain the extraction results
        assert len(messages.root) == 2
        user_message = messages[1]
        assert (
            "Strong brand" in user_message.content
            or "strengths" in user_message.content
        )

    @pytest.mark.asyncio
    async def test_summarize_notifications(
        self,
        summarization_context,
        generation_config,
        mock_language_model_service,
        mock_notifier,
    ):
        """Test notification messages during summarization."""
        await summarize_swot_extraction(
            context=summarization_context,
            configuration=generation_config,
            language_model_service=mock_language_model_service,
            notifier=mock_notifier,
        )

        # Verify notify was called twice (start and complete)
        assert mock_notifier.notify.call_count == 2

        # Check notification content
        notify_calls = mock_notifier.notify.call_args_list
        first_call_kwargs = notify_calls[0][1]
        second_call_kwargs = notify_calls[1][1]

        # First notification should indicate running
        assert "RUNNING" in str(first_call_kwargs.get("status"))

        # Second notification should indicate completed
        assert "COMPLETED" in str(second_call_kwargs.get("status"))

    @pytest.mark.asyncio
    async def test_summarize_error_handling(
        self,
        summarization_context,
        generation_config,
        mock_notifier,
    ):
        """Test error handling during summarization."""
        service = Mock()
        service.complete_async = AsyncMock(
            side_effect=Exception("Summarization failed")
        )

        result = await summarize_swot_extraction(
            context=summarization_context,
            configuration=generation_config,
            language_model_service=service,
            notifier=mock_notifier,
        )

        # Should return error message
        assert isinstance(result, str)
        assert "Unavailable summary" in result
        assert "error" in result.lower()


class TestModifyReport:
    """Test cases for modify_report function."""

    @pytest.fixture
    def mock_language_model_service(self):
        """Create a mock language model service."""
        return Mock()

    @pytest.fixture
    def mock_notifier(self):
        """Create a mock notifier."""
        return Mock()

    @pytest.fixture
    def generation_config(self):
        """Create a generation configuration."""
        return ReportGenerationConfig(language_model=LANGUAGE_MODEL)

    @pytest.mark.asyncio
    async def test_modify_report_not_implemented(
        self,
        generation_config,
        mock_language_model_service,
        mock_notifier,
    ):
        """Test that modify_report raises NotImplementedError."""
        from unique_swot.services.generation.contexts import ReportModificationContext

        context = ReportModificationContext(
            step_name=SWOTComponent.STRENGTHS,
            sources=[],
            system_prompt="Modify strengths",
            modify_instruction="Add new data",
            structured_report=StrengthsExtraction(strengths=[]),
        )

        with pytest.raises(NotImplementedError, match="Not implemented"):
            await modify_report(
                context=context,
                configuration=generation_config,
                language_model_service=mock_language_model_service,
                notifier=mock_notifier,
            )


class TestGenerationPipeline:
    """Integration tests for the generation pipeline."""

    @pytest.mark.asyncio
    async def test_full_extraction_and_summarization_pipeline(
        self, sample_sources, mock_notifier
    ):
        """Test complete pipeline from extraction to summarization."""
        # Mock LLM service
        llm_service = Mock()

        # Mock extraction response
        extraction_response = Mock()
        extraction_response.choices = [Mock()]
        extraction_response.choices[0].message.parsed = {
            "strengths": [
                {
                    "item": "Strong market position",
                    "reasoning": "Leader in industry",
                    "citation_ids": ["chunk_1"],
                }
            ]
        }

        # Mock summarization response
        summary_response = Mock()
        summary_response.choices = [Mock()]
        summary_response.choices[
            0
        ].message.content = "The company has strong market position as a leader."

        llm_service.complete_async = AsyncMock(
            side_effect=[extraction_response, summary_response]
        )

        # Create contexts
        generation_context = ReportGenerationContext(
            component=SWOTComponent.STRENGTHS,
            sources=sample_sources,
            extraction_system_prompt="Extract strengths",
            extraction_output_model=StrengthsExtraction,
            company_name="Test Company",
        )

        config = ReportGenerationConfig(
            extraction_batch_size=10,
            max_tokens_per_extraction_batch=5000,
            language_model=LANGUAGE_MODEL,
        )

        # Run extraction
        extraction_result = await extract_swot_from_sources(
            context=generation_context,
            configuration=config,
            language_model_service=llm_service,
            notifier=mock_notifier,
            batch_parser=lambda chunks: "\n".join([c.text for c in chunks]),
        )

        # Verify extraction
        assert isinstance(extraction_result, StrengthsExtraction)

        # Run summarization
        summarization_context = ReportSummarizationContext(
            component=SWOTComponent.STRENGTHS,
            summarization_system_prompt="Summarize",
            extraction_results=extraction_result,
            company_name="Test Company",
        )

        summary = await summarize_swot_extraction(
            context=summarization_context,
            configuration=config,
            language_model_service=llm_service,
            notifier=mock_notifier,
        )

        # Verify summarization
        assert isinstance(summary, str)
        assert len(summary) > 0
