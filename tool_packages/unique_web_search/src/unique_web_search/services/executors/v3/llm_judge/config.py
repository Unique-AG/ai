from typing import Annotated

from pydantic import BaseModel, Field
from unique_toolkit._common.pydantic.rjsf_tags import RJSFMetaTag
from unique_toolkit._common.pydantic_helpers import get_configuration_dict

from unique_web_search.services.executors.v3.llm_judge.prompts import (
    DEFAULT_V3_SEARCH_OUTCOME_JUDGE_SYSTEM,
    DEFAULT_V3_SEARCH_OUTCOME_JUDGE_USER_TEMPLATE,
)


class V3LlmJudgeConfig(BaseModel):
    """Optional LLM judge after V3 `search`: fetch recommendation + follow-up queries."""

    model_config = get_configuration_dict()

    enabled: bool = Field(
        default=True,
        title="Enable V3 search-outcome judge",
        description=(
            "When enabled, after each V3 `search` an LLM reviews snippets vs the objective "
            "and records a verdict (debug) including whether to recommend `fetch_urls` "
            "and suggested follow-up search queries."
        ),
    )
    system_prompt: Annotated[
        str,
        RJSFMetaTag.StringWidget.textarea(rows=8),
    ] = Field(
        default=DEFAULT_V3_SEARCH_OUTCOME_JUDGE_SYSTEM,
        title="Judge system prompt",
        description="System message for the search-outcome judge.",
    )
    user_prompt_template: Annotated[
        str,
        RJSFMetaTag.StringWidget.textarea(rows=8),
    ] = Field(
        default=DEFAULT_V3_SEARCH_OUTCOME_JUDGE_USER_TEMPLATE,
        title="Judge user prompt template",
        description=(
            "Jinja2 template for the user message. Variables: objective, numbered_results."
        ),
    )
