from pydantic import Field

from unique_swot.utils import StructuredOutputWithNotification


class SourceSelectionResult(StructuredOutputWithNotification):
    """This class is responsible for the result of the source selection."""

    reason: str = Field(description="The reason for the source selection")
    should_select: bool = Field(description="Whether the source should be selected")
