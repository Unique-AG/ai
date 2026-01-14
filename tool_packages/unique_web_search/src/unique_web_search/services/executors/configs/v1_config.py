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
        description="The tool parameter query description",
    )
    date_restrict_description: Annotated[
        str,
        RJSFMetaTag.StringWidget.textarea(
            rows=len(RESTRICT_DATE_DESCRIPTION.split("\n"))
        ),
    ] = Field(
        default=RESTRICT_DATE_DESCRIPTION,
        description="The tool parameter date restrict description",
    )


class QueryRefinementConfig(BaseModel):
    model_config = get_configuration_dict()

    mode: RefineQueryMode = Field(
        default=RefineQueryMode.BASIC,
        description="The mode of the query refinement",
    )

    system_prompt: Annotated[
        str,
        RJSFMetaTag.StringWidget.textarea(
            rows=len(REFINE_QUERY_SYSTEM_PROMPT.split("\n"))
        ),
    ] = Field(
        default=REFINE_QUERY_SYSTEM_PROMPT,
        description="The system prompt to refine the query",
    )


class WebSearchV1Config(BaseWebSearchModeConfig[WebSearchMode.V1]):
    mode: SkipJsonSchema[Literal[WebSearchMode.V1]] = WebSearchMode.V1

    refine_query_mode: QueryRefinementConfig = Field(
        default_factory=QueryRefinementConfig,
        description="Query refinement strategy for WebSearch V1. Determines how user queries are improved before searching (e.g., BASIC, ADVANCED).",
    )

    max_queries: int = Field(
        default=5,
        description="Maximum number of search queries that WebSearch V1 will issue per user request. This parameter is only used if the refine query mode is set to ADVANCED.",
    )

    tool_parameters_description: WebSearchToolParametersDescriptionConfig = Field(
        default_factory=WebSearchToolParametersDescriptionConfig,
        description="The description of the tool parameters",
    )

    tool_description: Annotated[
        str,
        RJSFMetaTag.StringWidget.textarea(
            rows=int(len(DEFAULT_TOOL_DESCRIPTION["v1"].split("\n")))
        ),
    ] = Field(
        default=DEFAULT_TOOL_DESCRIPTION["v1"],
        description="Information to help the language model decide when to select this tool; describes the tool's general purpose and when it is relevant.",
    )
    tool_description_for_system_prompt: Annotated[
        str,
        RJSFMetaTag.StringWidget.textarea(
            rows=int(len(DEFAULT_TOOL_DESCRIPTION_FOR_SYSTEM_PROMPT["v1"].split("\n"))/2)
        ),
    ] = Field(
        default=DEFAULT_TOOL_DESCRIPTION_FOR_SYSTEM_PROMPT["v1"],
        description="Description of the tool's capabilities, intended for inclusion in system prompts to inform the language model what the tool can do.",
    )
