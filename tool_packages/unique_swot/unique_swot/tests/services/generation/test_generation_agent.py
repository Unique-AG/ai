"""Tests for the GenerationAgent."""

from unittest.mock import AsyncMock, Mock, patch

import pytest
from unique_toolkit.content import Content, ContentChunk

from unique_swot.services.generation.agentic.agent import GenerationAgent
from unique_swot.services.generation.config import GenerationMode
from unique_swot.services.generation.context import SWOTComponent
from unique_swot.services.generation.models.base import (
    SWOTReportComponents,
    SWOTReportComponentSection,
    SWOTReportSectionEntry,
)
from unique_swot.services.schemas import SWOTOperation, SWOTPlan, SWOTStepPlan
from unique_swot.services.source_management.selection.schema import (
    SourceSelectionResult,
)


def _make_content(content_id="content_1", title="Test Document"):
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
                text="Test content for analysis.",
                start_page=1,
                end_page=1,
                order=0,
            ),
            ContentChunk(
                id=content_id,
                chunk_id="chunk_2",
                title=title,
                key=f"{title}.pdf",
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


async def _async_content_iter(*contents: Content):
    """Helper to create an async iterator over Content objects."""
    for content in contents:
        yield content


def _make_source_selector(should_select: bool = True):
    """Helper to create a mock source selector."""
    selector = Mock()
    selector.select = AsyncMock(
        return_value=SourceSelectionResult(
            should_select=should_select,
            reason="test reason",
            notification_message="test notification",
        )
    )
    return selector


def _make_agent(
    mock_llm,
    mock_language_model_service,
    mock_swot_report_registry,
    mock_agentic_executor,
    generation_mode: GenerationMode = GenerationMode.INTERLEAVED,
):
    """Helper to create a GenerationAgent with standard mocks."""
    config = Mock()
    config.max_tokens_per_extraction_batch = 1000

    return GenerationAgent(
        company_name="ACME Corp",
        llm=mock_llm,
        llm_service=mock_language_model_service,
        registry=mock_swot_report_registry,
        executor=mock_agentic_executor,
        config=config,
        generation_mode=generation_mode,
    )


# =============================================================================
# Interleaved mode tests (default)
# =============================================================================


@pytest.mark.asyncio
@pytest.mark.ai
async def test_generation_agent__interleaved_generate__calls_handle_generate(
    mock_llm,
    mock_language_model_service,
    mock_swot_report_registry,
    mock_agentic_executor,
    mock_step_notifier,
    mock_progress_notifier,
) -> None:
    """
    Purpose: Verify interleaved mode calls handle_generate_operation for each selected source.
    Why this matters: Core path for per-source extraction and generation.
    Setup summary: One content, mock handle_generate_operation, verify it is called with STRENGTHS.
    """
    source_registry = Mock()
    source_registry.register.return_value = "chunk_generated_id"
    source_selector = _make_source_selector(should_select=True)

    agent = _make_agent(
        mock_llm,
        mock_language_model_service,
        mock_swot_report_registry,
        mock_agentic_executor,
    )

    content = _make_content()
    plan = _make_plan()

    with patch(
        "unique_swot.services.generation.agentic.agent.handle_generate_operation",
        new_callable=AsyncMock,
    ) as mock_handle:
        result = await agent.generate(
            plan=plan,
            total_steps=1,
            source_iterator=_async_content_iter(content),
            source_selector=source_selector,
            source_registry=source_registry,
            step_notifier=mock_step_notifier,
            progress_notifier=mock_progress_notifier,
        )

        mock_handle.assert_awaited_once()
        call_kwargs = mock_handle.call_args.kwargs
        assert call_kwargs["component"] == SWOTComponent.STRENGTHS
        assert call_kwargs["company_name"] == "ACME Corp"

    assert isinstance(result, SWOTReportComponents)


@pytest.mark.asyncio
@pytest.mark.ai
async def test_generation_agent__interleaved__prepares_source_batches(
    mock_llm,
    mock_language_model_service,
    mock_swot_report_registry,
    mock_agentic_executor,
    mock_step_notifier,
    mock_progress_notifier,
) -> None:
    """
    Purpose: Verify source batches are prepared correctly with chunk ids and text.
    Why this matters: Correct batch preparation is essential for citation tracking.
    Setup summary: Two chunks with distinct ids, verify batch structure.
    """
    source_registry = Mock()
    chunk_ids = ["chunk_id_1", "chunk_id_2"]
    source_registry.register.side_effect = chunk_ids
    source_selector = _make_source_selector(should_select=True)

    agent = _make_agent(
        mock_llm,
        mock_language_model_service,
        mock_swot_report_registry,
        mock_agentic_executor,
    )

    content = _make_content()
    plan = _make_plan()

    with patch(
        "unique_swot.services.generation.agentic.agent.handle_generate_operation",
        new_callable=AsyncMock,
    ) as mock_handle:
        await agent.generate(
            plan=plan,
            total_steps=1,
            source_iterator=_async_content_iter(content),
            source_selector=source_selector,
            source_registry=source_registry,
            step_notifier=mock_step_notifier,
            progress_notifier=mock_progress_notifier,
        )

        call_kwargs = mock_handle.call_args.kwargs
        source_batches = call_kwargs["source_batches"]

        assert len(source_batches) == 2
        assert source_batches[0]["id"] == "chunk_id_1"
        assert source_batches[0]["text"] == "Test content for analysis."
        assert source_batches[1]["id"] == "chunk_id_2"
        assert source_batches[1]["text"] == "More test content."


@pytest.mark.asyncio
@pytest.mark.ai
async def test_generation_agent__interleaved__skips_not_requested_operations(
    mock_llm,
    mock_language_model_service,
    mock_swot_report_registry,
    mock_agentic_executor,
    mock_step_notifier,
    mock_progress_notifier,
) -> None:
    """
    Purpose: Verify that NOT_REQUESTED operations are skipped.
    Why this matters: Users can selectively request SWOT components.
    Setup summary: All components NOT_REQUESTED, verify handle_generate_operation is never called.
    """
    source_registry = Mock()
    source_registry.register.return_value = "chunk_id"
    source_selector = _make_source_selector(should_select=True)

    agent = _make_agent(
        mock_llm,
        mock_language_model_service,
        mock_swot_report_registry,
        mock_agentic_executor,
    )

    content = _make_content()
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
            plan=plan,
            total_steps=1,
            source_iterator=_async_content_iter(content),
            source_selector=source_selector,
            source_registry=source_registry,
            step_notifier=mock_step_notifier,
            progress_notifier=mock_progress_notifier,
        )

        mock_handle.assert_not_awaited()


