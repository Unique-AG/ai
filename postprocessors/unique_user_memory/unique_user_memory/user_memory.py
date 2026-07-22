import re
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from datetime import datetime, timezone
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
from unique_toolkit.language_model.invocation_stats import (
    LanguageModelInvocationStats,
)

from unique_user_memory.config import UserMemoryConfig
from unique_user_memory.user_memory_prompts import (
    SECTION_HEADINGS,
    condensation_system_prompt,
    condensation_user_prompt,
    consolidation_system_prompt,
    consolidation_user_prompt,
    empty_profile,
    memory_gate_system_prompt,
    memory_gate_user_prompt,
)

MEMORY_FILENAME = "memory.md"
MIME_TYPE = "text/markdown"
_LLM_OUTPUT_HEADROOM_TOKENS = 200


async def noop_update_callback() -> None:
    """Default update hook that does nothing.

    Used as the default for ``on_update_start`` / ``on_update_end`` so callers
    that do not need update notifications can be awaited unconditionally.
    """
    return None


# The gate only ever replies with the single word UPDATE or NOOP; a tiny
# output budget keeps the common (NOOP) path cheap and fast.
_GATE_MAX_TOKENS = 4
# When condensing an oversized profile, aim below the hard cap so the LLM
# output leaves headroom and the hard-cut safety net rarely has to fire.
_CONDENSE_TARGET_RATIO = 0.9
_TRUNCATION_MARKER = "\n\n<!-- truncated to fit memory budget -->"
_DEFAULT_LANGUAGE_MODEL = LanguageModelInfo.from_name(DEFAULT_GPT_4o)
_FRONTMATTER_RE = re.compile(r"^---\n.*?\n---\n", re.DOTALL)
_TURN_COUNT_RE = re.compile(r"^turn_count:\s*(\d+)\s*$", re.MULTILINE)


def _profile_body(content: str) -> str:
    return _FRONTMATTER_RE.sub("", content, count=1).strip()


def _turn_count(content: str) -> int:
    frontmatter_match = _FRONTMATTER_RE.match(content)
    if frontmatter_match is None:
        return 0
    match = _TURN_COUNT_RE.search(frontmatter_match.group(0))
    return int(match.group(1)) if match else 0


def _assemble_profile(*, body: str, user_id: str, turn_count: int) -> str:
    """Prefix an LLM-generated body with trusted application metadata."""
    timestamp = datetime.now(timezone.utc).isoformat(timespec="seconds")
    return (
        "---\n"
        f"user_id: {user_id}\n"
        "schema_version: 1\n"
        f"last_updated: {timestamp}\n"
        f"turn_count: {turn_count}\n"
        "---\n\n"
        f"{body.strip()}\n"
    )


def _restore_frontmatter(original: str, body: str) -> str:
    match = _FRONTMATTER_RE.match(original)
    if match is None:
        return body
    return f"{match.group(0).rstrip()}\n\n{body.strip()}\n"


@dataclass(frozen=True)
class UserMemoryState:
    scope_id: str
    text: str
    load_invocation_stats: tuple[LanguageModelInvocationStats, ...] = ()


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
    # Split on lines rather than blank-line paragraphs: memory profiles keep
    # each bullet on its own line inside a section, so paragraph-level cuts
    # would treat a whole (multi-thousand-token) section as one indivisible
    # unit and drop the entire body once it exceeds the budget.
    lines = content.split("\n")
    accepted: list[str] = []
    running = 0
    for line in lines:
        line_tokens = _count_tokens(content=line + "\n", encode=encode)
        if running + line_tokens > target:
            break
        accepted.append(line)
        running += line_tokens

    if accepted:
        truncated = "\n".join(accepted)
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


