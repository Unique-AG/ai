import asyncio
import os
import re
import tempfile
from dataclasses import dataclass
from logging import Logger
from pathlib import Path

import tiktoken
import unique_sdk
import unique_sdk.utils.file_io as file_io
from unique_toolkit.app import ChatEvent
from unique_toolkit.content.service import ContentService
from unique_toolkit.language_model import (
    LanguageModelMessages,
    LanguageModelService,
    LanguageModelSystemMessage,
    LanguageModelUserMessage,
)

from unique_user_memory.config import UserMemoryConfig
from unique_user_memory.user_memory_prompts import (
    SECTION_HEADINGS,
    consolidation_system_prompt,
    consolidation_user_prompt,
    empty_profile,
)

MEMORY_FILENAME = "memory.md"
MIME_TYPE = "text/markdown"
ROOT_GROUP_NAME = "Root Group"
_LLM_OUTPUT_HEADROOM_TOKENS = 200
_TRUNCATION_MARKER = "\n\n<!-- truncated to fit memory budget -->"
_TOKENIZER = tiktoken.get_encoding("cl100k_base")
_FRONTMATTER_RE = re.compile(r"^---\n.*?\n---\n", re.DOTALL)


@dataclass(frozen=True)
class UserMemoryState:
    scope_id: str
    text: str


def count_tokens(content: str) -> int:
    if not content:
        return 0
    return len(_TOKENIZER.encode(content))


def enforce_token_cap(content: str, max_tokens: int) -> str:
    if not content:
        return content

    if count_tokens(content) <= max_tokens:
        return content

    marker_tokens = count_tokens(_TRUNCATION_MARKER)
    target = max(0, max_tokens - marker_tokens)
    paragraphs = content.split("\n\n")
    accepted: list[str] = []
    running = 0
    for paragraph in paragraphs:
        paragraph_tokens = count_tokens(paragraph + "\n\n")
        if running + paragraph_tokens > target:
            break
        accepted.append(paragraph)
        running += paragraph_tokens

    if accepted:
        truncated = "\n\n".join(accepted)
    else:
        truncated = _TOKENIZER.decode(_TOKENIZER.encode(content)[:target])

    result = truncated.rstrip() + _TRUNCATION_MARKER
    shrink = target
    while count_tokens(result) > max_tokens and shrink > 0:
        shrink -= 1
        body = _TOKENIZER.decode(_TOKENIZER.encode(result)[:shrink]).rstrip()
        result = body + _TRUNCATION_MARKER

    if count_tokens(result) > max_tokens:
        result = _TOKENIZER.decode(_TOKENIZER.encode(result)[:max_tokens])

    return result


async def load_user_memory(
    *,
    event: ChatEvent,
    content_service: ContentService,
    config: UserMemoryConfig,
    logger: Logger,
) -> UserMemoryState | None:
    user_id = event.user_id
    company_id = event.company_id
    if not user_id or not company_id:
        logger.warning("[user-memory] empty user_id/company_id - skipping memory load")
        return None

    scope_id = await ensure_user_memory_folder(
        user_id=user_id,
        company_id=company_id,
        root_folder=config.root_folder,
        logger=logger,
    )
    if scope_id is None:
        logger.info("[user-memory] folder ensure failed - running without memory")
        return None

    text = await download_user_memory(
        scope_id=scope_id,
        chat_id=event.payload.chat_id or "",
        content_service=content_service,
        logger=logger,
    )
    return UserMemoryState(
        scope_id=scope_id,
        text=enforce_token_cap(text, config.max_tokens),
    )


async def ensure_user_memory_folder(
    *,
    user_id: str,
    company_id: str,
    root_folder: str,
    logger: Logger,
) -> str | None:
    root_scope_id = await _ensure_root_folder_with_company_access(
        user_id=user_id,
        company_id=company_id,
        root_folder=root_folder,
        logger=logger,
    )
    if root_scope_id is None:
        return None

    user_folder_path = f"/{root_folder.strip('/')}/{user_id}"
    scope_id: str | None = None
    try:
        info = await unique_sdk.Folder.get_info_async(
            user_id=user_id,
            company_id=company_id,
            folderPath=user_folder_path,
        )
        scope_id = info.get("id")
    except Exception:
        scope_id = None

    if not scope_id:
        try:
            created = await unique_sdk.Folder.create_paths_async(
                user_id=user_id,
                company_id=company_id,
                paths=[user_folder_path],
                inheritAccess=False,
            )
        except Exception as exc:
            logger.warning(
                "[user-memory] failed to create user folder %s: [%s] %s",
                user_folder_path,
                type(exc).__name__,
                exc,
            )
            return None

        created_folders = (created or {}).get("createdFolders", []) or []
        scope_id = created_folders[-1].get("id") if created_folders else None
        if not scope_id:
            logger.warning(
                "[user-memory] create_paths returned no folder id for %s",
                user_folder_path,
            )
            return None

    try:
        await unique_sdk.Folder.add_access_async(
            user_id=user_id,
            company_id=company_id,
            scopeId=scope_id,
            scopeAccesses=[
                {
                    "entityId": user_id,
                    "type": "READ",
                    "entityType": "USER",
                }
            ],
            applyToSubScopes=True,
        )
    except Exception as exc:
        logger.debug(
            "[user-memory] redundant per-user add_access did not apply on "
            "scope %s for user %s: [%s] %s",
            scope_id,
            user_id,
            type(exc).__name__,
            exc,
        )

    return scope_id


