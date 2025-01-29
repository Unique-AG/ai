from typing import (
    ClassVar,
    Literal,
    Unpack,
)

from unique_sdk._api_resource import APIResource
from unique_sdk._request_options import RequestOptions


class MessageAssessment(APIResource["MessageAssessment"]):
    OBJECT_NAME: ClassVar[Literal["message_assessment"]] = "message_assessment"

    class MessageAssessmentCreateParams(RequestOptions):
        assistant_message_id: str
        pass

    class MessageAssessmentModifyParams(RequestOptions):
        assistant_message_id: str
        pass

    @classmethod
    def create(
        cls,
        user_id: str,
        company_id: str,
        **params: Unpack["MessageAssessmentCreateParams"],
    ) -> "MessageAssessment":
        return cls._static_request(
            "post", cls.class_url(), user_id, company_id, params=params
        )

    @classmethod
    async def create_async(
        cls,
        user_id: str,
        company_id: str,
        **params: Unpack["MessageAssessmentCreateParams"],
    ) -> "MessageAssessment":
        return cls._static_request(
            "post", cls.class_url(), user_id, company_id, params=params
        )

    @classmethod
    def modify(
        cls,
        user_id: str,
        company_id: str,
        **params: Unpack["MessageAssessmentModifyParams"],
    ) -> "MessageAssessment":
        return cls._static_request(
            "patch", cls.class_url(), user_id, company_id, params=params
        )
