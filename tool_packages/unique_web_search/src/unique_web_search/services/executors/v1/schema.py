"""V1 WebSearch tool parameters (single-query tool call)."""

from __future__ import annotations

from pydantic import ConfigDict, Field, create_model
from pydantic.alias_generators import to_camel
from unique_search_proxy_core.param_policy.exposed_params import ExposedParams

_DEFAULT_QUERY_DESCRIPTION = "The search query to issue to the web."


class WebSearchToolParameters(ExposedParams):
    """Parameters for the Websearch tool."""

    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
        extra="forbid",
    )

    query: str = Field(description=_DEFAULT_QUERY_DESCRIPTION)

    @classmethod
    def with_exposed_params(
        cls,
        exposed: type[ExposedParams] | None,
    ) -> type[WebSearchToolParameters]:
        """Graft admin-exposed engine knobs onto the V1 tool-parameter model.

        Returns ``cls`` unchanged when nothing is exposed; otherwise builds a
        dynamic subclass via ``create_model(__base__=(cls, exposed))``.
        """
        if exposed is None:
            return cls
        return create_model(
            cls.__name__,
            __base__=(cls, exposed),
        )
