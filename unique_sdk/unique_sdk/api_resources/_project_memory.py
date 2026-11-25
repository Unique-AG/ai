"""Project memory: the per-project memory of a user's project chats.

Wraps the endpoint ``/projects/{projectId}/memory``. Each project has one
memory. The endpoint is service-only: the calling service (the nightly
project memory job, which runs in assistants-core) acts for the project's
owner, so every call takes the owner's ``user_id`` and ``company_id`` and the
service's ``service_id``, sent as ``x-service-id``. Direct calls by users,
including the owner, are rejected (403).
"""

from typing import Any, Literal, TypedDict, cast
from urllib.parse import quote

from unique_sdk._api_resource import APIResource
from unique_sdk._util import classproperty


class ProjectMemory(APIResource["ProjectMemory"]):
    """The memory of one project, read and written for its owner.

    Until the memory is first written, ``id``, ``document``, ``state``,
    ``createdAt`` and ``updatedAt`` are ``None``.

    Attributes:
        id (str | None): Memory identifier.
        projectId (str): Project identifier.
        document (str | None): Markdown that project chats read, at most
            32 KB of UTF-8.
        state (str | None): Opaque JSON owned by the project memory job, at
            most 256 KB of UTF-8. Not meant for display.
        createdAt (str | None): Creation timestamp in ISO 8601 format.
        updatedAt (str | None): Last update timestamp in ISO 8601 format.
        object (Literal["project-memory"]): Object type identifier.
    """

    @classproperty
    def OBJECT_NAME(cls) -> Literal["project-memory"]:
        return "project-memory"

    class DeletedObject(TypedDict):
        """Response of ``delete`` and ``delete_async``.

        Attributes:
            id (str): The project id; a project has at most one memory.
            object (Literal["project-memory"]): Object type identifier.
            deleted (bool): Always ``True``.
        """

        id: str
        object: Literal["project-memory"]
        deleted: bool

    id: str | None
    projectId: str
    document: str | None
    state: str | None
    createdAt: str | None
    updatedAt: str | None
    object: Literal["project-memory"]

    @staticmethod
    def _url(project_id: str) -> str:
        # Escape the id so it stays one path segment: "/", "?" or "#" in a
        # caller- or agent-supplied id cannot reach another endpoint. quote()
        # leaves "." and ".." unchanged and HTTP clients collapse them as dot
        # segments (/projects/../memory -> /memory), and "" leaves an empty
        # segment, so those ids are rejected outright.
        if project_id in ("", ".", ".."):
            raise ValueError(f"invalid project id: {project_id!r}")
        return f"/projects/{quote(project_id, safe='')}/memory"

    @staticmethod
    def _update_body(document: str, state: str | None) -> dict[str, Any]:
        # Only the endpoint's fields go into the body. Explicit arguments (no
        # **params) mean request options such as api_key or headers cannot
        # end up in the PATCH body: an unexpected keyword raises TypeError.
        body: dict[str, Any] = {"document": document}
        if state is not None:
            body["state"] = state
        return body

    @staticmethod
    def _headers(service_id: str | None) -> dict[str, str] | None:
        # One named header instead of arbitrary headers, for the same reason
        # as _update_body: nothing else can be smuggled into the request.
        if service_id is None:
            return None
        if not service_id.strip():
            raise ValueError("service_id must not be empty")
        return {"x-service-id": service_id}

    @classmethod
    def retrieve(
        cls,
        user_id: str,
        company_id: str,
        project_id: str,
        *,
        service_id: str | None = None,
    ) -> "ProjectMemory":
        """Get the memory of a project, for its owner.

        Args:
            user_id (str): The project's owner.
            company_id (str): The owner's company.
            project_id (str): The project.
            service_id (str | None): The calling service, sent as
                ``x-service-id``. Required by the endpoint, which only admits
                the project memory service (``"assistants-core"``).

        Returns:
            ProjectMemory: The memory; its fields are ``None`` until it is
                first written.

        Raises:
            ValueError: ``project_id`` is empty, ``.`` or ``..``, or
                ``service_id`` is empty.
            InvalidRequestError: The project does not exist or belongs to
                another user or company (404).
            AuthenticationError: The API key is missing or invalid (401).
            PermissionError: The caller is not the project memory service,
                the user lacks access, or the Projects feature flag is off
                (403).
            APIError: Any other API failure.
        """
        return cast(
            "ProjectMemory",
            cls._static_request(
                "get",
                cls._url(project_id),
                user_id,
                company_id,
                supplied_headers=cls._headers(service_id),
            ),
        )

    @classmethod
    async def retrieve_async(
        cls,
        user_id: str,
        company_id: str,
        project_id: str,
        *,
        service_id: str | None = None,
    ) -> "ProjectMemory":
        """Get the memory of a project, for its owner.

        Args:
            user_id (str): The project's owner.
            company_id (str): The owner's company.
            project_id (str): The project.
            service_id (str | None): The calling service, sent as
                ``x-service-id``. Required by the endpoint, which only admits
                the project memory service (``"assistants-core"``).

        Returns:
            ProjectMemory: The memory; its fields are ``None`` until it is
                first written.

        Raises:
            ValueError: ``project_id`` is empty, ``.`` or ``..``, or
                ``service_id`` is empty.
            InvalidRequestError: The project does not exist or belongs to
                another user or company (404).
            AuthenticationError: The API key is missing or invalid (401).
            PermissionError: The caller is not the project memory service,
                the user lacks access, or the Projects feature flag is off
                (403).
            APIError: Any other API failure.
        """
        return cast(
            "ProjectMemory",
            await cls._static_request_async(
                "get",
                cls._url(project_id),
                user_id,
                company_id,
                supplied_headers=cls._headers(service_id),
            ),
        )

    @classmethod
    def modify(
        cls,
        user_id: str,
        company_id: str,
        project_id: str,
        *,
        document: str,
        state: str | None = None,
        service_id: str | None = None,
    ) -> "ProjectMemory":
        """Create or replace the memory of a project, for its owner.

        Args:
            user_id (str): The project's owner.
            company_id (str): The owner's company.
            project_id (str): The project.
            document (str): Markdown document that replaces the stored one,
                at most 32 KB of UTF-8.
            state (str | None): JSON string that replaces the stored job
                state, at most 256 KB of UTF-8. When omitted or ``None``, the
                stored state is kept.
            service_id (str | None): The calling service, sent as
                ``x-service-id``. Required by the endpoint, which only admits
                the project memory service (``"assistants-core"``).

        Returns:
            ProjectMemory: The updated memory.

        Raises:
            ValueError: ``project_id`` is empty, ``.`` or ``..``, or
                ``service_id`` is empty.
            InvalidRequestError: The project does not exist or belongs to
                another user or company (404), or a field is too large (400).
            AuthenticationError: The API key is missing or invalid (401).
            PermissionError: The caller is not the project memory service,
                the user lacks access, or the Projects feature flag is off
                (403).
            APIError: Any other API failure.
        """
        return cast(
            "ProjectMemory",
            cls._static_request(
                "patch",
                cls._url(project_id),
                user_id,
                company_id,
                params=cls._update_body(document, state),
                supplied_headers=cls._headers(service_id),
            ),
        )

    @classmethod
    async def modify_async(
        cls,
        user_id: str,
        company_id: str,
        project_id: str,
        *,
        document: str,
        state: str | None = None,
        service_id: str | None = None,
    ) -> "ProjectMemory":
        """Create or replace the memory of a project, for its owner.

        Args:
            user_id (str): The project's owner.
            company_id (str): The owner's company.
            project_id (str): The project.
            document (str): Markdown document that replaces the stored one,
                at most 32 KB of UTF-8.
            state (str | None): JSON string that replaces the stored job
                state, at most 256 KB of UTF-8. When omitted or ``None``, the
                stored state is kept.
            service_id (str | None): The calling service, sent as
                ``x-service-id``. Required by the endpoint, which only admits
                the project memory service (``"assistants-core"``).

        Returns:
            ProjectMemory: The updated memory.

        Raises:
            ValueError: ``project_id`` is empty, ``.`` or ``..``, or
                ``service_id`` is empty.
            InvalidRequestError: The project does not exist or belongs to
                another user or company (404), or a field is too large (400).
            AuthenticationError: The API key is missing or invalid (401).
            PermissionError: The caller is not the project memory service,
                the user lacks access, or the Projects feature flag is off
                (403).
            APIError: Any other API failure.
        """
        return cast(
            "ProjectMemory",
            await cls._static_request_async(
                "patch",
                cls._url(project_id),
                user_id,
                company_id,
                params=cls._update_body(document, state),
                supplied_headers=cls._headers(service_id),
            ),
        )

    @classmethod
    def delete(
        cls,
        user_id: str,
        company_id: str,
        project_id: str,
        *,
        service_id: str | None = None,
    ) -> "ProjectMemory.DeletedObject":
        """Delete the memory of a project, for its owner.

        Deleting a memory that does not exist succeeds.

        Args:
            user_id (str): The project's owner.
            company_id (str): The owner's company.
            project_id (str): The project.
            service_id (str | None): The calling service, sent as
                ``x-service-id``. Required by the endpoint, which only admits
                the project memory service (``"assistants-core"``).

        Returns:
            ProjectMemory.DeletedObject: The deletion result, with the project
                id as ``id``.

        Raises:
            ValueError: ``project_id`` is empty, ``.`` or ``..``, or
                ``service_id`` is empty.
            InvalidRequestError: The project does not exist or belongs to
                another user or company (404).
            AuthenticationError: The API key is missing or invalid (401).
            PermissionError: The caller is not the project memory service,
                the user lacks access, or the Projects feature flag is off
                (403).
            APIError: Any other API failure.
        """
        return cast(
            "ProjectMemory.DeletedObject",
            cls._static_request(
                "delete",
                cls._url(project_id),
                user_id,
                company_id,
                supplied_headers=cls._headers(service_id),
            ),
        )

    @classmethod
    async def delete_async(
        cls,
        user_id: str,
        company_id: str,
        project_id: str,
        *,
        service_id: str | None = None,
    ) -> "ProjectMemory.DeletedObject":
        """Delete the memory of a project, for its owner.

        Deleting a memory that does not exist succeeds.

        Args:
            user_id (str): The project's owner.
            company_id (str): The owner's company.
            project_id (str): The project.
            service_id (str | None): The calling service, sent as
                ``x-service-id``. Required by the endpoint, which only admits
                the project memory service (``"assistants-core"``).

        Returns:
            ProjectMemory.DeletedObject: The deletion result, with the project
                id as ``id``.

        Raises:
            ValueError: ``project_id`` is empty, ``.`` or ``..``, or
                ``service_id`` is empty.
            InvalidRequestError: The project does not exist or belongs to
                another user or company (404).
            AuthenticationError: The API key is missing or invalid (401).
            PermissionError: The caller is not the project memory service,
                the user lacks access, or the Projects feature flag is off
                (403).
            APIError: Any other API failure.
        """
        return cast(
            "ProjectMemory.DeletedObject",
            await cls._static_request_async(
                "delete",
                cls._url(project_id),
                user_id,
                company_id,
                supplied_headers=cls._headers(service_id),
            ),
        )
