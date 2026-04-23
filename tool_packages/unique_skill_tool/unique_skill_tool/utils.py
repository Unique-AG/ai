from __future__ import annotations

import re

from unique_skill_tool.config import (
    CHARS_PER_TOKEN,
    DEFAULT_CHAR_BUDGET,
    SkillToolConfig,
)
from unique_skill_tool.schemas import (
    SkillDefinition,
)

MIN_DESC_LENGTH = 20

_SKILL_PREFIX_TOKEN_RE = re.compile(r"\A\s*/([A-Za-z0-9][A-Za-z0-9_-]*)(?=\s|\Z)")


def get_char_budget(
    context_window_tokens: int | None,
    config: SkillToolConfig,
) -> int:
    """Return the character budget for the skill listing.

    Uses *config.skill_budget_context_percent* of the context window
    (converted to characters via ``CHARS_PER_TOKEN``).  Falls back to
    ``DEFAULT_CHAR_BUDGET`` when the context window size is unknown.
    """
    if context_window_tokens is not None:
        return int(
            context_window_tokens
            * CHARS_PER_TOKEN
            * config.skill_budget_context_percent
        )
    return DEFAULT_CHAR_BUDGET


def _get_skill_description(skill: SkillDefinition, max_chars: int) -> str:
    desc = skill.description
    if len(desc) > max_chars:
        return desc[: max_chars - 3] + "..."
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
    max_desc_len = available_for_descs // len(skills)

    if max_desc_len < MIN_DESC_LENGTH:
        return "\n".join(f"- {s.name}" for s in skills)

    return "\n".join(
        f"- {s.name}: {_get_skill_description(s, max_desc_len)}" for s in skills
    )


def normalize_skill_name(skill: str) -> str:
    """Strip whitespace and a leading ``/`` from a skill name."""
    skill = skill.strip()
    if skill.startswith("/"):
        return skill[1:]
    return skill


def extract_prefix_skills(
    user_text: str,
    skill_registry: dict[str, SkillDefinition],
) -> tuple[list[SkillDefinition], str]:
    """Pull consecutive ``/skill-name`` tokens from the very start of *user_text*.

    Matches only tokens at the beginning of the message (after optional
    leading whitespace). Matching stops at the first non-token or unknown
    skill name, so ``/``-prefixed words appearing mid-message (URLs, code,
    prose) are ignored.

    Duplicates are dropped while preserving first-occurrence order.

    Returns ``(ordered_skills, remaining_text)`` where *remaining_text* is
    the original message with the matched prefix tokens stripped and
    leading whitespace removed.
    """
    remaining = user_text
    ordered: list[SkillDefinition] = []
    seen: set[str] = set()

    while True:
        match = _SKILL_PREFIX_TOKEN_RE.match(remaining)
        if match is None:
            break
        name = match.group(1)
        skill = skill_registry.get(name)
        if skill is None:
            break
        if name not in seen:
            seen.add(name)
            ordered.append(skill)
        remaining = remaining[match.end() :]

    return ordered, remaining.lstrip()
