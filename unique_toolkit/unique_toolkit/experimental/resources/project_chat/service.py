"""The :class:`ProjectChats` service: search and read a project's earlier chats.

.. warning::

    **Experimental.** Lives under :mod:`unique_toolkit.experimental`. The
    public API may change without notice.

Wraps :class:`unique_sdk.ProjectChat` for one project of one user:

- :meth:`ProjectChats.search`: the chunks that best match a query.
- :meth:`ProjectChats.list_chunks`: one chat in order, one page at a time.
- :meth:`ProjectChats.list_recent`: the chats, most recently active first.

Every method has an ``_async`` twin with the same signature. Only the
project's owner can call the endpoints.
"""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING, Self

from unique_toolkit._common.validate_required_values import validate_required_values
from unique_toolkit.experimental.resources.project_chat.functions import (
    list_project_chat_chunks,
    list_project_chat_chunks_async,
    list_recent_project_chats,
    list_recent_project_chats_async,
    search_project_chats,
    search_project_chats_async,
)
from unique_toolkit.experimental.resources.project_chat.schemas import (
    ProjectChatChunkPage,
    ProjectChatSummaryPage,
)

if TYPE_CHECKING:
    from unique_toolkit.app.schemas import ChatEvent
    from unique_toolkit.app.unique_settings import UniqueContext, UniqueSettings


class ProjectChats:
    """The earlier chats of one project, searched and read as its owner.

    .. warning::

        **Experimental.** Import path is
        :mod:`unique_toolkit.experimental.resources.project_chat`. The API may
        change without notice.
    """

    def __init__(self, *, user_id: str, company_id: str, project_id: str) -> None:
        [user_id, company_id, project_id] = validate_required_values(
            [user_id, company_id, project_id]
        )
        if not project_id:
            raise ValueError("project_id must not be empty.")
        self._user_id = user_id
        self._company_id = company_id
        self._project_id = project_id

    # ── Construction ──────────────────────────────────────────────────────

    @classmethod
    def from_event(cls, event: ChatEvent) -> Self:
        """Create for the project of a chat event.

        Raises:
            ValueError: The event does not come from a project chat.
        """
        project_id = event.payload.project_id
        if not project_id:
            raise ValueError("The chat event has no project_id: not a project chat.")
        return cls(
            user_id=event.user_id,
            company_id=event.company_id,
            project_id=project_id,
        )

    @classmethod
    def from_context(cls, context: UniqueContext, *, project_id: str) -> Self:
        """Create from a :class:`UniqueContext` and a project id."""
        return cls(
            user_id=context.auth.get_confidential_user_id(),
            company_id=context.auth.get_confidential_company_id(),
            project_id=project_id,
        )

    @classmethod
    def from_settings(cls, settings: UniqueSettings, *, project_id: str) -> Self:
        """Create from :class:`UniqueSettings` and a project id."""
        return cls.from_context(settings.context, project_id=project_id)

    @property
    def project_id(self) -> str:
        """The project this service is bound to."""
        return self._project_id

    # ── Search ────────────────────────────────────────────────────────────

    def search(
        self,
        *,
        query: str,
        chat_ids: list[str] | None = None,
        exclude_chat_ids: list[str] | None = None,
        created_after: datetime | None = None,
        created_before: datetime | None = None,
        limit: int | None = None,
        include_chat_stats: bool | None = None,
    ) -> ProjectChatChunkPage:
        """Return the chunks of the project's chats that best match ``query``.

        See :func:`~.functions.search_project_chats` for the arguments.
        """
        return search_project_chats(
            self._user_id,
            self._company_id,
            project_id=self._project_id,
            query=query,
            chat_ids=chat_ids,
            exclude_chat_ids=exclude_chat_ids,
            created_after=created_after,
            created_before=created_before,
            limit=limit,
            include_chat_stats=include_chat_stats,
        )

    async def search_async(
        self,
        *,
        query: str,
        chat_ids: list[str] | None = None,
        exclude_chat_ids: list[str] | None = None,
        created_after: datetime | None = None,
        created_before: datetime | None = None,
        limit: int | None = None,
        include_chat_stats: bool | None = None,
    ) -> ProjectChatChunkPage:
        """Async :meth:`search`."""
        return await search_project_chats_async(
            self._user_id,
            self._company_id,
            project_id=self._project_id,
            query=query,
            chat_ids=chat_ids,
            exclude_chat_ids=exclude_chat_ids,
            created_after=created_after,
            created_before=created_before,
            limit=limit,
            include_chat_stats=include_chat_stats,
        )

    # ── Read one chat ─────────────────────────────────────────────────────

    def list_chunks(
        self,
        *,
        chat_id: str,
        limit: int | None = None,
        after: str | None = None,
        include_chat_stats: bool | None = None,
    ) -> ProjectChatChunkPage:
        """Return one page of a chat's chunks, in order.

        See :func:`~.functions.list_project_chat_chunks` for the arguments.
        """
        return list_project_chat_chunks(
            self._user_id,
            self._company_id,
            project_id=self._project_id,
            chat_id=chat_id,
            limit=limit,
            after=after,
            include_chat_stats=include_chat_stats,
        )

    async def list_chunks_async(
        self,
        *,
        chat_id: str,
        limit: int | None = None,
        after: str | None = None,
        include_chat_stats: bool | None = None,
    ) -> ProjectChatChunkPage:
        """Async :meth:`list_chunks`."""
        return await list_project_chat_chunks_async(
            self._user_id,
            self._company_id,
            project_id=self._project_id,
            chat_id=chat_id,
            limit=limit,
            after=after,
            include_chat_stats=include_chat_stats,
        )

    # ── Recent chats ──────────────────────────────────────────────────────

    def list_recent(
        self,
        *,
        exclude_chat_ids: list[str] | None = None,
        updated_after: datetime | None = None,
        updated_before: datetime | None = None,
        limit: int | None = None,
        after: str | None = None,
    ) -> ProjectChatSummaryPage:
        """Return one page of the project's chats, most recently active first.

        See :func:`~.functions.list_recent_project_chats` for the arguments.
        """
        return list_recent_project_chats(
            self._user_id,
            self._company_id,
            project_id=self._project_id,
            exclude_chat_ids=exclude_chat_ids,
            updated_after=updated_after,
            updated_before=updated_before,
            limit=limit,
            after=after,
        )

    async def list_recent_async(
        self,
        *,
        exclude_chat_ids: list[str] | None = None,
        updated_after: datetime | None = None,
        updated_before: datetime | None = None,
        limit: int | None = None,
        after: str | None = None,
    ) -> ProjectChatSummaryPage:
        """Async :meth:`list_recent`."""
        return await list_recent_project_chats_async(
            self._user_id,
            self._company_id,
            project_id=self._project_id,
            exclude_chat_ids=exclude_chat_ids,
            updated_after=updated_after,
            updated_before=updated_before,
            limit=limit,
            after=after,
        )
