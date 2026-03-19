"""Configuration for Web Search V3 (snippet judge + ranked crawl)."""

from typing import Annotated, Literal

from pydantic import Field, field_validator
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
)
from unique_web_search.services.helpers import clean_model_title_generator
from unique_web_search.services.snippet_judge import SnippetJudgeConfig


class WebSearchV3Config(BaseWebSearchModeConfig[WebSearchMode.V3]):
    """V3 mode: pre-filter search results by relevance (snippet judge) before crawling."""

    model_config = get_configuration_dict(
        model_title_generator=clean_model_title_generator
    )
    mode: SkipJsonSchema[Literal[WebSearchMode.V3]] = WebSearchMode.V3

    max_steps: int = Field(
        default=5,
        title="Maximum Research Steps",
        description="Maximum number of sequential actions (searches or page reads) in a single research plan.",
    )
    snippet_judge_config: SnippetJudgeConfig = Field(
        default_factory=SnippetJudgeConfig,
        title="Snippet Judge",
        description="Relevance filtering of search results before crawling (score + rank).",
    )
    tool_description: Annotated[
        str,
        RJSFMetaTag.StringWidget.textarea(
            rows=len(DEFAULT_TOOL_DESCRIPTION["v3"].split("\n"))
        ),
    ] = Field(
        default=DEFAULT_TOOL_DESCRIPTION["v3"],
        title="Tool Description",
        description="Advanced: Description that helps the AI model decide when to use web search.",
    )
    tool_description_for_system_prompt: Annotated[
        str,
        RJSFMetaTag.StringWidget.textarea(
            rows=int(
                len(DEFAULT_TOOL_DESCRIPTION_FOR_SYSTEM_PROMPT["v3"].split("\n")) / 2
            )
        ),
    ] = Field(
        default=DEFAULT_TOOL_DESCRIPTION_FOR_SYSTEM_PROMPT["v3"],
        title="Tool Usage Instructions",
        description="Advanced: Instructions for the AI on how to plan and execute web research (V3).",
    )

    @field_validator("mode", mode="before")
    @classmethod
    def validate_mode(cls, v: str) -> Literal["v3"]:
        if "v3" in v.lower():
            return "v3"
        raise ValueError(f"Invalid mode: {v}")
