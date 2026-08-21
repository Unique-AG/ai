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

    def model_dump(self, **_kwargs: Any) -> dict[str, str]:
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


class TestVertexAIEnterpriseSearchLock:
    @pytest.mark.ai
    def test_grounding_uses_enterprise_tool_when_forced(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """
        Purpose: Search-proxy grounding calls use enterprise search when infra locks it.
        Why this matters: The derived request model does not copy config validators, so request-time coercion must happen at the Gemini config builder.
        Setup summary: Force the env lock, build a generate-content config with enable_enterprise_search=False, and assert the enterprise tool is selected.
        """
        from pydantic import BaseModel
        from unique_search_proxy_core.agent_engines.vertexai import (
            settings as vertex_settings,
        )

        from unique_search_proxy_client.web.core.agent_engines.vertexai.gemini import (
            build_generate_content_config,
        )

        monkeypatch.setattr(
            vertex_settings.vertex_ai_env_settings,
            "force_activate_enterprise_search",
            True,
        )

        class _Output(BaseModel):
            answer: str

        config = build_generate_content_config(
            generation_instructions="instr",
            output_schema=_Output,
            enable_enterprise_search=False,
        )
        assert config.tools is not None
        assert config.tools[0].enterprise_web_search is not None
        assert config.tools[0].google_search is None


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
