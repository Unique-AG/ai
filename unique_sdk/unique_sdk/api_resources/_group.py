from typing import (
    ClassVar,
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

    class CreateParams(RequestOptions):
        """
        Parameters for creating a group.
        """

        name: str
        externalId: NotRequired[Optional[str]]
        parentId: NotRequired[Optional[str]]

    class UpdateParams(RequestOptions):
        """
        Parameters for updating a group.
        """

        name: NotRequired[Optional[str]]

    class AddUsersParams(RequestOptions):
        """
        Parameters for adding users to a group.
        """

        userIds: List[str]

    class RemoveUsersParams(RequestOptions):
        """
        Parameters for removing users from a group.
        """

        userIds: List[str]

    class GroupMember(TypedDict):
        """
        Represents a member of a group.
        """

        entityId: str

    class GroupMembership(TypedDict):
        """
        Represents a membership relationship between a user and a group.
        """

        entityId: str
        groupId: str
        createdAt: str

    class Group(TypedDict):
        """
        Represents a group in the company.
        """

        id: str
        name: str
        externalId: str
        parentId: Optional[str]
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

    class AddUsersToGroupResponse(TypedDict):
        """
        Response for adding users to a group.
        """

        memberships: List["Group.GroupMembership"]

    class RemoveUsersFromGroupResponse(TypedDict):
        """
        Response for removing users from a group.
        """

        success: bool

    @classmethod
    def create_group(
        cls,
        user_id: str,
        company_id: str,
        **params: Unpack["Group.CreateParams"],
    ) -> "Group.Group":
        """
        Create a group in a company.
        """
        return cast(
            "Group.Group",
            cls._static_request(
                "post",
                "/groups",
                user_id,
                company_id,
                params=params,
            ),
        )

    @classmethod
    async def create_group_async(
        cls,
        user_id: str,
        company_id: str,
        **params: Unpack["Group.CreateParams"],
    ) -> "Group.Group":
        """
        Async create a group in a company.
        """
        return cast(
            "Group.Group",
            await cls._static_request_async(
                "post",
                "/groups",
                user_id,
                company_id,
                params=params,
            ),
        )

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
    def delete_group(
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
    async def delete_group_async(
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

    @classmethod
    def add_users_to_group(
        cls,
        user_id: str,
        company_id: str,
        group_id: str,
        **params: Unpack["Group.AddUsersParams"],
    ) -> "Group.AddUsersToGroupResponse":
        """
        Add users to a group in a company.
        """
        return cast(
            "Group.AddUsersToGroupResponse",
            cls._static_request(
                "post",
                f"/groups/{group_id}/users",
                user_id,
                company_id,
                params=params,
            ),
        )

    @classmethod
    async def add_users_to_group_async(
        cls,
        user_id: str,
        company_id: str,
        group_id: str,
        **params: Unpack["Group.AddUsersParams"],
    ) -> "Group.AddUsersToGroupResponse":
        """
        Async add users to a group in a company.
        """
        return cast(
            "Group.AddUsersToGroupResponse",
            await cls._static_request_async(
                "post",
                f"/groups/{group_id}/users",
                user_id,
                company_id,
                params=params,
            ),
        )

    @classmethod
    def remove_users_from_group(
        cls,
        user_id: str,
        company_id: str,
        group_id: str,
        **params: Unpack["Group.RemoveUsersParams"],
    ) -> "Group.RemoveUsersFromGroupResponse":
        """
        Remove users from a group in a company.
        """
        return cast(
            "Group.RemoveUsersFromGroupResponse",
            cls._static_request(
                "delete",
                f"/groups/{group_id}/users",
                user_id,
                company_id,
                params=params,
            ),
        )

    @classmethod
    async def remove_users_from_group_async(
        cls,
        user_id: str,
        company_id: str,
        group_id: str,
        **params: Unpack["Group.RemoveUsersParams"],
    ) -> "Group.RemoveUsersFromGroupResponse":
        """
        Async remove users from a group in a company.
        """
        return cast(
            "Group.RemoveUsersFromGroupResponse",
            await cls._static_request_async(
                "delete",
                f"/groups/{group_id}/users",
                user_id,
                company_id,
                params=params,
            ),
        )
