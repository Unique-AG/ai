"""The :class:`ProjectMemories` service: read a project's memory document.

.. warning::

    **Experimental.** Lives under :mod:`unique_toolkit.experimental`. The
    public API may change without notice.

Wraps :class:`unique_sdk.ProjectMemory` for one project of one user. Only the
project's owner can call the endpoint; the nightly memory job writes it, so
this service only reads the ``document`` that chats use.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Self

import unique_sdk

from unique_toolkit._common.validate_required_values import validate_required_values

if TYPE_CHECKING:
    from unique_toolkit.app.schemas import ChatEvent


class ProjectMemories:
    """The memory of one project, read as its owner.

    .. warning::

        **Experimental.** Import path is
        :mod:`unique_toolkit.experimental.resources.project_memory`. The API may
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

    def get_document(self) -> str | None:
        """The memory document, or ``None`` until the job first writes it."""
        memory = unique_sdk.ProjectMemory.retrieve(
            self._user_id, self._company_id, self._project_id
        )
        return memory.get("document") or None

    async def get_document_async(self) -> str | None:
        """Async variant of :meth:`get_document`."""
        memory = await unique_sdk.ProjectMemory.retrieve_async(
            self._user_id, self._company_id, self._project_id
        )
        return memory.get("document") or None
