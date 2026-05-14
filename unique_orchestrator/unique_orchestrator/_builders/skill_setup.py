"""Helpers for the Skill tool.

Loads skill definitions from the knowledge base and registers the
SkillTool with the tool manager. Which files to load is determined only
by the per-message skill list: callers map ``ChatEventPayload.available_skills``
through ``message_skills_as_selectable`` before ``configure_skill_tool``.

Skill discovery follows the official Agent Skills protocol — see
https://agentskills.io/home. Each skill is a **folder**
that contains a ``SKILL.md`` entrypoint with required YAML frontmatter::

    <skill-folder>/
      SKILL.md          (required: name + description + body)
      scripts/          (optional: executable code)
      references/       (optional: documentation)
      assets/           (optional: templates, resources)
      ...               # Any additional files or directories

The ``SKILL.md`` body looks like::

    ---
    name: summarize-report
    description: >-
      Summarize a document into key findings.
      Use when the user asks for a summary or overview.
    ---

    # Summarize Report
    ...instructions...

Only files whose basename is ``SKILL.md`` (case-insensitive) are
treated as skill entrypoints. Any other ``.md`` files in a skill
folder (``references/*.md``, README, etc.) are ignored by the loader
— they are treated as assets, not separate skills. This matches the
"each skill is a folder" semantics of the official protocol.

The frontmatter fields are used for the skill listing shown to the
LLM. The body (everything after the frontmatter) is the prompt
content injected when the skill is invoked.
"""

from __future__ import annotations

import asyncio
from logging import Logger
from typing import TYPE_CHECKING, Any

import frontmatter
from pydantic import ValidationError
from unique_skill_tool.schemas import SkillReference, SkillDefinition
from unique_skill_tool.service import SkillTool
from unique_skill_tool.utils import normalize_skill_name
from unique_toolkit.agentic.tools.config import ToolBuildConfig
from unique_toolkit.agentic.tools.schemas import ToolCallResponse
from unique_toolkit.language_model.schemas import LanguageModelFunction

if TYPE_CHECKING:
    from unique_toolkit.agentic.history_manager.history_manager import HistoryManager
    from unique_toolkit.agentic.tools.tool_manager import (
        ResponsesApiToolManager,
        ToolManager,
    )
    from unique_toolkit.content.service import ContentService

    from unique_orchestrator.config import UniqueAIConfig


def _find_skill_tool_build_config(
    tools: list[ToolBuildConfig],
) -> ToolBuildConfig | None:
    """Return the SkillTool entry from ``space.tools`` if present."""
    for tool in tools:
        if tool.name == SkillTool.name:
            return tool
    return None


