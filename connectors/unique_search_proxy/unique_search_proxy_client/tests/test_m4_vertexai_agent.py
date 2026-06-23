from __future__ import annotations

from typing import Any
from unittest.mock import MagicMock, patch

import pytest
from unique_search_proxy_core.agent_engines.vertexai.schema import (
    VertexAIAgentSearchRequest,
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

    def model_dump(self) -> dict[str, str]:
        return {"text": self.text}


class TestVertexAIAgentSearchService:
    @pytest.mark.ai
    @pytest.mark.asyncio
    async def test_search_streams_answer(self) -> None:
        async def fake_stream(**_kwargs: Any):
            yield _Chunk("Hello ")
            yield _Chunk("world")

        with (
            patch(
                "unique_search_proxy_client.web.core.agent_engines.vertexai.service.get_vertex_client",
                return_value=MagicMock(),
            ),
            patch(
                "unique_search_proxy_client.web.core.agent_engines.vertexai.service.stream_vertexai_response",
                side_effect=fake_stream,
            ),
        ):
            service = VertexAIAgentSearchService()
            result = await service.search(_vertex_request())

        assert result.answer == "Hello world"
        assert result.engine == "vertexai"


class TestVertexSerialization:
    @pytest.mark.ai
    def test_agent_search_response_serializes_raw_with_bytes(self) -> None:
        from unique_search_proxy_core.schema import AgentSearchResponse

        from unique_search_proxy_client.web.core.agent_engines.serialization import (
            json_safe_sdk_object,
        )

        class _SdkModel:
            def model_dump(self) -> dict[str, object]:
                return {"text": "ok", "blob": b"\x8f\xff"}

        raw = json_safe_sdk_object(_SdkModel())
        payload = AgentSearchResponse(
            engine="vertexai",
            query="q",
            answer="ok",
            raw=raw,
        ).model_dump(mode="json")

        assert payload["raw"]["blob"]["__bytes_base64__"] == "j/8="
