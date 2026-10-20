from __future__ import annotations

import json
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest
from unique_search_proxy_core.agent_engines.output_schema import AgentSearchOutput
from unique_search_proxy_core.agent_engines.vertexai.schema import (
    VertexAIAgentSearchRequest,
)
from unique_search_proxy_core.schema import AgentSearchDelta, AgentSearchDone
from unique_search_proxy_core.url_safety import (
    ResolvedCrawlTarget,
    UrlSafetyOutcome,
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

    @pytest.mark.ai
    @pytest.mark.asyncio
    @pytest.mark.parametrize("enable_redirect_resolution", [True, False])
    async def test_stream_respects_redirect_resolution_setting(
        self,
        enable_redirect_resolution: bool,
    ) -> None:
        """
        Purpose: Keep stream output consistent with the redirect-resolution setting.
        Why this matters: Enabled streams must not expose unresolved intermediate JSON.
        Setup summary: Stream two chunks and compare enabled and disabled output.
        """
        http_client = MagicMock()
        redirect_url = (
            "https://vertexaisearch.cloud.google.com/grounding-api-redirect/token"
        )
        final_url = "https://example.com/article"
        raw_answer = json.dumps(
            {
                "results": [
                    {
                        "source_url": redirect_url,
                        "source_title": "Example",
                        "detailed_answer": "Details",
                        "key_facts": ["Fact"],
                    }
                ]
            }
        )
        outcome = UrlSafetyOutcome(
            url=redirect_url,
            resolved=ResolvedCrawlTarget(
                normalized_url=final_url,
                hostname="example.com",
                resolved_ip="203.0.113.10",
                used_dns_resolution=True,
            ),
        )

        async def fake_stream(**_kwargs: Any):
            yield _Chunk(raw_answer[:6])
            yield _Chunk(raw_answer[6:])

        with (
            patch(
                "unique_search_proxy_client.web.core.agent_engines.vertexai.service.get_vertex_client",
                return_value=MagicMock(),
            ),
            patch(
                "unique_search_proxy_client.web.core.agent_engines.vertexai.service.stream_vertexai_response",
                side_effect=fake_stream,
            ),
            patch(
                "unique_search_proxy_client.web.core.agent_engines.vertexai.redirects.UrlSafetyService.validate_urls_individually",
                new_callable=AsyncMock,
                return_value=[outcome],
            ) as validate_urls,
        ):
            service = VertexAIAgentSearchService(http_client=http_client)
            events = [
                event
                async for event in service.stream(
                    _vertex_request(
                        enable_redirect_resolution=enable_redirect_resolution
                    )
                )
            ]

        deltas = [event.text for event in events if isinstance(event, AgentSearchDelta)]
        done = events[-1]
        assert isinstance(done, AgentSearchDone)
        if enable_redirect_resolution:
            assert len(deltas) == 1
            resolved = AgentSearchOutput.model_validate_json(deltas[0])
            assert resolved.results[0].source_url == final_url
            assert done.response.answer == deltas[0]
            validate_urls.assert_awaited_once_with(
                [redirect_url],
                redirect_http_client=http_client,
            )
        else:
            assert deltas == [raw_answer[:6], raw_answer[6:]]
            assert done.response.answer == raw_answer
            validate_urls.assert_not_awaited()


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
