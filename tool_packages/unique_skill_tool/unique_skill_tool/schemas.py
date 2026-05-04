from __future__ import annotations

from pydantic import BaseModel, Field

SKILL_NAME_PATTERN = r"^[a-z0-9]+(?:-[a-z0-9]+)*$"
SKILL_NAME_MAX_LENGTH = 64


class SelectableSkill(BaseModel):
    """A specific skill selected from the knowledge base.

    Used alongside ``scope_ids`` to let operators pin individual
    ``SKILL.md`` files instead of (or in addition to) loading every
    skill under a scope. Each entry resolves to exactly one knowledge
    base document via its ``content_id``; ``scope_id`` scopes the
    lookup so access is explicit, and ``name`` is a human-readable
    label for admin UIs and logs.
    """

    name: str = Field(
        default="",
        description=("Skill name"),
        min_length=1,
        max_length=SKILL_NAME_MAX_LENGTH,
        pattern=SKILL_NAME_PATTERN,
    )
    scope_id: str = Field(
        description="Knowledge base scope ID that contains the skill file.",
        min_length=1,
    )
    content_id: str = Field(
        description="Knowledge base content ID of the ``SKILL.md`` file.",
        min_length=1,
    )


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
