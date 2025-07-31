from typing import Any, ClassVar, Literal, Optional, TypedDict, Unpack, cast

from unique_sdk._api_resource import APIResource
from unique_sdk._request_options import RequestOptions


class Agent(APIResource["Agent"]):
    OBJECT_NAME: ClassVar[Literal["agent"]] = "agent"

    class ChatEventUserMessage(TypedDict):
        """
        Represents a user message in the chat event.
        """

        id: str
        text: str
        createdAt: str
        originalText: str
        language: str

    class ChatEventAssistantMessage(TypedDict):
        """
        Represents an assistant message in the chat event.
        """

        id: str
        createdAt: str

    class ChatEventAssistant(TypedDict):
        """
        Represents the assistant in the chat event.
        """

        name: str

    class ChatEventAdditionalParameters(TypedDict, total=False):
        """
        Additional parameters for the chat event.
        """

        translateToLanguage: str | None = None
        contentIdToTranslate: str | None = None

    class RunParams(RequestOptions):
        """
        Parameters for querying the assistant for a message.
        """

        name: str
        description: str
        configuration: dict[str, Any]
        chatId: str
        assistantId: str
        userMessage: "Agent.ChatEventUserMessage"
        assistantMessage: "Agent.ChatEventAssistantMessage"
        assistant: "Agent.ChatEventAssistant"
        toolParameters: dict[str, Any]
        userMetadata: dict[str, Any]
        metadataFilter: dict[str, Any] | None = None
        toolChoices: list[str] | None = None
        additionalParameters: Optional["Agent.ChatEventAdditionalParameters"]

    class RunResponse(TypedDict):
        """
        Response structure for running an agent.
        """

        moduleType: str
        name: str

    @classmethod
    def run(
        cls,
        user_id: str,
        company_id: str,
        **params: Unpack["Agent.RunParams"],
    ) -> "Agent.RunResponse":
        """
        Send a message in a space.
        """
        return cast(
            "Agent.RunResponse",
            cls._static_request(
                "post",
                "/agent/run",
                user_id,
                company_id,
                params=params,
            ),
        )

    @classmethod
    async def run_async(
        cls,
        user_id: str,
        company_id: str,
        **params: Unpack["Agent.RunParams"],
    ) -> "Agent.RunResponse":
        """
        Async send a message in a space.
        """
        return cast(
            "Agent.RunResponse",
            await cls._static_request_async(
                "post",
                "/agent/run",
                user_id,
                company_id,
                params=params,
            ),
        )
