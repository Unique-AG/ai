from typing import AsyncIterator, Protocol

from tqdm.asyncio import tqdm
from unique_toolkit.content.schemas import ContentReference

from unique_swot.services.generation.context import SWOTComponent
from unique_swot.services.generation.extraction.models import SWOTExtractionModel
from unique_swot.services.generation.reporting.models import SWOTConsolidatedReport
from unique_swot.services.memory.base import SwotMemoryService
from unique_swot.services.schemas import SWOTPlan
from unique_swot.services.source_management.schema import Source
from unique_swot.services.source_management.selection.schema import (
    SourceSelectionResult,
)


class Notifier(Protocol):
    """This class is responsible for notifying the user of the progress of the SWOT analysis."""

    def set_progress_total_steps(self, total_steps: int): ...

    async def notify(
        self, title: str, description: str = "", sources: list[ContentReference] = []
    ): ...

    async def init_progress(self, session_info: str): ...

    async def increment_progress(self, step_increment: float, progress_info: str): ...

    async def end_progress(
        self, failed: bool = False, failure_message: str | None = None
    ): ...


class SourceCollector(Protocol):
    """This class is responsible for collecting the sources from the various data sources."""

    async def collect(self) -> list[Source]: ...


class SourceSelector(Protocol):
    """This class is responsible for selecting the sources that are most relevant to the SWOT analysis."""

    async def select(
        self, *, company_name: str, source: Source
    ) -> SourceSelectionResult: ...


class SourceIterator(Protocol):
    """This class is responsible for prioritizing the sources that are most relevant to the SWOT analysis."""

    async def iterate(self, *, sources: list[Source]) -> AsyncIterator[Source]: ...


class Extractor(Protocol):
    """This class is responsible for extracting the SWOT analysis from the sources."""

    async def extract(
        self,
        *,
        company_name: str,
        component: SWOTComponent,
        source: Source,
        optional_instruction: str | None,
    ) -> SWOTExtractionModel: ...


class ReportManager(Protocol):
    """This class is responsible for loading the SWOT analysis from the sources."""

    async def generate_and_update_memory(
        self,
        *,
        company_name: str,
        component: SWOTComponent,
        extraction_result: SWOTExtractionModel,
        optional_instruction: str | None,
    ) -> str: ...

    def get_report(self) -> list[SWOTConsolidatedReport]: ...


class SWOTOrchestrator:
    def __init__(
        self,
        notifier: Notifier,
        source_collector: SourceCollector,
        source_selector: SourceSelector,
        source_iterator: SourceIterator,
        extractor: Extractor,
        report_manager: ReportManager,
        memory_service: SwotMemoryService,
    ):
        self._source_collector = source_collector
        self._source_selector = source_selector
        self._extractor = extractor
        self._report_manager = report_manager
        self._source_iterator = source_iterator
        self._memory_service = memory_service
        self._notifier = notifier

    async def run(
        self, *, company_name: str, plan: SWOTPlan
    ) -> list[SWOTConsolidatedReport]:
        sources = await self._source_collector.collect()

        self._notifier.set_progress_total_steps(total_steps=len(sources) * len(plan))

        await self._notifier.notify(title="Sorting sources by date")
        await self._notifier.increment_progress(
            step_increment=0, progress_info="Sorting sources by date"
        )

        source_iterator = await self._source_iterator.iterate(sources=sources)

        async for source in tqdm(source_iterator, desc="Processing sources"):
            title = f"Processing source {source.title}"
            await self._notifier.notify(title=title)

            await self._notifier.increment_progress(
                step_increment=0, progress_info="Evaluating source relevance..."
            )
            source_selection_result = await self._source_selector.select(
                company_name=company_name, source=source
            )
            notification_message = source_selection_result.notification_message
            await self._notifier.notify(
                title=title,
                description=notification_message,
            )
            if not source_selection_result.should_select:
                await self._notifier.increment_progress(
                    step_increment=len(plan),
                    progress_info=notification_message,
                )
                continue

            await self._notifier.notify(
                title=title,
                description=notification_message,
            )

            for component in tqdm(SWOTComponent, desc="Processing components"):
                step = plan.get_step_result(component)

                await self._notifier.notify(
                    title=title,
                    description=f"Extracting information for {component.value}...",
                )

                await self._notifier.increment_progress(
                    step_increment=0.5, progress_info="Extracting information..."
                )

                extraction_result = await self._extractor.extract(
                    company_name=company_name,
                    component=component,
                    source=source,
                    optional_instruction=step.modify_instruction,
                )

                notification_message = extraction_result.notification_message

                await self._notifier.notify(
                    title=title,
                    description=notification_message,
                )
                await self._notifier.increment_progress(
                    step_increment=0.5,
                    progress_info=notification_message,
                )

                notification_message = (
                    await self._report_manager.generate_and_update_memory(
                        company_name=company_name,
                        component=component,
                        extraction_result=extraction_result,
                        optional_instruction=step.modify_instruction,
                    )
                )

                await self._notifier.notify(
                    title=title,
                    description=notification_message,
                )
                await self._notifier.increment_progress(
                    step_increment=0.5,
                    progress_info=notification_message,
                )

        return self._report_manager.get_report()
