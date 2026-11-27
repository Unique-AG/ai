from __future__ import annotations

import pytest

from unique_search_proxy_client.web.settings.providers.firecrawl import (
    _FirecrawlCredentials,
)
from unique_search_proxy_client.web.settings.providers.jina import _JinaCredentials
from unique_search_proxy_client.web.settings.providers.tavily import _TavilyCredentials


class TestCrawlerProviderEndpoints:
    @pytest.mark.ai
    def test_tavily_endpoints(self) -> None:
        credentials = _TavilyCredentials(
            api_key="key",
            api_endpoint="https://api.tavily.com",
        )
        assert credentials.extract_endpoint == "https://api.tavily.com/extract"
        assert credentials.search_endpoint == "https://api.tavily.com/search"

    @pytest.mark.ai
    def test_tavily_default_base(self) -> None:
        credentials = _TavilyCredentials(api_key="key")
        assert credentials.extract_endpoint == "https://api.tavily.com/extract"
        assert credentials.search_endpoint == "https://api.tavily.com/search"

    @pytest.mark.ai
    def test_jina_global_endpoints(self) -> None:
        credentials = _JinaCredentials(api_key="key", deployment="global")
        assert credentials.reader_endpoint == "https://r.jina.ai/"
        assert credentials.search_endpoint == "https://s.jina.ai/"

    @pytest.mark.ai
    def test_jina_eu_beta_endpoints(self) -> None:
        credentials = _JinaCredentials(api_key="key", deployment="eu-beta")
        assert credentials.reader_endpoint == "https://eu-r-beta.jina.ai/"
        assert credentials.search_endpoint == "https://eu-s-beta.jina.ai/"

    @pytest.mark.ai
    def test_firecrawl_v2_endpoints(self) -> None:
        credentials = _FirecrawlCredentials(
            api_key="key",
            api_endpoint="https://api.firecrawl.dev",
            api_version="v2",
        )
        assert (
            credentials.batch_scrape_endpoint
            == "https://api.firecrawl.dev/v2/batch/scrape"
        )
        assert credentials.scrape_endpoint == "https://api.firecrawl.dev/v2/scrape"
        assert credentials.search_endpoint == "https://api.firecrawl.dev/v2/search"

    @pytest.mark.ai
    def test_firecrawl_default_base_and_version(self) -> None:
        credentials = _FirecrawlCredentials(api_key="key")
        assert credentials.batch_scrape_endpoint == (
            "https://api.firecrawl.dev/v2/batch/scrape"
        )
        assert credentials.scrape_endpoint == "https://api.firecrawl.dev/v2/scrape"

    @pytest.mark.ai
    def test_firecrawl_zero_data_retention__defaults_to_none(self) -> None:
        credentials = _FirecrawlCredentials(api_key="key")

        assert credentials.zero_data_retention == "none"
        assert credentials.search_enterprise_modes() == []

    @pytest.mark.ai
    @pytest.mark.parametrize(
        ("deployed", "requested", "expected"),
        [
            ("none", "deployment", []),
            ("none", "anon", ["anon"]),
            ("none", "zdr", ["zdr"]),
            ("anon", "deployment", ["anon"]),
            ("anon", "zdr", ["zdr"]),
            ("zdr", "deployment", ["zdr"]),
            ("zdr", "anon", ["zdr"]),
        ],
    )
    def test_firecrawl_search_enterprise_modes__take_the_stricter_mode(
        self,
        deployed: str,
        requested: str,
        expected: list[str],
    ) -> None:
        credentials = _FirecrawlCredentials(api_key="key", zero_data_retention=deployed)

        assert credentials.search_enterprise_modes(requested) == expected

    @pytest.mark.ai
    @pytest.mark.parametrize(
        ("deployed", "requested", "expected"),
        [
            ("none", False, False),
            ("none", True, True),
            ("anon", False, True),
            ("zdr", False, True),
            ("zdr", True, True),
        ],
    )
    def test_firecrawl_scrape_zero_data_retention__is_on_when_either_asks(
        self,
        deployed: str,
        requested: bool,
        expected: bool,
    ) -> None:
        credentials = _FirecrawlCredentials(api_key="key", zero_data_retention=deployed)

        assert credentials.scrape_zero_data_retention(requested) is expected
