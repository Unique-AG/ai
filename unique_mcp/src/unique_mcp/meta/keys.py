from __future__ import annotations

from enum import StrEnum

UNIQUE_META_PREFIX = "unique.app/"


class MetaKeys(StrEnum):
    """Canonical ``_meta`` key names for auth and chat context shared by every tool."""

    # Identity (auth scope)
    USER_ID = f"{UNIQUE_META_PREFIX}auth/user-id"
    COMPANY_ID = f"{UNIQUE_META_PREFIX}auth/company-id"

    # Chat session scope
    CHAT_ID = f"{UNIQUE_META_PREFIX}chat/chat-id"
    USER_MESSAGE_ID = f"{UNIQUE_META_PREFIX}chat/user-message-id"
    ASSISTANT_ID = f"{UNIQUE_META_PREFIX}chat/assistant-id"
    PARENT_CHAT_ID = f"{UNIQUE_META_PREFIX}chat/parent-chat-id"
    LAST_ASSISTANT_MESSAGE_ID = f"{UNIQUE_META_PREFIX}chat/last-assistant-message-id"
    LAST_USER_MESSAGE_TEXT = f"{UNIQUE_META_PREFIX}chat/last-user-message-text"

    # Tool listing
    TOOL_ICON = f"{UNIQUE_META_PREFIX}icon"

    # Unique AI tool configuration
    UNIQUE_AI_TOOL_SYSTEM_PROMPT = f"{UNIQUE_META_PREFIX}system-prompt"
    UNIQUE_AI_TOOL_USER_PROMPT = f"{UNIQUE_META_PREFIX}user-prompt"
    UNIQUE_AI_TOOL_FORMAT_INFORMATION = f"{UNIQUE_META_PREFIX}tool-format-information"


META_FLAT_ALIASES: dict[str, str] = {
    MetaKeys.USER_ID: "userId",
    MetaKeys.COMPANY_ID: "companyId",
    MetaKeys.CHAT_ID: "chatId",
    MetaKeys.USER_MESSAGE_ID: "messageId",
}

CONFIG_SCHEMA_META_KEY = "unique.app/config-schema"

CONFIG_META_KEY = "unique.app/config"

CONTEXT_REQUIREMENTS_META_KEY = "unique.app/context-requirements"

__all__ = [
    "CONTEXT_REQUIREMENTS_META_KEY",
    "CONFIG_META_KEY",
    "CONFIG_SCHEMA_META_KEY",
    "META_FLAT_ALIASES",
    "MetaKeys",
    "UNIQUE_META_PREFIX",
]
