from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

from unique_search_proxy_core.url_safety import (
    CrawlTargetValidationError,
    UrlSafetyService,
)
from unique_search_proxy_core.url_safety import redirect as redirect_module

_REDIRECT_HTTPX = "unique_search_proxy_core.url_safety.redirect.httpx.AsyncClient"


class TestResolveRedirectChain:
    @pytest.fixture(autouse=True)
    def _use_fake_public_dns(self, fake_public_dns: None) -> None:
        pass

    def _make_mock_client(self, responses: list[tuple[int, str | None]]) -> AsyncMock:
        mock_responses = []
        for status_code, location in responses:
            resp = MagicMock()
            resp.status_code = status_code
            resp.headers = {"location": location} if location else {}
            mock_responses.append(resp)

        mock_client = AsyncMock()
        mock_client.head = AsyncMock(side_effect=mock_responses)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)
        return mock_client

    async def _resolve_redirect_chain(self, url: str) -> str:
        return await redirect_module.resolve_redirect_chain(
            url,
            validate_url=UrlSafetyService.validate_url,
        )

    @pytest.mark.ai
    @pytest.mark.asyncio
    async def test_resolve_redirect_chain__no_redirect__returns_original_url(
        self,
    ) -> None:
        mock_client = self._make_mock_client([(200, None)])

        with patch(_REDIRECT_HTTPX, return_value=mock_client):
            result = await self._resolve_redirect_chain("https://example.com/page")

        assert result == "https://example.com/page"
        mock_client.head.assert_called_once_with("https://example.com/page")

    @pytest.mark.ai
    @pytest.mark.asyncio
    async def test_resolve_redirect_chain__safe_http_to_https__returns_final_https_url(
        self,
    ) -> None:
        mock_client = self._make_mock_client(
            [
                (301, "https://example.com/page"),
                (200, None),
            ]
        )

        with patch(_REDIRECT_HTTPX, return_value=mock_client):
            result = await self._resolve_redirect_chain("http://example.com/page")

        assert result == "https://example.com/page"
        assert mock_client.head.call_count == 2

    @pytest.mark.ai
    @pytest.mark.asyncio
    async def test_resolve_redirect_chain__blocked_redirect__raises_before_head_to_blocked_host(
        self,
    ) -> None:
        mock_client = self._make_mock_client(
            [(302, "http://api.default.svc/loki/api/v1/query_range")]
        )

        with patch(_REDIRECT_HTTPX, return_value=mock_client):
            with pytest.raises(CrawlTargetValidationError) as exc_info:
                await self._resolve_redirect_chain("https://evil.example.com/article")

        blocked = exc_info.value.blocked_targets[0]
        assert blocked.hostname == "api.default.svc"
        assert blocked.category == "cluster"
        assert mock_client.head.call_count == 1

    @pytest.mark.ai
    @pytest.mark.asyncio
    async def test_resolve_redirect_chain__network_error_on_hop__raises_instead_of_failing_open(
        self,
    ) -> None:
        mock_client = AsyncMock()
        mock_client.head = AsyncMock(
            side_effect=httpx.ConnectError("connection refused")
        )
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)

        with patch(_REDIRECT_HTTPX, return_value=mock_client):
            with pytest.raises(CrawlTargetValidationError) as exc_info:
                await self._resolve_redirect_chain("https://example.com/page")

        blocked = exc_info.value.blocked_targets[0]
        assert blocked.hostname == "example.com"
        assert blocked.category == "redirect"
        assert "Unable to verify redirect chain" in blocked.reason

    @pytest.mark.ai
    @pytest.mark.asyncio
    async def test_resolve_redirect_chain__head_error_before_hidden_redirect__blocks_url(
        self,
    ) -> None:
        """HEAD failure must not allow crawl GET to discover an unvalidated redirect."""
        mock_client = AsyncMock()
        mock_client.head = AsyncMock(
            side_effect=httpx.ConnectError("connection refused")
        )
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)

        with patch(_REDIRECT_HTTPX, return_value=mock_client):
            with pytest.raises(CrawlTargetValidationError) as exc_info:
                await self._resolve_redirect_chain("https://evil.example.com/article")

        blocked = exc_info.value.blocked_targets[0]
        assert blocked.hostname == "evil.example.com"
        assert blocked.category == "redirect"

    @pytest.mark.ai
    @pytest.mark.asyncio
    async def test_resolve_redirect_chain__max_hops_exceeded__stops_at_last_validated_url(
        self,
    ) -> None:
        responses: list[tuple[int, str | None]] = [
            (302, f"https://hop{i}.example.com/") for i in range(15)
        ]
        responses.append((200, None))
        mock_client = self._make_mock_client(responses)

        with patch(_REDIRECT_HTTPX, return_value=mock_client):
            result = await self._resolve_redirect_chain("https://start.example.com/")

        assert result == "https://hop9.example.com/"
        assert mock_client.head.call_count == 10

    @pytest.mark.ai
    @pytest.mark.asyncio
    async def test_resolve_redirect_chain__relative_path_redirect__resolves_against_base(
        self,
    ) -> None:
        mock_client = self._make_mock_client(
            [
                (301, "/new-path"),
                (200, None),
            ]
        )

        with patch(_REDIRECT_HTTPX, return_value=mock_client):
            result = await self._resolve_redirect_chain("https://example.com/old-path")

        assert result == "https://example.com/new-path"
        assert mock_client.head.call_count == 2

    @pytest.mark.ai
    @pytest.mark.asyncio
    async def test_resolve_redirect_chain__relative_dotdot_redirect__resolves_against_base(
        self,
    ) -> None:
        mock_client = self._make_mock_client(
            [
                (302, "../other"),
                (200, None),
            ]
        )

        with patch(_REDIRECT_HTTPX, return_value=mock_client):
            result = await self._resolve_redirect_chain("https://example.com/a/b/page")

        assert result == "https://example.com/a/other"
        assert mock_client.head.call_count == 2
