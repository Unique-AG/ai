import pytest
from pydantic import ValidationError

from unique_search_proxy_core.crawlers.base import CrawlerType
from unique_search_proxy_core.crawlers.basic.schema import BasicConfig
from unique_search_proxy_core.crawlers.config_types import (
    parse_crawl_request,
    parse_crawler_config,
)
from unique_search_proxy_core.providers.schema import provider_default_config


class TestCrawlerConfigRequestSplit:
    @pytest.mark.ai
    def test_config_parses_without_urls(self) -> None:
        config = parse_crawler_config({"crawler": CrawlerType.BASIC.value})
        assert isinstance(config, BasicConfig)

    @pytest.mark.ai
    def test_config_ignores_urls(self) -> None:
        # Crawler deployment configs mirror the search-engine configs: they do
        # not set ``extra='forbid'`` (that would emit ``additionalProperties:
        # false`` and break the RJSF admin form's discriminated ``oneOf``). The
        # config/request split is preserved because ``urls`` is not a config
        # field: it is silently dropped, never surfaced on the parsed model.
        config = parse_crawler_config(
            {
                "crawler": CrawlerType.BASIC.value,
                "urls": ["https://example.com"],
            },
        )
        assert isinstance(config, BasicConfig)
        assert not hasattr(config, "urls")
        assert "urls" not in config.model_dump()
        assert "urls" not in BasicConfig.model_json_schema().get("properties", {})

    @pytest.mark.ai
    def test_default_config_json_has_no_urls(self) -> None:
        defaults = provider_default_config("crawler", CrawlerType.BASIC.value)
        assert "urls" not in defaults

    @pytest.mark.ai
    def test_crawl_request_requires_urls(self) -> None:
        with pytest.raises(ValidationError):
            parse_crawl_request({"crawler": CrawlerType.BASIC.value})


class TestFirecrawlLegacyCacheAge:
    @pytest.mark.ai
    @pytest.mark.parametrize("key", ["maxAge", "max_age"])
    def test_config__reads_legacy_max_age_as_cache_age__when_seconds_absent(
        self, key: str
    ) -> None:
        """
        Purpose: Verify a stored config that only has the millisecond cache age
            keeps that age.
        Why this matters: The seconds field now has a one-hour default, which
            would otherwise replace the cache age such a space chose.
        Setup summary: Parse a config with only the legacy field; assert the
            cache age in seconds.
        """
        config = parse_crawler_config(
            {"crawler": CrawlerType.FIRECRAWL.value, key: 90_000}
        )

        assert config.max_cache_age_seconds == 90

    @pytest.mark.ai
    def test_config__prefers_seconds__when_both_are_stored(self) -> None:
        """
        Purpose: Verify the seconds field wins once a config has both.
        Why this matters: After an admin saves the form both fields are stored;
            the visible one must be the one that applies.
        Setup summary: Parse a config with both fields; assert the seconds value.
        """
        config = parse_crawler_config(
            {
                "crawler": CrawlerType.FIRECRAWL.value,
                "maxAge": 90_000,
                "maxCacheAgeSeconds": 0,
            }
        )

        assert config.max_cache_age_seconds == 0

    @pytest.mark.ai
    def test_config__caps_legacy_max_age__at_seven_days(self) -> None:
        """
        Purpose: Verify an oversized legacy cache age still loads.
        Why this matters: The millisecond field had no upper bound, so a stored
            value above seven days must not make the whole space config invalid.
        Setup summary: Parse a config with a 30-day legacy value; assert the cap.
        """
        config = parse_crawler_config(
            {"crawler": CrawlerType.FIRECRAWL.value, "maxAge": 30 * 86_400_000}
        )

        assert config.max_cache_age_seconds == 7 * 86_400
