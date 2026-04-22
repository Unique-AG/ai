"""Helpers for the Skill tool.

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
from typing import TYPE_CHECKING, Any

import yaml
from unique_skill_tool.schemas import SkillDefinition
from unique_skill_tool.service import SkillTool
from unique_skill_tool.utils import extract_prefix_skills
from unique_toolkit.agentic.tools.schemas import ToolCallResponse
from unique_toolkit.content.schemas import Content, ContentInfo
from unique_toolkit.content.smart_rules import (
    AndStatement,
    Operator,
    OrStatement,
    Statement,
)
from unique_toolkit.language_model.schemas import LanguageModelFunction
from unique_toolkit.services.knowledge_base import KnowledgeBaseService

if TYPE_CHECKING:
    from unique_toolkit.agentic.history_manager.history_manager import HistoryManager
    from unique_toolkit.agentic.tools.tool_manager import (
        ResponsesApiToolManager,
        ToolManager,
    )
    from unique_toolkit.app.schemas import ChatEvent
    from unique_toolkit.content.service import ContentService

    from unique_orchestrator.config import UniqueAIConfig


_SUBTREE_PAGE_SIZE = 100
_MAX_SUBTREE_ITEMS = 10_000


def _is_markdown(*, content: Content | ContentInfo) -> bool:
    return content.key.lower().endswith(".md")


def _build_subtree_metadata_filter(*, scope_ids: list[str]) -> dict[str, Any]:
    """Build a UniqueQL filter matching any file under the given scope IDs.

    For each configured scope ID we add a ``folderIdPath CONTAINS
    uniquepathid://<scope_id>`` predicate, then OR them together. The
    backend's ACL is then applied to the matching set, so only files
    the current user can access are returned.
    """
    statements: list[Statement | AndStatement | OrStatement] = [
        Statement(
            operator=Operator.CONTAINS,
            value=f"uniquepathid://{scope_id}",
            path=["folderIdPath"],
        )
        for scope_id in scope_ids
    ]
    if len(statements) == 1:
        return statements[0].model_dump(mode="json")
    return OrStatement(or_list=statements).model_dump(mode="json")


def _parse_frontmatter(*, text: str) -> tuple[dict[str, Any], str]:
    """Split YAML frontmatter from the markdown body.

    Follows the standard YAML frontmatter convention: the document must
    begin with a ``---`` delimiter on its own line, and the frontmatter
    block ends at the next ``---`` (or ``...``) on its own line.  ``---``
    appearing inside values (e.g. ``name: my---skill``) is not treated as
    a delimiter.

    Returns ``(frontmatter_dict, body)``.  If no frontmatter is found,
    the dict is empty and the full text is returned as the body.
    """
    lines = text.splitlines(keepends=True)
    if not lines or lines[0].rstrip("\r\n") != "---":
        return {}, text

    for idx in range(1, len(lines)):
        stripped = lines[idx].rstrip("\r\n")
        if stripped == "---" or stripped == "...":
            fm_text = "".join(lines[1:idx])
            body = "".join(lines[idx + 1 :]).lstrip("\n")
            try:
                fm = yaml.safe_load(fm_text)
            except yaml.YAMLError:
                return {}, text
            if not isinstance(fm, dict):
                return {}, text
            return fm, body

    return {}, text


def _build_skill(
    *,
    content: Content | ContentInfo,
    file_text: str,
    logger: Logger,
) -> SkillDefinition | None:
    """Build a ``SkillDefinition`` from the raw file text of a KB document.

    Parses YAML frontmatter for ``name`` and ``description``.
    """
    if not file_text.strip():
        return None

    frontmatter, body = _parse_frontmatter(text=file_text)

    name = frontmatter.get("name")
    description = frontmatter.get("description")

    if not name or not description:
        logger.warning(
            "Skipping '%s' (%s): wrong skill format.",
            content.key,
            content.id,
        )
        return None

    return SkillDefinition(
        name=name,
        description=description,
        content=body,
    )


def load_skills_from_knowledge_base(
    *,
    content_service: ContentService,
    knowledge_base_service: KnowledgeBaseService,
    scope_ids: list[str],
    logger: Logger,
) -> dict[str, SkillDefinition]:
    """Load all ``.md`` files from *scope_ids* (recursively) into a skill registry.

    Pages through ``/content/infos`` with a UniqueQL metadata filter that
    OR's ``folderIdPath CONTAINS uniquepathid://<scope_id>`` for every
    configured scope. The public API caps ``take`` at 100, so results are
    accumulated across pages up to ``_MAX_SUBTREE_ITEMS``. This matches
    any file whose folder path contains the configured scope at any
    depth, so:

    * Each configured scope ID acts as a subtree root — all files inside
      it and any of its descendants are considered.
    * The backend's ACL is applied to the matching set, so only files
      the current user can access are returned.
    * To expose skills to users who only have access to specific
      sub-folders, configure those sub-folder scope IDs directly.
    """
    if not scope_ids:
        logger.info("SkillTool has no scope_ids configured.")
        return {}

    metadata_filter = _build_subtree_metadata_filter(scope_ids=scope_ids)

    all_infos: list[ContentInfo] = []
    skip = 0
    try:
        while skip < _MAX_SUBTREE_ITEMS:
            paginated = knowledge_base_service.get_paginated_content_infos(
                metadata_filter=metadata_filter,
                skip=skip,
                take=_SUBTREE_PAGE_SIZE,
            )
            all_infos.extend(paginated.content_infos)
            skip += len(paginated.content_infos)
            if (
                len(paginated.content_infos) < _SUBTREE_PAGE_SIZE
                or skip >= paginated.total_count
            ):
                break
    except Exception:
        logger.warning(
            "Failed to list contents for scope_ids=%s — "
            "SkillTool will have an empty skill registry.",
            scope_ids,
            exc_info=True,
        )
        return {}

    md_infos = [ci for ci in all_infos if _is_markdown(content=ci)]
    if not md_infos:
        logger.info("No .md files found for scope_ids=%s.", scope_ids)
        return {}

    skill_registry: dict[str, SkillDefinition] = {}
    for info in md_infos:
        try:
            raw_bytes = content_service.download_content_to_bytes(
                content_id=info.id,
            )
            file_text = raw_bytes.decode("utf-8")
        except Exception:
            logger.warning(
                "Failed to download '%s' (%s) — skipping.",
                info.key,
                info.id,
                exc_info=True,
            )
            continue

        skill = _build_skill(content=info, file_text=file_text, logger=logger)
        if skill is None:
            logger.debug(
                "Skipping '%s' (%s): empty file.",
                info.key,
                info.id,
            )
            continue

        if skill.name in skill_registry:
            logger.warning(
                "Duplicate skill name '%s' — keeping the first occurrence.",
                skill.name,
            )
            continue

        skill_registry[skill.name] = skill

    logger.info(
        "Loaded %d skill(s) from knowledge base (scope_ids=%s).",
        len(skill_registry),
        scope_ids,
    )
    return skill_registry


def configure_skill_tool(
    *,
    config: UniqueAIConfig,
    event: ChatEvent,
    logger: Logger,
    content_service: ContentService,
    tool_manager: ToolManager | ResponsesApiToolManager,
) -> None:
    """Register the SkillTool if enabled in the config.

    Lists all ``.md`` files in the configured ``scope_ids`` (and every
    sub-folder reachable from them), downloads each one, and registers
    the SkillTool with the parsed skills.
    """
    skill_config = config.agent.experimental.skill_tool_config
    if not skill_config.enabled:
        return

    if not skill_config.scope_ids:
        logger.warning(
            "SkillTool is enabled but no scope_ids are configured — "
            "no skills will be loaded."
        )
        return

    knowledge_base_service = KnowledgeBaseService(
        company_id=event.company_id,
        user_id=event.user_id,
    )

    skill_registry = load_skills_from_knowledge_base(
        content_service=content_service,
        knowledge_base_service=knowledge_base_service,
        scope_ids=skill_config.scope_ids,
        logger=logger,
    )

    tool_manager.add_tool(
        SkillTool(
            event=event,
            skill_registry=skill_registry,
            config=skill_config,
        )
    )


async def preload_invoked_skills(
    *,
    event: ChatEvent,
    tool_manager: ToolManager | ResponsesApiToolManager,
    history_manager: HistoryManager,
    logger: Logger,
) -> str | None:
    """Preload skills invoked as ``/skill-name`` prefix(es) in the user message.

    Mirrors the normal mid-loop activation path so preloaded skills are
    indistinguishable from skills the model activates itself:

    1. Parses consecutive ``/skill-name`` tokens from the start of the
       user message.
    2. For each matched skill, synthesizes a ``LanguageModelFunction``
       and runs it through the already-registered ``SkillTool`` — the
       exact same code path ``UniqueAI._handle_tool_calls`` uses.
    3. Appends the synthetic assistant tool-call message plus the
       resulting tool-result messages to history, so the first model
       turn sees the skills as already-activated tool calls.
    4. Strips the matched ``/skill-name`` tokens from the user message
       so the rendered turn shows only the user's actual query.

    No-ops when the SkillTool is not registered or no tokens match.
    """
    skill_tool = tool_manager.get_tool_by_name(SkillTool.name)
    if not isinstance(skill_tool, SkillTool):
        return None

    original_text = event.payload.user_message.text or ""

    skills, stripped_text = extract_prefix_skills(
        original_text, skill_tool.skill_registry
    )
    if not skills:
        return None

    tool_calls: list[LanguageModelFunction] = []
    responses: list[ToolCallResponse] = []
    for skill in skills:
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
        "Preloaded %d skill(s) from slash invocation: %s",
        len(skills),
        [s.name for s in skills],
    )

    return stripped_text
