from __future__ import annotations

from pydantic import BaseModel, Field

SKILL_NAME_PATTERN = r"^[a-z0-9]+(?:-[a-z0-9]+)*$"
SKILL_NAME_MAX_LENGTH = 64


class SkillDefinition(BaseModel):
    """A skill that the agent can activate via the SkillTool.

    Skills are prompt instruction sets loaded from the knowledge base.
    The listing (name + description) is shown to the LLM for discovery;
    the full ``content`` is only returned when the skill is actually
    invoked.
    """

    name: str = Field(
        description=(
            "Unique identifier for the skill (used as the tool parameter value). "
            "Must be lowercase kebab-case (a-z, 0-9, hyphens), 1-64 chars."
        ),
        min_length=1,
        max_length=SKILL_NAME_MAX_LENGTH,
        pattern=SKILL_NAME_PATTERN,
    )
    description: str = Field(
        description="Short description shown in the skill listing for the LLM.",
    )
    content: str = Field(
        description="Full prompt / instructions injected when the skill is invoked.",
    )
