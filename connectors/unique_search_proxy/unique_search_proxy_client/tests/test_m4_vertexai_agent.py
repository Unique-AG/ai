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
from unique_search_proxy_core.url_safety import (
    BlockedCrawlTarget,
    ResolvedCrawlTarget,
    UrlSafetyOutcome,
)

from unique_search_proxy_client.web.core.agent_engines.vertexai.client import (
    _get_base_api_client_from_adc,
)
from unique_search_proxy_client.web.core.agent_engines.vertexai.service import (
    VertexAIAgentSearchService,
    resolve_redirect_urls,
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
    async def test_search_skips_redirect_resolution_when_disabled(self) -> None:
        """
        Purpose: Verify the persisted resolution setting still controls proxy behavior.
        Why this matters: Disabling resolution must not trigger any URL egress.
        Setup summary: Stream a response with the setting off and spy on the resolver.
        """
        http_client = MagicMock()

        async def fake_stream(**_kwargs: Any):
            yield _Chunk('{"results":[]}')

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
                "unique_search_proxy_client.web.core.agent_engines.vertexai.service.resolve_redirect_urls",
                new_callable=AsyncMock,
            ) as resolver,
        ):
            service = VertexAIAgentSearchService(http_client=http_client)
            await service.search(_vertex_request(enable_redirect_resolution=False))

        resolver.assert_not_awaited()


class TestResolveRedirectUrls:
    @staticmethod
    def _answer(url: str) -> str:
        return json.dumps(
            {
                "results": [
                    {
                        "source_url": url,
                        "source_title": "Example",
                        "detailed_answer": "Details",
                        "key_facts": ["Fact"],
                    }
                ]
            }
        )

    @pytest.mark.ai
    @pytest.mark.asyncio
    async def test_redirecting_target_uses_validated_final_url(self) -> None:
        """
        Purpose: Verify Search Proxy replaces a provider redirect with its safe target.
        Why this matters: Canonical URLs must be preserved without assistants egress.
        Setup summary: Return a validated resolution and inspect the rewritten answer.
        """
        redirect_url = (
            "https://vertexaisearch.cloud.google.com/grounding-api-redirect/token"
        )
        final_url = "https://example.com/article"
        http_client = MagicMock(spec=httpx.AsyncClient)
        outcome = UrlSafetyOutcome(
            url=redirect_url,
            resolved=ResolvedCrawlTarget(
                normalized_url=final_url,
                hostname="example.com",
                resolved_ip="203.0.113.10",
                used_dns_resolution=True,
            ),
        )

        with patch(
            "unique_search_proxy_client.web.core.agent_engines.vertexai.service.UrlSafetyService.validate_urls_individually",
            new_callable=AsyncMock,
            return_value=[outcome],
        ) as validate_urls:
            answer = await resolve_redirect_urls(
                self._answer(redirect_url),
                http_client=http_client,
            )

        output = AgentSearchOutput.model_validate_json(answer)
        assert output.results[0].source_url == final_url
        validate_urls.assert_awaited_once_with(
            [redirect_url],
            redirect_http_client=http_client,
        )

    @pytest.mark.ai
    @pytest.mark.asyncio
    async def test_private_redirect_target_keeps_provider_url(self) -> None:
        """
        Purpose: Verify a blocked redirect target is never exposed as a resolved URL.
        Why this matters: Redirect resolution must fail closed for private destinations.
        Setup summary: Return a private-target block and assert the wrapper is unchanged.
        """
        redirect_url = (
            "https://vertexaisearch.cloud.google.com/grounding-api-redirect/token"
        )
        http_client = MagicMock(spec=httpx.AsyncClient)
        outcome = UrlSafetyOutcome(
            url=redirect_url,
            blocked=BlockedCrawlTarget(
                hostname="169.254.169.254",
                category="metadata",
                reason="Cloud metadata endpoints are blocked",
            ),
        )

        with patch(
            "unique_search_proxy_client.web.core.agent_engines.vertexai.service.UrlSafetyService.validate_urls_individually",
            new_callable=AsyncMock,
            return_value=[outcome],
        ):
            answer = await resolve_redirect_urls(
                self._answer(redirect_url),
                http_client=http_client,
            )

        output = AgentSearchOutput.model_validate_json(answer)
        assert output.results[0].source_url == redirect_url


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
