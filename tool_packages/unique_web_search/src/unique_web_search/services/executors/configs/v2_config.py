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
        description="Maximum number of sequential steps (searches or URL reads) allowed in a single WebSearch V2 plan.",
    )
    tool_description: Annotated[
        str,
        RJSFMetaTag.StringWidget.textarea(
            rows=len(DEFAULT_TOOL_DESCRIPTION["v2"].split("\n"))
        ),
    ] = Field(
        default=DEFAULT_TOOL_DESCRIPTION["v2"],
        description="Information to help the language model decide when to select this tool; describes the tool's general purpose and when it is relevant.",
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
        description="Description of the tool's capabilities, intended for inclusion in system prompts to inform the language model what the tool can do.",
    )

    @field_validator("mode", mode="before")
    @classmethod
    def validate_mode(cls, v: str) -> Literal["v2"]:
        if "v2" in v.lower():  # Make sure to handle "v2 (beta)" as well
            return "v2"
        raise ValueError(f"Invalid mode: {v}")
