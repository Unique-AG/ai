"""Tests for agentic generation operations (extract-first helpers)."""

from unittest.mock import AsyncMock, Mock, patch

import pytest

from unique_swot.services.generation.agentic.exceptions import (
    FailedToExtractFactsException,
    FailedToGeneratePlanException,
)
from unique_swot.services.generation.agentic.operations import (
    extract_facts,
    handle_accumulated_generate_operation,
    handle_generate_operation,
)
from unique_swot.services.generation.context import SWOTComponent
from unique_swot.services.generation.models.base import SWOTExtractionFactsList
from unique_swot.services.generation.models.plan import (
    GenerationPlan,
    GenerationPlanCommand,
    GenerationPlanCommandType,
)

# =============================================================================
# extract_facts
# =============================================================================


@pytest.mark.asyncio
@pytest.mark.ai
async def test_extract_facts__returns_facts__on_success(
    mock_llm, mock_language_model_service, mock_step_notifier
) -> None:
    """
    Purpose: Verify extract_facts returns a list of fact strings on successful LLM call.
    Why this matters: Extraction is the core data-gathering step for all generation modes.
    Setup summary: Mock generate_structured_output to return facts, verify return value.
    """
    extraction_config = Mock()
    extraction_config.system_prompt = (
        "System: {{ company_name }} {{ component }} {{ component_definition }}"
    )
    extraction_config.user_prompt = (
        "User: {{ company_name }} {{ component }} {{ source_batches }}"
    )

    definition_config = Mock()

    with patch(
        "unique_swot.services.generation.agentic.operations.generate_structured_output",
        new_callable=AsyncMock,
        return_value=SWOTExtractionFactsList(
            facts=["fact A", "fact B"], notification_message="Extracted 2 facts"
        ),
    ):
        with patch(
            "unique_swot.services.generation.agentic.operations.get_component_definition",
            return_value="definition text",
        ):
            result = await extract_facts(
                company_name="ACME Corp",
                component=SWOTComponent.STRENGTHS,
                source_batches=[{"id": "c1", "text": "data"}],
                step_notifier=mock_step_notifier,
                llm=mock_llm,
                llm_service=mock_language_model_service,
                notification_title="Extracting",
                prompts_config=extraction_config,
                component_definition_prompt_config=definition_config,
            )

    assert result == ["fact A", "fact B"]


@pytest.mark.asyncio
@pytest.mark.ai
async def test_extract_facts__raises__on_none_result(
    mock_llm, mock_language_model_service, mock_step_notifier
) -> None:
    """
    Purpose: Verify extract_facts raises FailedToExtractFactsException when LLM returns None.
    Why this matters: Signals that extraction failed so the caller can skip or retry.
    Setup summary: Mock generate_structured_output to return None, expect exception.
    """
    extraction_config = Mock()
    extraction_config.system_prompt = (
        "System: {{ company_name }} {{ component }} {{ component_definition }}"
    )
    extraction_config.user_prompt = (
        "User: {{ company_name }} {{ component }} {{ source_batches }}"
    )

    definition_config = Mock()

    with patch(
        "unique_swot.services.generation.agentic.operations.generate_structured_output",
        new_callable=AsyncMock,
        return_value=None,
    ):
        with patch(
            "unique_swot.services.generation.agentic.operations.get_component_definition",
            return_value="definition text",
        ):
            with pytest.raises(FailedToExtractFactsException):
                await extract_facts(
                    company_name="ACME Corp",
                    component=SWOTComponent.STRENGTHS,
                    source_batches=[{"id": "c1", "text": "data"}],
                    step_notifier=mock_step_notifier,
                    llm=mock_llm,
                    llm_service=mock_language_model_service,
                    notification_title="Extracting",
                    prompts_config=extraction_config,
                    component_definition_prompt_config=definition_config,
                )


# =============================================================================
# handle_generate_operation
# =============================================================================


@pytest.mark.asyncio
@pytest.mark.ai
async def test_handle_generate_operation__catches_extraction_failure(
    mock_llm, mock_language_model_service, mock_step_notifier
) -> None:
    """
    Purpose: Verify handle_generate_operation catches FailedToExtractFactsException.
    Why this matters: A single failed extraction should not crash the entire pipeline.
    Setup summary: Mock extract_facts to raise, verify notifier receives error description.
    """
    config = Mock()
    config.prompts_config.extraction_prompt_config = Mock()
    config.prompts_config.definition_prompt_config = Mock()

    with patch(
        "unique_swot.services.generation.agentic.operations.extract_facts",
        new_callable=AsyncMock,
        side_effect=FailedToExtractFactsException("boom"),
    ):
        await handle_generate_operation(
            component=SWOTComponent.STRENGTHS,
            source_batches=[{"id": "c1", "text": "data"}],
            step_notifier=mock_step_notifier,
            company_name="ACME",
            llm=mock_llm,
            llm_service=mock_language_model_service,
            notification_title="Test",
            swot_report_registry=Mock(),
            executor=Mock(),
            config=config,
        )

    assert mock_step_notifier.notify.await_count >= 1


