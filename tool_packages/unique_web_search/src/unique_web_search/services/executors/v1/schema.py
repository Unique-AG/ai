"""V1 WebSearch tool parameters (single-query tool call)."""

from typing import Any

from pydantic import ConfigDict, Field
from unique_search_proxy_core.search_engines.call_schema import (
    ExposedToolParameterModel,
)


class WebSearchToolParameters(ExposedToolParameterModel):
    """Parameters for the Websearch tool."""

    model_config = ConfigDict(extra="forbid", populate_by_name=True)
    query: str

    @classmethod
    def with_exposed_fields(
        cls,
        exposed_field_defs: dict[str, tuple[Any, Any]] | None,
        *,
        query_description: str,
    ) -> type["WebSearchToolParameters"]:
        """Build tool parameters with ``query`` plus flat engine-exposed fields."""
        return super().with_exposed_fields(
            exposed_field_defs,
            extra_field_defs={
                "query": (str, Field(description=query_description)),
            },
        )
