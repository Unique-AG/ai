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


def _make_source_iterator():
    """Helper to create a mock source iterator."""
    source_iterator = Mock()

    async def _iterate_impl(contents, step_notifier):
        for content in contents:
            yield content

    async def _iterate(contents, step_notifier):
        return _iterate_impl(contents, step_notifier)

    source_iterator.iterate = _iterate
    return source_iterator


@pytest.mark.asyncio
@pytest.mark.ai
async def test_orchestrator__full_workflow__collect_iterate_generate():
    """
    Purpose: Verify the complete orchestration workflow delegates to the reporting agent.
    Why this matters: The orchestrator is the top-level coordinator; it must collect sources,
    iterate them, then hand off to the reporting agent for generation.
    Setup summary: Two contents collected, reporting agent returns a report with one strength.
    """
    step_notifier = Mock()
    step_notifier.notify = AsyncMock()

    contents = [_make_content("content_1", "Doc1"), _make_content("content_2", "Doc2")]

    source_collector = Mock()
    source_collector.collect = AsyncMock(return_value=contents)

    source_iterator = _make_source_iterator()
    source_selector = Mock()

    reporting_agent = Mock()
    reporting_agent.generate = AsyncMock(return_value=_make_report_components())

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
    result = await orchestrator.run(plan=plan)

    # Verify workflow
    source_collector.collect.assert_awaited_once()
    reporting_agent.generate.assert_awaited_once()

    # Verify result
    assert isinstance(result, SWOTReportComponents)
    assert len(result.strengths) == 1


@pytest.mark.asyncio
@pytest.mark.ai
async def test_orchestrator__raises_value_error__empty_sources():
    """
    Purpose: Verify orchestrator raises ValueError when no sources are collected.
    Why this matters: Prevents silent failures when no documents are available.
    Setup summary: Collector returns empty list, expect ValueError.
    """
    step_notifier = Mock()
    step_notifier.notify = AsyncMock()

    source_collector = Mock()
    source_collector.collect = AsyncMock(return_value=[])

    source_iterator = _make_source_iterator()
    source_selector = Mock()
    reporting_agent = Mock()

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

    with pytest.raises(ValueError, match="No sources to process"):
        await orchestrator.run(plan=plan)

    source_collector.collect.assert_awaited_once()


@pytest.mark.asyncio
@pytest.mark.ai
async def test_orchestrator__passes_correct_parameters__to_reporting_agent():
    """
    Purpose: Verify that the orchestrator forwards the correct arguments to reporting_agent.generate.
    Why this matters: Ensures the contract between orchestrator and reporting agent is maintained.
    Setup summary: Single content, verify generate is called with plan, total_steps, source_iterator,
    source_selector, source_registry, step_notifier, and progress_notifier.
    """
    step_notifier = Mock()
    step_notifier.notify = AsyncMock()

    content = _make_content()
    source_collector = Mock()
    source_collector.collect = AsyncMock(return_value=[content])

    source_iterator = _make_source_iterator()
    source_selector = Mock()

    reporting_agent = Mock()
    reporting_agent.generate = AsyncMock(return_value=_make_report_components())

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
    await orchestrator.run(plan=plan)

    reporting_agent.generate.assert_awaited_once()
    gen_kwargs = reporting_agent.generate.call_args.kwargs
    assert gen_kwargs["plan"] == plan
    assert gen_kwargs["total_steps"] == 1
    assert gen_kwargs["source_selector"] == source_selector
    assert gen_kwargs["source_registry"] == source_registry
    assert gen_kwargs["step_notifier"] == step_notifier
    assert gen_kwargs["progress_notifier"] == progress_notifier
    assert gen_kwargs["source_iterator"] is not None


@pytest.mark.asyncio
@pytest.mark.ai
async def test_orchestrator__returns_report__with_multiple_components():
    """
    Purpose: Verify orchestrator returns the full report from the reporting agent.
    Why this matters: The orchestrator must faithfully relay the agent's output.
    Setup summary: Plan with strengths and weaknesses; reporting agent returns both.
    """
    step_notifier = Mock()
    step_notifier.notify = AsyncMock()

    content = _make_content()
    source_collector = Mock()
    source_collector.collect = AsyncMock(return_value=[content])

    source_iterator = _make_source_iterator()
    source_selector = Mock()

    multi_report = SWOTReportComponents(
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

    reporting_agent = Mock()
    reporting_agent.generate = AsyncMock(return_value=multi_report)

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

    result = await orchestrator.run(plan=plan)

    assert len(result.strengths) == 1
    assert len(result.weaknesses) == 1
    assert len(result.opportunities) == 0
    assert len(result.threats) == 0


@pytest.mark.asyncio
@pytest.mark.ai
async def test_orchestrator__updates_progress__before_generation():
    """
    Purpose: Verify progress notifier receives initial progress updates.
    Why this matters: Users rely on progress updates during long-running analysis.
    Setup summary: Single content, verify progress_notifier.update is called with early progress values.
    """
    step_notifier = Mock()
    step_notifier.notify = AsyncMock()

    content = _make_content()
    source_collector = Mock()
    source_collector.collect = AsyncMock(return_value=[content])

    source_iterator = _make_source_iterator()
    source_selector = Mock()

    reporting_agent = Mock()
    reporting_agent.generate = AsyncMock(
        return_value=SWOTReportComponents(
            strengths=[], weaknesses=[], opportunities=[], threats=[]
        )
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
    await orchestrator.run(plan=plan)

    assert progress_notifier.update.await_count >= 2