@pytest.mark.asyncio
@pytest.mark.ai
async def test_generation_agent__interleaved__handles_modify_as_generate(
    mock_llm,
    mock_language_model_service,
    mock_swot_report_registry,
    mock_agentic_executor,
    mock_step_notifier,
    mock_progress_notifier,
) -> None:
    """
    Purpose: Verify that MODIFY operations fall through to handle_generate_operation.
    Why this matters: MODIFY is not yet implemented, so it uses the GENERATE path.
    Setup summary: Plan with MODIFY for strengths, verify generate handler is called.
    """
    source_registry = Mock()
    source_registry.register.return_value = "chunk_id"
    source_selector = _make_source_selector(should_select=True)

    agent = _make_agent(
        mock_llm,
        mock_language_model_service,
        mock_swot_report_registry,
        mock_agentic_executor,
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
            plan=plan,
            total_steps=1,
            source_iterator=_async_content_iter(content),
            source_selector=source_selector,
            source_registry=source_registry,
            step_notifier=mock_step_notifier,
            progress_notifier=mock_progress_notifier,
        )

        mock_handle.assert_awaited_once()


@pytest.mark.asyncio
@pytest.mark.ai
async def test_generation_agent__interleaved__sends_notifications(
    mock_llm,
    mock_language_model_service,
    mock_swot_report_registry,
    mock_agentic_executor,
    mock_step_notifier,
    mock_progress_notifier,
) -> None:
    """
    Purpose: Verify notifications are sent during interleaved generation.
    Why this matters: Users rely on step-by-step progress indicators.
    Setup summary: One content with one component, verify step_notifier receives at least 2 calls.
    """
    source_registry = Mock()
    source_registry.register.return_value = "chunk_id"
    source_selector = _make_source_selector(should_select=True)

    agent = _make_agent(
        mock_llm,
        mock_language_model_service,
        mock_swot_report_registry,
        mock_agentic_executor,
    )

    content = _make_content()
    plan = _make_plan()

    with patch(
        "unique_swot.services.generation.agentic.agent.handle_generate_operation",
        new_callable=AsyncMock,
    ):
        await agent.generate(
            plan=plan,
            total_steps=1,
            source_iterator=_async_content_iter(content),
            source_selector=source_selector,
            source_registry=source_registry,
            step_notifier=mock_step_notifier,
            progress_notifier=mock_progress_notifier,
        )

        assert mock_step_notifier.notify.await_count >= 2


