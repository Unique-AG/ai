from enum import StrEnum
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, create_model
from unique_toolkit._common.utils.structured_output.schema import StructuredOutputModel


class RefinedQuery(StructuredOutputModel):
    """A refined query."""

    optimized_query: str = Field(description="The refined query.")


class WebSearchToolParameters(BaseModel):
    """Parameters for the Websearch tool."""

    model_config = ConfigDict(extra="forbid")
    query: str
    date_restrict: str | None

    @classmethod
    def from_tool_parameter_query_description(
        cls, query_description: str, date_restrict_description: str
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


class SearchStep(BaseModel):
    model_config = ConfigDict(extra="forbid")
    step_type: Literal[StepType.SEARCH]
    objective: str = Field(description="The objective of the step")
    query: str = Field(description="Optimized query to send to the search engine")


class ReadUrlStep(BaseModel):
    model_config = ConfigDict(extra="forbid")
    step_type: Literal[StepType.READ_URL]
    objective: str = Field(description="The objective of the step")
    url: str = Field(description="URL to read")


STEP_TYPES = SearchStep | ReadUrlStep


class WebSearchPlan(BaseModel):
    model_config = ConfigDict(extra="forbid")
    objective: str = Field(description="The objective of the plan")
    query_analysis: str = Field(
        description="Analysis of the user's query and what information is needed"
    )
    steps: list[STEP_TYPES] = Field(description="Steps to execute")
    expected_outcome: str = Field(description="Expected outcome")
