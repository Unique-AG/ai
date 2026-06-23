import re
from dataclasses import dataclass
from logging import Logger

import unique_sdk
from unique_toolkit.app import ChatEvent
from unique_toolkit.content.functions import (
    download_content_to_bytes_async,
    search_contents_async,
    upload_content_from_bytes_async,
)
from unique_toolkit.language_model import (
    DEFAULT_GPT_4o,
    LanguageModelMessages,
    LanguageModelService,
    LanguageModelSystemMessage,
    LanguageModelUserMessage,
    TypeDecoder,
    TypeEncoder,
)
from unique_toolkit.language_model.infos import LanguageModelInfo

from unique_user_memory.config import UserMemoryConfig
from unique_user_memory.user_memory_prompts import (
    SECTION_HEADINGS,
    consolidation_system_prompt,
    consolidation_user_prompt,
    empty_profile,
)

MEMORY_FILENAME = "memory.md"
MIME_TYPE = "text/markdown"
_LLM_OUTPUT_HEADROOM_TOKENS = 200
_TRUNCATION_MARKER = "\n\n<!-- truncated to fit memory budget -->"
_DEFAULT_LANGUAGE_MODEL = LanguageModelInfo.from_name(DEFAULT_GPT_4o)
_FRONTMATTER_RE = re.compile(r"^---\n.*?\n---\n", re.DOTALL)


@dataclass(frozen=True)
class UserMemoryState:
    scope_id: str
    text: str


def _get_model_tokenizer(
    *,
    language_model: LanguageModelInfo,
) -> tuple[TypeEncoder, TypeDecoder]:
    model_info = language_model or _DEFAULT_LANGUAGE_MODEL
    return model_info.get_encoder(), model_info.get_decoder()


def _count_tokens(
    *,
    content: str,
    encode: TypeEncoder,
) -> int:
    if not content:
        return 0
    return len(encode(content))


def count_tokens(
    *,
    content: str,
    language_model: LanguageModelInfo = _DEFAULT_LANGUAGE_MODEL,
) -> int:
    encode, _ = _get_model_tokenizer(language_model=language_model)
    return _count_tokens(content=content, encode=encode)


def enforce_token_cap(
    *,
    content: str,
    max_tokens: int,
    language_model: LanguageModelInfo = _DEFAULT_LANGUAGE_MODEL,
) -> str:
    if not content:
        return content

    encode, decode = _get_model_tokenizer(language_model=language_model)

    if _count_tokens(content=content, encode=encode) <= max_tokens:
        return content

    marker_tokens = _count_tokens(content=_TRUNCATION_MARKER, encode=encode)
    target = max(0, max_tokens - marker_tokens)
    paragraphs = content.split("\n\n")
    accepted: list[str] = []
    running = 0
    for paragraph in paragraphs:
        paragraph_tokens = _count_tokens(content=paragraph + "\n\n", encode=encode)
        if running + paragraph_tokens > target:
            break
        accepted.append(paragraph)
        running += paragraph_tokens

    if accepted:
        truncated = "\n\n".join(accepted)
    else:
        truncated = decode(encode(content)[:target])

    result = truncated.rstrip() + _TRUNCATION_MARKER
    shrink = target
    while _count_tokens(content=result, encode=encode) > max_tokens and shrink > 0:
        shrink -= 1
        body = decode(encode(result)[:shrink]).rstrip()
        result = body + _TRUNCATION_MARKER

    if _count_tokens(content=result, encode=encode) > max_tokens:
        result = decode(encode(result)[:max_tokens])

    return result


async def load_user_memory(
    *,
    event: ChatEvent,
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
        user_id=user_id,
        company_id=company_id,
        logger=logger,
    )
    return UserMemoryState(
        scope_id=scope_id,
        text=enforce_token_cap(
            content=text,
            max_tokens=config.max_tokens,
            language_model=config.language_model,
        ),
    )


