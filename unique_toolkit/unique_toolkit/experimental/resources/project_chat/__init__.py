"""``unique_toolkit.experimental.resources.project_chat``: a project's earlier chats.

.. warning::

    **Experimental.** This subpackage is exposed under
    :mod:`unique_toolkit.experimental` and its public API may change without
    notice. It is not covered by the toolkit's normal stability guarantees.

A thin, typed wrapper around :class:`unique_sdk.ProjectChat`. The entry point
is :class:`ProjectChats`; the subpackage also re-exports the response models
and the function wrappers.
"""

from unique_toolkit.experimental.resources.project_chat.functions import (
    list_project_chat_chunks,
    list_project_chat_chunks_async,
    list_recent_project_chats,
    list_recent_project_chats_async,
    search_project_chats,
    search_project_chats_async,
)
from unique_toolkit.experimental.resources.project_chat.schemas import (
    ProjectChatChunk,
    ProjectChatChunkPage,
    ProjectChatStats,
    ProjectChatSummary,
    ProjectChatSummaryPage,
)
from unique_toolkit.experimental.resources.project_chat.service import ProjectChats

__all__ = [
    "ProjectChatChunk",
    "ProjectChatChunkPage",
    "ProjectChatStats",
    "ProjectChatSummary",
    "ProjectChatSummaryPage",
    "ProjectChats",
    "list_project_chat_chunks",
    "list_project_chat_chunks_async",
    "list_recent_project_chats",
    "list_recent_project_chats_async",
    "search_project_chats",
    "search_project_chats_async",
]
