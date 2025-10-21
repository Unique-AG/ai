from logging import getLogger
from typing import Protocol, Self, Sequence

from unique_toolkit.content import ContentChunk

from unique_swot.services.collection.registry import ContentChunkRegistry

_LOGGER = getLogger(__name__)


class ReportGenerationOutputModel(Protocol):
    @classmethod
    def group_batches(cls, batches: Sequence[Self]) -> Self:
        """
        Combine multiple batches of the same type into a single instance.

        This method is crucial for processing large datasets that need to be split
        into multiple batches due to token limits. Each batch generates partial results
        that must be combined into a final comprehensive report.

        Args:
            batches: Sequence of instances of the same type to combine

        Returns:
            A single combined instance of the same type
        """
        ...


class ReportGenerationSummaryModel(Protocol):
    @classmethod
    def create_from_failed(cls) -> Self: ...

    def get_referenced_chunks(
        self, chunk_registry: ContentChunkRegistry
    ) -> list[ContentChunk]: ...