async def ensure_user_memory_folder(
    *,
    user_id: str,
    company_id: str,
    root_folder: str,
    logger: Logger,
) -> str | None:
    root_scope_id = await _resolve_root_folder(
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
        return info.get("id")
    except Exception:
        logger.warning("[user-memory] user memory folder not found - creating new one")

    try:
        created = await unique_sdk.Folder.create_paths_async(
            user_id=user_id,
            company_id=company_id,
            parentScopeId=root_scope_id,
            relativePaths=[user_id],
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
    if len(created_folders) > 1:
        logger.warning(
            "[user-memory] create_paths returned %d folders for %s, "
            "expected exactly 1; using the first one",
            len(created_folders),
            user_folder_path,
        )
    scope_id = created_folders[0].get("id") if created_folders else None
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
                },
                {
                    "entityId": user_id,
                    "type": "WRITE",
                    "entityType": "USER",
                },
            ],
            applyToSubScopes=True,
        )
    except Exception as exc:
        logger.warning(
            "[user-memory] failed to grant read/write access on scope %s "
            "for user %s: [%s] %s",
            scope_id,
            user_id,
            type(exc).__name__,
            exc,
        )
        return None

    return scope_id


async def _resolve_root_folder(
    *,
    user_id: str,
    company_id: str,
    root_folder: str,
    logger: Logger,
) -> str | None:
    root_path = f"/{root_folder.strip('/')}"
    try:
        root_info = await unique_sdk.Folder.get_info_async(
            user_id=user_id,
            company_id=company_id,
            folderPath=root_path,
        )
    except Exception as exc:
        logger.warning(
            "[user-memory] failed to resolve pre-provisioned root folder %s: [%s] %s",
            root_path,
            type(exc).__name__,
            exc,
        )
        return None

    root_scope_id = root_info.get("id")
    if not root_scope_id:
        logger.warning(
            "[user-memory] root folder lookup returned no id for %s",
            root_path,
        )
        return None

    return root_scope_id


async def download_user_memory(
    *,
    scope_id: str,
    user_id: str,
    company_id: str,
    logger: Logger,
) -> str:
    try:
        contents = await search_contents_async(
            user_id=user_id,
            company_id=company_id,
            chat_id=None,
            where={"ownerId": {"equals": scope_id}},
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

    try:
        content_bytes = await download_content_to_bytes_async(
            user_id=user_id,
            company_id=company_id,
            content_id=memory_content.id,
            chat_id=None,
        )
        text = content_bytes.decode("utf-8", errors="replace")
        logger.info(
            "[user-memory] downloaded %s (%d bytes) from scope %s",
            MEMORY_FILENAME,
            len(content_bytes),
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

    try:
        await upload_content_from_bytes_async(
            user_id=user_id,
            company_id=company_id,
            content=content.encode("utf-8"),
            content_name=MEMORY_FILENAME,
            mime_type=MIME_TYPE,
            scope_id=scope_id,
            ingestion_config={
                "uniqueIngestionMode": "SKIP_INGESTION",
                "hideInChat": True,
            },
        )
        logger.info(
            "[user-memory] uploaded %s (%d bytes) to scope %s",
            MEMORY_FILENAME,
            len(content.encode("utf-8")),
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
    safe_current = enforce_token_cap(
        content=current_memory,
        max_tokens=config.max_tokens,
        language_model=config.language_model,
    )
    logger.info(
        "[user-memory] consolidating turn - existing_memory_tokens=%d | "
        "user_msg_chars=%d | assistant_msg_chars=%d",
        count_tokens(content=safe_current, language_model=config.language_model),
        len(user_message or ""),
        len(assistant_message or ""),
    )

    if not (user_message or "").strip() and not (assistant_message or "").strip():
        return safe_current or enforce_token_cap(
            content=empty_profile(user_id),
            max_tokens=config.max_tokens,
            language_model=config.language_model,
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
        logger.info("[user-memory] consolidation NOOP - keeping existing memory")
        return safe_current

    candidate = _strip_code_fences(raw).strip()
    if not _is_well_formed_profile(candidate):
        logger.warning(
            "[user-memory] LLM output did not look like a profile (%d chars)",
            len(candidate),
        )
        return safe_current

    capped = enforce_token_cap(
        content=candidate,
        max_tokens=config.max_tokens,
        language_model=config.language_model,
    )
    if (
        safe_current
        and _FRONTMATTER_RE.sub("", capped).strip()
        == _FRONTMATTER_RE.sub("", safe_current).strip()
    ):
        logger.debug("[user-memory] memory body unchanged - skipping update")
        return safe_current

    logger.info(
        "[user-memory] consolidation produced %d tokens (cap=%d)",
        count_tokens(content=capped, language_model=config.language_model),
        config.max_tokens,
    )
    return capped


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