@pytest.mark.asyncio
@pytest.mark.ai
async def test_generation_agent__interleaved__skips_unselected_sources(
    mock_llm,
    mock_language_model_service,
    mock_swot_report_registry,
    mock_agentic_executor,
    mock_step_notifier,
    mock_progress_notifier,
) -> None:
    """
    Purpose: Verify sources rejected by the selector are not processed.
    Why this matters: Prevents wasting LLM calls on irrelevant documents.
    Setup summary: Selector returns should_select=False, handle_generate_operation should not be called.
    """
    source_registry = Mock()
    source_registry.register.return_value = "chunk_id"
    source_selector = _make_source_selector(should_select=False)

    agent = _make_agent(
        mock_llm,
        mock_language_model_service,
        mock_swot_report_registry,
        mock_agentic_executor,
    )

    content = _make_content()
    plan = _make_plan()

    with patch(
        "unique_swot.services.generation.agentic.agent.handle_generate_operation",
        new_callable=AsyncMock,
    ) as mock_handle:
        await agent.generate(
            plan=plan,
            total_steps=1,
            source_iterator=_async_content_iter(content),
            source_selector=source_selector,
            source_registry=source_registry,
            step_notifier=mock_step_notifier,
            progress_notifier=mock_progress_notifier,
        )

        mock_handle.assert_not_awaited()


# =============================================================================
# Report retrieval
# =============================================================================


@pytest.mark.ai
def test_generation_agent__get_swot_report_components__returns_structure(
    mock_llm, mock_language_model_service, mock_agentic_executor
) -> None:
    """
    Purpose: Verify _get_swot_report_components returns correct SWOTReportComponents.
    Why this matters: Report assembly from registry must produce the expected structure.
    Setup summary: Registry returns one section per component, verify all four are populated.
    """
    registry = Mock()
    registry.retrieve_component_sections.return_value = [
        SWOTReportComponentSection(
            h2="Test", entries=[SWOTReportSectionEntry(preview="P", content="C")]
        )
    ]

    config = Mock()
    config.max_tokens_per_extraction_batch = 1000

    agent = GenerationAgent(
        company_name="ACME Corp",
        llm=mock_llm,
        llm_service=mock_language_model_service,
        registry=registry,
        executor=mock_agentic_executor,
        config=config,
    )

    reports = agent._get_swot_report_components()

    assert isinstance(reports, SWOTReportComponents)
    assert len(reports.strengths) == 1
    assert len(reports.weaknesses) == 1
    assert len(reports.opportunities) == 1
    assert len(reports.threats) == 1


# =============================================================================
# Properties
# =============================================================================


