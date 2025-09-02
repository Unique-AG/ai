import json
from abc import abstractmethod
from typing import Any

from unique_toolkit import LanguageModelToolDescription
from unique_toolkit._common.endpoint_builder import (
    EndpointClassProtocol,
    EndpointClient,
)
from unique_toolkit.app.dev_util import ChatEvent
from unique_toolkit.content.schemas import ContentChunk
from unique_toolkit.language_model.schemas import (
    LanguageModelFunction,
)
from unique_toolkit.tools.config import GenericToolBuildConfig
from unique_toolkit.tools.schemas import BaseToolConfig, ToolCallResponse
from unique_toolkit.tools.tool import Tool
from unique_toolkit.tools.tool_progress_reporter import ToolProgressReporter


class EndpointToolFrontendConfig(BaseToolConfig):
    api_name: str


class EndpointToolConfig(EndpointToolFrontendConfig):
    endpoint: EndpointClassProtocol
    client: EndpointClient


class EndpointToolBuildConfig(GenericToolBuildConfig[EndpointToolConfig]):
    pass


class FakeEndpointClient(EndpointClient):
    def request(
        self,
        endpoint: EndpointClassProtocol,
        method: str,
        headers: dict[str, str],
        payload: dict[str, Any],
    ) -> dict[str, Any]:
        return {
            "status": "success",
            "payload": payload,
            "method": method,
            "headers": headers,
            "endpoint": endpoint,
        }


class EndpointTool(Tool[EndpointToolConfig]):
    settings: EndpointToolBuildConfig

    def __init__(
        self,
        config: EndpointToolConfig,
        event: ChatEvent,
        tool_progress_reporter: ToolProgressReporter | None = None,
    ):
        super().__init__(
            config=config, event=event, tool_progress_reporter=tool_progress_reporter
        )
        self._client = config.client
        self._endpoint = config.endpoint

    @abstractmethod
    def tool_description(self) -> LanguageModelToolDescription:
        raise NotImplementedError

    async def run(self, tool_call: LanguageModelFunction) -> ToolCallResponse:
        function_call = tool_call.to_openai_param()

        try:
            function_call_payload = json.loads(function_call.get("arguments", "{}"))
        except json.JSONDecodeError:
            return ToolCallResponse(
                id=tool_call.id or "unknown_id",
                name=tool_call.name,
                content_chunks=[
                    ContentChunk(
                        id=tool_call.id or "unknown_id",
                        order=0,
                        text="The arguments are not valid JSON",
                    )
                ],
            )

        response = self._client.request(
            endpoint=self._endpoint,
            payload=function_call_payload,
            headers={},
            method="POST",
        )

        return ToolCallResponse(
            id=tool_call.id or "unknown_id",
            name=tool_call.name,
            content_chunks=[
                ContentChunk(
                    id=tool_call.id or "unknown_id",
                    order=0,
                    text=json.dumps(response),
                )
            ],
        )
