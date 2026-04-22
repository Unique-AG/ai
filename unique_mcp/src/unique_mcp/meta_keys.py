from __future__ import annotations

from enum import StrEnum


class MetaKeys(StrEnum):
    """Canonical ``_meta`` key names for auth and chat context shared by every tool."""

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


META_FLAT_ALIASES: dict[str, str] = {
    MetaKeys.USER_ID: "userId",
    MetaKeys.COMPANY_ID: "companyId",
    MetaKeys.CHAT_ID: "chatId",
    MetaKeys.USER_MESSAGE_ID: "messageId",
}

__all__ = ["MetaKeys", "META_FLAT_ALIASES"]
