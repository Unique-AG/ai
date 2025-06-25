from typing import (
    ClassVar,
    List,
    Literal,
    NotRequired,
    Optional,
    TypedDict,
    Union,
    Unpack,
    cast,
)

from unique_sdk._api_resource import APIResource
from unique_sdk._request_options import RequestOptions


class Responses(APIResource["Responses"]):
    OBJECT_NAME: ClassVar[Literal["openai.response"]] = "openai.response"

    class Reasoning(TypedDict):
        effort: Literal["low", "medium", "high"] | None = None
        summary: Literal["auto", "concise", "detailed"] | None = None

    class CreateParams(RequestOptions):
        # expand the input type to allow more complex structures. e.g.: image or file inputs
        input: str
        model: NotRequired[
            Literal[
                "AZURE_o4_MINI_2025_0416",
                "AZURE_o3_2025_0416",
            ]
        ]
        reasoning: Optional["Responses.Reasoning"] = None

    class OutputRefusal(TypedDict):
        type: Literal["refusal"]
        refusal: str

    class OutputText(TypedDict):
        type: Literal["output_text"]
        text: NotRequired[str]

    class OutputMessage(TypedDict):
        id: str
        content: Union["Responses.OutputText", "Responses.OutputRefusal"]
        role: Literal["assistant"]
        type: Literal["message"]

    # expand the output type to allow tool calls / web search
    class OutputItem(TypedDict):
        Union["Responses.OutputMessage"]

    id: str
    outputText: str
    model: Literal[
        "AZURE_o4_MINI_2025_0416",
        "AZURE_o3_2025_0416",
    ]
    output: List[OutputItem]
    reasoning: Optional["Responses.Reasoning"] = None

    @classmethod
    def create(
        cls,
        company_id: str,
        user_id: str | None = None,
        **params: Unpack["Responses.CreateParams"],
    ) -> "Responses":
        return cast(
            "Responses",
            cls._static_request(
                "post",
                cls.class_url(),
                company_id=company_id,
                user_id=user_id,
                params=params,
            ),
        )

    @classmethod
    async def create_async(
        cls,
        company_id: str,
        user_id: str | None = None,
        **params: Unpack["Responses.CreateParams"],
    ) -> "Responses":
        return cast(
            "Responses",
            await cls._static_request_async(
                "post",
                cls.class_url(),
                company_id=company_id,
                user_id=user_id,
                params=params,
            ),
        )
