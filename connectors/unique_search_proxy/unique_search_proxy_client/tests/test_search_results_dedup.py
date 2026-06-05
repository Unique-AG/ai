import pytest
from unique_search_proxy_core.schema import WebSearchResult, WebSearchResults


class TestWebSearchResultsDedupe:
    @pytest.mark.ai
    def test_dedupe_drops_exact_url_duplicates(self) -> None:
        results = WebSearchResults(
            results=[
                WebSearchResult(
                    url="https://example.com/a",
                    title="1",
                    snippet="s",
                ),
                WebSearchResult(
                    url="https://example.com/a",
                    title="2",
                    snippet="s",
                ),
            ],
        )
        deduped = results.dedupe()
        assert len(deduped) == 1
        assert deduped.results[0].title == "1"
