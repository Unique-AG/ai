from unittest.mock import AsyncMock, Mock

import pytest

from unique_swot.services.generation.extraction.models.strengths import (
    StrengthItem,
    StrengthsExtraction,
)
from unique_swot.services.generation.reporting.models.strengths import (
    ConsolidatedStrengthItem,
    ConsolidatedStrengthsReport,
    StrengthBulletPoint,
)
from unique_swot.services.orchestrator.service import SWOTOrchestrator
from unique_swot.services.schemas import SWOTOperation, SWOTPlan, SWOTStepPlan
from unique_swot.services.source_management.schema import (
    Source,
    SourceChunk,
    SourceType,
)
from unique_swot.services.source_management.selection.schema import (
    SourceSelectionResult,
)


def _plan_strengths_only():
    return SWOTPlan(
        objective="Obj",
        strengths=SWOTStepPlan(
            operation=SWOTOperation.GENERATE, modify_instruction=None
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


def _source():
    return Source(
        type=SourceType.WEB,
        url=None,
        title="240101_example",
        chunks=[SourceChunk(id="c1", text="text")],
    )


def _extraction():
    return StrengthsExtraction(
        strengths=[
            StrengthItem(
                justification="j",
                title="t",
                reference_chunk_ids=["chunk_a"],
            )
        ],
        notification_message="note",
        progress_notification_message="progress",
    )


def _consolidated():
    return ConsolidatedStrengthsReport(
        strengths=[
            ConsolidatedStrengthItem(
                id="s1",
                title="Strength",
                bullet_points=[
                    StrengthBulletPoint(
                        key_reasoning="key",
                        detailed_context="details [chunk_a]",
                    ),
                    StrengthBulletPoint(
                        key_reasoning="key2",
                        detailed_context="details2 [chunk_b]",
                    ),
                ],
            )
        ],
        notification_message="done",
        progress_notification_message="done",
    )


@pytest.mark.asyncio
async def test_orchestrator_runs_happy_path():
    notifier = Mock()
    notifier.set_progress_total_steps = Mock()
    notifier.notify = AsyncMock()
    notifier.increment_progress = AsyncMock()
    notifier.init_progress = AsyncMock()
    notifier.end_progress = AsyncMock()

    source_collector = Mock()
    source_collector.collect = AsyncMock(return_value=[_source()])

    async def _iterate(sources):
        for source in sources:
            yield source

    source_iterator = Mock()
    source_iterator.iterate = AsyncMock(side_effect=lambda sources: _iterate(sources))

    source_selector = Mock()
    source_selector.select = AsyncMock(
        return_value=SourceSelectionResult(
            should_select=True,
            reason="",
            notification_message="ok",
            progress_notification_message="ok",
        )
    )

    extractor = Mock()
    extractor.extract = AsyncMock(return_value=_extraction())

    report_manager = Mock()
    report_manager.generate_and_update_memory = AsyncMock(return_value=_consolidated())
    report_manager.get_report.return_value = [_consolidated()]

    orchestrator = SWOTOrchestrator(
        notifier=notifier,
        source_collector=source_collector,
        source_selector=source_selector,
        source_iterator=source_iterator,
        extractor=extractor,
        report_manager=report_manager,
        memory_service=Mock(),
    )

    result = await orchestrator.run(company_name="ACME", plan=_plan_strengths_only())

    assert len(result) == 1
    extractor.extract.assert_awaited_once()
    report_manager.generate_and_update_memory.assert_awaited_once()
    notifier.notify.assert_awaited()
