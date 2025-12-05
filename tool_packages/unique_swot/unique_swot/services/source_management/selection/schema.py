from pydantic import BaseModel, ConfigDict, Field


class SourceSelectionResult(BaseModel):
    """This class is responsible for the result of the source selection."""

    model_config = ConfigDict(extra="forbid")

    reason: str = Field(description="The reason for the source selection")
    should_select: bool = Field(description="Whether the source should be selected")
    notification_message: str = Field(
        description="A message to be displayed to the user to keep him updated on the progress of the source selection decision"
    )
