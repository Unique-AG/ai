"""Tests for the SWOT Orchestrator service."""

from unittest.mock import AsyncMock, Mock

import pytest
from unique_toolkit.content import Content, ContentChunk

from unique_swot.services.generation.models.base import (
    SWOTReportComponents,
    SWOTReportComponentSection,
    SWOTReportSectionEntry,
)
from unique_swot.services.orchestrator.service import SWOTOrchestrator
from unique_swot.services.schemas import SWOTOperation, SWOTPlan, SWOTStepPlan
from unique_swot.services.source_management.selection.schema import (
    SourceSelectionResult,
)


def _make_content(content_id="content_1", title="Test Doc"):
    """Helper to create test Content."""
    return Content(
        id=content_id,
        title=title,
        key=f"{title}.pdf",
        chunks=[
            ContentChunk(
                id=content_id,
                chunk_id="chunk_1",
                title=title,
                key=f"{title}.pdf",
                text="Test content",
                start_page=1,
                end_page=1,
                order=0,
            )
        ],
    )


def _make_plan(strengths_op=SWOTOperation.GENERATE):
    """Helper to create test SWOTPlan."""
    return SWOTPlan(
        objective="Test objective",
        strengths=SWOTStepPlan(operation=strengths_op, modify_instruction=None),
        weaknesses=SWOTStepPlan(
            operation=SWOTOperation.NOT_REQUESTED, modify_instruction=None
        ),
        opportunities=SWOTStepPlan(
            operation=SWOTOperation.NOT_REQUESTED, modify_instruction=None
        ),
        threats=SWOTStepPlan(
            operation=SWOTOperation.NOT_REQUESTED, modify_instruction=None
        ),
    )


def _make_report_components():
    """Helper to create test SWOTReportComponents."""
    return SWOTReportComponents(
        strengths=[
            SWOTReportComponentSection(
                h2="Test Strength",
                entries=[
                    SWOTReportSectionEntry(
                        preview="Preview", content="Content [chunk_1]"
                    )
                ],
            )
        ],
        weaknesses=[],
        opportunities=[],
        threats=[],
    )


@pytest.mark.asyncio
async def test_orchestrator_full_workflow():
    """Test the complete orchestration workflow: collect → iterate → select → generate."""
    # Setup mocks
    step_notifier = Mock()
    step_notifier.notify = AsyncMock()

    contents = [_make_content("content_1", "Doc1"), _make_content("content_2", "Doc2")]

    source_collector = Mock()
    source_collector.collect = AsyncMock(return_value=contents)

    source_iterator = Mock()

    async def _iterate_impl(contents, step_notifier):
        for content in contents:
            yield content

    async def _iterate(contents, step_notifier):
        return _iterate_impl(contents, step_notifier)

    source_iterator.iterate = _iterate

    source_selector = Mock()
    source_selector.select = AsyncMock(
        return_value=SourceSelectionResult(
            should_select=True,
            reason="Relevant",
            notification_message="Selected",
        )
    )

    reporting_agent = Mock()
    reporting_agent.generate = AsyncMock()
    reporting_agent.get_reports.return_value = _make_report_components()

    source_registry = Mock()
    memory_service = Mock()

    progress_notifier = Mock()
    progress_notifier.update = AsyncMock()

    chat_service = Mock()

    # Create orchestrator
    orchestrator = SWOTOrchestrator(
        step_notifier=step_notifier,
        source_collector=source_collector,
        source_selector=source_selector,
        source_iterator=source_iterator,
        reporting_agent=reporting_agent,
        source_registry=source_registry,
        progress_notifier=progress_notifier,
        memory_service=memory_service,
        chat_service=chat_service,
    )

    # Run orchestration
    plan = _make_plan()
    result = await orchestrator.run(company_name="ACME Corp", plan=plan)

    # Verify workflow
    source_collector.collect.assert_awaited_once()
    assert source_selector.select.await_count == 2  # Called for each content
    assert reporting_agent.generate.await_count == 2  # Called for each selected content
    reporting_agent.get_reports.assert_called_once()

    # Verify result
    assert isinstance(result, SWOTReportComponents)
    assert len(result.strengths) == 1


