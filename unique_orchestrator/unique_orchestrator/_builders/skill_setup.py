"""Helpers for the Skill tool.

Loads skill definitions from the knowledge base and registers the
SkillTool with the tool manager.

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
from typing import TYPE_CHECKING, Any, cast

import frontmatter
from pydantic import ValidationError
from unique_skill_tool.config import SkillToolConfig
from unique_skill_tool.schemas import SkillDefinition
from unique_skill_tool.service import SkillTool
from unique_skill_tool.utils import extract_invoked_skills
from unique_toolkit.agentic.tools.config import ToolBuildConfig
from unique_toolkit.agentic.tools.schemas import ToolCallResponse
from unique_toolkit.content.schemas import Content, ContentInfo
from unique_toolkit.content.smart_rules import (
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


def _find_skill_tool_build_config(
    tools: list[ToolBuildConfig],
) -> ToolBuildConfig | None:
    """Return the SkillTool entry from ``space.tools`` if present."""
    for tool in tools:
        if tool.name == SkillTool.name:
            return tool
    return None


_SUBTREE_PAGE_SIZE = 100
_MAX_SUBTREE_ITEMS = 10_000

_SKILL_ENTRYPOINT_FILENAME = "skill.md"


def _is_skill_entrypoint(*, content: Content | ContentInfo) -> bool:
    """Return True when *content*'s basename is the skill entrypoint file.

    Matches only ``SKILL.md`` (case-insensitive). Other ``.md`` files in
    a skill folder — README, ``references/*.md``, etc. — are treated as
    assets and not registered as separate skills, which is what the
    "each skill is a folder" semantics of the official Agent Skills
    protocol requires.
    """
    return content.key.lower() == _SKILL_ENTRYPOINT_FILENAME


def _build_subtree_metadata_filter(*, scope_ids: list[str]) -> dict[str, Any]:
    """Build a UniqueQL filter matching any file under the given scope IDs.

    The ``folderIdPath`` metadata is stored as a single string with one
    ``uniquepathid://`` prefix at the start, followed by ``/``-separated
    scope IDs from root to leaf — e.g. for a file in
    ``Root/Skills/Programming``::

        uniquepathid://scope_root/scope_skills/scope_programming
    """
    statements: list[Statement] = [
        Statement(
            operator=Operator.CONTAINS,
            value=f"/{scope_id}",
            path=["folderIdPath"],
        )
        for scope_id in scope_ids
    ]
    if len(statements) == 1:
        return statements[0].model_dump(mode="json")
    return OrStatement(or_list=statements).model_dump(mode="json")


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


def _build_skill(
    *,
    content: Content | ContentInfo,
    file_text: str,
    logger: Logger,
) -> SkillDefinition | None:
    """Build a ``SkillDefinition`` from the raw file text of a KB document.

    Parses YAML frontmatter for ``name`` and ``description``. A malformed
    ``name`` (non-kebab-case, contains whitespace/punctuation, too long)
    is rejected by ``SkillDefinition`` rather than silently flowing into
    the OpenAI tool enum where the model could never emit it verbatim.
    """
    if not file_text.strip():
        return None

    metadata, body = _parse_frontmatter(text=file_text)

    name = metadata.get("name")
    description = metadata.get("description")

    if not name or not description:
        logger.warning(
            "Skipping '%s' (%s): wrong skill format.",
            content.key,
            content.id,
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
            content.key,
            content.id,
            exc.errors(include_url=False),
        )
        return None


async def load_skills_from_knowledge_base(
    *,
    content_service: ContentService,
    knowledge_base_service: KnowledgeBaseService,
    scope_ids: list[str],
    logger: Logger,
) -> dict[str, SkillDefinition]:
    """Load all ``SKILL.md`` files from *scope_ids* (recursively) into a skill registry.

    Pages through ``/content/infos`` with the UniqueQL metadata filter
    built by :func:`_build_subtree_metadata_filter`, which OR's two
    ``CONTAINS`` predicates per scope (``uniquepathid://<scope_id>`` and
    ``/<scope_id>``) so a configured scope matches at the root *and* at
    any descendant depth. The public API caps ``take`` at 100, so
    results are accumulated across pages up to ``_MAX_SUBTREE_ITEMS``.
    This means:

    * Each configured scope ID acts as a subtree root — every skill
      folder inside it (and any descendant folder) is considered,
      regardless of whether the scope is itself a top-level folder or
      a nested one.
    * Only files whose basename is ``SKILL.md`` are kept; everything
      else (assets, references, scripts, READMEs) is filtered out so
      a single skill folder maps to a single registered skill.
    * The backend's ACL is applied to the matching set, so only skills
      the current user can access are returned.
    * To expose skills to users who only have access to specific
      sub-folders, configure those sub-folder scope IDs directly.

    File downloads are fanned out concurrently via ``asyncio.gather`` so
    per-request build latency stays ~O(1) in the number of skills rather
    than O(N) synchronous HTTP round-trips.
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

    skill_infos = [ci for ci in all_infos if _is_skill_entrypoint(content=ci)]
    if not skill_infos:
        logger.info(
            "No SKILL.md entrypoints found for scope_ids=%s.",
            scope_ids,
        )
        return {}

    download_results = await asyncio.gather(
        *(
            content_service.download_content_to_bytes_async(content_id=info.id)
            for info in skill_infos
        ),
        return_exceptions=True,
    )

    skill_registry: dict[str, SkillDefinition] = {}
    for info, result in zip(skill_infos, download_results, strict=True):
        if isinstance(result, BaseException):
            logger.warning(
                "Failed to download '%s' (%s) — skipping.",
                info.key,
                info.id,
                exc_info=result,
            )
            continue

        try:
            file_text = result.decode("utf-8")
        except UnicodeDecodeError:
            logger.warning(
                "Failed to decode '%s' (%s) as UTF-8 — skipping.",
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


async def configure_skill_tool(
    *,
    config: UniqueAIConfig,
    event: ChatEvent,
    logger: Logger,
    content_service: ContentService,
    tool_manager: ToolManager | ResponsesApiToolManager,
) -> None:
    """Populate the SkillTool's skill registry when it is enabled in ``space.tools``.

    Lists every ``SKILL.md`` entrypoint reachable from the configured
    ``scope_ids`` (and every sub-folder under them), downloads each one
    concurrently, and registers the SkillTool with the parsed skills.
    Each skill folder follows the official Agent Skills protocol layout
    (``<skill>/SKILL.md`` plus optional ``scripts/``, ``references/``,
    ``assets/``).
    """
    skill_tool_build_config = _find_skill_tool_build_config(config.space.tools)
    if skill_tool_build_config is None or not skill_tool_build_config.is_enabled:
        return

    skill_config = cast(SkillToolConfig, skill_tool_build_config.configuration)

    if not skill_config.scope_ids:
        logger.warning(
            "SkillTool is enabled but no scope_ids are configured — "
            "no skills will be loaded."
        )
        tool_manager.exclude_tool(SkillTool.name)
        return

    knowledge_base_service = KnowledgeBaseService(
        company_id=event.company_id,
        user_id=event.user_id,
    )

    skill_registry = await load_skills_from_knowledge_base(
        content_service=content_service,
        knowledge_base_service=knowledge_base_service,
        scope_ids=skill_config.scope_ids,
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
    event: ChatEvent,
    tool_manager: ToolManager | ResponsesApiToolManager,
    history_manager: HistoryManager,
    logger: Logger,
) -> str | None:
    """Preload skills invoked as ``/skill-name`` tokens in the user message.

    Mirrors the normal mid-loop activation path so preloaded skills are
    indistinguishable from skills the model activates itself:

    1. Pulls every ``/skill-name`` token out of the user message —
       whether at the start, between words, or at the end — as long as
       it is properly word-boundaried so URLs and file paths are not
       mistaken for invocations. Unknown tokens are left as ordinary
       text.
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

    skills, stripped_text = extract_invoked_skills(
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
