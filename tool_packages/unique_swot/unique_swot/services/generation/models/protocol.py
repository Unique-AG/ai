from typing import Protocol, Self, Sequence


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
