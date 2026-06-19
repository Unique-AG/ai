from typing import Annotated

from pydantic import BaseModel, Field, field_validator
from unique_toolkit._common.pydantic.rjsf_tags import RJSFMetaTag
from unique_toolkit._common.pydantic_helpers import get_configuration_dict
from unique_toolkit._common.validators import LMI, get_LMI_default_field

from unique_web_search.services.argument_screening.prompts import (
    DEFAULT_GUIDELINES,
    DEFAULT_REJECTION_RESPONSE_TEMPLATE,
    DEFAULT_SYSTEM_PROMPT,
    DEFAULT_USER_PROMPT_TEMPLATE,
)
from unique_web_search.settings import env_settings

ORGANIZATION_SPECIFIC_BLOCKED_KEYWORDS_TEMPLATE = """{% for keyword in organization_specific_blocked_keywords -%}
- {{ keyword }}
{% else -%}
- [none configured]
{% endfor %}"""


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
    language_model: LMI = get_LMI_default_field(
        env_settings.web_search_default_language_model,
        title="Screening Language Model",
        description=(
            "AI model used by the screening agent to decide whether tool"
            " call arguments are safe to forward."
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
    organization_specific_blocked_keywords: Annotated[
        list[str],
        RJSFMetaTag({"ui:options": {"orderable": False}}),
    ] = Field(
        default_factory=list,
        title="Organization-Specific Blocked Keywords",
        description=(
            "Terms, domains, product names, portals, or internal project names "
            "that must always block WebSearch when detected."
        ),
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
    rejection_response_template: Annotated[
        str,
        RJSFMetaTag.StringWidget.textarea(rows=4),
    ] = Field(
        default=DEFAULT_REJECTION_RESPONSE_TEMPLATE,
        title="Rejection Response Template",
        description=(
            "Template for the tool response content when arguments are blocked. "
            "Use {{ reason }} for the screening agent's verdict reason."
        ),
    )

    @field_validator("guidelines")
    @classmethod
    def ensure_blocked_keywords_template(cls, guidelines: str) -> str:
        if "organization_specific_blocked_keywords" in guidelines:
            return guidelines

        separator = (
            "\n"
            if guidelines.rstrip().endswith("Configured blocked terms:")
            else "\n\nConfigured blocked terms:\n"
        )
        return (
            f"{guidelines.rstrip()}{separator}"
            f"{ORGANIZATION_SPECIFIC_BLOCKED_KEYWORDS_TEMPLATE}"
        )
