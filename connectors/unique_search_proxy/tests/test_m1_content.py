import pytest

from unique_search_proxy.web.core.schema import WebSearchResult
from unique_search_proxy.web.core.utils.content import (
    canonicalize_url,
    dedupe_results_by_url,
    html_to_markdown,
)


class TestContentUtils:
    @pytest.mark.ai
    def test_canonicalize_url_strips_fragment_and_lowercases_host(self) -> None:
        assert (
            canonicalize_url("HTTPS://Example.COM/path#section")
            == "https://example.com/path"
        )

    @pytest.mark.ai
    def test_dedupe_results_by_url(self) -> None:
        results = [
            WebSearchResult(url="https://example.com/a", title="1", snippet="s"),
            WebSearchResult(
                url="https://example.com/a#frag",
                title="2",
                snippet="s",
            ),
        ]
        deduped = dedupe_results_by_url(results)
        assert len(deduped) == 1

    @pytest.mark.ai
    def test_html_to_markdown_converts_headings(self) -> None:
        markdown = html_to_markdown("<h1>Title</h1><p>Body</p>")
        assert "Title" in markdown
        assert "Body" in markdown