@pytest.mark.asyncio
@pytest.mark.ai
async def test_handle_generate_operation__catches_plan_failure(
    mock_llm, mock_language_model_service, mock_step_notifier
) -> None:
    """
    Purpose: Verify handle_generate_operation catches FailedToGeneratePlanException.
    Why this matters: Plan generation failures should be handled gracefully.
    Setup summary: Mock extract_facts success then _generate_plan failure, verify recovery.
    """
    config = Mock()
    config.prompts_config.extraction_prompt_config = Mock()
    config.prompts_config.definition_prompt_config = Mock()
    config.prompts_config.plan_prompt_config = Mock()

    with (
        patch(
            "unique_swot.services.generation.agentic.operations.extract_facts",
            new_callable=AsyncMock,
            return_value=["fact1"],
        ),
        patch(
            "unique_swot.services.generation.agentic.operations._generate_plan",
            new_callable=AsyncMock,
            side_effect=FailedToGeneratePlanException("plan failed"),
        ),
    ):
        await handle_generate_operation(
            component=SWOTComponent.STRENGTHS,
            source_batches=[{"id": "c1", "text": "data"}],
            step_notifier=mock_step_notifier,
            company_name="ACME",
            llm=mock_llm,
            llm_service=mock_language_model_service,
            notification_title="Test",
            swot_report_registry=Mock(),
            executor=Mock(),
            config=config,
        )

    assert mock_step_notifier.notify.await_count >= 1


# =============================================================================
# handle_accumulated_generate_operation
# =============================================================================


def _make_generation_plan() -> GenerationPlan:
    """Helper to create a minimal GenerationPlan."""
    return GenerationPlan(
        notification_message="Plan ready",
        commands=[
            GenerationPlanCommand(
                reasoning="test reasoning",
                command=GenerationPlanCommandType.CREATE_SECTION,
                instruction="Create section about market share",
                target_section_id=None,
                source_facts_ids=["fact_1"],
            )
        ],
    )


@pytest.mark.asyncio
@pytest.mark.ai
async def test_handle_accumulated_generate__plans_and_executes(
    mock_llm,
    mock_language_model_service,
    mock_step_notifier,
    mock_swot_report_registry,
    mock_agentic_executor,
) -> None:
    """
    Purpose: Verify handle_accumulated_generate_operation clusters facts and executes the plan.
    Why this matters: This is the core Phase 2 path in extract-first mode.
    Setup summary: Mock cluster plan and execute plan, verify both are called.
    """
    config = Mock()
    config.prompts_config.cluster_plan_prompt_config = Mock()
    config.prompts_config.commands_prompt_config = Mock()

    plan = _make_generation_plan()
    mock_section = Mock()

    with (
        patch(
            "unique_swot.services.generation.agentic.operations._generate_cluster_plan",
            new_callable=AsyncMock,
            return_value=plan,
        ) as mock_cluster_plan,
        patch(
            "unique_swot.services.generation.agentic.operations._execute_plan",
            new_callable=AsyncMock,
            return_value=[mock_section],
        ) as mock_execute,
    ):
        await handle_accumulated_generate_operation(
            component=SWOTComponent.STRENGTHS,
            fact_id_map={"fact_1": "Company has 35% market share"},
            step_notifier=mock_step_notifier,
            company_name="ACME",
            llm=mock_llm,
            llm_service=mock_language_model_service,
            notification_title="Generating",
            swot_report_registry=mock_swot_report_registry,
            executor=mock_agentic_executor,
            config=config,
        )

        mock_cluster_plan.assert_awaited_once()
        mock_execute.assert_awaited_once()


@pytest.mark.asyncio
@pytest.mark.ai
async def test_handle_accumulated_generate__catches_plan_failure(
    mock_llm,
    mock_language_model_service,
    mock_step_notifier,
    mock_swot_report_registry,
    mock_agentic_executor,
) -> None:
    """
    Purpose: Verify handle_accumulated_generate_operation catches FailedToGeneratePlanException.
    Why this matters: Cluster plan failures should be reported and not crash the pipeline.
    Setup summary: Mock _generate_cluster_plan to raise, verify notifier receives error message.
    """
    config = Mock()
    config.prompts_config.cluster_plan_prompt_config = Mock()

    with patch(
        "unique_swot.services.generation.agentic.operations._generate_cluster_plan",
        new_callable=AsyncMock,
        side_effect=FailedToGeneratePlanException("cluster failed"),
    ):
        await handle_accumulated_generate_operation(
            component=SWOTComponent.STRENGTHS,
            fact_id_map={"fact_1": "Some fact"},
            step_notifier=mock_step_notifier,
            company_name="ACME",
            llm=mock_llm,
            llm_service=mock_language_model_service,
            notification_title="Generating",
            swot_report_registry=mock_swot_report_registry,
            executor=mock_agentic_executor,
            config=config,
        )

    notified_descriptions = [
        call.kwargs.get("description", call.args[1] if len(call.args) > 1 else "")
        for call in mock_step_notifier.notify.call_args_list
    ]
    assert any(
        "clustering" in d.lower() or "error" in d.lower()
        for d in notified_descriptions
        if d
    )


@pytest.mark.asyncio
@pytest.mark.ai
async def test_handle_accumulated_generate__catches_unexpected_exception(
    mock_llm,
    mock_language_model_service,
    mock_step_notifier,
    mock_swot_report_registry,
    mock_agentic_executor,
) -> None:
    """
    Purpose: Verify handle_accumulated_generate_operation catches unexpected exceptions.
    Why this matters: Any failure in generation should be logged and not propagate.
    Setup summary: Mock _generate_cluster_plan to raise RuntimeError, verify graceful handling.
    """
    config = Mock()
    config.prompts_config.cluster_plan_prompt_config = Mock()

    with patch(
        "unique_swot.services.generation.agentic.operations._generate_cluster_plan",
        new_callable=AsyncMock,
        side_effect=RuntimeError("unexpected"),
    ):
        await handle_accumulated_generate_operation(
            component=SWOTComponent.STRENGTHS,
            fact_id_map={"fact_1": "Some fact"},
            step_notifier=mock_step_notifier,
            company_name="ACME",
            llm=mock_llm,
            llm_service=mock_language_model_service,
            notification_title="Generating",
            swot_report_registry=mock_swot_report_registry,
            executor=mock_agentic_executor,
            config=config,
        )

    assert mock_step_notifier.notify.await_count >= 1
