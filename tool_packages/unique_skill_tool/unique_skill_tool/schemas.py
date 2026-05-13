from __future__ import annotations

from pydantic import BaseModel, Field
from unique_toolkit._common.pydantic_helpers import get_configuration_dict

SKILL_NAME_PATTERN = r"^[a-z0-9]+(?:-[a-z0-9]+)*$"
SKILL_NAME_MAX_LENGTH = 64


class SelectableSkill(BaseModel):
    """A specific skill file selected by reference from the knowledge base.

    Each entry resolves to exactly one knowledge base document via its
    ``content_id``; ``scope_id`` scopes the lookup so access is explicit,
    and ``name`` is the skill file's own frontmatter name.
    """

    model_config = get_configuration_dict()

    name: str = Field(
        default="",
        description=("Skill name"),
    )
    scope_id: str = Field(
        default="",
        description="Knowledge base scope ID that contains the skill file.",
    )
    content_id: str = Field(
        default="",
        description="Knowledge base content ID of the ``SKILL.md`` file.",
    )


class SkillDefinition(BaseModel):
    """A skill that the agent can activate via the SkillTool.

    Skills are prompt instruction sets loaded from the knowledge base.
    The listing (name + description) is shown to the LLM for discovery;
    the full ``content`` is only returned when the skill is actually
    invoked.
    """

    model_config = get_configuration_dict()

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
    source_content_id: str = Field(
        default="",
        description=(
            "Knowledge base content id this definition was loaded from; "
            "used to match per-message skill choices that omit ``name``."
        ),
    )
