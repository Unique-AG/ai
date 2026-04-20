from __future__ import annotations

from pydantic import BaseModel, Field


class SkillDefinition(BaseModel):
    """A skill that the agent can activate via the SkillTool.

    Skills are prompt instruction sets loaded from the knowledge base.
    The listing (name + description) is shown to the LLM for discovery;
    the full ``content`` is only returned when the skill is actually
    invoked.
    """

    name: str = Field(
        description="Unique identifier for the skill (used as the tool parameter value).",
    )
    description: str = Field(
        description="Short description shown in the skill listing for the LLM.",
    )
    content: str = Field(
        description="Full prompt / instructions injected when the skill is invoked.",
    )
