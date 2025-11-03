"""Tests for SWOT execution manager."""

from unittest.mock import AsyncMock, Mock, patch

import pytest

from unique_swot.services.executor import SWOTExecutionManager
from unique_swot.services.generation import ReportGenerationConfig, SWOTComponent
from unique_swot.services.schemas import (
    SWOTOperation,
    SWOTPlan,
    SWOTResult,
    SWOTStepPlan,
)


class TestSWOTExecutionManager:
    """Test cases for SWOTExecutionManager class."""

    @pytest.fixture
    def execution_manager(
        self,
        mock_language_model_service,
        mock_notifier,
        mock_knowledge_base_service,
    ):
        """Create a SWOTExecutionManager instance for testing."""
        from unique_swot.services.citations import CitationManager
        from unique_swot.services.collection.registry import ContentChunkRegistry
        from unique_swot.services.memory.base import SwotMemoryService

        memory_service = Mock(spec=SwotMemoryService)
        memory_service.get.return_value = None
        memory_service.set.return_value = None

        content_chunk_registry = Mock(spec=ContentChunkRegistry)
        citation_manager = Mock(spec=CitationManager)
        citation_manager.add_citations_to_report.return_value = "Processed result"

        config = ReportGenerationConfig()

        return SWOTExecutionManager(
            configuration=config,
            language_model_service=mock_language_model_service,
            memory_service=memory_service,
            knowledge_base_service=mock_knowledge_base_service,
            content_chunk_registry=content_chunk_registry,
            cache_scope_id="test_scope",
            citation_manager=citation_manager,
            notifier=mock_notifier,
        )

    @pytest.mark.asyncio
    async def test_executor_initialization(self, execution_manager):
        """Test that SWOTExecutionManager initializes correctly."""
        assert execution_manager is not None
        assert hasattr(execution_manager, "_configuration")
        assert hasattr(execution_manager, "_language_model_service")
        assert hasattr(execution_manager, "_notifier")
        assert hasattr(execution_manager, "_memory_service")

    @pytest.mark.asyncio
    async def test_run_with_generate_operations(
        self, execution_manager, sample_swot_plan, sample_sources
    ):
        """Test running executor with all generate operations."""
        # Mock the generation function
        with patch.object(
            execution_manager, "run_generation_function", new_callable=AsyncMock
        ) as mock_generate:
            mock_generate.return_value = "Generated analysis"

            result = await execution_manager.run(
                plan=sample_swot_plan,
                sources=sample_sources,
            )

            assert isinstance(result, SWOTResult)
            assert mock_generate.call_count == 4  # Called for each component

    @pytest.mark.asyncio
    async def test_run_with_modify_operation(
        self, execution_manager, sample_modify_swot_plan, sample_sources
    ):
        """Test running executor with modify operations."""
        with (
            patch.object(
                execution_manager, "run_modify_function", new_callable=AsyncMock
            ) as mock_modify,
            patch.object(
                execution_manager, "run_generation_function", new_callable=AsyncMock
            ) as mock_generate,
        ):
            mock_modify.return_value = "Modified analysis"
            mock_generate.return_value = "Generated analysis"

            result = await execution_manager.run(
                plan=sample_modify_swot_plan,
                sources=sample_sources,
            )

            assert isinstance(result, SWOTResult)
            # Should call modify for strengths and threats
            assert mock_modify.call_count == 2
            # Should call generate for opportunities
            assert mock_generate.call_count == 1

    @pytest.mark.asyncio
    async def test_run_with_not_requested_operations(
        self, execution_manager, sample_sources
    ):
        """Test running executor with not_requested operations."""
        plan = SWOTPlan(
            objective="Test",
            strengths=SWOTStepPlan(
                operation=SWOTOperation.NOT_REQUESTED,
                modify_instruction=None,
            ),
            weaknesses=SWOTStepPlan(
                operation=SWOTOperation.NOT_REQUESTED,
                modify_instruction=None,
            ),
            opportunities=SWOTStepPlan(
                operation=SWOTOperation.GENERATE,
                modify_instruction=None,
            ),
            threats=SWOTStepPlan(
                operation=SWOTOperation.NOT_REQUESTED,
                modify_instruction=None,
            ),
        )

        with patch.object(
            execution_manager, "run_generation_function", new_callable=AsyncMock
        ) as mock_generate:
            mock_generate.return_value = "Generated analysis"

            await execution_manager.run(plan=plan, sources=sample_sources)

            # Only opportunities should be generated
            assert mock_generate.call_count == 1

    @pytest.mark.asyncio
    async def test_run_generation_function(self, execution_manager, sample_sources):
        """Test the run_generation_function method."""
        with (
            patch(
                "unique_swot.services.executor.extract_swot_from_sources",
                new_callable=AsyncMock,
            ) as mock_extract,
            patch(
                "unique_swot.services.executor.summarize_swot_extraction",
                new_callable=AsyncMock,
            ) as mock_summarize,
        ):
            # Create a proper extraction result instance
            from unique_swot.services.generation.models.strengths import (
                StrengthsExtraction,
            )

            mock_extraction_result = StrengthsExtraction(strengths=[])
            mock_extract.return_value = mock_extraction_result
            mock_summarize.return_value = "Summarized result"

            result = await execution_manager.run_generation_function(
                component=SWOTComponent.STRENGTHS,
                sources=sample_sources,
            )

            assert result == "Summarized result"
            mock_extract.assert_called_once()
            mock_summarize.assert_called_once()
            execution_manager._memory_service.set.assert_called_once()

    @pytest.mark.asyncio
    async def test_run_modify_function_no_saved_analysis(
        self, execution_manager, sample_sources
    ):
        """Test run_modify_function when no saved analysis exists."""
        execution_manager._memory_service.get.return_value = None

        with patch.object(
            execution_manager, "run_generation_function", new_callable=AsyncMock
        ) as mock_generate:
            mock_generate.return_value = "Generated analysis"

            result = await execution_manager.run_modify_function(
                component=SWOTComponent.STRENGTHS,
                sources=sample_sources,
                modify_instruction="Update analysis",
            )

            assert result == "Generated analysis"
            mock_generate.assert_called_once()

    @pytest.mark.asyncio
    async def test_run_modify_function_with_saved_analysis(
        self, execution_manager, sample_sources
    ):
        """Test run_modify_function when saved analysis exists (currently falls back to generation)."""
        from unique_swot.services.generation.models.strengths import (
            StrengthsExtraction,
        )

        saved_analysis = StrengthsExtraction(strengths=[])
        execution_manager._memory_service.get.return_value = saved_analysis

        with patch.object(
            execution_manager, "run_generation_function", new_callable=AsyncMock
        ) as mock_generate:
            mock_generate.return_value = "Generated analysis"

            result = await execution_manager.run_modify_function(
                component=SWOTComponent.STRENGTHS,
                sources=sample_sources,
                modify_instruction="Update analysis",
            )

            # Currently falls back to generation
            assert result == "Generated analysis"
            mock_generate.assert_called_once()

    @pytest.mark.asyncio
    async def test_run_all_components(
        self, execution_manager, sample_swot_plan, sample_sources
    ):
        """Test that all SWOT components are processed."""
        with patch.object(
            execution_manager, "run_generation_function", new_callable=AsyncMock
        ) as mock_generate:
            mock_generate.side_effect = [
                "Strengths analysis",
                "Weaknesses analysis",
                "Opportunities analysis",
                "Threats analysis",
            ]

            result = await execution_manager.run(
                plan=sample_swot_plan,
                sources=sample_sources,
            )

            assert result.strengths.result == "Strengths analysis"
            assert result.weaknesses.result == "Weaknesses analysis"
            assert result.opportunities.result == "Opportunities analysis"
            assert result.threats.result == "Threats analysis"

    @pytest.mark.asyncio
    async def test_run_empty_sources(self, execution_manager, sample_swot_plan):
        """Test running with empty sources list."""
        with patch.object(
            execution_manager, "run_generation_function", new_callable=AsyncMock
        ) as mock_generate:
            mock_generate.return_value = "Analysis with no sources"

            result = await execution_manager.run(
                plan=sample_swot_plan,
                sources=[],
            )

            assert isinstance(result, SWOTResult)
            assert mock_generate.call_count == 4