@pytest.mark.asyncio
async def test_orchestrator_skips_unselected_sources():
    """Test that sources marked as should_select=False are skipped."""
    step_notifier = Mock()
    step_notifier.notify = AsyncMock()

    contents = [_make_content("content_1", "Doc1"), _make_content("content_2", "Doc2")]

    source_collector = Mock()
    source_collector.collect = AsyncMock(return_value=contents)

    source_iterator = Mock()

    async def _iterate_impl(contents, step_notifier):
        for content in contents:
            yield content

    async def _iterate(contents, step_notifier):
        return _iterate_impl(contents, step_notifier)

    source_iterator.iterate = _iterate

    # First source selected, second skipped
    selection_results = [
        SourceSelectionResult(
            should_select=True,
            reason="Relevant",
            notification_message="Selected",
        ),
        SourceSelectionResult(
            should_select=False,
            reason="Not relevant",
            notification_message="Skipped",
        ),
    ]

    source_selector = Mock()
    source_selector.select = AsyncMock(side_effect=selection_results)

    reporting_agent = Mock()
    reporting_agent.generate = AsyncMock()
    reporting_agent.get_reports.return_value = _make_report_components()

    source_registry = Mock()
    memory_service = Mock()

    progress_notifier = Mock()
    progress_notifier.update = AsyncMock()

    chat_service = Mock()

    orchestrator = SWOTOrchestrator(
        step_notifier=step_notifier,
        source_collector=source_collector,
        source_selector=source_selector,
        source_iterator=source_iterator,
        reporting_agent=reporting_agent,
        source_registry=source_registry,
        progress_notifier=progress_notifier,
        memory_service=memory_service,
        chat_service=chat_service,
    )

    plan = _make_plan()
    await orchestrator.run(company_name="ACME Corp", plan=plan)

    # Only one source should be processed
    assert reporting_agent.generate.await_count == 1


@pytest.mark.asyncio
async def test_orchestrator_handles_empty_sources():
    """Test that orchestrator handles empty source list gracefully."""
    step_notifier = Mock()
    step_notifier.notify = AsyncMock()

    source_collector = Mock()
    source_collector.collect = AsyncMock(return_value=[])

    source_iterator = Mock()

    async def _iterate_impl(contents, step_notifier):
        for content in contents:
            yield content

    async def _iterate(contents, step_notifier):
        return _iterate_impl(contents, step_notifier)

    source_iterator.iterate = _iterate

    source_selector = Mock()
    reporting_agent = Mock()
    reporting_agent.get_reports.return_value = SWOTReportComponents(
        strengths=[], weaknesses=[], opportunities=[], threats=[]
    )

    source_registry = Mock()
    memory_service = Mock()

    progress_notifier = Mock()
    progress_notifier.update = AsyncMock()

    chat_service = Mock()

    orchestrator = SWOTOrchestrator(
        step_notifier=step_notifier,
        source_collector=source_collector,
        source_selector=source_selector,
        source_iterator=source_iterator,
        reporting_agent=reporting_agent,
        source_registry=source_registry,
        progress_notifier=progress_notifier,
        memory_service=memory_service,
        chat_service=chat_service,
    )

    plan = _make_plan()
    result = await orchestrator.run(company_name="ACME Corp", plan=plan)

    # Should complete without errors
    source_collector.collect.assert_awaited_once()
    assert result.is_empty()


