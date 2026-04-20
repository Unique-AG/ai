from __future__ import annotations

from typing import Annotated

from pydantic import Field

from unique_toolkit._common.pydantic.rjsf_tags import RJSFMetaTag
from unique_toolkit.agentic.tools.schemas import BaseToolConfig

DEFAULT_TOOL_DESCRIPTION = (
    "PRIORITY TOOL — call FIRST before any other tool when a skill matches. "
    "Execute a skill to activate specialized capabilities and domain knowledge. "
    "When a skill matches the user's request, this is a BLOCKING REQUIREMENT: "
    "invoke the Skill tool BEFORE calling any other tool or generating any "
    "response. NEVER mention a skill without actually calling this tool."
)

DEFAULT_TOOL_DESCRIPTION_FOR_SYSTEM_PROMPT = (
    "You have access to the Skill tool which lets you activate specialized "
    "capabilities. Available skills are listed below.\n\n"
    "CRITICAL — Skill tool has HIGHEST PRIORITY among all tools:\n"
    "1. Before you call ANY other tool (InternalSearch, OpenFile, etc.) or "
    "generate ANY response, check if a skill matches the user's request.\n"
    "2. If a skill matches, you MUST invoke the Skill tool FIRST as your "
    "very first action. This is a BLOCKING REQUIREMENT — do not call other "
    "tools or produce text until the skill is loaded.\n"
    "3. NEVER mention a skill without actually calling the tool.\n"
    "4. Do not invoke a skill that is already active in the current turn "
    "(check for <skill_loaded> tags in the conversation).\n"
    "5. After the skill is loaded, follow its instructions directly. The "
    "skill may tell you to call other tools (e.g. InternalSearch) as part "
    "of its workflow — that is expected.\n\n"
    "How to invoke:\n"
    '- skill_name: "analyze-data" — invoke a skill by name\n'
    '- skill_name: "summarize", arguments: "focus on key metrics" — invoke with arguments'
)

DEFAULT_TOOL_PARAMETER_SKILL_NAME_DESCRIPTION = (
    "The name of the skill to invoke. Must be one of the available skills."
)

DEFAULT_TOOL_PARAMETER_ARGUMENTS_DESCRIPTION = (
    "Optional arguments or context to pass to the skill."
)

CHARS_PER_TOKEN = 4
DEFAULT_CHAR_BUDGET = 8_000
SKILL_BUDGET_CONTEXT_PERCENT = 0.01
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

    scope_id: str = Field(
        default="",
        description=(
            "Knowledge base scope ID to load skills from. "
            "All .md files within this scope are treated as skills. "
            "Leave empty to disable skill loading."
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
        ge=0.001,
        le=0.1,
        description="Percentage of context window allocated for the skill listing.",
    )
