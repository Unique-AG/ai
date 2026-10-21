"""Tests for shared grounding response parsing (Bing + VertexAI)."""

import logging
from unittest.mock import AsyncMock

import pytest
from unique_search_proxy_core.schema import GroundingCitation

from unique_web_search.services.search_engine.schema import WebSearchResult
from unique_web_search.services.search_engine.utils.grounding import (
    CitationBulletParserStrategy,
    convert_response_to_search_results,
)


class TestConvertResponseToSearchResults:
    """Strategy-chain conversion lives in ``grounding.response_parsing``."""

    @pytest.mark.ai
    @pytest.mark.asyncio
    async def test_convert__first_strategy_succeeds__returns_immediately(self) -> None:
        expected = [
            WebSearchResult(url="https://a.com", title="A", snippet="s", content="c")
        ]
        strategy_1 = AsyncMock(return_value=expected)
        strategy_2 = AsyncMock()

        results = await convert_response_to_search_results(
            "some response", [strategy_1, strategy_2]
        )

        assert results == expected
        strategy_1.assert_called_once_with("some response")
        strategy_2.assert_not_called()

    @pytest.mark.ai
    @pytest.mark.asyncio
    async def test_convert__first_fails__falls_back_to_second(
        self, caplog: pytest.LogCaptureFixture
    ) -> None:
        expected = [
            WebSearchResult(url="https://b.com", title="B", snippet="s", content="c")
        ]
        strategy_1 = AsyncMock(side_effect=ValueError("parse error"))
        strategy_2 = AsyncMock(return_value=expected)

        with caplog.at_level(logging.INFO):
            results = await convert_response_to_search_results(
                "some response", [strategy_1, strategy_2]
            )

        assert results == expected
        strategy_1.assert_called_once()
        strategy_2.assert_called_once()
        assert "strategy_index=0 fallback=False" in caplog.text
        assert "strategy_index=1 fallback=True" in caplog.text
        assert "result_urls=['https://b.com']" in caplog.text

    @pytest.mark.ai
    @pytest.mark.asyncio
    async def test_convert__all_strategies_fail__raises_value_error(self) -> None:
        strategy_1 = AsyncMock(side_effect=ValueError("no JSON"))
        strategy_2 = AsyncMock(side_effect=RuntimeError("LLM failure"))

        with pytest.raises(ValueError) as exc_info:
            await convert_response_to_search_results(
                "bad response", [strategy_1, strategy_2]
            )
        assert "No conversion strategy found" in str(exc_info.value)


def _citation(
    response: str,
    marker: str,
    url: str,
    *,
    title: str | None = None,
) -> GroundingCitation:
    """Citation whose span is the first occurrence of ``marker`` in ``response``."""
    start_index = response.index(marker)
    return GroundingCitation(
        url=url,
        title=title or url,
        marker=marker,
        start_index=start_index,
        end_index=start_index + len(marker),
    )


