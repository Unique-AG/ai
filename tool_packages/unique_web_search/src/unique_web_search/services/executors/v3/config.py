"""Configuration for Web Search V3 (search SERP + fetch URLs)."""

from typing import Annotated, Literal

from pydantic import Field, field_validator
from pydantic.json_schema import SkipJsonSchema
from unique_toolkit._common.pydantic.rjsf_tags import RJSFMetaTag
from unique_toolkit.agentic.tools.config import get_configuration_dict

from unique_web_search.prompts import (
    DEFAULT_TOOL_FORMAT_INFORMATION_FOR_SYSTEM_PROMPT_V3,
)
from unique_web_search.services.executors.base_config import (
    BaseWebSearchModeConfig,
    WebSearchMode,
)
from unique_web_search.services.executors.v3.llm_judge.config import V3LlmJudgeConfig
from unique_web_search.services.executors.v3.prompts import (
    DEFAULT_TOOL_DESCRIPTION,
    DEFAULT_TOOL_DESCRIPTION_FOR_SYSTEM_PROMPT,
)
from unique_web_search.services.helpers import clean_model_title_generator


class WebSearchV3Config(BaseWebSearchModeConfig[WebSearchMode.V3]):
    """V3 mode: ``search`` returns SERP rows as JSON chunks; ``fetch_urls`` crawls and processes pages."""

    model_config = get_configuration_dict(
        model_title_generator=clean_model_title_generator
    )
    mode: SkipJsonSchema[Literal[WebSearchMode.V3]] = WebSearchMode.V3

    tool_description: Annotated[
        str,
        RJSFMetaTag.StringWidget.textarea(
            rows=len(DEFAULT_TOOL_DESCRIPTION.split("\n"))
        ),
    ] = Field(
        default=DEFAULT_TOOL_DESCRIPTION,
        title="Tool Description",
        description="Advanced: Description that helps the AI model decide when to use web search.",
    )
    tool_description_for_system_prompt: Annotated[
        str,
        RJSFMetaTag.StringWidget.textarea(
            rows=int(len(DEFAULT_TOOL_DESCRIPTION_FOR_SYSTEM_PROMPT.split("\n")) / 2)
        ),
    ] = Field(
        default=DEFAULT_TOOL_DESCRIPTION_FOR_SYSTEM_PROMPT,
        title="Tool Description for System Prompt",
        description="Advanced: Description that helps the AI model decide when to use web search (V3).",
    )
    tool_format_information_for_system_prompt: Annotated[
        str,
        RJSFMetaTag.StringWidget.textarea(
            rows=int(
                len(DEFAULT_TOOL_FORMAT_INFORMATION_FOR_SYSTEM_PROMPT_V3.split("\n"))
                / 3
            )
        ),
    ] = Field(
        default=DEFAULT_TOOL_FORMAT_INFORMATION_FOR_SYSTEM_PROMPT_V3,
        title="Tool Format Information For System Prompt",
        description="Advanced: Instructions that tell the AI how to cite web search sources in its answers (V3 includes domain diversity requirements).",
    )
    search_outcome_judge: V3LlmJudgeConfig = Field(
        default_factory=V3LlmJudgeConfig,
        title="V3 search-outcome judge",
        description=(
            "Optional LLM pass after `search`: whether snippets meet the objective, "
            "whether to recommend `fetch_urls`, and suggested follow-up search queries "
            "(stored in debug steps when enabled)."
        ),
    )

    @field_validator("mode", mode="before")
    @classmethod
    def validate_mode(cls, v: str) -> Literal["v3"]:
        if "v3" in v.lower():
            return "v3"
        raise ValueError(f"Invalid mode: {v}")