@pytest.mark.asyncio
async def test_orchestrator_passes_correct_parameters():
    """Test that orchestrator passes correct parameters to each component."""
    step_notifier = Mock()
    step_notifier.notify = AsyncMock()

    content = _make_content()
    source_collector = Mock()
    source_collector.collect = AsyncMock(return_value=[content])

    source_iterator = Mock()

    async def _iterate_impl(contents, step_notifier):
        for content in contents:
            yield content

    async def _iterate(contents, step_notifier):
        return _iterate_impl(contents, step_notifier)

    source_iterator.iterate = _iterate

    source_selector = Mock()
    source_selector.select = AsyncMock(
        return_value=SourceSelectionResult(
            should_select=True,
            reason="Relevant",
            notification_message="Selected",
        )
    )

    reporting_agent = Mock()
    reporting_agent.generate = AsyncMock()
    reporting_agent.get_reports.return_value = _make_report_components()

    source_registry = Mock()
    memory_service = Mock()

    progress_notifier = Mock()
    progress_notifier.update = AsyncMock()

    chat_service = Mock()

    orchestrator = SWOTOrchestrator(
        step_notifier=step_notifier,
        source_collector=source_collector,
        source_selector=source_selector,
        source_iterator=source_iterator,
        reporting_agent=reporting_agent,
        source_registry=source_registry,
        progress_notifier=progress_notifier,
        memory_service=memory_service,
        chat_service=chat_service,
    )

    company_name = "ACME Corp"
    plan = _make_plan()
    await orchestrator.run(company_name=company_name, plan=plan)

    # Verify parameters passed to selector
    source_selector.select.assert_awaited_once()
    call_kwargs = source_selector.select.call_args.kwargs
    assert call_kwargs["company_name"] == company_name
    assert call_kwargs["content"] == content
    assert call_kwargs["step_notifier"] == step_notifier

    # Verify parameters passed to reporting agent
    reporting_agent.generate.assert_awaited_once()
    gen_kwargs = reporting_agent.generate.call_args.kwargs
    assert gen_kwargs["plan"] == plan
    assert gen_kwargs["content"] == content
    assert gen_kwargs["step_notifier"] == step_notifier
    assert gen_kwargs["source_registry"] == source_registry


@pytest.mark.asyncio
async def test_orchestrator_with_multiple_components():
    """Test orchestrator with a plan requesting multiple SWOT components."""
    step_notifier = Mock()
    step_notifier.notify = AsyncMock()

    content = _make_content()
    source_collector = Mock()
    source_collector.collect = AsyncMock(return_value=[content])

    source_iterator = Mock()

    async def _iterate_impl(contents, step_notifier):
        for content in contents:
            yield content

    async def _iterate(contents, step_notifier):
        return _iterate_impl(contents, step_notifier)

    source_iterator.iterate = _iterate

    source_selector = Mock()
    source_selector.select = AsyncMock(
        return_value=SourceSelectionResult(
            should_select=True,
            reason="Relevant",
            notification_message="Selected",
        )
    )

    reporting_agent = Mock()
    reporting_agent.generate = AsyncMock()
    reporting_agent.get_reports.return_value = SWOTReportComponents(
        strengths=[
            SWOTReportComponentSection(
                h2="Strength",
                entries=[SWOTReportSectionEntry(preview="P", content="C")],
            )
        ],
        weaknesses=[
            SWOTReportComponentSection(
                h2="Weakness",
                entries=[SWOTReportSectionEntry(preview="P", content="C")],
            )
        ],
        opportunities=[],
        threats=[],
    )

    source_registry = Mock()
    memory_service = Mock()

    progress_notifier = Mock()
    progress_notifier.update = AsyncMock()

    chat_service = Mock()

    orchestrator = SWOTOrchestrator(
        step_notifier=step_notifier,
        source_collector=source_collector,
        source_selector=source_selector,
        source_iterator=source_iterator,
        reporting_agent=reporting_agent,
        source_registry=source_registry,
        progress_notifier=progress_notifier,
        memory_service=memory_service,
        chat_service=chat_service,
    )

    # Plan with multiple components
    plan = SWOTPlan(
        objective="Full analysis",
        strengths=SWOTStepPlan(
            operation=SWOTOperation.GENERATE, modify_instruction=None
        ),
        weaknesses=SWOTStepPlan(
            operation=SWOTOperation.GENERATE, modify_instruction=None
        ),
        opportunities=SWOTStepPlan(
            operation=SWOTOperation.NOT_REQUESTED, modify_instruction=None
        ),
        threats=SWOTStepPlan(
            operation=SWOTOperation.NOT_REQUESTED, modify_instruction=None
        ),
    )

    result = await orchestrator.run(company_name="ACME Corp", plan=plan)

    assert len(result.strengths) == 1
    assert len(result.weaknesses) == 1
    assert len(result.opportunities) == 0
    assert len(result.threats) == 0
