from typing import (
    ClassVar,
    Literal,
    Unpack,
)

from unique_sdk._api_resource import APIResource
from unique_sdk._request_options import RequestOptions


class MessageAssessment(APIResource["MessageAssessment"]):
    OBJECT_NAME: ClassVar[Literal["message_assessment"]] = "message_assessment"
    RESOURCE_URL = "/message-assessment"

    class CreateParams(RequestOptions):
        messageId: str
        status: Literal["PENDING", "DONE", "ERROR"]
        explanation: str | None
        label: Literal["POSITIVE", "NEGATIVE", "VERIFIED", "UNVERIFIED"] | None
        type: Literal["HALLUCINATION", "COMPLIANCE"] | None
        isVisible: bool

    class ModifyParams(RequestOptions):
        messageId: str
        type: Literal["HALLUCINATION", "COMPLIANCE"]
        status: Literal["PENDING", "DONE", "ERROR"] | None
        explanation: str | None
        label: Literal["POSITIVE", "NEGATIVE", "VERIFIED", "UNVERIFIED"] | None

    @classmethod
    def create(
        cls,
        user_id: str,
        company_id: str,
        **params: Unpack["MessageAssessment.CreateParams"],
    ) -> "MessageAssessment":
        return cls._static_request(
            "post", "/message-assessment", user_id, company_id, params=params
        )

    @classmethod
    async def create_async(
        cls,
        user_id: str,
        company_id: str,
        **params: Unpack["MessageAssessment.CreateParams"],
    ) -> "MessageAssessment":
        return await cls._static_request_async(
            "post", "/message-assessment", user_id, company_id, params=params
        )

    @classmethod
    def modify(
        cls,
        user_id: str,
        company_id: str,
        **params: Unpack["MessageAssessment.ModifyParams"],
    ) -> "MessageAssessment":
        url = f"{cls.RESOURCE_URL}/{params['messageId']}"
        return cls._static_request("patch", url, user_id, company_id, params=params)

    @classmethod
    async def modify_async(
        cls,
        user_id: str,
        company_id: str,
        **params: Unpack["MessageAssessment.ModifyParams"],
    ) -> "MessageAssessment":
        url = f"{cls.RESOURCE_URL}/{params['messageId']}"
        return await cls._static_request_async(
            "patch", url, user_id, company_id, params=params
        )
