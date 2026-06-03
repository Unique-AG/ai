import pytest

from unique_search_proxy.web.core.crawlers.url_safety.models import (
    CrawlTargetValidationError,
)
from unique_search_proxy.web.core.crawlers.url_safety.policy import (
    validate_target_cheap,
)
from unique_search_proxy.web.core.crawlers.url_safety.resolver import (
    resolve_crawl_target,
)


class TestUrlSafetyPolicy:
    @pytest.mark.ai
    @pytest.mark.parametrize(
        "url",
        [
            "http://169.254.169.254/latest/meta-data/",
            "http://localhost/admin",
            "http://metadata.google.internal/computeMetadata/v1/",
            "ftp://example.com/file",
        ],
    )
    def test_validate_target_cheap_blocks_unsafe_urls(self, url: str) -> None:
        assert validate_target_cheap(url) is not None

    @pytest.mark.ai
    def test_validate_target_cheap_allows_public_https(self) -> None:
        assert validate_target_cheap("https://example.com/page") is None


class TestUrlSafetyResolver:
    @pytest.mark.ai
    async def test_resolve_crawl_target_blocks_metadata_ip(self) -> None:
        with pytest.raises(CrawlTargetValidationError):
            await resolve_crawl_target("http://169.254.169.254/")
