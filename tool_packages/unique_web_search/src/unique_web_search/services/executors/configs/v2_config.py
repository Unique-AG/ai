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


class WebSearchV2Config(BaseWebSearchModeConfig[WebSearchMode.V2]):
    model_config = get_configuration_dict(
        model_title_generator=clean_model_title_generator
    )
    mode: SkipJsonSchema[Literal[WebSearchMode.V2]] = WebSearchMode.V2

    max_steps: int = Field(
        default=5,
        title="Maximum Research Steps",
        description="Maximum number of sequential actions (searches or page reads) the AI can perform in a single research plan.",
    )
    tool_description: Annotated[
        str,
        RJSFMetaTag.StringWidget.textarea(
            rows=len(DEFAULT_TOOL_DESCRIPTION["v2"].split("\n"))
        ),
    ] = Field(
        default=DEFAULT_TOOL_DESCRIPTION["v2"],
        title="Tool Description",
        description="Advanced: Description that helps the AI model decide when to use web search.",
    )
    tool_description_for_system_prompt: Annotated[
        str,
        RJSFMetaTag.StringWidget.textarea(
            rows=int(
                len(DEFAULT_TOOL_DESCRIPTION_FOR_SYSTEM_PROMPT["v2"].split("\n")) / 2
            )
        ),
    ] = Field(
        default=DEFAULT_TOOL_DESCRIPTION_FOR_SYSTEM_PROMPT["v2"],
        title="Tool Usage Instructions",
        description="Advanced: Detailed instructions for the AI model on how to plan and execute web research.",
    )

    @field_validator("mode", mode="before")
    @classmethod
    def validate_mode(cls, v: str) -> Literal["v2"]:
        if "v2" in v.lower():  # Make sure to handle "v2 (beta)" as well
            return "v2"
        raise ValueError(f"Invalid mode: {v}")
