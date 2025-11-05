from typing import (
    ClassVar,
    Literal,
    NotRequired,
    Optional,
    Unpack,
)

from unique_sdk._api_resource import APIResource
from unique_sdk._request_options import RequestOptions


class MessageAssessment(APIResource["MessageAssessment"]):
    OBJECT_NAME: ClassVar[Literal["message_assessment"]] = "message_assessment"
    RESOURCE_URL = "/message-assessment"

    class CreateParams(RequestOptions):
        messageId: str
        status: str
        type: NotRequired[Optional[str]]
        isVisible: NotRequired[Optional[bool]]
        explanation: Optional[str]
        label: NotRequired[Optional[str]]

    class ModifyParams(RequestOptions):
        messageId: str
        type: str
        status: NotRequired[Optional[str]]
        explanation: Optional[str]
        label: NotRequired[Optional[str]]
        isVisible: NotRequired[Optional[bool]]

    @classmethod
    def create(
        cls,
        user_id: str,
        company_id: str,
        **params: Unpack["MessageAssessment.CreateParams"],
    ) -> "MessageAssessment":
        return cls._static_request(
            "post", cls.RESOURCE_URL, user_id, company_id, params=params
        )

    @classmethod
    async def create_async(
        cls,
        user_id: str,
        company_id: str,
        **params: Unpack["MessageAssessment.CreateParams"],
    ) -> "MessageAssessment":
        return await cls._static_request_async(
            "post", cls.RESOURCE_URL, user_id, company_id, params=params
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
