"""Configuration for Web Search V3 (search SERP + fetch URLs)."""

from typing import Annotated, Literal

from pydantic import BaseModel, Field, field_validator
from pydantic.json_schema import SkipJsonSchema
from unique_toolkit._common.pydantic.rjsf_tags import RJSFMetaTag
from unique_toolkit._common.validators import LMI, get_LMI_default_field
from unique_toolkit.agentic.tools.config import get_configuration_dict

from unique_web_search.prompts import (
    DEFAULT_TOOL_FORMAT_INFORMATION_FOR_SYSTEM_PROMPT_V3,
)
from unique_web_search.services.executors.base_config import (
    BaseWebSearchModeConfig,
    WebSearchMode,
)
from unique_web_search.services.executors.v3.prompts import (
    DEFAULT_TOOL_DESCRIPTION,
    DEFAULT_TOOL_DESCRIPTION_FOR_SYSTEM_PROMPT,
)
from unique_web_search.services.helpers import clean_model_title_generator
from unique_web_search.settings import env_settings


class SerpFilterConfig(BaseModel):
    """LLM-based relevance filter applied to SERP results before returning them to the model.

    When enabled, each search call scores every result against the search ``objective``,
    ``query``, and ``gap``, drops results below ``min_score``, and keeps the top
    ``max_results`` (subject to ``max_results_per_domain``). Returns all original results
    unmodified on LLM failure so the caller does not silently lose URLs.
    """

    model_config = get_configuration_dict()

    enabled: bool = Field(
        default=True,
        title="Enable SERP Filter",
        description=(
            "Score and filter SERP results for relevance before returning them to the model. "
            "Removes low-quality hits (forum threads, stale news, off-topic pages) at the cost "
            "of one lightweight LLM call per search."
        ),
    )
    language_model: LMI = get_LMI_default_field(
        env_settings.web_search_default_language_model,
        title="Filter Language Model",
        description="AI model used to score and filter SERP results for relevance.",
    )
    max_results: int = Field(
        default=5,
        ge=1,
        title="Max Results After Filtering",
        description="Maximum number of SERP results to keep after the relevance filter.",
    )
    max_results_per_domain: int = Field(
        default=2,
        ge=1,
        title="Max Results per Domain",
        description="Hard cap on how many results from the same registered domain can be kept.",
    )
    min_score: float = Field(
        default=0.3,
        ge=0.0,
        le=1.0,
        title="Minimum Relevance Score",
        description=(
            "Drop SERP results whose relevance score (0.0–1.0) is strictly below this "
            "threshold. Set higher (e.g. 0.5) to be aggressive about removing low-quality "
            "hits; set to 0.0 to keep top-k unconditionally."
        ),
    )


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
    serp_filter: SerpFilterConfig = Field(
        default_factory=SerpFilterConfig,
        title="SERP Relevance Filter",
        description="LLM-based filter that removes low-quality search results before the model sees them.",
    )

    @field_validator("mode", mode="before")
    @classmethod
    def validate_mode(cls, v: str) -> Literal["v3"]:
        if "v3" in v.lower():
            return "v3"
        raise ValueError(f"Invalid mode: {v}")