async def _ensure_root_folder_with_company_access(
    *,
    user_id: str,
    company_id: str,
    root_folder: str,
    logger: Logger,
) -> str | None:
    root_path = f"/{root_folder.strip('/')}"
    try:
        root_scope_id = await unique_sdk.Folder.resolve_scope_id_from_folder_path_with_create_async(
            user_id=user_id,
            company_id=company_id,
            folder_path=root_path,
            create_if_not_exists=True,
        )
    except Exception as exc:
        logger.warning(
            "[user-memory] failed to resolve/create root folder %s: [%s] %s",
            root_path,
            type(exc).__name__,
            exc,
        )
        return None

    if not root_scope_id:
        logger.warning(
            "[user-memory] resolve_scope_id returned no id for root path %s",
            root_path,
        )
        return None

    group_id = await _resolve_root_group_id(user_id, company_id, logger)
    if group_id is None:
        return root_scope_id

    try:
        await unique_sdk.Folder.add_access_async(
            user_id=user_id,
            company_id=company_id,
            scopeId=root_scope_id,
            scopeAccesses=[
                {"entityId": group_id, "type": "READ", "entityType": "GROUP"},
                {"entityId": group_id, "type": "WRITE", "entityType": "GROUP"},
            ],
            applyToSubScopes=False,
        )
    except Exception as exc:
        logger.debug(
            "[user-memory] add_access for group %s on root scope %s did not apply: [%s] %s",
            group_id,
            root_scope_id,
            type(exc).__name__,
            exc,
        )

    return root_scope_id


async def _resolve_root_group_id(
    user_id: str,
    company_id: str,
    logger: Logger,
) -> str | None:
    try:
        response = await unique_sdk.Group.get_groups_async(
            user_id=user_id,
            company_id=company_id,
            name=ROOT_GROUP_NAME,
        )
    except Exception as exc:
        logger.warning(
            "[user-memory] failed to list groups while looking for %r: [%s] %s",
            ROOT_GROUP_NAME,
            type(exc).__name__,
            exc,
        )
        return None

    groups = (response or {}).get("groups", []) or []
    exact = next(
        (group for group in groups if (group.get("name") or "") == ROOT_GROUP_NAME),
        None,
    )
    if exact is None:
        logger.warning(
            "[user-memory] backend group %r not found in company %s",
            ROOT_GROUP_NAME,
            company_id,
        )
        return None
    return exact.get("id")


async def download_user_memory(
    *,
    scope_id: str,
    chat_id: str,
    content_service: ContentService,
    logger: Logger,
) -> str:
    try:
        contents = await content_service.search_contents_async(
            where={"ownerId": {"equals": scope_id}},
            chat_id=chat_id,
        )
    except Exception as exc:
        logger.warning(
            "[user-memory] failed to list contents in scope %s: [%s] %s",
            scope_id,
            type(exc).__name__,
            exc,
        )
        return ""

    memory_content = next(
        (content for content in contents if (content.key or "") == MEMORY_FILENAME),
        None,
    )
    if memory_content is None:
        logger.debug(
            "[user-memory] no %s in scope %s - first turn for this user",
            MEMORY_FILENAME,
            scope_id,
        )
        return ""

    tmp_path: Path | None = None
    try:
        tmp_path = await asyncio.to_thread(
            file_io.download_content,
            content_service._company_id,
            content_service._user_id,
            memory_content.id,
            memory_content.key,
            chat_id,
        )
        text = tmp_path.read_text(encoding="utf-8", errors="replace")
        logger.info(
            "[user-memory] downloaded %s (%d bytes, %d tokens) from scope %s",
            MEMORY_FILENAME,
            len(text.encode("utf-8")),
            count_tokens(text),
            scope_id,
        )
        return text
    except Exception as exc:
        logger.warning(
            "[user-memory] failed to download %s from scope %s: [%s] %s",
            MEMORY_FILENAME,
            scope_id,
            type(exc).__name__,
            exc,
        )
        return ""
    finally:
        if tmp_path is not None:
            tmp_path.unlink(missing_ok=True)


