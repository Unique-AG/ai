from typing import ClassVar, List, Literal, NotRequired, TypedDict, Unpack, cast

from unique_sdk._api_resource import APIResource
from unique_sdk._request_options import RequestOptions


class LLMModels(APIResource["LLMModels"]):
    OBJECT_NAME: ClassVar[Literal["llm-models"]] = "llm-models"

    class GetParams(RequestOptions):
        """
        Parameters for getting available LLM models.
        """

        module: NotRequired[str | None]
        skipCache: NotRequired[bool | None]

    class LLMModelsResponse(TypedDict):
        """
        Response for getting available LLM models.
        """

        llmModels: List[str]
        object: Literal["llm-models"]

    @classmethod
    def get(
        cls,
        user_id: str,
        company_id: str,
        **params: Unpack["LLMModels.GetParams"],
    ) -> "LLMModels.LLMModelsResponse":
        """
        Get available LLM models.
        """
        return cast(
            "LLMModels.LLMModelsResponse",
            cls._static_request(
                "get",
                "/openai/models",
                user_id,
                company_id,
                params=params,
            ),
        )

    @classmethod
    async def get_async(
        cls,
        user_id: str,
        company_id: str,
        **params: Unpack["LLMModels.GetParams"],
    ) -> "LLMModels.LLMModelsResponse":
        """
        Async get available LLM models.
        """
        return cast(
            "LLMModels.LLMModelsResponse",
            await cls._static_request_async(
                "get",
                "/openai/models",
                user_id,
                company_id,
                params=params,
            ),
        )
