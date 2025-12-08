from copy import deepcopy
from unittest.mock import AsyncMock, Mock

import pytest

from unique_swot.services.generation.context import SWOTComponent
from unique_swot.services.generation.extraction.models.strengths import (
    StrengthItem,
    StrengthsExtraction,
)
from unique_swot.services.generation.reporting.agent import ProgressiveReportingAgent
from unique_swot.services.generation.reporting.config import ReportingConfig
from unique_swot.services.generation.reporting.models.strengths import (
    ConsolidatedStrengthItem,
    ConsolidatedStrengthsReport,
    StrengthBulletPoint,
)


def _strength_report(id: str, title: str) -> ConsolidatedStrengthsReport:
    bullet_points = [
        StrengthBulletPoint(
            key_reasoning="reason 1",
            detailed_context="context 1 [chunk_a]",
        ),
        StrengthBulletPoint(
            key_reasoning="reason 2",
            detailed_context="context 2 [chunk_b]",
        ),
    ]
    return ConsolidatedStrengthsReport(
        strengths=[
            ConsolidatedStrengthItem(id=id, title=title, bullet_points=bullet_points)
        ],
        notification_message="notify",
        progress_notification_message="progress",
    )


def _extraction_result() -> StrengthsExtraction:
    return StrengthsExtraction(
        strengths=[
            StrengthItem(
                justification="j",
                title="t",
                reference_chunk_ids=["chunk_a"],
            )
        ],
        notification_message="extract",
        progress_notification_message="extracting",
    )


@pytest.mark.asyncio
async def test_generate_and_update_memory_creates_new_report(monkeypatch):
    memory_service = Mock()
    memory_service.get.return_value = None
    llm_service = Mock()

    generated_report = _strength_report(id="s1", title="First")
    monkeypatch.setattr(
        "unique_swot.services.generation.reporting.agent.generate_structured_output",
        AsyncMock(return_value=generated_report),
    )

    agent = ProgressiveReportingAgent(
        memory_service=memory_service,
        llm_service=llm_service,
        llm=Mock(),
        reporting_config=ReportingConfig(),
    )

    result = await agent.generate_and_update_memory(
        company_name="ACME",
        component=SWOTComponent.STRENGTHS,
        extraction_result=_extraction_result(),
        optional_instruction=None,
    )

    assert result.strengths[0].id == "s1"
    memory_service.set.assert_called_once_with(generated_report)


@pytest.mark.asyncio
async def test_generate_and_update_memory_updates_existing(monkeypatch):
    existing_report = _strength_report(id="s1", title="Old title")
    memory_service = Mock()
    memory_service.get.return_value = deepcopy(existing_report)
    llm_service = Mock()

    new_report = _strength_report(id="s1", title="New title")
    monkeypatch.setattr(
        "unique_swot.services.generation.reporting.agent.generate_structured_output",
        AsyncMock(return_value=new_report),
    )

    agent = ProgressiveReportingAgent(
        memory_service=memory_service,
        llm_service=llm_service,
        llm=Mock(),
        reporting_config=ReportingConfig(),
    )

    updated = await agent.generate_and_update_memory(
        company_name="ACME",
        component=SWOTComponent.STRENGTHS,
        extraction_result=_extraction_result(),
        optional_instruction="update",
    )

    assert updated.strengths[0].title == "New title"
    # Should call set with the merged report
    memory_service.set.assert_called()
    saved_report = memory_service.set.call_args.args[0]
    assert saved_report.strengths[0].title == "New title"
