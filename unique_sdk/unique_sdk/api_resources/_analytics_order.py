from __future__ import annotations

import builtins
from typing import Any, ClassVar, Literal, NotRequired, cast, get_args
from urllib.parse import quote_plus

from typing_extensions import Unpack

from unique_sdk._api_requestor import APIRequestor
from unique_sdk._api_resource import APIResource
from unique_sdk._request_options import RequestOptions
from unique_sdk._util import classproperty


class AnalyticsOrder(APIResource["AnalyticsOrder"]):
    @classproperty
    def OBJECT_NAME(cls) -> Literal["analytics-order"]:
        return "analytics-order"

    RESOURCE_URL = "/analytics/orders"

    AnalyticsTypeLiteral = Literal[
        "ACTIVE_USER",
        "CHAT_INTERACTION",
        "CHAT_INTERACTION_DETAILED",
        "INGESTION_STAT",
        "MODEL_USAGE",
        "NPS",
        "PRODUCT_METRICS",
        "REFERENCE_STAT",
        "USER_CHAT_EXPORT",
    ]

    ANALYTICS_TYPE_VALUES: ClassVar[tuple[str, ...]] = tuple(
        get_args(AnalyticsTypeLiteral)
    )

    class CreateParams(RequestOptions):
        type: "AnalyticsOrder.AnalyticsTypeLiteral"
        startDate: str
        endDate: str
        assistantId: NotRequired[str | None]

    class ListParams(RequestOptions):
        skip: NotRequired[int | None]
        take: NotRequired[int | None]

    id: str
    type: str
    state: str
    configuration: dict[str, Any]
    createdAt: str
    updatedAt: str
    stateUpdatedAt: str
    object: str

    @classmethod
    def create(
        cls,
        user_id: str,
        company_id: str,
        **params: Unpack["AnalyticsOrder.CreateParams"],
    ) -> "AnalyticsOrder":
        return cast(
            "AnalyticsOrder",
            cls._static_request(
                "post",
                cls.RESOURCE_URL,
                user_id,
                company_id,
                params,
            ),
        )

    @classmethod
    async def create_async(
        cls,
        user_id: str,
        company_id: str,
        **params: Unpack["AnalyticsOrder.CreateParams"],
    ) -> "AnalyticsOrder":
        return cast(
            "AnalyticsOrder",
            await cls._static_request_async(
                "post",
                cls.RESOURCE_URL,
                user_id,
                company_id,
                params,
            ),
        )

    @classmethod
    def list(
        cls,
        user_id: str,
        company_id: str,
        **params: Unpack["AnalyticsOrder.ListParams"],
    ) -> builtins.list["AnalyticsOrder"]:
        return cast(
            builtins.list["AnalyticsOrder"],
            cls._static_request(
                "get",
                cls.RESOURCE_URL,
                user_id,
                company_id,
                params,
            ),
        )

    @classmethod
    async def list_async(
        cls,
        user_id: str,
        company_id: str,
        **params: Unpack["AnalyticsOrder.ListParams"],
    ) -> builtins.list["AnalyticsOrder"]:
        return cast(
            builtins.list["AnalyticsOrder"],
            await cls._static_request_async(
                "get",
                cls.RESOURCE_URL,
                user_id,
                company_id,
                params,
            ),
        )

    @classmethod
    def retrieve(
        cls,
        user_id: str,
        company_id: str,
        order_id: str,
    ) -> "AnalyticsOrder":
        url = f"{cls.RESOURCE_URL}/{quote_plus(order_id)}"
        return cast(
            "AnalyticsOrder",
            cls._static_request("get", url, user_id, company_id),
        )

    @classmethod
    async def retrieve_async(
        cls,
        user_id: str,
        company_id: str,
        order_id: str,
    ) -> "AnalyticsOrder":
        url = f"{cls.RESOURCE_URL}/{quote_plus(order_id)}"
        return cast(
            "AnalyticsOrder",
            await cls._static_request_async("get", url, user_id, company_id),
        )

    @classmethod
    def delete(
        cls,
        user_id: str,
        company_id: str,
        order_id: str,
    ) -> "AnalyticsOrder":
        url = f"{cls.RESOURCE_URL}/{quote_plus(order_id)}"
        return cast(
            "AnalyticsOrder",
            cls._static_request("delete", url, user_id, company_id),
        )

    @classmethod
    async def delete_async(
        cls,
        user_id: str,
        company_id: str,
        order_id: str,
    ) -> "AnalyticsOrder":
        url = f"{cls.RESOURCE_URL}/{quote_plus(order_id)}"
        return cast(
            "AnalyticsOrder",
            await cls._static_request_async("delete", url, user_id, company_id),
        )

    @classmethod
    def download(
        cls,
        user_id: str,
        company_id: str,
        order_id: str,
    ) -> str:
        url = f"{cls.RESOURCE_URL}/{quote_plus(order_id)}/download"
        requestor = APIRequestor(user_id=user_id, company_id=company_id)
        rbody, rcode, rheaders = requestor.request_raw("get", url)
        if not 200 <= rcode < 300:
            requestor.interpret_response(rbody, rcode, rheaders)
        if isinstance(rbody, bytes):
            return rbody.decode("utf-8-sig")
        return str(rbody).lstrip("\ufeff")

    @classmethod
    async def download_async(
        cls,
        user_id: str,
        company_id: str,
        order_id: str,
    ) -> str:
        url = f"{cls.RESOURCE_URL}/{quote_plus(order_id)}/download"
        requestor = APIRequestor(user_id=user_id, company_id=company_id)
        rbody, rcode, rheaders = await requestor.request_raw_async("get", url)
        if not 200 <= rcode < 300:
            requestor.interpret_response(rbody, rcode, rheaders)
        if isinstance(rbody, bytes):
            return rbody.decode("utf-8-sig")
        return str(rbody).lstrip("\ufeff")