async def condense_user_memory(
    *,
    content: str,
    max_tokens: int,
    language_model: LanguageModelInfo,
    event: ChatEvent,
    logger: Logger,
    invocation_stats: list[LanguageModelInvocationStats] | None = None,
    invocation_source: str = "user_memory_condense",
) -> str | None:
    """Ask the LLM to rewrite an oversized profile into a shorter one.

    Removes duplicate and outdated bullets and tightens prose, targeting a
    fraction of the hard cap so the result leaves headroom. Returns the
    condensed profile, or ``None`` when the call fails or the output does
    not look like a profile (the caller then falls back to a hard cut).
    """
    body = _profile_body(content)
    current_tokens = count_tokens(content=body, language_model=language_model)
    target_tokens = max(1, int(max_tokens * _CONDENSE_TARGET_RATIO))

    try:
        llm_service = LanguageModelService(event)
    except Exception as exc:
        logger.warning(
            "[user-memory] cannot construct LanguageModelService for condense: [%s] %s",
            type(exc).__name__,
            exc,
        )
        return None

    messages = LanguageModelMessages(
        [
            LanguageModelSystemMessage(
                content=condensation_system_prompt(
                    max_tokens=max_tokens,
                    current_tokens=current_tokens,
                    target_tokens=target_tokens,
                )
            ),
            LanguageModelUserMessage(
                content=condensation_user_prompt(_sanitize_for_xml_context(body))
            ),
        ]
    )

    try:
        response = await llm_service.complete_async(
            messages=messages,
            model_name=language_model.name,
            other_options={"max_tokens": max_tokens + _LLM_OUTPUT_HEADROOM_TOKENS},
        )
    except Exception as exc:
        logger.warning(
            "[user-memory] condense LLM call failed (model=%s): [%s] %s",
            language_model.name,
            type(exc).__name__,
            exc,
        )
        return None

    if invocation_stats is not None and response.usage is not None:
        invocation_stats.append(
            LanguageModelInvocationStats.from_usage(
                language_model.name,
                response.usage,
                source=invocation_source,
            )
        )

    try:
        raw = response.choices[0].message.content or ""
    except Exception as exc:
        logger.warning(
            "[user-memory] could not extract content from condense response: [%s] %s",
            type(exc).__name__,
            exc,
        )
        return None

    if not isinstance(raw, str):
        logger.warning(
            "[user-memory] condense returned non-string content (%s)",
            type(raw).__name__,
        )
        return None

    candidate = _profile_body(_strip_code_fences(raw))
    if not _is_well_formed_profile(candidate):
        logger.warning(
            "[user-memory] condense output did not look like a profile (%d chars)",
            len(candidate),
        )
        return None

    return candidate


async def fit_user_memory(
    *,
    content: str,
    max_tokens: int,
    language_model: LanguageModelInfo,
    event: ChatEvent,
    logger: Logger,
    invocation_stats: list[LanguageModelInvocationStats] | None = None,
    invocation_source: str = "user_memory_condense",
) -> str:
    """Ensure ``content`` fits ``max_tokens``, condensing before cutting.

    Fast path: content already within budget is returned untouched (no LLM
    call). Otherwise the profile is first condensed by the LLM, and only a
    still-oversized result is hard-cut by :func:`enforce_token_cap`.
    """
    if not content:
        return content

    if count_tokens(content=content, language_model=language_model) <= max_tokens:
        return content

    current_tokens = count_tokens(content=content, language_model=language_model)
    logger.info(
        "[user-memory] memory over budget (%d > %d tokens) - condensing via LLM",
        current_tokens,
        max_tokens,
    )
    condensed = await condense_user_memory(
        content=content,
        max_tokens=max_tokens,
        language_model=language_model,
        event=event,
        logger=logger,
        invocation_stats=invocation_stats,
        invocation_source=invocation_source,
    )
    if condensed is not None:
        condensed = _restore_frontmatter(content, condensed)
        condensed_tokens = count_tokens(
            content=condensed, language_model=language_model
        )
        if condensed_tokens <= max_tokens:
            logger.info(
                "[user-memory] memory condensed from %d to %d tokens (cap=%d)",
                current_tokens,
                condensed_tokens,
                max_tokens,
            )
            return condensed
        logger.info(
            "[user-memory] still over budget after condense (%d > %d) - "
            "applying hard cut",
            condensed_tokens,
            max_tokens,
        )
        content = condensed

    result = enforce_token_cap(
        content=content,
        max_tokens=max_tokens,
        language_model=language_model,
    )
    logger.info(
        "[user-memory] memory condensed from %d to %d tokens (cap=%d)",
        current_tokens,
        count_tokens(content=result, language_model=language_model),
        max_tokens,
    )
    return result


