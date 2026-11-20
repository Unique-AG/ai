"""Project memory: the per-project memory of a user's project chats.

Wraps the public endpoint ``/projects/{projectId}/memory``. Each project has
one memory, which only the project's owner can read, replace or delete.
"""

from typing import Any, Literal, TypedDict, cast

from unique_sdk._api_resource import APIResource
from unique_sdk._util import classproperty


class ProjectMemory(APIResource["ProjectMemory"]):
    """The calling user's memory for one of their projects.

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
        return f"/projects/{project_id}/memory"

    @staticmethod
    def _update_body(document: str, state: str | None) -> dict[str, Any]:
        # Only the endpoint's fields go into the body. Explicit arguments (no
        # **params) mean request options such as api_key or headers cannot
        # end up in the PATCH body: an unexpected keyword raises TypeError.
        body: dict[str, Any] = {"document": document}
        if state is not None:
            body["state"] = state
        return body

    @classmethod
    def retrieve(
        cls, user_id: str, company_id: str, project_id: str
    ) -> "ProjectMemory":
        """Get the memory of a project the user owns.

        Args:
            user_id (str): The user who owns the project.
            company_id (str): The user's company.
            project_id (str): The project.

        Returns:
            ProjectMemory: The memory; its fields are ``None`` until it is
                first written.

        Raises:
            InvalidRequestError: The project does not exist or belongs to
                another user or company (404).
            AuthenticationError: The API key is missing or invalid (401).
            PermissionError: The user lacks access, e.g. the Projects feature
                flag is off (403).
            APIError: Any other API failure.
        """
        return cast(
            "ProjectMemory",
            cls._static_request("get", cls._url(project_id), user_id, company_id),
        )

    @classmethod
    async def retrieve_async(
        cls, user_id: str, company_id: str, project_id: str
    ) -> "ProjectMemory":
        """Get the memory of a project the user owns.

        Args:
            user_id (str): The user who owns the project.
            company_id (str): The user's company.
            project_id (str): The project.

        Returns:
            ProjectMemory: The memory; its fields are ``None`` until it is
                first written.

        Raises:
            InvalidRequestError: The project does not exist or belongs to
                another user or company (404).
            AuthenticationError: The API key is missing or invalid (401).
            PermissionError: The user lacks access, e.g. the Projects feature
                flag is off (403).
            APIError: Any other API failure.
        """
        return cast(
            "ProjectMemory",
            await cls._static_request_async(
                "get", cls._url(project_id), user_id, company_id
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
    ) -> "ProjectMemory":
        """Create or replace the memory of a project the user owns.

        Args:
            user_id (str): The user who owns the project.
            company_id (str): The user's company.
            project_id (str): The project.
            document (str): Markdown document that replaces the stored one,
                at most 32 KB of UTF-8.
            state (str | None): JSON string that replaces the stored job
                state, at most 256 KB of UTF-8. When omitted or ``None``, the
                stored state is kept.

        Returns:
            ProjectMemory: The updated memory.

        Raises:
            InvalidRequestError: The project does not exist or belongs to
                another user or company (404), or a field is too large (400).
            AuthenticationError: The API key is missing or invalid (401).
            PermissionError: The user lacks access, e.g. the Projects feature
                flag is off (403).
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
    ) -> "ProjectMemory":
        """Create or replace the memory of a project the user owns.

        Args:
            user_id (str): The user who owns the project.
            company_id (str): The user's company.
            project_id (str): The project.
            document (str): Markdown document that replaces the stored one,
                at most 32 KB of UTF-8.
            state (str | None): JSON string that replaces the stored job
                state, at most 256 KB of UTF-8. When omitted or ``None``, the
                stored state is kept.

        Returns:
            ProjectMemory: The updated memory.

        Raises:
            InvalidRequestError: The project does not exist or belongs to
                another user or company (404), or a field is too large (400).
            AuthenticationError: The API key is missing or invalid (401).
            PermissionError: The user lacks access, e.g. the Projects feature
                flag is off (403).
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
            ),
        )

    @classmethod
    def delete(
        cls, user_id: str, company_id: str, project_id: str
    ) -> "ProjectMemory.DeletedObject":
        """Delete the memory of a project the user owns.

        Deleting a memory that does not exist succeeds.

        Args:
            user_id (str): The user who owns the project.
            company_id (str): The user's company.
            project_id (str): The project.

        Returns:
            ProjectMemory.DeletedObject: The deletion result, with the project
                id as ``id``.

        Raises:
            InvalidRequestError: The project does not exist or belongs to
                another user or company (404).
            AuthenticationError: The API key is missing or invalid (401).
            PermissionError: The user lacks access, e.g. the Projects feature
                flag is off (403).
            APIError: Any other API failure.
        """
        return cast(
            "ProjectMemory.DeletedObject",
            cls._static_request("delete", cls._url(project_id), user_id, company_id),
        )

    @classmethod
    async def delete_async(
        cls, user_id: str, company_id: str, project_id: str
    ) -> "ProjectMemory.DeletedObject":
        """Delete the memory of a project the user owns.

        Deleting a memory that does not exist succeeds.

        Args:
            user_id (str): The user who owns the project.
            company_id (str): The user's company.
            project_id (str): The project.

        Returns:
            ProjectMemory.DeletedObject: The deletion result, with the project
                id as ``id``.

        Raises:
            InvalidRequestError: The project does not exist or belongs to
                another user or company (404).
            AuthenticationError: The API key is missing or invalid (401).
            PermissionError: The user lacks access, e.g. the Projects feature
                flag is off (403).
            APIError: Any other API failure.
        """
        return cast(
            "ProjectMemory.DeletedObject",
            await cls._static_request_async(
                "delete", cls._url(project_id), user_id, company_id
            ),
        )
