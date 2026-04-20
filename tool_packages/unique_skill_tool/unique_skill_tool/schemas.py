from __future__ import annotations

from pydantic import BaseModel, Field


class SkillDefinition(BaseModel):
    """A skill that the agent can activate via the SkillTool.

    Skills are prompt instruction sets loaded from the knowledge base.
    The listing (name + description + when_to_use) is shown to the LLM
    for discovery; the full ``content`` is only returned when the skill
    is actually invoked.
    """

    name: str = Field(
        description="Unique identifier for the skill (used as the tool parameter value).",
    )
    description: str = Field(
        description="Short description shown in the skill listing for the LLM.",
    )
    when_to_use: str = Field(
        default="",
        description=(
            "Additional context for when the LLM should activate this skill. "
            "Appended to the description in the listing."
        ),
    )
    content: str = Field(
        description="Full prompt / instructions injected when the skill is invoked.",
    )