async def load_user_memory(
    *,
    event: ChatEvent,
    config: UserMemoryConfig,
    language_model: LanguageModelInfo,
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
    invocation_stats: list[LanguageModelInvocationStats] = []
    return UserMemoryState(
        scope_id=scope_id,
        text=await fit_user_memory(
            content=text,
            max_tokens=config.max_tokens,
            language_model=language_model,
            event=event,
            logger=logger,
            invocation_stats=invocation_stats,
            invocation_source="user_memory_load_condense",
        ),
        load_invocation_stats=tuple(invocation_stats),
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


async def should_consolidate_memory(
    *,
    current_memory: str,
    user_id: str,
    user_message: str,
    assistant_message: str,
    language_model: LanguageModelInfo,
    event: ChatEvent,
    logger: Logger,
    invocation_stats: list[LanguageModelInvocationStats] | None = None,
) -> bool:
    """Cheaply decide whether the turn warrants a full memory rewrite.

    Runs a focused LLM call capped at a few output tokens that answers
    ``UPDATE`` or ``NOOP``. Returns ``False`` only on an explicit ``NOOP``
    so the caller can skip the expensive full-profile regeneration. Any
    error (or ambiguous output) falls back to ``True`` so behaviour stays
    identical to the pre-gate path.
    """
    try:
        llm_service = LanguageModelService(event)
    except Exception as exc:
        logger.warning(
            "[user-memory] cannot construct LanguageModelService for gate: [%s] %s",
            type(exc).__name__,
            exc,
        )
        return True

    messages = LanguageModelMessages(
        [
            LanguageModelSystemMessage(content=memory_gate_system_prompt()),
            LanguageModelUserMessage(
                content=memory_gate_user_prompt(
                    user_id=user_id,
                    existing_memory=current_memory,
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
            model_name=language_model.name,
            other_options={"max_tokens": _GATE_MAX_TOKENS},
        )
    except Exception as exc:
        logger.warning(
            "[user-memory] gate LLM call failed (model=%s): [%s] %s",
            language_model.name,
            type(exc).__name__,
            exc,
        )
        return True

    if invocation_stats is not None and response.usage is not None:
        invocation_stats.append(
            LanguageModelInvocationStats.from_usage(
                language_model.name,
                response.usage,
                source="user_memory_gate",
            )
        )

    try:
        raw = response.choices[0].message.content or ""
    except Exception as exc:
        logger.warning(
            "[user-memory] could not extract content from gate response: [%s] %s",
            type(exc).__name__,
            exc,
        )
        return True

    if not isinstance(raw, str):
        logger.warning(
            "[user-memory] gate returned non-string content (%s)",
            type(raw).__name__,
        )
        return True

    decision = raw.strip().upper()
    if decision.startswith("NOOP"):
        logger.info("[user-memory] gate decided NOOP - skipping consolidation")
        return False

    logger.info("[user-memory] gate decided UPDATE - consolidating")
    return True


async def consolidate_user_memory(
    *,
    current_memory: str,
    user_id: str,
    user_message: str,
    assistant_message: str,
    config: UserMemoryConfig,
    language_model: LanguageModelInfo,
    event: ChatEvent,
    logger: Logger,
    on_update_start: Callable[[], Awaitable[None]] = noop_update_callback,
    on_update_end: Callable[[], Awaitable[None]] = noop_update_callback,
    invocation_stats: list[LanguageModelInvocationStats] | None = None,
) -> str:
    """Consolidate the latest turn into the user's memory profile.

    When the (optional) gate decides the turn is worth remembering, the
    expensive full-profile rewrite runs. ``on_update_start`` is awaited
    just before that slow rewrite begins and ``on_update_end`` right after
    it finishes (even on failure), so a caller can surface a transient
    "updating memory" notice to the user only while real work happens.
    """
    safe_current = enforce_token_cap(
        content=current_memory,
        max_tokens=config.max_tokens,
        language_model=language_model,
    )
    logger.info(
        "[user-memory] consolidating turn - existing_memory_tokens=%d | "
        "user_msg_chars=%d | assistant_msg_chars=%d",
        count_tokens(content=safe_current, language_model=language_model),
        len(user_message or ""),
        len(assistant_message or ""),
    )

    if not (user_message or "").strip() and not (assistant_message or "").strip():
        return safe_current or enforce_token_cap(
            content=empty_profile(user_id),
            max_tokens=config.max_tokens,
            language_model=language_model,
        )

    if config.consolidation_gate_enabled and not await should_consolidate_memory(
        current_memory=safe_current,
        user_id=user_id,
        user_message=user_message,
        assistant_message=assistant_message,
        language_model=language_model,
        event=event,
        logger=logger,
        invocation_stats=invocation_stats,
    ):
        return safe_current

    try:
        await on_update_start()
        return await _rewrite_user_memory(
            safe_current=safe_current,
            user_id=user_id,
            user_message=user_message,
            assistant_message=assistant_message,
            config=config,
            language_model=language_model,
            event=event,
            logger=logger,
            invocation_stats=invocation_stats,
        )
    finally:
        await on_update_end()


async def _rewrite_user_memory(
    *,
    safe_current: str,
    user_id: str,
    user_message: str,
    assistant_message: str,
    config: UserMemoryConfig,
    language_model: LanguageModelInfo,
    event: ChatEvent,
    logger: Logger,
    invocation_stats: list[LanguageModelInvocationStats] | None = None,
) -> str:
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
                    existing_memory=_profile_body(safe_current),
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
            model_name=language_model.name,
            other_options={
                "max_tokens": config.max_tokens + _LLM_OUTPUT_HEADROOM_TOKENS,
            },
        )
    except Exception as exc:
        logger.warning(
            "[user-memory] consolidation LLM call failed (model=%s): [%s] %s",
            language_model.name,
            type(exc).__name__,
            exc,
        )
        return safe_current

    if invocation_stats is not None and response.usage is not None:
        invocation_stats.append(
            LanguageModelInvocationStats.from_usage(
                language_model.name,
                response.usage,
                source="user_memory_consolidation",
            )
        )

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

    candidate_body = _profile_body(_strip_code_fences(raw))
    if not _is_well_formed_profile(candidate_body):
        logger.warning(
            "[user-memory] LLM output did not look like a profile (%d chars)",
            len(candidate_body),
        )
        return safe_current

    if safe_current and candidate_body == _profile_body(safe_current):
        logger.debug("[user-memory] memory body unchanged - skipping update")
        return safe_current

    candidate = _assemble_profile(
        body=candidate_body,
        user_id=user_id,
        turn_count=_turn_count(safe_current) + 1,
    )
    capped = await fit_user_memory(
        content=candidate,
        max_tokens=config.max_tokens,
        language_model=language_model,
        event=event,
        logger=logger,
        invocation_stats=invocation_stats,
        invocation_source="user_memory_post_consolidation_condense",
    )
    logger.info(
        "[user-memory] consolidation produced %d tokens (cap=%d)",
        count_tokens(content=capped, language_model=language_model),
        config.max_tokens,
    )
    return capped


def _sanitize_for_xml_context(text: str) -> str:
    return text.replace("</", "< /")


def _is_well_formed_profile(content: str) -> bool:
    if not content or len(content.strip()) < 20:
        return False
    return content.startswith("# User Memory") and "## Identity" in content


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
