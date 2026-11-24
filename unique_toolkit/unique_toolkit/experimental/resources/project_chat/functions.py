"""Function wrappers around :class:`unique_sdk.ProjectChat`.

Each call has a sync and an ``_async`` variant. They take the acting user's
``user_id`` and ``company_id`` first, then keyword-only arguments, and return
the toolkit models from :mod:`.schemas`, so SDK ``TypedDict``\\s never leak out.

.. warning::

    **Experimental.** Lives under :mod:`unique_toolkit.experimental`. The API
    may change without notice.
"""

from __future__ import annotations

from datetime import datetime

import unique_sdk

from unique_toolkit.experimental.resources.project_chat.schemas import (
    ProjectChatChunkPage,
    ProjectChatSummaryPage,
)


def search_project_chats(
    user_id: str,
    company_id: str,
    *,
    project_id: str,
    query: str,
    chat_ids: list[str] | None = None,
    exclude_chat_ids: list[str] | None = None,
    created_after: datetime | None = None,
    created_before: datetime | None = None,
    limit: int | None = None,
    include_chat_stats: bool | None = None,
) -> ProjectChatChunkPage:
    """Return the chunks of the project's chats that best match ``query``.

    Args:
        user_id: The user who owns the project.
        company_id: The user's company.
        project_id: The project to search.
        query: What to look for, at most 2000 characters.
        chat_ids: Only search these chats.
        exclude_chat_ids: Leave out these chats, e.g. the current one.
        created_after: Only chunks whose first message is at or after this time.
        created_before: Only chunks whose first message is at or before this time.
        limit: Number of chunks, 1 to 50 (endpoint default 20).
        include_chat_stats: Also return chunk and token totals per chat.
    """
    result = unique_sdk.ProjectChat.search(
        user_id,
        company_id,
        project_id=project_id,
        query=query,
        chat_ids=chat_ids,
        exclude_chat_ids=exclude_chat_ids,
        created_after=created_after,
        created_before=created_before,
        limit=limit,
        include_chat_stats=include_chat_stats,
    )
    return ProjectChatChunkPage.model_validate(result, by_alias=True, by_name=True)


async def search_project_chats_async(
    user_id: str,
    company_id: str,
    *,
    project_id: str,
    query: str,
    chat_ids: list[str] | None = None,
    exclude_chat_ids: list[str] | None = None,
    created_after: datetime | None = None,
    created_before: datetime | None = None,
    limit: int | None = None,
    include_chat_stats: bool | None = None,
) -> ProjectChatChunkPage:
    """Async :func:`search_project_chats`."""
    result = await unique_sdk.ProjectChat.search_async(
        user_id,
        company_id,
        project_id=project_id,
        query=query,
        chat_ids=chat_ids,
        exclude_chat_ids=exclude_chat_ids,
        created_after=created_after,
        created_before=created_before,
        limit=limit,
        include_chat_stats=include_chat_stats,
    )
    return ProjectChatChunkPage.model_validate(result, by_alias=True, by_name=True)


def list_project_chat_chunks(
    user_id: str,
    company_id: str,
    *,
    project_id: str,
    chat_id: str,
    limit: int | None = None,
    after: str | None = None,
    include_chat_stats: bool | None = None,
) -> ProjectChatChunkPage:
    """Return one page of a chat's chunks, in order.

    Args:
        user_id: The user who owns the project.
        company_id: The user's company.
        project_id: The project of the chat.
        chat_id: The chat to read.
        limit: Number of chunks per page, 1 to 50 (endpoint default 20).
        after: ``next_cursor`` of the previous page.
        include_chat_stats: Also return the chat's chunk and token totals.
    """
    result = unique_sdk.ProjectChat.list_chunks(
        user_id,
        company_id,
        project_id=project_id,
        chat_id=chat_id,
        limit=limit,
        after=after,
        include_chat_stats=include_chat_stats,
    )
    return ProjectChatChunkPage.model_validate(result, by_alias=True, by_name=True)


async def list_project_chat_chunks_async(
    user_id: str,
    company_id: str,
    *,
    project_id: str,
    chat_id: str,
    limit: int | None = None,
    after: str | None = None,
    include_chat_stats: bool | None = None,
) -> ProjectChatChunkPage:
    """Async :func:`list_project_chat_chunks`."""
    result = await unique_sdk.ProjectChat.list_chunks_async(
        user_id,
        company_id,
        project_id=project_id,
        chat_id=chat_id,
        limit=limit,
        after=after,
        include_chat_stats=include_chat_stats,
    )
    return ProjectChatChunkPage.model_validate(result, by_alias=True, by_name=True)


def list_recent_project_chats(
    user_id: str,
    company_id: str,
    *,
    project_id: str,
    exclude_chat_ids: list[str] | None = None,
    updated_after: datetime | None = None,
    updated_before: datetime | None = None,
    limit: int | None = None,
    after: str | None = None,
) -> ProjectChatSummaryPage:
    """Return one page of the project's chats, most recently active first.

    Args:
        user_id: The user who owns the project.
        company_id: The user's company.
        project_id: The project to list.
        exclude_chat_ids: Leave out these chats.
        updated_after: Only chats active at or after this time.
        updated_before: Only chats last active at or before this time.
        limit: Number of chats per page, 1 to 20 (endpoint default 20).
        after: ``next_cursor`` of the previous page.
    """
    result = unique_sdk.ProjectChat.list_recent(
        user_id,
        company_id,
        project_id=project_id,
        exclude_chat_ids=exclude_chat_ids,
        updated_after=updated_after,
        updated_before=updated_before,
        limit=limit,
        after=after,
    )
    return ProjectChatSummaryPage.model_validate(result, by_alias=True, by_name=True)


async def list_recent_project_chats_async(
    user_id: str,
    company_id: str,
    *,
    project_id: str,
    exclude_chat_ids: list[str] | None = None,
    updated_after: datetime | None = None,
    updated_before: datetime | None = None,
    limit: int | None = None,
    after: str | None = None,
) -> ProjectChatSummaryPage:
    """Async :func:`list_recent_project_chats`."""
    result = await unique_sdk.ProjectChat.list_recent_async(
        user_id,
        company_id,
        project_id=project_id,
        exclude_chat_ids=exclude_chat_ids,
        updated_after=updated_after,
        updated_before=updated_before,
        limit=limit,
        after=after,
    )
    return ProjectChatSummaryPage.model_validate(result, by_alias=True, by_name=True)
