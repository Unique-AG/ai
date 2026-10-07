from __future__ import annotations

from typing import Any
from unittest.mock import MagicMock, patch

import httpx
import pytest
from unique_search_proxy_core.agent_engines.vertexai.schema import (
    VertexAIAgentSearchRequest,
)

from unique_search_proxy_client.web.core.agent_engines.vertexai.client import (
    _get_base_api_client_from_adc,
)
from unique_search_proxy_client.web.core.agent_engines.vertexai.service import (
    VertexAIAgentSearchService,
)


def _vertex_request(**fields: Any) -> VertexAIAgentSearchRequest:
    return VertexAIAgentSearchRequest.model_validate(
        {
            "query": "hello",
            "timeout": 120,
            **fields,
        },
    )


class _Chunk:
    def __init__(self, text: str) -> None:
        self.text = text

    def model_dump(self, **_kwargs: Any) -> dict[str, str]:
        return {"text": self.text}


class TestVertexAIAgentSearchService:
    @pytest.mark.ai
    @pytest.mark.asyncio
    async def test_search_streams_answer(self) -> None:
        http_client = MagicMock()

        async def fake_stream(**_kwargs: Any):
            yield _Chunk("Hello ")
            yield _Chunk("world")

        with (
            patch(
                "unique_search_proxy_client.web.core.agent_engines.vertexai.service.get_vertex_client",
                return_value=MagicMock(),
            ) as get_vertex_client,
            patch(
                "unique_search_proxy_client.web.core.agent_engines.vertexai.service.stream_vertexai_response",
                side_effect=fake_stream,
            ),
        ):
            service = VertexAIAgentSearchService(http_client=http_client)
            result = await service.search(_vertex_request())

        assert result.answer == "Hello world"
        assert result.engine == "vertexai"
        get_vertex_client.assert_called_once_with(http_client)


class TestVertexHttpClient:
    @pytest.mark.ai
    def test_adc_client_receives_shared_httpx_client(self) -> None:
        http_client = MagicMock(spec=httpx.AsyncClient)

        with patch(
            "unique_search_proxy_client.web.core.agent_engines.vertexai.client.BaseApiClient",
        ) as base_api_client:
            _get_base_api_client_from_adc(http_client)

        options = base_api_client.call_args.kwargs["http_options"]
        assert options.httpx_async_client is http_client


class TestVertexSerialization:
    @pytest.mark.ai
    def test_agent_search_response_accepts_model_dump_raw(self) -> None:
        from pydantic import BaseModel
        from unique_search_proxy_core.schema import AgentSearchResponse

        class _SdkModel(BaseModel):
            text: str

        raw = _SdkModel(text="ok").model_dump(mode="json")
        payload = AgentSearchResponse(
            engine="vertexai",
            query="q",
            answer="ok",
            raw=raw,
        ).model_dump(mode="json")

        assert payload["raw"] == {"text": "ok"}