def _parse_frontmatter(*, text: str) -> tuple[dict[str, Any], str]:
    """Split YAML frontmatter from the markdown body.

    Thin wrapper around ``python-frontmatter``. On a YAML parse error,
    or when the frontmatter parses to a non-mapping (e.g. a top-level
    YAML list), we fall back to ``({}, <stripped body>)`` so a broken
    skill file never leaks its raw ``---\\nname: ...\\n---`` block into
    the LLM prompt, but also never crashes ``_build_skill`` with an
    unhandled ``TypeError``/``ValueError`` from ``dict(...)``.
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


def message_skills_as_selectable(
    available_skills: list[SkillReference],
) -> list[SkillReference]:
    """Normalize ``ChatEventPayload.available_skills`` for the Skill tool.

    Call this at the orchestration boundary (e.g. when building ``UniqueAI``)
    before ``configure_skill_tool``. Deduplicates by ``content_id`` while
    preserving first-seen order. Entries without a ``content_id`` are skipped.
    """
    seen: set[str] = set()
    out: list[SkillReference] = []
    for choice in available_skills:
        cid = choice.content_id
        if not cid or cid in seen:
            continue
        seen.add(cid)
        out.append(
            SkillReference(
                name=choice.name,
                scope_id=choice.scope_id,
                content_id=choice.content_id,
            )
        )
    return out


def _build_skill(
    *,
    content_id: str,
    content_key: str,
    file_text: str,
    logger: Logger,
) -> SkillDefinition | None:
    """Build a ``SkillDefinition`` from the raw file text of a KB document.

    Parses YAML frontmatter for ``name`` and ``description``. A malformed
    ``name`` (non-kebab-case, contains whitespace/punctuation, too long)
    is rejected by ``SkillDefinition`` rather than silently flowing into
    the OpenAI tool enum where the model could never emit it verbatim.

    ``content_id`` and ``content_key`` are used only for log messages so
    operators can locate the offending file in the knowledge base.
    """
    if not file_text.strip():
        return None

    metadata, body = _parse_frontmatter(text=file_text)

    name = metadata.get("name")
    description = metadata.get("description")

    if not name or not description:
        logger.warning(
            "Skipping '%s' (%s): wrong skill format.",
            content_key,
            content_id,
        )
        return None

    try:
        return SkillDefinition(
            name=name,
            description=description,
            content=body,
        )
    except ValidationError as exc:
        logger.warning(
            "Skipping '%s' (%s): invalid skill definition: %s",
            content_key,
            content_id,
            exc.errors(include_url=False),
        )
        return None


async def load_selectable_skills(
    *,
    content_service: ContentService,
    selectable_skills: list[SkillReference],
    logger: Logger,
) -> dict[str, SkillDefinition]:
    """Load skills from an explicit list of ``SkillReference`` references.

    Entries with an empty ``content_id`` are skipped (admin UIs commonly
    leave a blank row as a placeholder). Failures are logged and do not
    abort the rest of the registry so one broken entry cannot hide the
    rest of the skill list.
    """
    valid_entries = [entry for entry in selectable_skills if entry.content_id]
    if not valid_entries:
        logger.info("SkillTool has no selectable_skills with a content_id set.")
        return {}

    download_results = await asyncio.gather(
        *(
            content_service.download_content_to_bytes_async(content_id=entry.content_id)
            for entry in valid_entries
        ),
        return_exceptions=True,
    )

    skill_registry: dict[str, SkillDefinition] = {}
    for entry, result in zip(valid_entries, download_results, strict=True):
        label = entry.name or entry.content_id
        if isinstance(result, BaseException):
            logger.warning(
                "Failed to download selectable skill '%s' (%s) — skipping.",
                label,
                entry.content_id,
                exc_info=result,
            )
            continue

        try:
            file_text = result.decode("utf-8")
        except UnicodeDecodeError:
            logger.warning(
                "Failed to decode selectable skill '%s' (%s) as UTF-8 — skipping.",
                label,
                entry.content_id,
                exc_info=True,
            )
            continue

        skill = _build_skill(
            content_id=entry.content_id,
            content_key=label,
            file_text=file_text,
            logger=logger,
        )
        if skill is None:
            logger.debug(
                "Skipping selectable skill '%s' (%s): empty or invalid file.",
                label,
                entry.content_id,
            )
            continue

        if skill.name in skill_registry:
            logger.warning(
                "Duplicate skill name '%s' from selectable_skills — "
                "keeping the first occurrence.",
                skill.name,
            )
            continue

        skill_registry[skill.name] = skill

    logger.info(
        "Loaded %d skill(s) from selectable_skills.",
        len(skill_registry),
    )
    return skill_registry


async def configure_skill_tool(
    *,
    config: UniqueAIConfig,
    logger: Logger,
    content_service: ContentService,
    tool_manager: ToolManager | ResponsesApiToolManager,
    selectable_skills: list[SkillReference] | None = None,
) -> None:
    """Populate the SkillTool's skill registry when it is enabled in ``space.tools``.
    """
    skill_tool_build_config = _find_skill_tool_build_config(config.space.tools)
    if skill_tool_build_config is None or not skill_tool_build_config.is_enabled:
        return

    to_load = list(selectable_skills or [])
    skill_tool_build_config.configuration.selectable_skills.selected = to_load

    if not to_load:
        logger.warning(
            "SkillTool is enabled but selectable_skills is empty — "
            "no skills will be loaded."
        )
        tool_manager.exclude_tool(SkillTool.name)
        return

    skill_registry = await load_selectable_skills(
        content_service=content_service,
        selectable_skills=to_load,
        logger=logger,
    )

    if not skill_registry:
        logger.info("SkillTool has an empty skill registry — tool will be excluded.")
        tool_manager.exclude_tool(SkillTool.name)
        return

    skill_tool = tool_manager.get_tool_by_name(SkillTool.name)
    if not isinstance(skill_tool, SkillTool):
        logger.warning(
            "SkillTool is configured in space.tools but the manager did "
            "not produce a SkillTool instance — skills will not be "
            "available."
        )
        return

    skill_tool.skill_registry = skill_registry


async def preload_invoked_skills(
    *,
    tool_manager: ToolManager | ResponsesApiToolManager,
    history_manager: HistoryManager,
    logger: Logger,
    skill_choices: list[SkillReference],
) -> None:
    """Preload skills selected in ``skill_choices`` before the first model turn.

    Only explicit per-turn ``skill_choices`` are considered.

    Mirrors the normal mid-loop activation path so preloaded skills are
    indistinguishable from skills the model activates itself:

    1. Resolves each ``skill_choices`` entry against the registered
       ``SkillTool`` registry (by normalized name or ``content_id``).
    2. For each matched skill, synthesizes a ``LanguageModelFunction``
       and runs it through the already-registered ``SkillTool`` — the
       exact same code path ``UniqueAI._handle_tool_calls`` uses.
    3. Appends the synthetic assistant tool-call message plus the
       resulting tool-result messages to history, so the first model
       turn sees the skills as already-activated tool calls.

    Duplicate choices that resolve to the same registered skill are
    ignored after the first.
    """
    skill_tool = tool_manager.get_tool_by_name(SkillTool.name)
    if not isinstance(skill_tool, SkillTool):
        return

    forced_skills: list[SkillDefinition] = []
    seen_forced: set[str] = set()
    for choice in skill_choices:
        forced_skill: SkillDefinition | None = None
        if choice.name:
            normalized_name = normalize_skill_name(choice.name)
            forced_skill = skill_tool.skill_registry.get(normalized_name)
        if forced_skill is None:
            continue
        if forced_skill.name in seen_forced:
            continue
        seen_forced.add(forced_skill.name)
        forced_skills.append(forced_skill)

    if not forced_skills:
        return

    tool_calls: list[LanguageModelFunction] = []
    responses: list[ToolCallResponse] = []
    for skill in forced_skills:
        tool_call = LanguageModelFunction(
            name=SkillTool.name,
            arguments={"skill_name": skill.name},
        )
        response = await skill_tool.run(tool_call)
        tool_calls.append(tool_call)
        responses.append(response)
        history_manager.add_tool_call(tool_call)

    history_manager._append_tool_calls_to_history(tool_calls)
    history_manager.add_tool_call_results(responses)

    logger.info(
        "Preloaded %d skill(s) before first model turn: %s",
        len(forced_skills),
        [s.name for s in forced_skills],
    )
