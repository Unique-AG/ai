"""Build Unique chat-embed URLs.

Mirrors ``widgetUrlFor`` from the browser extension
(``monorepo/next/apps/browser-extension/src/shared/config.ts``): the chat
frontend serves a chrome-less chat window at ``{frontend}/chat/embed`` (new
chat in a space) and ``{frontend}/chat/embed/{chatId}`` (existing chat), with
the space passed as the ``spaceId`` query parameter.
"""

from __future__ import annotations

from urllib.parse import quote, urlencode


def build_embed_url(
    frontend_base_url: str,
    space_id: str,
    chat_id: str | None = None,
) -> str:
    """Return the chat-embed URL for ``space_id`` (and optionally ``chat_id``).

    Args:
        frontend_base_url: Unique web app origin, e.g. ``https://next.qa.unique.app``.
        space_id: The space (assistant) id, e.g. ``assistant_...``.
        chat_id: Existing chat id to open; omitted for a fresh chat.
    """
    base = frontend_base_url.rstrip("/")
    path = f"/chat/embed/{quote(chat_id, safe='')}" if chat_id else "/chat/embed"
    query = urlencode({"spaceId": space_id})
    return f"{base}{path}?{query}"
