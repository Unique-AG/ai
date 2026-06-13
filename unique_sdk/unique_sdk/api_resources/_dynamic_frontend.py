from typing import Literal, cast

from typing_extensions import NotRequired, Unpack

from unique_sdk._api_resource import APIResource
from unique_sdk._request_options import RequestOptions
from unique_sdk._util import classproperty


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
            ),
        )

    @classmethod
    def modify(
        cls,
        space_id: str,
        user_id: str,
        company_id: str,
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
            ),
        )

    @classmethod
    def list(
        cls,
        user_id: str,
        company_id: str,
    ) -> list["DynamicFrontend"]:
        response = cls._static_request(
            "get",
            "/dynamic-frontend",
            user_id,
            company_id,
        )
        if isinstance(response, list):
            return cast(list[DynamicFrontend], response)
        data = response.get("data", []) if isinstance(response, dict) else []
        return cast(list[DynamicFrontend], data)
