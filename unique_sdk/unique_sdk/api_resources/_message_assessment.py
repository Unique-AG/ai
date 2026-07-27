from __future__ import annotations

from typing import TYPE_CHECKING, Literal, Unpack

from unique_sdk._api_resource import APIResource
from unique_sdk._request_options import RequestOptions
from unique_sdk._util import classproperty

if TYPE_CHECKING:
    from unique_sdk._client import _BaseClient


class MessageAssessment(APIResource["MessageAssessment"]):
    @classproperty
    def OBJECT_NAME(cls) -> Literal["message_assessment"]:
        return "message_assessment"

    RESOURCE_URL = "/message-assessment"

    class CreateParams(RequestOptions):
        messageId: str
        status: Literal["PENDING", "DONE", "ERROR"]
        type: Literal["HALLUCINATION", "COMPLIANCE"]
        isVisible: bool
        title: str | None
        explanation: str | None
        label: Literal["RED", "YELLOW", "GREEN"] | None

    class ModifyParams(RequestOptions):
        messageId: str
        type: Literal["HALLUCINATION", "COMPLIANCE"]
        status: Literal["PENDING", "DONE", "ERROR"] | None
        title: str | None
        explanation: str | None
        label: Literal["RED", "YELLOW", "GREEN"] | None

    @classmethod
    def create(
        cls,
        user_id: str,
        company_id: str,
        client: "_BaseClient | None" = None,
        **params: Unpack["MessageAssessment.CreateParams"],
    ) -> "MessageAssessment":
        return cls._static_request(
            "post", cls.RESOURCE_URL, user_id, company_id, params=params, client=client
        )

    @classmethod
    async def create_async(
        cls,
        user_id: str,
        company_id: str,
        client: "_BaseClient | None" = None,
        **params: Unpack["MessageAssessment.CreateParams"],
    ) -> "MessageAssessment":
        return await cls._static_request_async(
            "post", cls.RESOURCE_URL, user_id, company_id, params=params, client=client
        )

    @classmethod
    def modify(
        cls,
        user_id: str,
        company_id: str,
        client: "_BaseClient | None" = None,
        **params: Unpack["MessageAssessment.ModifyParams"],
    ) -> "MessageAssessment":
        url = f"{cls.RESOURCE_URL}/{params['messageId']}"
        return cls._static_request(
            "patch", url, user_id, company_id, params=params, client=client
        )

    @classmethod
    async def modify_async(
        cls,
        user_id: str,
        company_id: str,
        client: "_BaseClient | None" = None,
        **params: Unpack["MessageAssessment.ModifyParams"],
    ) -> "MessageAssessment":
        url = f"{cls.RESOURCE_URL}/{params['messageId']}"
        return await cls._static_request_async(
            "patch", url, user_id, company_id, params=params, client=client
        )
