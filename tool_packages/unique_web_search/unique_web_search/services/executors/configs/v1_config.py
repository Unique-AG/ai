from enum import StrEnum
from typing import Literal

from pydantic import BaseModel, Field
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
    BASIC = "basic"
    ADVANCED = "advanced"
    DEACTIVATED = "deactivated"


class WebSearchToolParametersDescriptionConfig(BaseModel):
    model_config = get_configuration_dict()

    query_description: str = Field(
        default="The search query to issue to the web.",
        description="The tool parameter query description",
    )
    date_restrict_description: str = Field(
        default=RESTRICT_DATE_DESCRIPTION,
        description="The tool parameter date restrict description",
    )


class QueryRefinementConfig(BaseModel):
    model_config = get_configuration_dict()

    mode: RefineQueryMode = Field(
        default=RefineQueryMode.BASIC,
        description="The mode of the query refinement",
    )

    system_prompt: str = Field(
        default=REFINE_QUERY_SYSTEM_PROMPT,
        description="The system prompt to refine the query",
    )


class WebSearchV1Config(BaseWebSearchModeConfig[WebSearchMode.V1]):
    mode: Literal[WebSearchMode.V1] = WebSearchMode.V1

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

    tool_description: str = Field(
        default=DEFAULT_TOOL_DESCRIPTION["v1"],
        description="Information to help the language model decide when to select this tool; describes the tool's general purpose and when it is relevant.",
    )
    tool_description_for_system_prompt: str = Field(
        default=DEFAULT_TOOL_DESCRIPTION_FOR_SYSTEM_PROMPT["v1"],
        description="Description of the tool's capabilities, intended for inclusion in system prompts to inform the language model what the tool can do.",
    )