@pytest.mark.ai
def test_generation_agent__notification_title__getter_and_setter(
    mock_llm,
    mock_language_model_service,
    mock_swot_report_registry,
    mock_agentic_executor,
) -> None:
    """
    Purpose: Verify notification_title property getter and setter work correctly.
    Why this matters: Notification titles are displayed to users during processing.
    Setup summary: Check default, set a custom title, verify it changed.
    """
    config = Mock()
    config.max_tokens_per_extraction_batch = 1000

    agent = GenerationAgent(
        company_name="ACME Corp",
        llm=mock_llm,
        llm_service=mock_language_model_service,
        registry=mock_swot_report_registry,
        executor=mock_agentic_executor,
        config=config,
    )

    assert agent.notification_title == "Generating SWOT report"

    agent.notification_title = "Custom Title"
    assert agent.notification_title == "Custom Title"


# =============================================================================
# Dispatch tests
# =============================================================================


@pytest.mark.asyncio
@pytest.mark.ai
async def test_generation_agent__generate__dispatches_interleaved__default_mode(
    mock_llm,
    mock_language_model_service,
    mock_swot_report_registry,
    mock_agentic_executor,
    mock_step_notifier,
    mock_progress_notifier,
) -> None:
    """
    Purpose: Verify generate() dispatches to _generate_interleaved when mode is INTERLEAVED.
    Why this matters: Default mode must route correctly to avoid unexpected behaviour.
    Setup summary: Default mode agent, patch _generate_interleaved, verify it is called.
    """
    agent = _make_agent(
        mock_llm,
        mock_language_model_service,
        mock_swot_report_registry,
        mock_agentic_executor,
        generation_mode=GenerationMode.INTERLEAVED,
    )

    expected = SWOTReportComponents(
        strengths=[], weaknesses=[], opportunities=[], threats=[]
    )

    with patch.object(
        agent, "_generate_interleaved", new_callable=AsyncMock, return_value=expected
    ) as mock_interleaved:
        result = await agent.generate(
            plan=_make_plan(),
            total_steps=1,
            source_iterator=_async_content_iter(_make_content()),
            source_selector=_make_source_selector(),
            source_registry=Mock(),
            step_notifier=mock_step_notifier,
            progress_notifier=mock_progress_notifier,
        )

        mock_interleaved.assert_awaited_once()
        assert result is expected


@pytest.mark.asyncio
@pytest.mark.ai
async def test_generation_agent__generate__dispatches_extract_first__when_configured(
    mock_llm,
    mock_language_model_service,
    mock_swot_report_registry,
    mock_agentic_executor,
    mock_step_notifier,
    mock_progress_notifier,
) -> None:
    """
    Purpose: Verify generate() dispatches to _generate_extract_first when mode is EXTRACT_FIRST.
    Why this matters: The new extract-first path must be reachable through the dispatch.
    Setup summary: EXTRACT_FIRST mode agent, patch _generate_extract_first, verify it is called.
    """
    agent = _make_agent(
        mock_llm,
        mock_language_model_service,
        mock_swot_report_registry,
        mock_agentic_executor,
        generation_mode=GenerationMode.EXTRACT_FIRST,
    )

    expected = SWOTReportComponents(
        strengths=[], weaknesses=[], opportunities=[], threats=[]
    )

    with patch.object(
        agent, "_generate_extract_first", new_callable=AsyncMock, return_value=expected
    ) as mock_extract_first:
        result = await agent.generate(
            plan=_make_plan(),
            total_steps=1,
            source_iterator=_async_content_iter(_make_content()),
            source_selector=_make_source_selector(),
            source_registry=Mock(),
            step_notifier=mock_step_notifier,
            progress_notifier=mock_progress_notifier,
        )

        mock_extract_first.assert_awaited_once()
        assert result is expected


