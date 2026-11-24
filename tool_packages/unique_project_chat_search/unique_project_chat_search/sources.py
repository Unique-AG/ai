"""Turn project chat results into the platform's standard sources.

Every result becomes a :class:`ContentChunk` in the knowledge-base chunk layout
(``<|document|>`` and ``<|info|>`` sections, then the text), named like a web
search source (``Chat: "<title>"``) and linked to the chat, so the history
manager, citations and reference chips treat it like any other source.
"""

from __future__ import annotations

from datetime import datetime
from urllib.parse import quote

from unique_toolkit._common.token import count_tokens
from unique_toolkit.agentic.tools.utils.source_handling.schema import SECTIONS
from unique_toolkit.content.schemas import ContentChunk
from unique_toolkit.experimental.resources.project_chat import (
    ProjectChatChunk,
    ProjectChatSummary,
)

UNTITLED_CHAT = "Untitled chat"


def source_name(chat_title: str | None) -> str:
    """Reference name of a chat, following web search's ``<site>: "<title>"``."""
    return f'Chat: "{chat_title or UNTITLED_CHAT}"'


def chat_url(template: str, chat_id: str) -> str:
    """Link of a chat, with the id escaped into one path segment."""
    return template.format(chat_id=quote(chat_id, safe=""))


def _day(value: datetime) -> str:
    return value.strftime("%Y-%m-%d %H:%M UTC")


def _pairs(chunk: ProjectChatChunk) -> str:
    if chunk.pair_index_start == chunk.pair_index_end:
        return f"exchange {chunk.pair_index_start}"
    return f"exchanges {chunk.pair_index_start}-{chunk.pair_index_end}"


def _text(name: str, info: str, body: str = "") -> str:
    return SECTIONS["document"].format(name) + SECTIONS["info"].format(info) + body


def excerpt_source(chunk: ProjectChatChunk, *, url_template: str) -> ContentChunk:
    """Source for one excerpt of an earlier chat (search and read)."""
    name = source_name(chunk.chat_title)
    info = (
        f"Earlier chat in this project (chat_id {chunk.chat_id}), "
        f"{_pairs(chunk)}, {_day(chunk.created_at)}"
    )
    return ContentChunk(
        id=chunk.chat_id,
        chunk_id=str(chunk.chunk_index),
        order=chunk.chunk_index,
        key=name,
        title=name,
        url=chat_url(url_template, chunk.chat_id),
        text=_text(name, info, chunk.text),
    )


def listing_source(
    chat: ProjectChatSummary, *, position: int, url_template: str
) -> ContentChunk:
    """Source for one chat of the recent listing: metadata only, no content."""
    name = source_name(chat.chat_title)
    excerpts = "excerpt" if chat.chunk_count == 1 else "excerpts"
    info = (
        f"Earlier chat in this project (chat_id {chat.chat_id}), started "
        f"{_day(chat.chat_created_at)}, last active {_day(chat.updated_at)}, "
        f"{chat.chunk_count} {excerpts}. Listing only, no content: read it with "
        "mode=read before quoting it."
    )
    return ContentChunk(
        id=chat.chat_id,
        order=position,
        key=name,
        title=name,
        url=chat_url(url_template, chat.chat_id),
        text=_text(name, info),
    )


def fit_to_budget(
    sources: list[ContentChunk], max_tokens: int
) -> tuple[list[ContentChunk], int]:
    """Keep whole sources, in order, while they fit in ``max_tokens``.

    Returns:
        The kept sources and how many were left out.
    """
    kept: list[ContentChunk] = []
    used = 0
    for source in sources:
        tokens = count_tokens(source.text)
        if used + tokens > max_tokens:
            break
        kept.append(source)
        used += tokens
    return kept, len(sources) - len(kept)
