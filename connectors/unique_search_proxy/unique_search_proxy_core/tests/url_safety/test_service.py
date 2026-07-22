from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from unique_search_proxy_core.url_safety import UrlSafetyService
from unique_search_proxy_core.url_safety.models import ResolvedCrawlTarget

_RESOLVE_TARGET = (
    "unique_search_proxy_core.url_safety.service.resolver.resolve_crawl_target"
)

_REDIRECT_HTTPX = "unique_search_proxy_core.url_safety.redirect.httpx.AsyncClient"


class TestValidateUrls:
    @pytest.fixture(autouse=True)
    def _use_fake_public_dns(self, fake_public_dns: None) -> None:
        pass

    @pytest.fixture(autouse=True)
    def _disable_redirects(self, disable_url_safety_redirects: None) -> None:
        pass

    @pytest.mark.ai
    @pytest.mark.asyncio
    async def test_validate_urls__returns_resolved_targets__without_redirect_resolution(
        self,
    ) -> None:
        targets = await UrlSafetyService.validate_batch_urls(
            ["https://example.com/page"]
        )

        assert len(targets) == 1
        assert targets[0].normalized_url == "https://example.com/page"
        assert targets[0].request_url == "https://93.184.216.34/page"
        assert targets[0].host_header == "example.com"

    @pytest.mark.ai
    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        "url_with_whitespace",
        [
            " https://example.com/page",
            "https://example.com/page ",
            "  https://example.com/page  ",
            "\thttps://example.com/page",
            "\u00a0https://example.com/page",
        ],
    )
    async def test_validate_urls__strips_whitespace__without_redirect_resolution(
        self, url_with_whitespace: str
    ) -> None:
        targets = await UrlSafetyService.validate_batch_urls([url_with_whitespace])

        assert len(targets) == 1
        assert targets[0].normalized_url == "https://example.com/page"


class TestValidateUrlsWithRedirects:
    @pytest.fixture(autouse=True)
    def _use_fake_public_dns(self, fake_public_dns: None) -> None:
        pass

    @pytest.mark.ai
    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        "url_with_whitespace",
        [
            " https://example.com/page",
            "https://example.com/page ",
            "\u00a0https://example.com/page",
        ],
    )
    async def test_validate_urls__strips_whitespace__before_redirect_resolution(
        self, url_with_whitespace: str
    ) -> None:
        response = MagicMock()
        response.status_code = 200
        response.headers = {}

        mock_client = AsyncMock()
        mock_client.head = AsyncMock(return_value=response)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)

        with patch(_REDIRECT_HTTPX, return_value=mock_client):
            targets = await UrlSafetyService.validate_batch_urls([url_with_whitespace])

        assert len(targets) == 1
        assert targets[0].normalized_url == "https://example.com/page"
        mock_client.head.assert_called_once_with("https://example.com/page")


class TestValidateUrlsIndividually:
    @pytest.fixture(autouse=True)
    def _use_fake_public_dns(self, fake_public_dns: None) -> None:
        pass

    @pytest.fixture(autouse=True)
    def _disable_redirects(self, disable_url_safety_redirects: None) -> None:
        pass

    @pytest.mark.ai
    @pytest.mark.asyncio
    async def test_validate_urls_individually__returns_mixed_outcomes(self) -> None:
        outcomes = await UrlSafetyService.validate_urls_individually(
            [
                "https://example.com",
                "http://127.0.0.1:8080",
            ]
        )

        assert len(outcomes) == 2
        assert outcomes[0].resolved is not None
        assert outcomes[0].blocked is None
        assert outcomes[1].resolved is None
        assert outcomes[1].blocked is not None
        assert outcomes[1].blocked.category == "private"

    @pytest.mark.ai
    @pytest.mark.asyncio
    async def test_validate_urls_individually__fails_closed_on_unexpected_error(
        self,
    ) -> None:
        async def fake_resolve(url: str) -> ResolvedCrawlTarget:
            if "boom" in url:
                raise RuntimeError("unexpected resolver failure")
            return ResolvedCrawlTarget(
                normalized_url=url.strip(),
                hostname="example.com",
                resolved_ip="93.184.216.34",
                used_dns_resolution=True,
            )

        with patch(_RESOLVE_TARGET, side_effect=fake_resolve):
            outcomes = await UrlSafetyService.validate_urls_individually(
                [
                    "https://boom.example.com",
                    "https://example.com",
                ]
            )

        assert len(outcomes) == 2
        # The URL that raised unexpectedly is blocked, not propagated as a batch failure.
        assert outcomes[0].resolved is None
        assert outcomes[0].blocked is not None
        assert outcomes[0].blocked.category == "validation_error"
        assert outcomes[0].blocked.hostname == "boom.example.com"
        # Its sibling still resolves successfully.
        assert outcomes[1].blocked is None
        assert outcomes[1].resolved is not None
