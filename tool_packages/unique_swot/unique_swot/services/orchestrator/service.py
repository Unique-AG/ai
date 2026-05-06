from logging import getLogger
from typing import AsyncIterator, Protocol

from unique_toolkit.chat.service import ChatService
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


class ProgressNotifier(Protocol):
    """This class is responsible for notifying the user of the progress of the SWOT analysis."""

    async def update(self, *, progress: int | float, title: str | None = None): ...

    async def increment(self, fraction: float): ...

    @property
    def step_size(self) -> int | float: ...

    @step_size.setter
    def step_size(self, value: int | float) -> None: ...


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
        total_steps: int,
        source_iterator: AsyncIterator[Content],
        source_selector: SourceSelector,
        source_registry: SourceRegistry,
        step_notifier: StepNotifier,
        progress_notifier: ProgressNotifier,
    ) -> SWOTReportComponents: ...


class SWOTOrchestrator:
    def __init__(
        self,
        step_notifier: StepNotifier,
        source_collector: SourceCollector,
        source_selector: SourceSelector,
        source_iterator: SourceIterator,
        reporting_agent: ReportingAgent,
        source_registry: SourceRegistry,
        progress_notifier: ProgressNotifier,
        memory_service: SwotMemoryService,
        chat_service: ChatService,
    ):
        self._source_collector = source_collector
        self._source_selector = source_selector
        self._reporting_agent = reporting_agent
        self._source_iterator = source_iterator
        self._memory_service = memory_service
        self._step_notifier = step_notifier
        self._source_registry = source_registry
        self._progress_notifier = progress_notifier
        self._chat_service = chat_service

    async def run(self, *, plan: SWOTPlan) -> SWOTReportComponents:
        contents = await self._source_collector.collect(
            step_notifier=self._step_notifier
        )

        await self._progress_notifier.update(progress=5)

        source_iterator = await self._source_iterator.iterate(
            contents=contents, step_notifier=self._step_notifier
        )

        await self._progress_notifier.update(progress=10)

        total_steps = len(contents)

        if total_steps == 0:
            # Early return if there are no sources to process (this should never happen)
            raise ValueError("No sources to process")

        # Execute the generation
        reports = await self._reporting_agent.generate(
            plan=plan,
            total_steps=total_steps,
            source_iterator=source_iterator,
            source_selector=self._source_selector,
            step_notifier=self._step_notifier,
            source_registry=self._source_registry,
            progress_notifier=self._progress_notifier,
        )

        return reports
