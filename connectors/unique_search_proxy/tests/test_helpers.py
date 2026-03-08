from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from core.schema import WebSearchResult, WebSearchResults
from core.vertexai.helpers import _resolve_url, resolve_all
from httpx import HTTPError


class TestResolveUrl:
    @pytest.mark.ai
    async def test_follows_redirect(self):
        """
        Purpose: Verify _resolve_url follows a redirect and updates the URL.
        Why this matters: Many search result URLs are shortened or redirected.
        Setup summary: Mock client.head to return a resolved URL and assert it replaces the original.
        """
        result = WebSearchResult(url="https://short.url", title="t", snippet="s")
        mock_client = AsyncMock()
        mock_resp = MagicMock()
        mock_resp.url = "https://resolved.example.com/page"
        mock_client.head.return_value = mock_resp

        resolved = await _resolve_url(mock_client, result)
        assert resolved.url == "https://resolved.example.com/page"

    @pytest.mark.ai
    async def test_keeps_url_on_error(self):
        """
        Purpose: Verify _resolve_url preserves the original URL on HTTP errors.
        Why this matters: Resolution failures should not discard valid search results.
        Setup summary: Mock client.head to raise HTTPError and assert original URL is kept.
        """
        result = WebSearchResult(url="https://broken.url", title="t", snippet="s")
        mock_client = AsyncMock()
        mock_client.head.side_effect = HTTPError("connection failed")

        resolved = await _resolve_url(mock_client, result)
        assert resolved.url == "https://broken.url"


class TestResolveAll:
    @pytest.mark.ai
    async def test_resolves_all_urls(self):
        """
        Purpose: Verify resolve_all resolves URLs for all results concurrently.
        Why this matters: Batch resolution is needed for performance with multiple results.
        Setup summary: Mock AsyncClient.head for two results and assert both are resolved.
        """
        results = WebSearchResults(
            results=[
                WebSearchResult(url="https://a.com", title="A", snippet="sA"),
                WebSearchResult(url="https://b.com", title="B", snippet="sB"),
            ]
        )

        mock_resp_a = MagicMock()
        mock_resp_a.url = "https://resolved-a.com"
        mock_resp_b = MagicMock()
        mock_resp_b.url = "https://resolved-b.com"

        mock_client = AsyncMock()
        mock_client.head.side_effect = [mock_resp_a, mock_resp_b]

        with patch(
            "core.vertexai.helpers.AsyncClient",
        ) as mock_cls:
            mock_cls.return_value.__aenter__ = AsyncMock(return_value=mock_client)
            mock_cls.return_value.__aexit__ = AsyncMock(return_value=False)
            resolved = await resolve_all(results)

        assert len(resolved.results) == 2
        assert resolved.results[0].url == "https://resolved-a.com"
        assert resolved.results[1].url == "https://resolved-b.com"
