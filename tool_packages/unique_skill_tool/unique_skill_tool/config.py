from __future__ import annotations

from typing import Annotated

from pydantic import BaseModel, Field
from unique_toolkit._common.pydantic.rjsf_tags import CustomWidgetName, RJSFMetaTag
from unique_toolkit._common.pydantic_helpers import get_configuration_dict
from unique_toolkit.agentic.tools.schemas import BaseToolConfig

from unique_skill_tool.prompts import (
    DEFAULT_TOOL_DESCRIPTION,
    DEFAULT_TOOL_DESCRIPTION_FOR_SYSTEM_PROMPT,
    DEFAULT_TOOL_DESCRIPTION_FOR_USER_PROMPT,
    DEFAULT_TOOL_PARAMETER_ARGUMENTS_DESCRIPTION,
    DEFAULT_TOOL_PARAMETER_SKILL_NAME_DESCRIPTION,
    DEFAULT_TOOL_SYSTEM_REMINDER_FOR_USER_MESSAGE,
)
from unique_skill_tool.schemas import SkillReference

CHARS_PER_TOKEN = 4
DEFAULT_CHAR_BUDGET = 8_000
SKILL_BUDGET_CONTEXT_PERCENT = 0.03
MAX_LISTING_DESC_CHARS = 250


class SkillSelection(BaseModel):
    """Operator-curated set of skills, plus the folder they were picked from.

    Bundles the picker's two pieces of state — the root folder being browsed
    and the explicit list of selected skills — so the SKILLS_PICKER widget
    sees them as a single object.
    """

    model_config = get_configuration_dict()

    source_folder_id: str = Field(
        default="",
        description="The root skills folder ID.",
    )
    selected: list[SkillReference] = Field(
        default_factory=list,
        description="Individual skills selected from the knowledge base.",
    )


class SkillToolConfig(BaseToolConfig):
    """Configuration for the Skill tool."""

    tool_description: Annotated[
        str,
        RJSFMetaTag.StringWidget.textarea(rows=3),
    ] = Field(
        default=DEFAULT_TOOL_DESCRIPTION,
        description="The LLM-facing description of the Skill tool.",
    )

    tool_description_for_system_prompt: Annotated[
        str,
        RJSFMetaTag.StringWidget.textarea(rows=7),
    ] = Field(
        default=DEFAULT_TOOL_DESCRIPTION_FOR_SYSTEM_PROMPT,
        description="Instructions for the system prompt explaining how to use skills.",
    )

    tool_description_for_user_prompt: Annotated[
        str,
        RJSFMetaTag.StringWidget.textarea(rows=5),
    ] = Field(
        default=DEFAULT_TOOL_DESCRIPTION_FOR_USER_PROMPT,
        description=(
            "Optional extra text appended to the per-turn user-message injection.."
        ),
    )

    tool_system_reminder_for_user_message: Annotated[
        str,
        RJSFMetaTag.StringWidget.textarea(rows=5),
    ] = Field(
        default=DEFAULT_TOOL_SYSTEM_REMINDER_FOR_USER_MESSAGE,
        description=(
            "Per-turn ``<system-reminder>`` template injected into the "
            "user message. Jinja variable ``skill_list`` is rendered "
            "with the budget-aware skill listing. Refreshed every loop "
            "iteration."
        ),
    )

    tool_parameter_description_skill_name: Annotated[
        str,
        RJSFMetaTag.StringWidget.textarea(rows=2),
    ] = Field(
        default=DEFAULT_TOOL_PARAMETER_SKILL_NAME_DESCRIPTION,
        description="The description of the 'skill_name' parameter.",
    )

    tool_parameter_description_arguments: Annotated[
        str,
        RJSFMetaTag.StringWidget.textarea(rows=2),
    ] = Field(
        default=DEFAULT_TOOL_PARAMETER_ARGUMENTS_DESCRIPTION,
        description="The description of the 'arguments' parameter.",
    )

    selectable_skills: Annotated[
        SkillSelection,
        RJSFMetaTag.CustomWidget.custom(CustomWidgetName.SKILLS_PICKER),
    ] = Field(
        default_factory=lambda: SkillSelection(),
        title="Selected Skills",
        description="Skills selected from the knowledge base.",
    )

    max_listing_desc_chars: int = Field(
        default=MAX_LISTING_DESC_CHARS,
        ge=20,
        le=1000,
        description=(
            "Per-entry hard cap on skill descriptions in the listing. "
            "The listing is for discovery only — the tool loads full "
            "content on invoke."
        ),
    )

    skill_budget_context_percent: float = Field(
        default=SKILL_BUDGET_CONTEXT_PERCENT,
        ge=0.01,
        le=0.15,
        description="Percentage of context window allocated for the skill listing.",
    )
