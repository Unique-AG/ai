"""Helpers for the experimental Skill tool.

Loads skill definitions from the knowledge base and registers the
SkillTool with the tool manager.

Skill files are ``.md`` documents with optional YAML frontmatter::

    ---
    name: summarize-report
    description: >-
      Summarize a document into key findings.
      Use when the user asks for a summary or overview.
    ---

    # Summarize Report
    ...instructions...

The frontmatter fields are used for the skill listing shown to the
LLM.  The body (everything after the frontmatter) is the prompt
content injected when the skill is invoked.
"""

from __future__ import annotations

from logging import Logger
from pathlib import PurePosixPath
from typing import TYPE_CHECKING, Any

import yaml
from unique_skill_tool.schemas import SkillDefinition
from unique_skill_tool.service import SkillTool
from unique_toolkit.content.schemas import Content

if TYPE_CHECKING:
    from unique_toolkit.agentic.tools.tool_manager import (
        ResponsesApiToolManager,
        ToolManager,
    )
    from unique_toolkit.app.schemas import ChatEvent
    from unique_toolkit.content.service import ContentService

    from unique_orchestrator.config import UniqueAIConfig


def _is_markdown(content: Content) -> bool:
    return content.key.lower().endswith(".md")


def _parse_frontmatter(text: str) -> tuple[dict[str, Any], str]:
    """Split YAML frontmatter from the markdown body.

    Returns ``(frontmatter_dict, body)``.  If no frontmatter is found,
    the dict is empty and the full text is returned as the body.
    """
    if not text.startswith("---"):
        return {}, text

    parts = text.split("---", 2)
    if len(parts) < 3:
        return {}, text

    try:
        fm = yaml.safe_load(parts[1])
    except yaml.YAMLError:
        return {}, text

    if not isinstance(fm, dict):
        return {}, text

    body = parts[2].lstrip("\n")
    return fm, body


def _build_skill(
    content: Content,
    file_text: str,
) -> SkillDefinition | None:
    """Build a ``SkillDefinition`` from the raw file text of a KB document.

    Parses YAML frontmatter for ``name`` and ``description``.
    Falls back to KB-level ``content.metadata``, then to the file stem
    for the name.  The legacy ``skill_name`` key is still accepted as a
    fallback for backward compatibility.
    """
    if not file_text.strip():
        return None

    kb_meta = content.metadata or {}
    frontmatter, body = _parse_frontmatter(file_text)

    name = (
        frontmatter.get("name")
        or frontmatter.get("skill_name")
        or kb_meta.get("name")
        or kb_meta.get("skill_name")
        or content.title
        or PurePosixPath(content.key).stem
        or content.id
    )

    description = frontmatter.get("description") or kb_meta.get("description") or ""

    return SkillDefinition(
        name=name,
        description=description,
        content=body or file_text,
    )


def load_skills_from_knowledge_base(
    content_service: ContentService,
    scope_id: str,
    logger: Logger,
) -> dict[str, SkillDefinition]:
    """Load all ``.md`` files from *scope_id* and return them as a skill registry.

    For each markdown document found in the scope, the raw file is
    downloaded via ``download_content_to_bytes`` and parsed for YAML
    frontmatter + body content.
    """
    try:
        contents = content_service.search_contents(
            where={
                "ownerId": {"equals": scope_id},
            },
        )
    except Exception:
        logger.warning(
            "Failed to list contents in scope_id=%s — "
            "SkillTool will have an empty registry.",
            scope_id,
            exc_info=True,
        )
        return {}

    md_contents = [c for c in contents if _is_markdown(c)]
    if not md_contents:
        logger.info("No .md files found in scope_id=%s.", scope_id)
        return {}

    registry: dict[str, SkillDefinition] = {}
    for content in md_contents:
        try:
            raw_bytes = content_service.download_content_to_bytes(
                content_id=content.id,
            )
            file_text = raw_bytes.decode("utf-8")
        except Exception:
            logger.warning(
                "Failed to download '%s' (%s) — skipping.",
                content.key,
                content.id,
                exc_info=True,
            )
            continue

        skill = _build_skill(content, file_text)
        if skill is None:
            logger.debug(
                "Skipping '%s' (%s): empty file.",
                content.key,
                content.id,
            )
            continue

        if skill.name in registry:
            logger.warning(
                "Duplicate skill name '%s' — keeping the first occurrence.",
                skill.name,
            )
            continue

        registry[skill.name] = skill

    logger.info(
        "Loaded %d skill(s) from knowledge base (scope_id=%s).",
        len(registry),
        scope_id,
    )
    return registry


def configure_skill_tool(
    config: UniqueAIConfig,
    event: ChatEvent,
    logger: Logger,
    content_service: ContentService,
    tool_manager: ToolManager | ResponsesApiToolManager,
) -> None:
    """Register the SkillTool if enabled in the config.

    Lists all ``.md`` files in the configured ``scope_id``, downloads
    each one, and registers the SkillTool with the parsed skills.
    """
    skill_config = config.agent.experimental.skill_tool_config
    if not skill_config.enabled:
        return

    if not skill_config.scope_id:
        logger.warning(
            "SkillTool is enabled but no scope_id is configured — "
            "no skills will be loaded."
        )
        return

    registry = load_skills_from_knowledge_base(
        content_service, skill_config.scope_id, logger
    )

    tool_manager.add_tool(
        SkillTool(
            event=event,
            registry=registry,
            config=skill_config,
        )
    )
