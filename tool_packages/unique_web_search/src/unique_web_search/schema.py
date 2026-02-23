from enum import StrEnum
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, create_model
from unidecode import unidecode
from unique_toolkit.content.schemas import ContentChunk


class WebSearchToolParameters(BaseModel):
    """Parameters for the Websearch tool."""

    model_config = ConfigDict(extra="forbid")
    query: str
    date_restrict: str | None

    @classmethod
    def from_tool_parameter_query_description(
        cls, query_description: str, date_restrict_description: str | None
    ) -> type["WebSearchToolParameters"]:
        """Create a new model with the query field."""
        return create_model(
            cls.__name__,
            query=(str, Field(description=query_description)),
            date_restrict=(
                str | None,
                Field(description=date_restrict_description),
            ),
            __base__=cls,
        )


class StepType(StrEnum):
    SEARCH = "search"
    READ_URL = "read_url"


class Step(BaseModel):
    step_type: Literal[StepType.SEARCH, StepType.READ_URL]
    objective: str = Field(description="The objective of the step")
    query_or_url: str = Field(
        description="The input for this step: either an optimized search query (for search steps) or a URL to read (for read_url steps)."
    )


class WebSearchPlan(BaseModel):
    model_config = ConfigDict(extra="forbid")
    objective: str = Field(description="The objective of the plan")
    query_analysis: str = Field(
        description="Analysis of the user's query and what information is needed"
    )
    steps: list[Step] = Field(description="Steps to execute")
    expected_outcome: str = Field(description="Expected outcome")


class StepDebugInfo(BaseModel):
    step_name: str
    execution_time: float
    config: str | dict
    extra: dict = Field(default_factory=dict)


class WebPageChunk(BaseModel):
    url: str
    display_link: str
    title: str
    snippet: str
    content: str
    order: str

    def to_content_chunk(self) -> "ContentChunk":
        """Convert WebPageChunk to ContentChunk format."""

        # Convert to ascii
        title = unidecode(self.title)
        name = f'{self.display_link}: "{title}"'

        return ContentChunk(
            id=name,
            text=self.content,
            order=int(self.order),
            start_page=None,
            end_page=None,
            key=name,
            chunk_id=self.order,
            url=self.url,
            title=name,
        )


class WebSearchDebugInfo(BaseModel):
    parameters: dict
    steps: list[StepDebugInfo] = []
    web_page_chunks: list[WebPageChunk] = []
    execution_time: float | None = None
    num_chunks_in_final_prompts: int = 0

    def model_dump(self, *, with_debug_details: bool = True, **kwargs):
        """
        Dump the model, dropping `additional_info` in steps when debug=False.
        """
        exclude = kwargs.pop("exclude", {})
        if not with_debug_details:
            # Build an exclude structure that applies to all steps
            exclude = {
                "steps": {i: {"extra"} for i in range(len(self.steps))},
                "web_page_chunks": True,
            } | exclude
        return super().model_dump(exclude=exclude, **kwargs)
