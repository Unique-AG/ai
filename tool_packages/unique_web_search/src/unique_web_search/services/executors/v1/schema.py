"""V1 WebSearch tool parameters (single-query tool call)."""

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
