from __future__ import annotations

import pytest

from unique_search_proxy_client.web.utils.url import join_url_path


class TestJoinUrlPath:
    @pytest.mark.ai
    def test_joins_base_and_segments(self) -> None:
        assert join_url_path("https://api.firecrawl.dev", "v2", "batch", "scrape") == (
            "https://api.firecrawl.dev/v2/batch/scrape"
        )

    @pytest.mark.ai
    def test_normalizes_trailing_slashes(self) -> None:
        assert join_url_path("https://api.tavily.com/", "/extract/") == (
            "https://api.tavily.com/extract"
        )

    @pytest.mark.ai
    def test_returns_base_when_no_segments(self) -> None:
        assert join_url_path("https://api.firecrawl.dev/", "") == (
            "https://api.firecrawl.dev"
        )
