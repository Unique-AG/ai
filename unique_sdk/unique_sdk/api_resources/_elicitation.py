from typing import (
    Any,
    Literal,
    NotRequired,
    TypedDict,
    Unpack,
    cast,
)

from unique_sdk._api_resource import APIResource
from unique_sdk._request_options import RequestOptions
from unique_sdk._util import classproperty

ACTION_TYPES = Literal["ACCEPT", "DECLINE", "CANCEL"]
SOURCE_TYPES = Literal["INTERNAL_TOOL", "MCP_SERVER"]
MODE_TYPES = Literal["FORM", "URL"]


class Elicitation(APIResource["Elicitation"]):
    @classproperty
    def OBJECT_NAME(cls) -> Literal["elicitation"]:
        return "elicitation"

    class CreateParams(RequestOptions):
        """
        Parameters for creating an elicitation request.
        """

        mode: MODE_TYPES
        message: str
        toolName: str
        schema: NotRequired[dict[str, Any] | None]
        url: NotRequired[str | None]
        externalElicitationId: NotRequired[str | None]
        chatId: NotRequired[str | None]
        messageId: NotRequired[str | None]
        expiresInSeconds: NotRequired[int | None]
        metadata: NotRequired[dict[str, Any] | None]

    class RespondParams(RequestOptions):
        """
        Parameters for responding to an elicitation request.
        """

        elicitationId: str
        action: ACTION_TYPES
        content: NotRequired[dict[str, str | int | bool | list[str]] | None]

    class Elicitation(TypedDict):
        """
        Represents an elicitation request.
        """

        id: str
        object: str
        source: SOURCE_TYPES
        mode: MODE_TYPES
        status: str
        message: str
        mcpServerId: NotRequired[str | None]
        toolName: NotRequired[str | None]
        schema: NotRequired[dict[str, Any] | None]
        url: NotRequired[str | None]
        externalElicitationId: NotRequired[str | None]
        responseContent: NotRequired[dict[str, Any] | None]
        respondedAt: NotRequired[str | None]
        companyId: str
        userId: str
        chatId: NotRequired[str | None]
        messageId: NotRequired[str | None]
        metadata: NotRequired[dict[str, Any] | None]
        createdAt: str
        updatedAt: NotRequired[str | None]
        expiresAt: NotRequired[str | None]

    class ElicitationResponseResult(TypedDict):
        """
        Response for responding to an elicitation request.
        """

        success: bool
        message: NotRequired[str | None]

    class Elicitations(TypedDict):
        """
        Response for getting pending elicitations.
        """

        elicitations: list["Elicitation.Elicitation"]

    @classmethod
    def create_elicitation(
        cls,
        user_id: str,
        company_id: str,
        **params: Unpack["Elicitation.CreateParams"],
    ) -> "Elicitation.Elicitation":
        """
        Create an elicitation request in a company.
        """
        return cast(
            "Elicitation.Elicitation",
            cls._static_request(
                "post",
                "/elicitation",
                user_id,
                company_id,
                params=params,
            ),
        )

    @classmethod
    async def create_elicitation_async(
        cls,
        user_id: str,
        company_id: str,
        **params: Unpack["Elicitation.CreateParams"],
    ) -> "Elicitation.Elicitation":
        """
        Async create an elicitation request in a company.
        """
        return cast(
            "Elicitation.Elicitation",
            await cls._static_request_async(
                "post",
                "/elicitation",
                user_id,
                company_id,
                params=params,
            ),
        )

    @classmethod
    def get_pending_elicitations(
        cls,
        user_id: str,
        company_id: str,
    ) -> "Elicitation.Elicitations":
        """
        Get all pending elicitation requests for a user in a company.
        """
        return cast(
            "Elicitation.Elicitations",
            cls._static_request(
                "get",
                "/elicitation/pending",
                user_id,
                company_id,
            ),
        )

    @classmethod
    async def get_pending_elicitations_async(
        cls,
        user_id: str,
        company_id: str,
    ) -> "Elicitation.Elicitations":
        """
        Async get all pending elicitation requests for a user in a company.
        """
        return cast(
            "Elicitation.Elicitations",
            await cls._static_request_async(
                "get",
                "/elicitation/pending",
                user_id,
                company_id,
            ),
        )

    @classmethod
    def get_elicitation(
        cls,
        user_id: str,
        company_id: str,
        elicitation_id: str,
    ) -> "Elicitation.Elicitation":
        """
        Get an elicitation request by ID in a company.
        """
        return cast(
            "Elicitation.Elicitation",
            cls._static_request(
                "get",
                f"/elicitation/{elicitation_id}",
                user_id,
                company_id,
            ),
        )

    @classmethod
    async def get_elicitation_async(
        cls,
        user_id: str,
        company_id: str,
        elicitation_id: str,
    ) -> "Elicitation.Elicitation":
        """
        Async get an elicitation request by ID in a company.
        """
        return cast(
            "Elicitation.Elicitation",
            await cls._static_request_async(
                "get",
                f"/elicitation/{elicitation_id}",
                user_id,
                company_id,
            ),
        )

    @classmethod
    def respond_to_elicitation(
        cls,
        user_id: str,
        company_id: str,
        **params: Unpack["Elicitation.RespondParams"],
    ) -> "Elicitation.ElicitationResponseResult":
        """
        Respond to an elicitation request in a company.
        """
        return cast(
            "Elicitation.ElicitationResponseResult",
            cls._static_request(
                "post",
                "/elicitation/respond",
                user_id,
                company_id,
                params=params,
            ),
        )

    @classmethod
    async def respond_to_elicitation_async(
        cls,
        user_id: str,
        company_id: str,
        **params: Unpack["Elicitation.RespondParams"],
    ) -> "Elicitation.ElicitationResponseResult":
        """
        Async respond to an elicitation request in a company.
        """
        return cast(
            "Elicitation.ElicitationResponseResult",
            await cls._static_request_async(
                "post",
                "/elicitation/respond",
                user_id,
                company_id,
                params=params,
            ),
        )
