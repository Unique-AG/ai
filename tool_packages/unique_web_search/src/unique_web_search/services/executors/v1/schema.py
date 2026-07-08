"""V1 WebSearch tool parameters (single-query tool call)."""

from typing import Any, cast

from pydantic import BaseModel, ConfigDict, Field, create_model

from unique_web_search.services.executors.exposed_params import (
    attach_exposed_schema_cleanup,
)


class WebSearchToolParameters(BaseModel):
    """Parameters for the Websearch tool."""

    model_config = ConfigDict(extra="forbid")
    query: str

    @classmethod
    def with_exposed_fields(
        cls,
        exposed_field_defs: dict[str, tuple[Any, Any]] | None,
        *,
        query_description: str,
    ) -> type["WebSearchToolParameters"]:
        """Build tool parameters with ``query`` plus flat engine-exposed fields."""
        field_defs: dict[str, tuple[Any, Any]] = {
            "query": (str, Field(description=query_description)),
        }
        exposed_names: list[str] = []
        if exposed_field_defs:
            exposed_names = list(exposed_field_defs.keys())
            field_defs.update(exposed_field_defs)

        model = create_model(
            cls.__name__,
            __base__=cls,
            **cast(Any, field_defs),
        )
        return cast(
            type[WebSearchToolParameters],
            attach_exposed_schema_cleanup(model, exposed_names),
        )

    @classmethod
    def from_tool_parameter_query_description(
        cls,
        query_description: str,
        date_restrict_description: str | None = None,
    ) -> type["WebSearchToolParameters"]:
        """Create a model with a custom ``query`` description (legacy entry point)."""
        _ = date_restrict_description
        return cls.with_exposed_fields(None, query_description=query_description)
