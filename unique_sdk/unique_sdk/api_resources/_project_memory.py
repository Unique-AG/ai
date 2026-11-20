from typing import Literal, NotRequired, TypedDict, Unpack, cast

from unique_sdk._api_resource import APIResource
from unique_sdk._request_options import RequestOptions
from unique_sdk._util import classproperty


class ProjectMemory(APIResource["ProjectMemory"]):
    """The calling user's memory for one of their projects.

    One memory per project; only the project's owner can reach it. Until the
    memory is first written, ``id``, ``document``, ``state``, ``createdAt``
    and ``updatedAt`` are ``None``.

    - ``document``: markdown that project chats read (at most 32 KB of UTF-8).
    - ``state``: opaque JSON string owned by the project memory job (at most
      256 KB of UTF-8). Not meant for display; other callers leave it unset.
    """

    @classproperty
    def OBJECT_NAME(cls) -> Literal["project-memory"]:
        return "project-memory"

    class UpdateParams(RequestOptions):
        document: str
        """Replaces the stored document."""
        state: NotRequired[str]
        """Replaces the stored state when set; the stored state is kept when omitted."""

    class DeletedObject(TypedDict):
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

    @classmethod
    def retrieve(
        cls, user_id: str, company_id: str, project_id: str
    ) -> "ProjectMemory":
        """Get the memory of a project the user owns."""
        return cast(
            "ProjectMemory",
            cls._static_request("get", cls._url(project_id), user_id, company_id),
        )

    @classmethod
    async def retrieve_async(
        cls, user_id: str, company_id: str, project_id: str
    ) -> "ProjectMemory":
        """Get the memory of a project the user owns."""
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
        **params: Unpack["ProjectMemory.UpdateParams"],
    ) -> "ProjectMemory":
        """Create or replace the memory of a project the user owns."""
        return cast(
            "ProjectMemory",
            cls._static_request(
                "patch",
                cls._url(project_id),
                user_id,
                company_id,
                params=params,
            ),
        )

    @classmethod
    async def modify_async(
        cls,
        user_id: str,
        company_id: str,
        project_id: str,
        **params: Unpack["ProjectMemory.UpdateParams"],
    ) -> "ProjectMemory":
        """Create or replace the memory of a project the user owns."""
        return cast(
            "ProjectMemory",
            await cls._static_request_async(
                "patch",
                cls._url(project_id),
                user_id,
                company_id,
                params=params,
            ),
        )

    @classmethod
    def delete(
        cls, user_id: str, company_id: str, project_id: str
    ) -> "ProjectMemory.DeletedObject":
        """Delete the memory of a project the user owns. Idempotent."""
        return cast(
            "ProjectMemory.DeletedObject",
            cls._static_request("delete", cls._url(project_id), user_id, company_id),
        )

    @classmethod
    async def delete_async(
        cls, user_id: str, company_id: str, project_id: str
    ) -> "ProjectMemory.DeletedObject":
        """Delete the memory of a project the user owns. Idempotent."""
        return cast(
            "ProjectMemory.DeletedObject",
            await cls._static_request_async(
                "delete", cls._url(project_id), user_id, company_id
            ),
        )
