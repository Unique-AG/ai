from typing import (
    ClassVar,
    Literal,
    Unpack,
)

from unique_sdk._api_resource import APIResource
from unique_sdk._request_options import RequestOptions


class MessageAssessment(APIResource["MessageAssessment"]):
    OBJECT_NAME: ClassVar[Literal["message_assessment"]] = "message_assessment"

    class CreateParams(RequestOptions):
        assistant_message_id: str
        status: Literal["PENDING", "DONE", "ERROR"]
        explanation: str
        label: Literal["POSITIVE", "NEGATIVE", "VERIFIED", "UNVERIFIED"]
        type: Literal["HALLUCINATION", "COMPLIANCE"]
        isVisible: bool

    class ModifyParams(RequestOptions):
        assistant_message_id: str
        status: Literal["PENDING", "DONE", "ERROR"]
        explanation: str
        label: Literal["POSITIVE", "NEGATIVE", "VERIFIED", "UNVERIFIED"]
        type: Literal["HALLUCINATION", "COMPLIANCE"]

    @classmethod
    def create(
        cls,
        user_id: str,
        company_id: str,
        **params: Unpack["MessageAssessment.CreateParams"],
    ) -> "MessageAssessment":
        url = "/message-assessment"
        return cls._static_request(
            "post", url, user_id, company_id, params=params
        )

    @classmethod
    async def create_async(
        cls,
        user_id: str,
        company_id: str,
        **params: Unpack["MessageAssessment.CreateParams"],
    ) -> "MessageAssessment":
        url = "/message-assessment"
        return cls._static_request_async(
            "post", url, user_id, company_id, params=params
        )

    @classmethod
    def modify(
        cls,
        user_id: str,
        company_id: str,
        **params: Unpack["MessageAssessment.ModifyParams"],
    ) -> "MessageAssessment":
        url = "/message-assessment"
        return cls._static_request(
            "patch", url, user_id, company_id, params=params
        )

    @classmethod
    def modify_async(
        cls,
        user_id: str,
        company_id: str,
        **params: Unpack["MessageAssessment.ModifyParams"],
    ) -> "MessageAssessment":
        url = "/message-assessment"
        return cls._static_request_async(
            "patch", url, user_id, company_id, params=params
        )
