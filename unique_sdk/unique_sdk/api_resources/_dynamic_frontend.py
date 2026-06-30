from __future__ import annotations

from typing import TYPE_CHECKING, Literal, cast

from typing_extensions import NotRequired, Unpack

from unique_sdk._api_resource import APIResource
from unique_sdk._request_options import RequestOptions
from unique_sdk._util import classproperty

if TYPE_CHECKING:
    from unique_sdk._client import _BaseClient


class DynamicFrontend(APIResource["DynamicFrontend"]):
    @classproperty
    def OBJECT_NAME(cls) -> Literal["dynamic-frontend"]:
        return "dynamic-frontend"

    id: str
    spaceId: str
    name: str
    contentId: str
    url: str | None
    configUrl: str | None
    status: dict[str, object] | None

    class CreateParams(RequestOptions):
        name: str
        contentId: str

    class UpdateParams(RequestOptions):
        contentId: str
        name: NotRequired[str | None]

    @classmethod
    def create(
        cls,
        user_id: str,
        company_id: str,
        client: "_BaseClient | None" = None,
        **params: Unpack["DynamicFrontend.CreateParams"],
    ) -> "DynamicFrontend":
        return cast(
            DynamicFrontend,
            cls._static_request(
                "post",
                "/dynamic-frontend",
                user_id,
                company_id,
                params=params,
                client=client,
            ),
        )

    @classmethod
    def modify(
        cls,
        space_id: str,
        user_id: str,
        company_id: str,
        client: "_BaseClient | None" = None,
        **params: Unpack["DynamicFrontend.UpdateParams"],
    ) -> "DynamicFrontend":
        return cast(
            DynamicFrontend,
            cls._static_request(
                "patch",
                f"/dynamic-frontend/{space_id}",
                user_id,
                company_id,
                params=params,
                client=client,
            ),
        )

    @classmethod
    def delete(
        cls,
        space_id: str,
        user_id: str,
        company_id: str,
        client: "_BaseClient | None" = None,
    ) -> "DynamicFrontend":
        """Delete a deployed Dynamic Frontend space."""
        return cast(
            DynamicFrontend,
            cls._static_request(
                "delete",
                f"/dynamic-frontend/{space_id}",
                user_id,
                company_id,
                client=client,
            ),
        )

    @classmethod
    def list(
        cls,
        user_id: str,
        company_id: str,
        client: "_BaseClient | None" = None,
    ) -> list["DynamicFrontend"]:
        response = cls._static_request(
            "get",
            "/dynamic-frontend",
            user_id,
            company_id,
            client=client,
        )
        if isinstance(response, list):
            return cast(list[DynamicFrontend], response)
        data = response.get("data", []) if isinstance(response, dict) else []
        return cast(list[DynamicFrontend], data)
