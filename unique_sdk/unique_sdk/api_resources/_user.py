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
        userConfiguration: Dict[str, Any]
        source: Optional[str]
        updatedAt: str
        createdAt: str
        active: bool

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
