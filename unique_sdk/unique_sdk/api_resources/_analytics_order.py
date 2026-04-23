from __future__ import annotations

import builtins
from typing import Any, Literal, NotRequired, cast
from urllib.parse import quote_plus

from typing_extensions import Unpack

from unique_sdk._api_resource import APIResource
from unique_sdk._request_options import RequestOptions
from unique_sdk._util import classproperty


class AnalyticsOrder(APIResource["AnalyticsOrder"]):
    """Analytics order resource for generating and managing analytics reports.

    Supports creating, listing, retrieving, deleting, and downloading
    analytics orders via the public API.
    """

    @classproperty
    def OBJECT_NAME(cls) -> Literal["analytics-order"]:
        return "analytics-order"

    RESOURCE_URL = "/analytics/orders"

    # -- Nested param types ------------------------------------------------

    class CreateParams(RequestOptions):
        type: str
        start_date: str
        end_date: str
        assistant_id: NotRequired[str | None]

    class ListParams(RequestOptions):
        skip: NotRequired[int | None]
        take: NotRequired[int | None]

    # -- Instance fields (typing only) -------------------------------------

    id: str
    companyId: str
    type: str
    state: str
    configuration: dict[str, Any]
    createdAt: str
    updatedAt: str
    stateUpdatedAt: str
    createdBy: str
    object: str

    # -- Class methods: sync -----------------------------------------------

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
    def list(
        cls,
        user_id: str,
        company_id: str,
        **params: Unpack["AnalyticsOrder.ListParams"],
    ) -> builtins.list["AnalyticsOrder"]:
        result = cls._static_request(
            "get",
            cls.RESOURCE_URL,
            user_id,
            company_id,
            params,
        )
        if isinstance(result, builtins.list):
            return cast(builtins.list["AnalyticsOrder"], result)
        items = result.get("items", []) if hasattr(result, "get") else []
        return cast(builtins.list["AnalyticsOrder"], items)

    @classmethod
    def retrieve(
        cls,
        user_id: str,
        company_id: str,
        order_id: str,
    ) -> "AnalyticsOrder":
        url = "%s/%s" % (cls.RESOURCE_URL, quote_plus(order_id))
        return cast(
            "AnalyticsOrder",
            cls._static_request("get", url, user_id, company_id),
        )

    @classmethod
    def delete(
        cls,
        user_id: str,
        company_id: str,
        order_id: str,
    ) -> "AnalyticsOrder":
        url = "%s/%s" % (cls.RESOURCE_URL, quote_plus(order_id))
        return cast(
            "AnalyticsOrder",
            cls._static_request("delete", url, user_id, company_id),
        )

    @classmethod
    def download(
        cls,
        user_id: str,
        company_id: str,
        order_id: str,
    ) -> str:
        """Download analytics order CSV content. Order must be in DONE state."""
        url = "%s/%s/download" % (cls.RESOURCE_URL, quote_plus(order_id))
        return cast(str, cls._static_request("get", url, user_id, company_id))

    # -- Class methods: async ----------------------------------------------

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
    async def list_async(
        cls,
        user_id: str,
        company_id: str,
        **params: Unpack["AnalyticsOrder.ListParams"],
    ) -> builtins.list["AnalyticsOrder"]:
        result = await cls._static_request_async(
            "get",
            cls.RESOURCE_URL,
            user_id,
            company_id,
            params,
        )
        if isinstance(result, builtins.list):
            return cast(builtins.list["AnalyticsOrder"], result)
        items = result.get("items", []) if hasattr(result, "get") else []
        return cast(builtins.list["AnalyticsOrder"], items)

    @classmethod
    async def retrieve_async(
        cls,
        user_id: str,
        company_id: str,
        order_id: str,
    ) -> "AnalyticsOrder":
        url = "%s/%s" % (cls.RESOURCE_URL, quote_plus(order_id))
        return cast(
            "AnalyticsOrder",
            await cls._static_request_async("get", url, user_id, company_id),
        )

    @classmethod
    async def delete_async(
        cls,
        user_id: str,
        company_id: str,
        order_id: str,
    ) -> "AnalyticsOrder":
        url = "%s/%s" % (cls.RESOURCE_URL, quote_plus(order_id))
        return cast(
            "AnalyticsOrder",
            await cls._static_request_async("delete", url, user_id, company_id),
        )

    @classmethod
    async def download_async(
        cls,
        user_id: str,
        company_id: str,
        order_id: str,
    ) -> str:
        """Async download analytics order CSV content. Order must be in DONE state."""
        url = "%s/%s/download" % (cls.RESOURCE_URL, quote_plus(order_id))
        return cast(
            str, await cls._static_request_async("get", url, user_id, company_id)
        )
