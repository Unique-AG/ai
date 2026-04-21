"""Canonical ``_meta`` key names on the Unique MCP wire.

The monorepo standard (see #22513) namespaces keys under ``unique.app/`` with
a **scope segment** — ``auth``, ``chat``, ``search`` — so unrelated fields do
not collide at the top level.

Pre-#22513 monorepo builds still emit **flat camelCase** aliases
(``userId``, ``companyId``, …). Those are tolerated through
:data:`META_FLAT_ALIASES` and gated by the
``enable_mcp_metadata_fallback_un_19145`` feature flag.

:class:`MetaKeys` is a :class:`~enum.StrEnum` so every member is both a real
enum value (iteration, reverse lookup via ``MetaKeys("unique.app/auth/user-id")``,
typed signatures) and a plain ``str`` (dict keys, pydantic ``validation_alias``,
JSON serialisation).
"""

from __future__ import annotations

from enum import StrEnum


class MetaKeys(StrEnum):
    """Canonical namespaced ``_meta`` key names."""

    # Identity (auth scope)
    USER_ID = "unique.app/auth/user-id"
    COMPANY_ID = "unique.app/auth/company-id"

    # Chat session scope
    CHAT_ID = "unique.app/chat/chat-id"
    USER_MESSAGE_ID = "unique.app/chat/user-message-id"
    ASSISTANT_ID = "unique.app/chat/assistant-id"
    PARENT_CHAT_ID = "unique.app/chat/parent-chat-id"
    LAST_ASSISTANT_MESSAGE_ID = "unique.app/chat/last-assistant-message-id"
    LAST_USER_MESSAGE_TEXT = "unique.app/chat/last-user-message-text"

    # Search scoping
    CONTENT_IDS = "unique.app/search/content-ids"
    METADATA_FILTER = "unique.app/search/metadata-filter"
    SELECTED_UPLOADED_FILE_IDS = "unique.app/search/selected-uploaded-file-ids"
    LANGUAGE_MODEL_MAX_INPUT_TOKENS = (
        "unique.app/search/language-model-max-input-tokens"
    )


META_FLAT_ALIASES: dict[str, str] = {
    MetaKeys.USER_ID: "userId",
    MetaKeys.COMPANY_ID: "companyId",
    MetaKeys.CHAT_ID: "chatId",
    MetaKeys.USER_MESSAGE_ID: "messageId",
}
"""Flat camelCase aliases produced by pre-#22513 monorepo builds.

Only keys present here are eligible for the camelCase fallback; anything
else must be sent under its canonical ``unique.app/...`` name.
"""


__all__ = ["MetaKeys", "META_FLAT_ALIASES"]
