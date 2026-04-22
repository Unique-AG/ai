from __future__ import annotations

from typing import Annotated

from pydantic import Field
from unique_toolkit._common.pydantic.rjsf_tags import RJSFMetaTag
from unique_toolkit.agentic.tools.schemas import BaseToolConfig

from unique_skill_tool.prompts import (
    DEFAULT_TOOL_DESCRIPTION,
    DEFAULT_TOOL_DESCRIPTION_FOR_SYSTEM_PROMPT,
    DEFAULT_TOOL_DESCRIPTION_FOR_USER_PROMPT,
    DEFAULT_TOOL_PARAMETER_ARGUMENTS_DESCRIPTION,
    DEFAULT_TOOL_PARAMETER_SKILL_NAME_DESCRIPTION,
    DEFAULT_TOOL_SYSTEM_REMINDER_FOR_USER_MESSAGE,
)

CHARS_PER_TOKEN = 4
DEFAULT_CHAR_BUDGET = 8_000
SKILL_BUDGET_CONTEXT_PERCENT = 0.03
MAX_LISTING_DESC_CHARS = 250


class SkillToolConfig(BaseToolConfig):
    """Configuration for the Skill tool."""

    enabled: Annotated[
        bool,
        RJSFMetaTag.BooleanWidget.checkbox(
            help=(
                "Master switch for the Skill tool. When disabled, the tool "
                "is not registered and skills are not available to the agent."
            ),
        ),
    ] = Field(
        default=False,
        description="Enable the Skill tool.",
    )

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

    scope_ids: list[str] = Field(
        default_factory=list,
        title="Scope IDs",
        description=(
            "Knowledge base scope IDs to load skills from. Only the "
            "scopes listed here are queried — sub-folders are not "
            "traversed automatically, so add each scope you want "
            "searched explicitly."
        ),
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