class TestCitationBulletParserStrategy:
    @pytest.mark.ai
    @pytest.mark.asyncio
    async def test_maps_one_cited_bullet_per_source(self) -> None:
        response = "- First source claim [1].\n\n- Second source claim [2]"
        citations = [
            _citation(response, "[1]", "https://canonical.example/one", title="One"),
            _citation(response, "[2]", "https://canonical.example/two", title="Two"),
        ]

        parsed = await CitationBulletParserStrategy()(response, citations)

        assert [result.url for result in parsed.results] == [
            "https://canonical.example/one",
            "https://canonical.example/two",
        ]
        assert [result.title for result in parsed.results] == ["One", "Two"]
        assert [result.content for result in parsed.results] == [
            "First source claim.",
            "Second source claim",
        ]
        assert [result.snippet for result in parsed.results] == [
            "First source claim.",
            "Second source claim",
        ]
        assert not parsed.dropped_citations
        assert not parsed.dropped_lines
        assert parsed.failure is None

    @pytest.mark.ai
    @pytest.mark.asyncio
    async def test_drops_uncited_lines(self) -> None:
        response = "Uncited preface\n- Cited claim [1]\n- Uncited claim"
        citation = _citation(response, "[1]", "https://canonical.example/source")

        parsed = await CitationBulletParserStrategy()(response, [citation])

        assert [result.content for result in parsed.results] == ["Cited claim"]
        assert parsed.dropped_lines == {"no_citation": 2}
        assert parsed.failure is None

    @pytest.mark.ai
    @pytest.mark.asyncio
    async def test_copies_line_to_each_source_when_multiple_sources_cited(
        self,
    ) -> None:
        response = "- Combined claim [1][2]"
        citations = [
            _citation(response, "[1]", "https://canonical.example/one"),
            _citation(response, "[2]", "https://canonical.example/two"),
        ]

        parsed = await CitationBulletParserStrategy()(response, citations)

        assert [result.url for result in parsed.results] == [
            "https://canonical.example/one",
            "https://canonical.example/two",
        ]
        assert [result.content for result in parsed.results] == [
            "Combined claim",
            "Combined claim",
        ]

    @pytest.mark.ai
    @pytest.mark.asyncio
    async def test_concatenates_lines_that_cite_same_source(self) -> None:
        response = "- First claim [1]\n- Second claim [2]"
        citations = [
            _citation(response, marker, "https://canonical.example/source")
            for marker in ("[1]", "[2]")
        ]

        parsed = await CitationBulletParserStrategy()(response, citations)

        assert len(parsed.results) == 1
        assert parsed.results[0].url == "https://canonical.example/source"
        assert parsed.results[0].content == "First claim\nSecond claim"
        assert parsed.results[0].snippet == "First claim\nSecond claim"

    @pytest.mark.ai
    @pytest.mark.asyncio
    async def test_maps_whole_line_to_each_mid_line_citation(self) -> None:
        response = "- First claim [1], second claim [2]."
        citations = [
            _citation(response, "[1]", "https://canonical.example/1"),
            _citation(response, "[2]", "https://canonical.example/2"),
        ]

        parsed = await CitationBulletParserStrategy()(response, citations)

        assert [result.url for result in parsed.results] == [
            "https://canonical.example/1",
            "https://canonical.example/2",
        ]
        assert [result.content for result in parsed.results] == [
            "First claim, second claim.",
            "First claim, second claim.",
        ]

    @pytest.mark.ai
    @pytest.mark.asyncio
    async def test_maps_text_after_citation_to_that_source(self) -> None:
        response = "- Claim [1] and continuation"
        citation = _citation(response, "[1]", "https://canonical.example/source")

        parsed = await CitationBulletParserStrategy()(response, [citation])

        assert [result.content for result in parsed.results] == [
            "Claim and continuation"
        ]

    @pytest.mark.ai
    @pytest.mark.asyncio
    async def test_maps_cited_prose_line_to_its_source(self) -> None:
        response = "A prose sentence [1] that is not a bullet."
        citation = _citation(response, "[1]", "https://canonical.example/source")

        parsed = await CitationBulletParserStrategy()(response, [citation])

        assert [result.url for result in parsed.results] == [
            "https://canonical.example/source"
        ]
        assert parsed.results[0].content == "A prose sentence that is not a bullet."

    @pytest.mark.ai
    @pytest.mark.asyncio
    async def test_strips_list_markers_other_than_flat_dash(self) -> None:
        response = (
            "* Star claim [1]\n1. Numbered claim [2]\n  - Nested claim [3]\n"
            "-5% growth [4]"
        )
        citations = [
            _citation(response, marker, f"https://canonical.example/{index}")
            for index, marker in enumerate(("[1]", "[2]", "[3]", "[4]"), 1)
        ]

        parsed = await CitationBulletParserStrategy()(response, citations)

        assert [result.content for result in parsed.results] == [
            "Star claim",
            "Numbered claim",
            "Nested claim",
            "-5% growth",
        ]

    @pytest.mark.ai
    @pytest.mark.asyncio
    async def test_drops_only_the_citation_with_non_http_url(self) -> None:
        response = "- Good claim [1]\n- Bad claim [2]"
        citations = [
            _citation(response, "[1]", "https://canonical.example/good"),
            _citation(response, "[2]", "javascript:alert(1)"),
        ]

        parsed = await CitationBulletParserStrategy()(response, citations)

        assert [(result.url, result.content) for result in parsed.results] == [
            ("https://canonical.example/good", "Good claim")
        ]
        assert parsed.dropped_citations == {"non_http_url": 1}
        assert parsed.dropped_lines == {"no_citation": 1}
        assert parsed.failure is None

    @pytest.mark.ai
    @pytest.mark.asyncio
    async def test_removes_marker_of_dropped_citation_from_shared_line(self) -> None:
        response = "- Shared claim [1][2]"
        citations = [
            _citation(response, "[1]", "https://canonical.example/good"),
            _citation(response, "[2]", "ftp://canonical.example/bad"),
        ]

        parsed = await CitationBulletParserStrategy()(response, citations)

        assert [(result.url, result.content) for result in parsed.results] == [
            ("https://canonical.example/good", "Shared claim")
        ]
        assert parsed.dropped_citations == {"non_http_url": 1}

    @pytest.mark.ai
    @pytest.mark.asyncio
    async def test_drops_only_the_citation_whose_marker_does_not_match(self) -> None:
        response = "- Good claim [1]\n- Other claim [2]"
        good = _citation(response, "[1]", "https://canonical.example/good")
        mismatched = _citation(response, "[2]", "https://canonical.example/other")
        mismatched.marker = "[9]"

        parsed = await CitationBulletParserStrategy()(response, [good, mismatched])

        assert [result.url for result in parsed.results] == [
            "https://canonical.example/good"
        ]
        assert parsed.dropped_citations == {"marker_mismatch": 1}
        assert parsed.dropped_lines == {"no_citation": 1}

    @pytest.mark.ai
    @pytest.mark.asyncio
    async def test_drops_only_the_citation_with_invalid_offsets(self) -> None:
        response = "- Good claim [1]"
        good = _citation(response, "[1]", "https://canonical.example/good")
        out_of_range = GroundingCitation(
            url="https://canonical.example/other",
            title="Other",
            marker="[2]",
            start_index=len(response),
            end_index=len(response) + 3,
        )

        parsed = await CitationBulletParserStrategy()(response, [good, out_of_range])

        assert [result.url for result in parsed.results] == [
            "https://canonical.example/good"
        ]
        assert parsed.dropped_citations == {"invalid_offsets": 1}

    @pytest.mark.ai
    @pytest.mark.asyncio
    async def test_drops_only_the_citation_spanning_two_lines(self) -> None:
        response = "- Good claim [1]\n- Other [2\n]"
        good = _citation(response, "[1]", "https://canonical.example/good")
        spanning = _citation(response, "[2\n]", "https://canonical.example/other")

        parsed = await CitationBulletParserStrategy()(response, [good, spanning])

        assert [result.url for result in parsed.results] == [
            "https://canonical.example/good"
        ]
        assert parsed.dropped_citations == {"citation_not_on_one_line": 1}

    @pytest.mark.ai
    @pytest.mark.asyncio
    async def test_drops_only_the_line_with_no_text_besides_its_citation(
        self,
    ) -> None:
        response = "- Good claim [1]\n- [2]"
        citations = [
            _citation(response, "[1]", "https://canonical.example/good"),
            _citation(response, "[2]", "https://canonical.example/empty"),
        ]

        parsed = await CitationBulletParserStrategy()(response, citations)

        assert [result.url for result in parsed.results] == [
            "https://canonical.example/good"
        ]
        assert parsed.dropped_lines == {"no_content": 1}
        assert parsed.failure is None

    @pytest.mark.ai
    @pytest.mark.asyncio
    async def test_reports_failure_when_no_citation_is_usable(self) -> None:
        response = "- Claim [1]"
        citation = _citation(response, "[1]", "javascript:alert(1)")

        parsed = await CitationBulletParserStrategy()(response, [citation])

        assert parsed.results == []
        assert parsed.dropped_citations == {"non_http_url": 1}
        assert parsed.failure == "no_usable_citations"

    @pytest.mark.ai
    @pytest.mark.asyncio
    async def test_reports_failure_for_answer_without_citations(self) -> None:
        parsed = await CitationBulletParserStrategy()("- Uncited claim", [])

        assert parsed.results == []
        assert parsed.failure == "no_citations"

    @pytest.mark.ai
    @pytest.mark.asyncio
    async def test_reports_failure_for_empty_answer(self) -> None:
        parsed = await CitationBulletParserStrategy()("  \n", [])

        assert parsed.results == []
        assert parsed.failure == "no_text"
