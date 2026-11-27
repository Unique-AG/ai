"""Resolve knowledge-base folder/scope ids for search result deep links."""

from __future__ import annotations

import asyncio
import logging

from mcp_search.references import scope_id_from_chunk, scope_id_from_metadata
from unique_toolkit.app.unique_settings import UniqueSettings
from unique_toolkit.content.functions import search_contents_async
from unique_toolkit.content.schemas import ContentChunk

_LOGGER = logging.getLogger(__name__)

_LOOKUP_CONCURRENCY = 8


async def resolve_scope_ids(
    chunks: list[ContentChunk],
    settings: UniqueSettings,
) -> dict[str, str]:
    """Map content id → leaf scope id for the given search chunks.

    Uses ``folderIdPath`` (or ``ownerId``) already present on chunk metadata
    when available; otherwise looks up each missing content via
    ``Content.search`` using the caller's identity.
    """
    resolved: dict[str, str] = {}
    missing: set[str] = set()

    for chunk in chunks:
        if not chunk.id:
            continue
        if chunk.id in resolved:
            continue
        scope = scope_id_from_chunk(chunk)
        if scope:
            resolved[chunk.id] = scope
        else:
            missing.add(chunk.id)

    if not missing:
        return resolved

    user_id = settings.auth.get_confidential_user_id()
    company_id = settings.auth.get_confidential_company_id()
    semaphore = asyncio.Semaphore(_LOOKUP_CONCURRENCY)

    async def _lookup(content_id: str) -> tuple[str, str | None]:
        async with semaphore:
            try:
                contents = await search_contents_async(
                    user_id=user_id,
                    company_id=company_id,
                    chat_id=None,
                    where={"id": {"equals": content_id}},
                )
            except Exception:
                _LOGGER.exception(
                    "Failed to resolve scope for content_id=%s", content_id
                )
                return content_id, None

        if not contents:
            return content_id, None
        content = contents[0]
        scope = scope_id_from_metadata(content.metadata)
        return content_id, scope

    results = await asyncio.gather(*(_lookup(cid) for cid in missing))
    for content_id, scope in results:
        if scope:
            resolved[content_id] = scope
        else:
            _LOGGER.debug("No scope id found for content_id=%s", content_id)

    return resolved
