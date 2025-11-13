from typing import (
    Any,
    ClassVar,
    Dict,
    List,
    Literal,
    NotRequired,
    Optional,
    TypedDict,
    Unpack,
    cast,
)

from unique_sdk._api_resource import APIResource
from unique_sdk._request_options import RequestOptions


class Group(APIResource["Group"]):
    OBJECT_NAME: ClassVar[Literal["group"]] = "group"

    class GetParams(RequestOptions):
        """
        Parameters for getting groups in a company.
        """

        skip: NotRequired[Optional[int]]
        take: NotRequired[Optional[int]]
        name: NotRequired[Optional[str]]

    class UpdateParams(RequestOptions):
        """
        Parameters for updating a group.
        """

        name: NotRequired[Optional[str]]

    class GroupMember(TypedDict):
        """
        Represents a member of a group.
        """

        entityId: str

    class Group(TypedDict):
        """
        Represents a group in the company.
        """

        id: str
        name: str
        configuration: Dict[str, Any]
        externalId: str
        parentId: Optional[str]
        roles: Optional[List[str]]
        members: Optional[List["Group.GroupMember"]]
        createdAt: str
        updatedAt: str

    class Groups(TypedDict):
        """
        Response for getting groups.
        """

        groups: List["Group.Group"]

    class DeleteResponse(TypedDict):
        """
        Response for deleting a group.
        """

        id: str

    @classmethod
    def get_groups(
        cls,
        user_id: str,
        company_id: str,
        **params: Unpack["Group.GetParams"],
    ) -> "Group.Groups":
        """
        Get groups in a company.
        """
        return cast(
            "Group.Groups",
            cls._static_request(
                "get",
                "/groups",
                user_id,
                company_id,
                params=params,
            ),
        )

    @classmethod
    async def get_groups_async(
        cls,
        user_id: str,
        company_id: str,
        **params: Unpack["Group.GetParams"],
    ) -> "Group.Groups":
        """
        Async get groups in a company.
        """
        return cast(
            "Group.Groups",
            await cls._static_request_async(
                "get",
                "/groups",
                user_id,
                company_id,
                params=params,
            ),
        )

    @classmethod
    def delete(
        cls,
        user_id: str,
        company_id: str,
        group_id: str,
    ) -> "Group.DeleteResponse":
        """
        Delete a group in a company.
        """
        return cast(
            "Group.DeleteResponse",
            cls._static_request(
                "delete",
                f"/groups/{group_id}",
                user_id,
                company_id,
            ),
        )

    @classmethod
    async def delete_async(
        cls,
        user_id: str,
        company_id: str,
        group_id: str,
    ) -> "Group.DeleteResponse":
        """
        Async delete a group in a company.
        """
        return cast(
            "Group.DeleteResponse",
            await cls._static_request_async(
                "delete",
                f"/groups/{group_id}",
                user_id,
                company_id,
            ),
        )

    @classmethod
    def update_group(
        cls,
        user_id: str,
        company_id: str,
        group_id: str,
        **params: Unpack["Group.UpdateParams"],
    ) -> "Group.Group":
        """
        Update a group in a company.
        """
        return cast(
            "Group.Group",
            cls._static_request(
                "patch",
                f"/groups/{group_id}",
                user_id,
                company_id,
                params=params,
            ),
        )

    @classmethod
    async def update_group_async(
        cls,
        user_id: str,
        company_id: str,
        group_id: str,
        **params: Unpack["Group.UpdateParams"],
    ) -> "Group.Group":
        """
        Async update a group in a company.
        """
        return cast(
            "Group.Group",
            await cls._static_request_async(
                "patch",
                f"/groups/{group_id}",
                user_id,
                company_id,
                params=params,
            ),
        )
