"""Parse SKILL.md files into ``SkillDefinition`` objects.

Every skill is a folder with a ``SKILL.md`` entrypoint that carries YAML
frontmatter::

    ---
    name: summarize-report
    description: >-
      Summarize a document into key findings.
    metadata:           # optional
      thinking_level: high
    ---

    # Summarize Report
    ...instructions...

:func:`parse_skill_file` is the single public entry point: it accepts the raw
text of one ``SKILL.md`` file and returns a ``SkillDefinition``, or ``None``
when the file is empty or malformed.
"""

from __future__ import annotations

from logging import Logger
from typing import Any

import frontmatter
from pydantic import ValidationError

from unique_skill_tool.schemas import SkillDefinition, SkillMetadata
from unique_toolkit.language_model.schemas import to_reasoning_effort


def _parse_frontmatter(*, text: str) -> tuple[dict[str, Any], str]:
    """Split YAML frontmatter from the markdown body.

    Thin wrapper around ``python-frontmatter``. On a YAML parse error, or when
    the frontmatter parses to a non-mapping (e.g. a top-level YAML list), falls
    back to ``({}, <original text>)`` so a broken skill file never leaks raw
    ``---\\nname: ...\\n---`` delimiters into the LLM prompt and never raises.
    """
    try:
        post = frontmatter.loads(text)
        metadata = post.metadata
        body = post.content
    except Exception:
        return {}, text

    if not isinstance(metadata, dict):
        return {}, body

    return dict(metadata), body


def parse_skill_file(
    *,
    file_text: str,
    source_label: str = "",
    logger: Logger | None = None,
) -> SkillDefinition | None:
    """Build a ``SkillDefinition`` from the raw text of a SKILL.md file.

    Parses YAML frontmatter for ``name`` and ``description``. A malformed
    ``name`` (non-kebab-case, contains whitespace/punctuation, too long) is
    rejected by ``SkillDefinition`` validation rather than silently flowing into
    the OpenAI tool enum where the model could never emit it verbatim.

    Args:
        file_text: Raw UTF-8 text of the SKILL.md file.
        source_label: Human-readable identifier used only in warning messages
            so callers can locate the offending file (e.g. a knowledge-base
            content key or file path).
        logger: Optional logger for diagnostic warnings. Pass ``None`` to
            suppress all log output (useful in tests).

    Returns:
        A validated ``SkillDefinition``, or ``None`` when the file is empty,
        missing required frontmatter fields, or fails schema validation.
    """
    if not file_text.strip():
        return None

    metadata, body = _parse_frontmatter(text=file_text)

    name = metadata.get("name")
    description = metadata.get("description")

    if not name or not description:
        if logger is not None:
            logger.warning(
                "Skipping '%s': wrong skill format.",
                source_label,
            )
        return None

    skill_meta: SkillMetadata | None = None
    raw_meta = metadata.get("metadata")
    if raw_meta is not None and not isinstance(raw_meta, dict):
        if logger is not None:
            logger.warning(
                "Skill '%s': 'metadata' must be a key-value mapping, got %r — ignoring.",
                source_label,
                type(raw_meta).__name__,
            )
        raw_meta = None
    if raw_meta is not None:
        raw_thinking = raw_meta.get("thinking_level")
        thinking_level = None
        if raw_thinking is not None:
            try:
                thinking_level = to_reasoning_effort(str(raw_thinking))
            except ValueError:
                if logger is not None:
                    logger.warning(
                        "Skill '%s': unknown thinking_level %r — ignoring.",
                        source_label,
                        raw_thinking,
                    )
        skill_meta = SkillMetadata(thinking_level=thinking_level)

    try:
        return SkillDefinition(
            name=name,
            description=description,
            content=body,
            metadata=skill_meta,
        )
    except ValidationError as exc:
        if logger is not None:
            logger.warning(
                "Skipping '%s': invalid skill definition: %s",
                source_label,
                exc.errors(include_url=False),
            )
        return None
