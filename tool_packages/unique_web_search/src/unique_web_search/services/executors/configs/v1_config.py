from enum import StrEnum
from typing import Annotated, Literal

from pydantic import BaseModel, Field
from pydantic.json_schema import SkipJsonSchema
from unique_toolkit._common.pydantic.rjsf_tags import RJSFMetaTag
from unique_toolkit.agentic.tools.config import get_configuration_dict

from unique_web_search.services.executors.configs.base import (
    BaseWebSearchModeConfig,
    WebSearchMode,
)
from unique_web_search.services.executors.configs.prompts import (
    DEFAULT_TOOL_DESCRIPTION,
    DEFAULT_TOOL_DESCRIPTION_FOR_SYSTEM_PROMPT,
    REFINE_QUERY_SYSTEM_PROMPT,
    RESTRICT_DATE_DESCRIPTION,
)


class RefineQueryMode(StrEnum):
    BASIC = "Basic"
    ADVANCED = "Advanced (Beta)"
    DEACTIVATED = "Deactivated"


_DEFAULT_QUERY_DESCRIPTION = "The search query to issue to the web."


class WebSearchToolParametersDescriptionConfig(BaseModel):
    model_config = get_configuration_dict()

    query_description: Annotated[
        str,
        RJSFMetaTag.StringWidget.textarea(
            rows=len(_DEFAULT_QUERY_DESCRIPTION.split("\n"))
        ),
    ] = Field(
        default=_DEFAULT_QUERY_DESCRIPTION,
        title="Query Parameter Description",
        description="Advanced: Description of the search query parameter shown to the AI model.",
    )
    date_restrict_description: Annotated[
        str,
        RJSFMetaTag.StringWidget.textarea(
            rows=len(RESTRICT_DATE_DESCRIPTION.split("\n"))
        ),
    ] = Field(
        default=RESTRICT_DATE_DESCRIPTION,
        title="Date Filter Description",
        description="Advanced: Description of the date restriction parameter shown to the AI model.",
    )


class QueryRefinementConfig(BaseModel):
    model_config = get_configuration_dict()

    mode: RefineQueryMode = Field(
        default=RefineQueryMode.BASIC,
        title="Refinement Mode",
        description="Basic: simple query cleanup. Advanced: AI-powered query optimization. Deactivated: use the original query as-is.",
    )

    system_prompt: Annotated[
        str,
        RJSFMetaTag.StringWidget.textarea(
            rows=len(REFINE_QUERY_SYSTEM_PROMPT.split("\n"))
        ),
    ] = Field(
        default=REFINE_QUERY_SYSTEM_PROMPT,
        title="Refinement Instructions",
        description="Advanced: Instructions for the AI on how to optimize search queries.",
    )


class WebSearchV1Config(BaseWebSearchModeConfig[WebSearchMode.V1]):
    mode: SkipJsonSchema[Literal[WebSearchMode.V1]] = WebSearchMode.V1

    refine_query_mode: QueryRefinementConfig = Field(
        default_factory=QueryRefinementConfig,
        title="Query Refinement",
        description="Controls how user questions are optimized before searching. Basic mode does simple cleanup; Advanced mode uses AI to generate better search queries.",
    )

    max_queries: int = Field(
        default=5,
        title="Maximum Search Queries",
        description="Maximum number of separate searches to run per user request. Only applies when Query Refinement is set to Advanced.",
    )

    tool_parameters_description: WebSearchToolParametersDescriptionConfig = Field(
        default_factory=WebSearchToolParametersDescriptionConfig,
        title="Search Parameter Descriptions",
        description="Advanced: Descriptions of each search parameter, shown to the AI model.",
    )

    tool_description: Annotated[
        str,
        RJSFMetaTag.StringWidget.textarea(
            rows=int(len(DEFAULT_TOOL_DESCRIPTION["v1"].split("\n")))
        ),
    ] = Field(
        default=DEFAULT_TOOL_DESCRIPTION["v1"],
        title="Tool Description",
        description="Advanced: Description that helps the AI model decide when to use web search.",
    )
    tool_description_for_system_prompt: Annotated[
        str,
        RJSFMetaTag.StringWidget.textarea(
            rows=int(
                len(DEFAULT_TOOL_DESCRIPTION_FOR_SYSTEM_PROMPT["v1"].split("\n")) / 2
            )
        ),
    ] = Field(
        default=DEFAULT_TOOL_DESCRIPTION_FOR_SYSTEM_PROMPT["v1"],
        title="Tool Usage Instructions",
        description="Advanced: Detailed instructions for the AI model on how and when to use web search.",
    )
