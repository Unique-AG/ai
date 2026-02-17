from typing import (
    Any,
    ClassVar,
    Dict,
    List,
    NotRequired,
    Optional,
    TypedDict,
    Unpack,
    cast,
)

from unique_sdk._api_resource import APIResource
from unique_sdk._request_options import RequestOptions


class User(APIResource["User"]):
    OBJECT_NAME: ClassVar[str] = "users"

    class GetParams(RequestOptions):
        """
        Parameters for getting users in a company.
        """

        skip: NotRequired[Optional[int]]
        take: NotRequired[Optional[int]]
        email: NotRequired[Optional[str]]
        displayName: NotRequired[Optional[str]]
        userName: NotRequired[Optional[str]]

    class UpdateUserConfigurationParams(RequestOptions):
        """
        Parameters for updating user configuration.
        """

        userConfiguration: Dict[str, Any]

    class UserGroup(TypedDict):
        id: str
        name: str
        externalId: Optional[str]
        parentId: Optional[str]
        createdAt: str
        updatedAt: str

    class UserGroupsResponse(TypedDict):
        groups: List["User.UserGroup"]

    class User(TypedDict):
        """
        Represents a user in the company.
        """

        id: str
        externalId: Optional[str]
        firstName: str
        lastName: str
        displayName: str
        userName: str
        email: str
        updatedAt: str
        createdAt: str
        active: bool

    class UserWithConfiguration(User):
        """
        Represents a user in the company with configuration.
        """

        userConfiguration: Dict[str, Any]

    class Users(TypedDict):
        """
        Response for getting users.
        """

        users: List["User.User"]

    @classmethod
    def get_users(
        cls,
        user_id: str,
        company_id: str,
        **params: Unpack["User.GetParams"],
    ) -> "User.Users":
        """
        Get users in a company.
        """
        return cast(
            "User.Users",
            cls._static_request(
                "get",
                "/users",
                user_id,
                company_id,
                params=params,
            ),
        )

    @classmethod
    async def get_users_async(
        cls,
        user_id: str,
        company_id: str,
        **params: Unpack["User.GetParams"],
    ) -> "User.Users":
        """
        Async get users in a company.
        """
        return cast(
            "User.Users",
            await cls._static_request_async(
                "get",
                "/users",
                user_id,
                company_id,
                params=params,
            ),
        )

    @classmethod
    def update_user_configuration(
        cls,
        user_id: str,
        company_id: str,
        **params: Unpack["User.UpdateUserConfigurationParams"],
    ) -> "User.UserWithConfiguration":
        """
        Update user configuration for the current user.
        """
        return cast(
            "User.UserWithConfiguration",
            cls._static_request(
                "patch",
                f"/users/{user_id}/configuration",
                user_id,
                company_id,
                params=params,
            ),
        )

    @classmethod
    async def update_user_configuration_async(
        cls,
        user_id: str,
        company_id: str,
        **params: Unpack["User.UpdateUserConfigurationParams"],
    ) -> "User.UserWithConfiguration":
        """
        Async update user configuration for the current user.
        """
        return cast(
            "User.UserWithConfiguration",
            await cls._static_request_async(
                "patch",
                f"/users/{user_id}/configuration",
                user_id,
                company_id,
                params=params,
            ),
        )

    @classmethod
    def get_by_id(
        cls,
        user_id: str,
        company_id: str,
        target_user_id: str,
    ) -> "User.User":
        """
        Get a user by their ID.
        """
        return cast(
            "User.User",
            cls._static_request(
                "get",
                f"/users/{target_user_id}",
                user_id,
                company_id,
            ),
        )

    @classmethod
    async def get_by_id_async(
        cls,
        user_id: str,
        company_id: str,
        target_user_id: str,
    ) -> "User.User":
        """
        Async get a user by their ID.
        """
        return cast(
            "User.User",
            await cls._static_request_async(
                "get",
                f"/users/{target_user_id}",
                user_id,
                company_id,
            ),
        )

    @classmethod
    def get_user_groups(
        cls,
        user_id: str,
        company_id: str,
        target_user_id: str,
    ) -> "User.UserGroupsResponse":
        return cast(
            "User.UserGroupsResponse",
            cls._static_request(
                "get",
                f"/users/{target_user_id}/groups",
                user_id,
                company_id,
            ),
        )

    @classmethod
    async def get_user_groups_async(
        cls,
        user_id: str,
        company_id: str,
        target_user_id: str,
    ) -> "User.UserGroupsResponse":
        return cast(
            "User.UserGroupsResponse",
            await cls._static_request_async(
                "get",
                f"/users/{target_user_id}/groups",
                user_id,
                company_id,
            ),
        )
