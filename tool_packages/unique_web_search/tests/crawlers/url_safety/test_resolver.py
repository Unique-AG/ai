from __future__ import annotations

import pytest

from unique_web_search.services.crawlers.url_safety import UrlSafetyService


class TestResolveCrawlTarget:
    @pytest.fixture(autouse=True)
    def _use_fake_public_dns(self, fake_public_dns: None) -> None:
        pass

    @pytest.mark.ai
    @pytest.mark.asyncio
    async def test_resolve_crawl_target__returns_request_values__for_dns_resolved_https_target(
        self,
    ) -> None:
        resolved_target = await UrlSafetyService.resolve_crawl_target(
            "https://example.com/docs?q=1"
        )

        assert resolved_target.normalized_url == "https://example.com/docs?q=1"
        assert resolved_target.request_url == "https://93.184.216.34/docs?q=1"
        assert resolved_target.host_header == "example.com"
        assert resolved_target.sni_hostname == "example.com"
