from __future__ import annotations

from unique_skill_tool.config import (
    CHARS_PER_TOKEN,
    DEFAULT_CHAR_BUDGET,
    SkillToolConfig,
)
from unique_skill_tool.schemas import (
    SkillDefinition,
)

MIN_DESC_LENGTH = 20


def get_char_budget(
    context_window_tokens: int | None,
    config: SkillToolConfig,
) -> int:
    """Return the character budget for the skill listing.

    Uses *config.skill_budget_context_percent* of the context window
    (converted to characters via ``CHARS_PER_TOKEN``).  Falls back to
    ``DEFAULT_CHAR_BUDGET`` when the context window size is unknown.
    """
    if context_window_tokens:
        return int(
            context_window_tokens * CHARS_PER_TOKEN * config.skill_budget_context_percent
        )
    return DEFAULT_CHAR_BUDGET


def _get_skill_description(skill: SkillDefinition, max_chars: int) -> str:
    desc = (
        f"{skill.description} - {skill.when_to_use}"
        if skill.when_to_use
        else skill.description
    )
    if len(desc) > max_chars:
        return desc[: max_chars - 1] + "\u2026"
    return desc


def _format_entry(skill: SkillDefinition, max_desc_chars: int) -> str:
    return f"- {skill.name}: {_get_skill_description(skill, max_desc_chars)}"


def format_skill_listing(
    skills: list[SkillDefinition],
    context_window_tokens: int | None = None,
    config: SkillToolConfig | None = None,
) -> str:
    """Format the skill listing for the system prompt within a character budget.

    Ported from Claude Code's ``formatCommandsWithinBudget`` (prompt.ts).

    Strategy:
    1. Try full descriptions (capped at ``max_listing_desc_chars``).
    2. If over budget, uniformly truncate descriptions to fit.
    3. If truncation leaves less than ``MIN_DESC_LENGTH`` per entry, fall
       back to names only.
    """
    if not skills:
        return ""

    if config is None:
        config = SkillToolConfig()

    budget = get_char_budget(context_window_tokens, config)
    max_desc = config.max_listing_desc_chars

    full_entries = [_format_entry(skill, max_desc) for skill in skills]
    full_total = sum(len(e) for e in full_entries) + len(full_entries) - 1

    if full_total <= budget:
        return "\n".join(full_entries)

    name_overhead = sum(len(s.name) + 4 for s in skills) + len(skills) - 1
    available_for_descs = budget - name_overhead

    if len(skills) == 0:
        return ""

    max_desc_len = available_for_descs // len(skills)

    if max_desc_len < MIN_DESC_LENGTH:
        return "\n".join(f"- {s.name}" for s in skills)

    return "\n".join(
        f"- {s.name}: {_get_skill_description(s, max_desc_len)}" for s in skills
    )
