from __future__ import annotations

import pytest

from unique_web_search.services.crawlers.url_safety import UrlSafetyService


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
