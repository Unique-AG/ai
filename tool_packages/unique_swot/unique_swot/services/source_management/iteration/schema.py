from pydantic import Field

from unique_swot.utils import StructuredOutputResult


class SourceIterationResult(StructuredOutputResult):
    """This class is responsible for the result of the source iteration."""

    id: str = Field(description="The id of the source")
    order: int = Field(description="The order of the source")


class SourceIterationResults(StructuredOutputResult):
    """This class is responsible for the results of the source iteration."""

    results_summary: str = Field(
        description="A detailed description of the ordering outcome."
    )
    ordered_sources: list[SourceIterationResult] = Field(
        description="The list of sources ordered from the oldest to the newest"
    )
