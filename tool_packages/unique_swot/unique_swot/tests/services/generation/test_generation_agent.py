"""Tests for the GenerationAgent."""

from unittest.mock import AsyncMock, Mock, patch

import pytest
from unique_toolkit.content import Content, ContentChunk

from unique_swot.services.generation.agentic.agent import GenerationAgent
from unique_swot.services.generation.context import SWOTComponent
from unique_swot.services.generation.models.base import (
    SWOTReportComponents,
    SWOTReportComponentSection,
    SWOTReportSectionEntry,
)
from unique_swot.services.schemas import SWOTOperation, SWOTPlan, SWOTStepPlan


def _make_content():
    """Helper to create test Content."""
    return Content(
        id="content_1",
        title="Test Document",
        key="test.pdf",
        chunks=[
            ContentChunk(
                id="content_1",
                chunk_id="chunk_1",
                title="Test Document",
                key="test.pdf",
                text="Test content for analysis.",
                start_page=1,
                end_page=1,
                order=0,
            ),
            ContentChunk(
                id="content_1",
                chunk_id="chunk_2",
                title="Test Document",
                key="test.pdf",
                text="More test content.",
                start_page=2,
                end_page=2,
                order=1,
            ),
        ],
    )


def _make_plan(strengths_op=SWOTOperation.GENERATE):
    """Helper to create test SWOTPlan."""
    return SWOTPlan(
        objective="Test analysis",
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


@pytest.mark.asyncio
async def test_generation_agent_generate_workflow(
    mock_llm,
    mock_language_model_service,
    mock_swot_report_registry,
    mock_agentic_executor,
    mock_step_notifier,
):
    """Test the complete generate workflow."""
    source_registry = Mock()
    source_registry.register.return_value = "chunk_generated_id"

    prompts_config = Mock()

    agent = GenerationAgent(
        company_name="ACME Corp",
        llm=mock_llm,
        llm_service=mock_language_model_service,
        registry=mock_swot_report_registry,
        executor=mock_agentic_executor,
        prompts_config=prompts_config,
    )

    content = _make_content()
    plan = _make_plan()

    # Mock the handle_generate_operation function
    with patch(
        "unique_swot.services.generation.agentic.agent.handle_generate_operation",
        new_callable=AsyncMock,
    ) as mock_handle:
        await agent.generate(
            content=content,
            source_registry=source_registry,
            plan=plan,
            step_notifier=mock_step_notifier,
        )

        # Verify handle_generate_operation was called
        mock_handle.assert_awaited_once()
        call_kwargs = mock_handle.call_args.kwargs
        assert call_kwargs["component"] == SWOTComponent.STRENGTHS
        assert call_kwargs["company_name"] == "ACME Corp"


@pytest.mark.asyncio
async def test_generation_agent_prepares_source_batches(
    mock_llm,
    mock_language_model_service,
    mock_swot_report_registry,
    mock_agentic_executor,
    mock_step_notifier,
):
    """Test that source batches are prepared correctly."""
    source_registry = Mock()
    chunk_ids = ["chunk_id_1", "chunk_id_2"]
    source_registry.register.side_effect = chunk_ids

    prompts_config = Mock()

    agent = GenerationAgent(
        company_name="ACME Corp",
        llm=mock_llm,
        llm_service=mock_language_model_service,
        registry=mock_swot_report_registry,
        executor=mock_agentic_executor,
        prompts_config=prompts_config,
    )

    content = _make_content()
    plan = _make_plan()

    with patch(
        "unique_swot.services.generation.agentic.agent.handle_generate_operation",
        new_callable=AsyncMock,
    ) as mock_handle:
        await agent.generate(
            content=content,
            source_registry=source_registry,
            plan=plan,
            step_notifier=mock_step_notifier,
        )

        # Verify source batches were prepared
        call_kwargs = mock_handle.call_args.kwargs
        source_batches = call_kwargs["source_batches"]

        assert len(source_batches) == 2
        assert source_batches[0]["id"] == "chunk_id_1"
        assert source_batches[0]["text"] == "Test content for analysis."
        assert source_batches[1]["id"] == "chunk_id_2"
        assert source_batches[1]["text"] == "More test content."


@pytest.mark.asyncio
async def test_generation_agent_skips_not_requested_operations(
    mock_llm,
    mock_language_model_service,
    mock_swot_report_registry,
    mock_agentic_executor,
    mock_step_notifier,
):
    """Test that NOT_REQUESTED operations are skipped."""
    source_registry = Mock()
    source_registry.register.return_value = "chunk_id"

    prompts_config = Mock()

    agent = GenerationAgent(
        company_name="ACME Corp",
        llm=mock_llm,
        llm_service=mock_language_model_service,
        registry=mock_swot_report_registry,
        executor=mock_agentic_executor,
        prompts_config=prompts_config,
    )

    content = _make_content()
    # Plan with all components NOT_REQUESTED
    plan = SWOTPlan(
        objective="Test",
        strengths=SWOTStepPlan(
            operation=SWOTOperation.NOT_REQUESTED, modify_instruction=None
        ),
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

    with patch(
        "unique_swot.services.generation.agentic.agent.handle_generate_operation",
        new_callable=AsyncMock,
    ) as mock_handle:
        await agent.generate(
            content=content,
            source_registry=source_registry,
            plan=plan,
            step_notifier=mock_step_notifier,
        )

        # Should not be called for any component
        mock_handle.assert_not_awaited()


@pytest.mark.asyncio
async def test_generation_agent_handles_modify_operation(
    mock_llm,
    mock_language_model_service,
    mock_swot_report_registry,
    mock_agentic_executor,
    mock_step_notifier,
):
    """Test that MODIFY operations are handled (currently uses GENERATE)."""
    source_registry = Mock()
    source_registry.register.return_value = "chunk_id"

    prompts_config = Mock()

    agent = GenerationAgent(
        company_name="ACME Corp",
        llm=mock_llm,
        llm_service=mock_language_model_service,
        registry=mock_swot_report_registry,
        executor=mock_agentic_executor,
        prompts_config=prompts_config,
    )

    content = _make_content()
    plan = SWOTPlan(
        objective="Update analysis",
        strengths=SWOTStepPlan(
            operation=SWOTOperation.MODIFY, modify_instruction="Update with new data"
        ),
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

    with patch(
        "unique_swot.services.generation.agentic.agent.handle_generate_operation",
        new_callable=AsyncMock,
    ) as mock_handle:
        await agent.generate(
            content=content,
            source_registry=source_registry,
            plan=plan,
            step_notifier=mock_step_notifier,
        )

        # Should be called once for MODIFY (currently treated as GENERATE)
        mock_handle.assert_awaited_once()


@pytest.mark.asyncio
async def test_generation_agent_sends_notifications(
    mock_llm,
    mock_language_model_service,
    mock_swot_report_registry,
    mock_agentic_executor,
    mock_step_notifier,
):
    """Test that notifications are sent during generation."""
    source_registry = Mock()
    source_registry.register.return_value = "chunk_id"

    prompts_config = Mock()

    agent = GenerationAgent(
        company_name="ACME Corp",
        llm=mock_llm,
        llm_service=mock_language_model_service,
        registry=mock_swot_report_registry,
        executor=mock_agentic_executor,
        prompts_config=prompts_config,
    )

    content = _make_content()
    plan = _make_plan()

    with patch(
        "unique_swot.services.generation.agentic.agent.handle_generate_operation",
        new_callable=AsyncMock,
    ):
        await agent.generate(
            content=content,
            source_registry=source_registry,
            plan=plan,
            step_notifier=mock_step_notifier,
        )

        # Verify notifications were sent
        assert mock_step_notifier.notify.await_count >= 2  # Start and end notifications


def test_generation_agent_get_reports(
    mock_llm, mock_language_model_service, mock_agentic_executor
):
    """Test get_reports returns correct structure."""
    registry = Mock()
    registry.retrieve_component_sections.return_value = [
        SWOTReportComponentSection(
            h2="Test", entries=[SWOTReportSectionEntry(preview="P", content="C")]
        )
    ]

    prompts_config = Mock()

    agent = GenerationAgent(
        company_name="ACME Corp",
        llm=mock_llm,
        llm_service=mock_language_model_service,
        registry=registry,
        executor=mock_agentic_executor,
        prompts_config=prompts_config,
    )

    reports = agent.get_reports()

    assert isinstance(reports, SWOTReportComponents)
    assert len(reports.strengths) == 1
    assert len(reports.weaknesses) == 1
    assert len(reports.opportunities) == 1
    assert len(reports.threats) == 1


def test_generation_agent_notification_title_property(
    mock_llm,
    mock_language_model_service,
    mock_swot_report_registry,
    mock_agentic_executor,
):
    """Test notification_title property getter and setter."""
    prompts_config = Mock()

    agent = GenerationAgent(
        company_name="ACME Corp",
        llm=mock_llm,
        llm_service=mock_language_model_service,
        registry=mock_swot_report_registry,
        executor=mock_agentic_executor,
        prompts_config=prompts_config,
    )

    # Default title
    assert agent.notification_title == "Generating SWOT report"

    # Set new title
    agent.notification_title = "Custom Title"
    assert agent.notification_title == "Custom Title"
