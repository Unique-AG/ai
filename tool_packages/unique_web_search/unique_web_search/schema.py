from enum import StrEnum
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, create_model


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
