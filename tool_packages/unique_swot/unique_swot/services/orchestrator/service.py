from logging import getLogger
from typing import AsyncIterator, Protocol

from tqdm.asyncio import tqdm
from unique_toolkit.content import Content, ContentChunk, ContentReference

from unique_swot.services.generation.models.base import SWOTReportComponents
from unique_swot.services.memory.base import SwotMemoryService
from unique_swot.services.schemas import SWOTPlan
from unique_swot.services.source_management.selection.schema import (
    SourceSelectionResult,
)

_LOGGER = getLogger(__name__)


class StepNotifier(Protocol):
    """This class is responsible for notifying the user of the progress of a specific step of the SWOT analysis."""

    async def notify(
        self,
        title: str,
        description: str = "",
        sources: list[ContentReference] = [],
        progress: int | None = None,
        completed: bool = False,
    ): ...


class SourceCollector(Protocol):
    """This class is responsible for collecting the sources from the various data sources."""

    async def collect(self, *, step_notifier: StepNotifier) -> list[Content]: ...


class SourceSelector(Protocol):
    """This class is responsible for selecting the sources that are most relevant to the SWOT analysis."""

    async def select(
        self, *, company_name: str, content: Content, step_notifier: StepNotifier
    ) -> SourceSelectionResult: ...


class SourceIterator(Protocol):
    """This class is responsible for prioritizing the sources that are most relevant to the SWOT analysis."""

    async def iterate(
        self, *, contents: list[Content], step_notifier: StepNotifier
    ) -> AsyncIterator[Content]: ...


class SourceRegistry(Protocol):
    """This class is responsible for registering the sources that are processed."""

    def register(self, *, chunk: ContentChunk) -> str: ...

    def retrieve(self, *, id: str) -> ContentChunk | None: ...


class ReportingAgent(Protocol):
    """This class is responsible for generating the SWOT report."""

    async def generate(
        self,
        *,
        plan: SWOTPlan,
        content: Content,
        source_registry: SourceRegistry,
        step_notifier: StepNotifier,
    ) -> None: ...

    def get_reports(self) -> SWOTReportComponents: ...


class SWOTOrchestrator:
    def __init__(
        self,
        step_notifier: StepNotifier,
        source_collector: SourceCollector,
        source_selector: SourceSelector,
        source_iterator: SourceIterator,
        reporting_agent: ReportingAgent,
        source_registry: SourceRegistry,
        memory_service: SwotMemoryService,
    ):
        self._source_collector = source_collector
        self._source_selector = source_selector
        self._reporting_agent = reporting_agent
        self._source_iterator = source_iterator
        self._memory_service = memory_service
        self._step_notifier = step_notifier
        self._source_registry = source_registry

    async def run(self, *, company_name: str, plan: SWOTPlan) -> SWOTReportComponents:
        contents = await self._source_collector.collect(
            step_notifier=self._step_notifier
        )

        source_iterator = await self._source_iterator.iterate(
            contents=contents, step_notifier=self._step_notifier
        )

        total_steps = len(contents)

        async for content in tqdm(
            source_iterator, total=total_steps, desc="Processing sources"
        ):
            source_selection_result = await self._source_selector.select(
                company_name=company_name,
                content=content,
                step_notifier=self._step_notifier,
            )

            if not source_selection_result.should_select:
                # Skip the source if it is not selected
                _LOGGER.info(
                    f"Skipping source `{_get_content_title(content)}` as it is not selected"
                )
                continue
            else:
                _LOGGER.info(
                    f"Selecting source `{_get_content_title(content)}` as it is selected"
                )

            await self._reporting_agent.generate(
                plan=plan,
                content=content,
                step_notifier=self._step_notifier,
                source_registry=self._source_registry,
            )

        return self._reporting_agent.get_reports()


def _get_content_title(content: Content) -> str:
    return content.title or content.key or "Unknown Title"