@pytest.mark.asyncio
@pytest.mark.ai
async def test_generation_agent__generate__raises_value_error__unsupported_mode(
    mock_llm,
    mock_language_model_service,
    mock_swot_report_registry,
    mock_agentic_executor,
    mock_step_notifier,
    mock_progress_notifier,
) -> None:
    """
    Purpose: Verify generate() raises ValueError for an unsupported generation mode.
    Why this matters: Defensive coding against invalid configuration values.
    Setup summary: Set _generation_mode to an invalid value, expect ValueError.
    """
    agent = _make_agent(
        mock_llm,
        mock_language_model_service,
        mock_swot_report_registry,
        mock_agentic_executor,
    )
    agent._generation_mode = "invalid_mode"

    with pytest.raises(ValueError, match="Unsupported generation mode"):
        await agent.generate(
            plan=_make_plan(),
            total_steps=1,
            source_iterator=_async_content_iter(_make_content()),
            source_selector=_make_source_selector(),
            source_registry=Mock(),
            step_notifier=mock_step_notifier,
            progress_notifier=mock_progress_notifier,
        )


# =============================================================================
# Extract-first mode tests
# =============================================================================


@pytest.mark.asyncio
@pytest.mark.ai
async def test_generation_agent__extract_first__extracts_facts_per_source(
    mock_llm,
    mock_language_model_service,
    mock_swot_report_registry,
    mock_agentic_executor,
    mock_step_notifier,
    mock_progress_notifier,
) -> None:
    """
    Purpose: Verify extract-first mode calls extract_facts for each selected source and component.
    Why this matters: Phase 1 must extract facts from all sources before clustering.
    Setup summary: One content, one requested component, verify extract_facts is called.
    """
    source_registry = Mock()
    source_registry.register.return_value = "chunk_id"
    source_selector = _make_source_selector(should_select=True)

    agent = _make_agent(
        mock_llm,
        mock_language_model_service,
        mock_swot_report_registry,
        mock_agentic_executor,
        generation_mode=GenerationMode.EXTRACT_FIRST,
    )

    content = _make_content()
    plan = _make_plan()

    with (
        patch(
            "unique_swot.services.generation.agentic.agent.extract_facts",
            new_callable=AsyncMock,
            return_value=["fact1", "fact2"],
        ) as mock_extract,
        patch(
            "unique_swot.services.generation.agentic.agent.handle_accumulated_generate_operation",
            new_callable=AsyncMock,
        ),
    ):
        await agent.generate(
            plan=plan,
            total_steps=1,
            source_iterator=_async_content_iter(content),
            source_selector=source_selector,
            source_registry=source_registry,
            step_notifier=mock_step_notifier,
            progress_notifier=mock_progress_notifier,
        )

        mock_extract.assert_awaited_once()
        call_kwargs = mock_extract.call_args.kwargs
        assert call_kwargs["component"] == SWOTComponent.STRENGTHS
        assert call_kwargs["company_name"] == "ACME Corp"


@pytest.mark.asyncio
@pytest.mark.ai
async def test_generation_agent__extract_first__skips_unselected_sources(
    mock_llm,
    mock_language_model_service,
    mock_swot_report_registry,
    mock_agentic_executor,
    mock_step_notifier,
    mock_progress_notifier,
) -> None:
    """
    Purpose: Verify extract-first mode skips sources rejected by the selector.
    Why this matters: Irrelevant sources should not contribute facts.
    Setup summary: Selector rejects all sources, verify extract_facts is never called.
    """
    source_registry = Mock()
    source_registry.register.return_value = "chunk_id"
    source_selector = _make_source_selector(should_select=False)

    agent = _make_agent(
        mock_llm,
        mock_language_model_service,
        mock_swot_report_registry,
        mock_agentic_executor,
        generation_mode=GenerationMode.EXTRACT_FIRST,
    )

    content = _make_content()
    plan = _make_plan()

    with (
        patch(
            "unique_swot.services.generation.agentic.agent.extract_facts",
            new_callable=AsyncMock,
        ) as mock_extract,
        patch(
            "unique_swot.services.generation.agentic.agent.handle_accumulated_generate_operation",
            new_callable=AsyncMock,
        ),
    ):
        await agent.generate(
            plan=plan,
            total_steps=1,
            source_iterator=_async_content_iter(content),
            source_selector=source_selector,
            source_registry=source_registry,
            step_notifier=mock_step_notifier,
            progress_notifier=mock_progress_notifier,
        )

        mock_extract.assert_not_awaited()


