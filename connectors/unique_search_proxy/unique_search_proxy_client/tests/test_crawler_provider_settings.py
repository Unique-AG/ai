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
