from typing import AsyncIterator, Protocol

from unique_swot.services.generation.context import SWOTComponent
from unique_swot.services.generation.extraction.models import SWOTExtractionModel
from unique_swot.services.memory.base import SwotMemoryService
from unique_swot.services.orchestrator.schema import SourceSelectionResult
from unique_swot.services.schemas import SWOTPlan
from unique_swot.services.source_management.schema import Source


class Notifier(Protocol):
    """This class is responsible for notifying the user of the progress of the SWOT analysis."""

    async def notify(self, message: str): ...

    async def init_progress(self, total_steps: int): ...

    async def update_progress(self, progress: float): ...

    async def end_progress(
        self, failed: bool = False, failure_message: str | None = None
    ): ...


class SourceCollector(Protocol):
    """This class is responsible for collecting the sources from the various data sources."""

    async def collect(self) -> list[Source]: ...


class SourceSelector(Protocol):
    """This class is responsible for selecting the sources that are most relevant to the SWOT analysis."""

    async def select(self, *, source: Source) -> SourceSelectionResult: ...


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
    ) -> None: ...

    def get_report(self) -> str: ...


class SWOTOrchestrator:
    def __init__(
        self,
        # notifier: Notifier,
        company_name: str,
        source_collector: SourceCollector,
        source_selector: SourceSelector,
        source_iterator: SourceIterator,
        extractor: Extractor,
        report_manager: ReportManager,
        memory_service: SwotMemoryService,
    ):
        self._company_name = company_name
        self._source_collector = source_collector
        self._source_selector = source_selector
        self._extractor = extractor
        self._report_manager = report_manager
        self._source_iterator = source_iterator
        self._memory_service = memory_service

    async def run(self, company_name: str, plan: SWOTPlan):
        sources = await self._source_collector.collect()

        source_iterator = await self._source_iterator.iterate(sources=sources)

        async for source in source_iterator:
            source_selection_result = await self._source_selector.select(source=source)

            if not source_selection_result.should_select:
                continue

            for component in SWOTComponent:
                step = plan.get_step_result(component)

                extraction_result = await self._extractor.extract(
                    company_name=self._company_name,
                    component=component,
                    source=source,
                    optional_instruction=step.modify_instruction,
                )

                await self._report_manager.generate_and_update_memory(
                    company_name=self._company_name,
                    component=component,
                    extraction_result=extraction_result,
                    optional_instruction=step.modify_instruction,
                )

        return self._report_manager.get_report()
