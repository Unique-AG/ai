from typing import Annotated

from pydantic import BaseModel, Field
from unique_toolkit._common.pydantic.rjsf_tags import RJSFMetaTag
from unique_toolkit._common.pydantic_helpers import get_configuration_dict

from unique_web_search.services.argument_screening.prompts import (
    DEFAULT_GUIDELINES,
    DEFAULT_SYSTEM_PROMPT,
    DEFAULT_USER_PROMPT_TEMPLATE,
)


class ArgumentScreeningConfig(BaseModel):
    model_config = get_configuration_dict()

    enabled: bool = Field(
        default=False,
        title="Enable Argument Screening",
        description=(
            "When enabled, an LLM agent screens tool call arguments for "
            "sensitive information before execution. Requires the associated "
            "feature flag to be active."
        ),
    )
    guidelines: Annotated[
        str,
        RJSFMetaTag.StringWidget.textarea(rows=10),
    ] = Field(
        default=DEFAULT_GUIDELINES,
        title="Screening Guidelines",
        description="Rules the screening agent follows to decide whether arguments are safe. This is the primary field for administrators to customize.",
    )
    system_prompt: Annotated[
        str,
        RJSFMetaTag.StringWidget.textarea(rows=4),
    ] = Field(
        default=DEFAULT_SYSTEM_PROMPT,
        title="System Prompt",
        description="System prompt that defines the screening agent's role and behavior.",
    )
    user_prompt_template: Annotated[
        str,
        RJSFMetaTag.StringWidget.textarea(rows=6),
    ] = Field(
        default=DEFAULT_USER_PROMPT_TEMPLATE,
        title="User Prompt Template",
        description=(
            "Template for the user message sent to the screening agent. "
            "Use {{ arguments }} for the serialized tool call arguments "
            "and {{ guidelines }} for the guidelines text."
        ),
    )