async def upload_user_memory(
    *,
    scope_id: str,
    content: str,
    user_id: str,
    company_id: str,
    logger: Logger,
) -> bool:
    if not content.strip():
        logger.warning(
            "[user-memory] refusing to upload empty memory file to scope %s",
            scope_id,
        )
        return False

    tmp_path: Path | None = None
    try:
        tmp_path = Path(await asyncio.to_thread(_write_tempfile, content, ".md"))
        await asyncio.to_thread(
            file_io.upload_file,
            user_id,
            company_id,
            str(tmp_path),
            MEMORY_FILENAME,
            MIME_TYPE,
            scope_or_unique_path=scope_id,
            ingestion_config={
                "uniqueIngestionMode": "SKIP_INGESTION",
                "hideInChat": True,
            },
        )
        logger.info(
            "[user-memory] uploaded %s (%d bytes, %d tokens) to scope %s",
            MEMORY_FILENAME,
            len(content.encode("utf-8")),
            count_tokens(content),
            scope_id,
        )
        return True
    except Exception as exc:
        logger.error(
            "[user-memory] upload failed for scope %s: [%s] %s",
            scope_id,
            type(exc).__name__,
            exc,
            exc_info=True,
        )
        return False
    finally:
        if tmp_path is not None:
            tmp_path.unlink(missing_ok=True)


async def consolidate_user_memory(
    *,
    current_memory: str,
    user_id: str,
    user_message: str,
    assistant_message: str,
    config: UserMemoryConfig,
    event: ChatEvent,
    logger: Logger,
) -> str:
    safe_current = enforce_token_cap(current_memory, config.max_tokens)
    logger.info(
        "[user-memory] consolidating turn user_id=%s | existing_memory_tokens=%d | "
        "user_msg_chars=%d | assistant_msg_chars=%d",
        user_id,
        count_tokens(safe_current),
        len(user_message or ""),
        len(assistant_message or ""),
    )

    if not (user_message or "").strip() and not (assistant_message or "").strip():
        return safe_current or enforce_token_cap(
            empty_profile(user_id), config.max_tokens
        )

    if not safe_current.strip():
        safe_current = empty_profile(user_id)

    try:
        llm_service = LanguageModelService(event)
    except Exception as exc:
        logger.error(
            "[user-memory] cannot construct LanguageModelService: [%s] %s",
            type(exc).__name__,
            exc,
        )
        return safe_current

    messages = LanguageModelMessages(
        [
            LanguageModelSystemMessage(
                content=consolidation_system_prompt(config.max_tokens)
            ),
            LanguageModelUserMessage(
                content=consolidation_user_prompt(
                    user_id=user_id,
                    existing_memory=safe_current,
                    user_message=_sanitize_for_xml_context(user_message or ""),
                    assistant_message=_sanitize_for_xml_context(
                        assistant_message or ""
                    ),
                )
            ),
        ]
    )

    try:
        response = await llm_service.complete_async(
            messages=messages,
            model_name=config.language_model.name,
            other_options={
                "max_tokens": config.max_tokens + _LLM_OUTPUT_HEADROOM_TOKENS,
            },
        )
    except Exception as exc:
        logger.warning(
            "[user-memory] consolidation LLM call failed (model=%s): [%s] %s",
            config.language_model.name,
            type(exc).__name__,
            exc,
        )
        return safe_current

    try:
        raw = response.choices[0].message.content or ""
    except Exception as exc:
        logger.warning(
            "[user-memory] could not extract content from LLM response: [%s] %s",
            type(exc).__name__,
            exc,
        )
        return safe_current

    if not isinstance(raw, str):
        logger.warning(
            "[user-memory] LLM returned non-string content (%s)",
            type(raw).__name__,
        )
        return safe_current

    if raw.strip().upper() == "NOOP":
        logger.debug("[user-memory] consolidation NOOP - keeping existing memory")
        return safe_current

    candidate = _strip_code_fences(raw).strip()
    if not _is_well_formed_profile(candidate):
        logger.warning(
            "[user-memory] LLM output did not look like a profile (%d chars)",
            len(candidate),
        )
        return safe_current

    capped = enforce_token_cap(candidate, config.max_tokens)
    if (
        safe_current
        and _FRONTMATTER_RE.sub("", capped).strip()
        == _FRONTMATTER_RE.sub("", safe_current).strip()
    ):
        logger.debug("[user-memory] memory body unchanged - skipping update")
        return safe_current

    logger.info(
        "[user-memory] consolidation produced %d tokens (cap=%d)",
        count_tokens(capped),
        config.max_tokens,
    )
    return capped


def _write_tempfile(content: str, suffix: str) -> str:
    fd, path = tempfile.mkstemp(prefix="user-memory-", suffix=suffix)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as file:
            file.write(content)
    except Exception:
        Path(path).unlink(missing_ok=True)
        raise
    return path


def _sanitize_for_xml_context(text: str) -> str:
    return text.replace("</", "< /")


def _is_well_formed_profile(content: str) -> bool:
    if not content or len(content.strip()) < 20:
        return False
    if _FRONTMATTER_RE.match(content):
        return True
    return "## Identity" in content or "# User Memory" in content


def _strip_code_fences(text: str) -> str:
    stripped = text.strip()
    if not stripped.startswith("```"):
        return text
    lines = stripped.splitlines()
    if len(lines) >= 3 and lines[-1].strip() == "```":
        return "\n".join(lines[1:-1])
    return text


def looks_empty_profile(content: str) -> bool:
    if not content:
        return True
    return content.count("_(empty)_") >= len(SECTION_HEADINGS)


def prompt_section(memory: str | None) -> str:
    if not memory or not memory.strip():
        return ""
    return memory.strip()