@pytest.mark.asyncio
@pytest.mark.ai
async def test_generation_agent__extract_first__calls_handle_accumulated_generate(
    mock_llm,
    mock_language_model_service,
    mock_swot_report_registry,
    mock_agentic_executor,
    mock_step_notifier,
    mock_progress_notifier,
) -> None:
    """
    Purpose: Verify phase 2 of extract-first calls handle_accumulated_generate_operation.
    Why this matters: After extraction, facts must be clustered and turned into report sections.
    Setup summary: Extract returns facts, verify handle_accumulated_generate_operation is called.
    """
    source_registry = Mock()
    source_registry.register.return_value = "chunk_id"
    source_selector = _make_source_selector(should_select=True)

    agent = _make_agent(
        mock_llm,
        mock_language_model_service,
        mock_swot_report_registry,
        mock_agentic_executor,
        generation_mode=GenerationMode.EXTRACT_FIRST,
    )

    content = _make_content()
    plan = _make_plan()

    with (
        patch(
            "unique_swot.services.generation.agentic.agent.extract_facts",
            new_callable=AsyncMock,
            return_value=["fact1", "fact2"],
        ),
        patch(
            "unique_swot.services.generation.agentic.agent.handle_accumulated_generate_operation",
            new_callable=AsyncMock,
        ) as mock_accumulated,
    ):
        await agent.generate(
            plan=plan,
            total_steps=1,
            source_iterator=_async_content_iter(content),
            source_selector=source_selector,
            source_registry=source_registry,
            step_notifier=mock_step_notifier,
            progress_notifier=mock_progress_notifier,
        )

        mock_accumulated.assert_awaited_once()
        call_kwargs = mock_accumulated.call_args.kwargs
        assert call_kwargs["component"] == SWOTComponent.STRENGTHS
        assert call_kwargs["company_name"] == "ACME Corp"


@pytest.mark.asyncio
@pytest.mark.ai
async def test_generation_agent__extract_first__skips_component_with_no_facts(
    mock_llm,
    mock_language_model_service,
    mock_swot_report_registry,
    mock_agentic_executor,
    mock_step_notifier,
    mock_progress_notifier,
) -> None:
    """
    Purpose: Verify extract-first skips accumulated generation for components with no facts.
    Why this matters: Prevents empty clustering calls when extraction yields nothing.
    Setup summary: Extract returns empty list, verify handle_accumulated_generate_operation is not called.
    """
    source_registry = Mock()
    source_registry.register.return_value = "chunk_id"
    source_selector = _make_source_selector(should_select=True)

    agent = _make_agent(
        mock_llm,
        mock_language_model_service,
        mock_swot_report_registry,
        mock_agentic_executor,
        generation_mode=GenerationMode.EXTRACT_FIRST,
    )

    content = _make_content()
    plan = _make_plan()

    with (
        patch(
            "unique_swot.services.generation.agentic.agent.extract_facts",
            new_callable=AsyncMock,
            return_value=[],
        ),
        patch(
            "unique_swot.services.generation.agentic.agent.handle_accumulated_generate_operation",
            new_callable=AsyncMock,
        ) as mock_accumulated,
    ):
        await agent.generate(
            plan=plan,
            total_steps=1,
            source_iterator=_async_content_iter(content),
            source_selector=source_selector,
            source_registry=source_registry,
            step_notifier=mock_step_notifier,
            progress_notifier=mock_progress_notifier,
        )

        mock_accumulated.assert_not_awaited()
