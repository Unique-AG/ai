"""Tests for shared grounding response parsing (Bing + VertexAI)."""

import logging
from unittest.mock import AsyncMock

import pytest
from unique_search_proxy_core.schema import AnswerSpanCitation

from unique_web_search.services.search_engine.schema import WebSearchResult
from unique_web_search.services.search_engine.utils.grounding import (
    CitationBulletParserStrategy,
    GroundingCitationDropReason,
    GroundingLineDropReason,
    GroundingParseFailureReason,
    convert_response_to_search_results,
)
from unique_web_search.services.search_engine.utils.grounding.response_parsing import (
    _answer_lines,
    _AnswerLine,
    _assign_citations_to_lines,
    _CitedLine,
    _group_lines_by_source,
    _is_http_url,
    _line_containing,
    _line_content,
    _marker_drop_reason,
    _Source,
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
        strategy_1 = AsyncMock(side_effect=ValueError("parse error near secret"))
        strategy_2 = AsyncMock(return_value=expected)

        with caplog.at_level(logging.INFO):
            results = await convert_response_to_search_results(
                "some response", [strategy_1, strategy_2]
            )

        assert results == expected
        strategy_1.assert_called_once()
        strategy_2.assert_called_once()
        assert "strategy_index=0 fallback=False" in caplog.text
        assert "error_type=ValueError" in caplog.text
        assert "strategy_index=1 fallback=True" in caplog.text
        assert "result_count=1" in caplog.text
        assert "https://b.com" not in caplog.text
        assert "secret" not in caplog.text

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
) -> AnswerSpanCitation:
    """Citation whose span is the first occurrence of ``marker`` in ``response``."""
    start_index = response.index(marker)
    return AnswerSpanCitation(
        url=url,
        title=title,
        marker=marker,
        start_index=start_index,
        end_index=start_index + len(marker),
    )


class TestCitationBulletParserStrategy:
    @pytest.mark.ai
    @pytest.mark.asyncio
    async def test_parses_the_docstring_example(self) -> None:
        """The example in the strategy's docstring parses as documented."""
        response = (
            "- Python 3.14 adds template string literals (PEP 750). 【4:0†source】\n"
            "- Free-threaded Python is officially supported. 【4:1†source】"
        )
        citations = [
            AnswerSpanCitation(
                url="https://docs.python.org/3/whatsnew/3.14.html",
                title="What's new in Python 3.14",
                marker="【4:0†source】",
                start_index=55,
                end_index=67,
            ),
            AnswerSpanCitation(
                url="https://peps.python.org/pep-0779/",
                title="PEP 779",
                marker="【4:1†source】",
                start_index=116,
                end_index=128,
            ),
        ]

        parsed = await CitationBulletParserStrategy()(response, citations)

        assert [
            (result.url, result.title, result.content) for result in parsed.results
        ] == [
            (
                "https://docs.python.org/3/whatsnew/3.14.html",
                "What's new in Python 3.14",
                "Python 3.14 adds template string literals (PEP 750).",
            ),
            (
                "https://peps.python.org/pep-0779/",
                "PEP 779",
                "Free-threaded Python is officially supported.",
            ),
        ]
        assert not parsed.dropped_citations
        assert not parsed.dropped_lines
        assert parsed.failure is None

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
        assert parsed.dropped_lines == {GroundingLineDropReason.NO_CITATION: 2}
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
        assert parsed.dropped_citations == {GroundingCitationDropReason.NON_HTTP_URL: 1}
        assert parsed.dropped_lines == {GroundingLineDropReason.NO_CITATION: 1}
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
        assert parsed.dropped_citations == {GroundingCitationDropReason.NON_HTTP_URL: 1}

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
        assert parsed.dropped_citations == {
            GroundingCitationDropReason.MARKER_MISMATCH: 1
        }
        assert parsed.dropped_lines == {GroundingLineDropReason.NO_CITATION: 1}

    @pytest.mark.ai
    @pytest.mark.asyncio
    async def test_drops_only_the_citation_with_invalid_offsets(self) -> None:
        response = "- Good claim [1]"
        good = _citation(response, "[1]", "https://canonical.example/good")
        out_of_range = AnswerSpanCitation(
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
        assert parsed.dropped_citations == {
            GroundingCitationDropReason.INVALID_OFFSETS: 1
        }

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
        assert parsed.dropped_citations == {
            GroundingCitationDropReason.NOT_ON_ONE_LINE: 1
        }

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
        assert parsed.dropped_lines == {GroundingLineDropReason.NO_CONTENT: 1}
        assert parsed.failure is None

    @pytest.mark.ai
    @pytest.mark.asyncio
    async def test_logs_drop_counts_without_urls_or_answer_text(
        self, caplog: pytest.LogCaptureFixture
    ) -> None:
        response = "- Private claim [1]\n- Other private claim [2]"
        citations = [
            _citation(response, "[1]", "https://private.example/good"),
            _citation(response, "[2]", "javascript:private()"),
        ]

        with caplog.at_level(logging.DEBUG):
            await CitationBulletParserStrategy()(response, citations)

        assert "non_http_url" in caplog.text
        assert "private" not in caplog.text.lower()

    @pytest.mark.ai
    @pytest.mark.asyncio
    async def test_reports_failure_when_no_citation_is_usable(self) -> None:
        response = "- Claim [1]"
        citation = _citation(response, "[1]", "javascript:alert(1)")

        parsed = await CitationBulletParserStrategy()(response, [citation])

        assert parsed.results == []
        assert parsed.dropped_citations == {GroundingCitationDropReason.NON_HTTP_URL: 1}
        assert parsed.failure is GroundingParseFailureReason.NO_USABLE_CITATIONS

    @pytest.mark.ai
    @pytest.mark.asyncio
    async def test_reports_failure_for_answer_without_citations(self) -> None:
        parsed = await CitationBulletParserStrategy()("- Uncited claim", [])

        assert parsed.results == []
        assert parsed.failure is GroundingParseFailureReason.NO_CITATIONS

    @pytest.mark.ai
    @pytest.mark.asyncio
    async def test_reports_failure_for_empty_answer(self) -> None:
        parsed = await CitationBulletParserStrategy()("  \n", [])

        assert parsed.results == []
        assert parsed.failure is GroundingParseFailureReason.NO_TEXT


class TestAnswerLines:
    @pytest.mark.ai
    def test_skips_blank_lines_and_keeps_offsets_into_the_answer(self) -> None:
        response = "first\n\n  \r\nsecond\r\nthird"

        lines = _answer_lines(response)

        assert lines == [
            _AnswerLine(start=0, end=5, text="first"),
            _AnswerLine(start=11, end=17, text="second"),
            _AnswerLine(start=19, end=24, text="third"),
        ]
        assert all(response[line.start : line.end] == line.text for line in lines)

    @pytest.mark.ai
    def test_returns_nothing_for_blank_answer(self) -> None:
        assert _answer_lines(" \n\t\n") == []


class TestMarkerDropReason:
    @pytest.mark.ai
    def test_accepts_span_holding_its_marker(self) -> None:
        response = "Claim [1]"

        assert _marker_drop_reason(response, _citation(response, "[1]", "u")) is None

    @pytest.mark.ai
    @pytest.mark.parametrize(
        ("start_index", "end_index"),
        [(-1, 2), (6, 6), (7, 6), (6, 10)],
        ids=["negative_start", "empty_span", "reversed_span", "past_the_end"],
    )
    def test_rejects_offsets_outside_the_answer(
        self, start_index: int, end_index: int
    ) -> None:
        citation = AnswerSpanCitation(
            url="https://canonical.example/source",
            marker="[1]",
            start_index=start_index,
            end_index=end_index,
        )

        assert (
            _marker_drop_reason("Claim [1]", citation)
            is GroundingCitationDropReason.INVALID_OFFSETS
        )

    @pytest.mark.ai
    def test_rejects_span_holding_other_text(self) -> None:
        response = "Claim [1]"
        citation = _citation(response, "[1]", "https://canonical.example/source")
        citation.marker = "[2]"

        assert (
            _marker_drop_reason(response, citation)
            is GroundingCitationDropReason.MARKER_MISMATCH
        )


class TestLineContaining:
    @pytest.mark.ai
    def test_returns_the_line_holding_the_whole_span(self) -> None:
        response = "- First [1]\n- Second [2]"
        cited_lines = [_CitedLine(line) for line in _answer_lines(response)]

        found = _line_containing(cited_lines, _citation(response, "[2]", "u"))

        assert found is cited_lines[1]

    @pytest.mark.ai
    def test_returns_none_for_span_crossing_a_line_break(self) -> None:
        response = "- First [1\n] second"
        cited_lines = [_CitedLine(line) for line in _answer_lines(response)]

        assert _line_containing(cited_lines, _citation(response, "[1\n]", "u")) is None


class TestAssignCitationsToLines:
    @pytest.mark.ai
    def test_attaches_verified_citations_and_counts_the_rest(self) -> None:
        response = "- Good [1]\n- Non-http [2] mismatched [3]\n- Split [4\n]"
        good = _citation(response, "[1]", "https://canonical.example/good")
        non_http = _citation(response, "[2]", "javascript:alert(1)")
        mismatched = _citation(response, "[3]", "https://canonical.example/other")
        mismatched.marker = "[9]"
        split = _citation(response, "[4\n]", "https://canonical.example/split")

        cited_lines, dropped = _assign_citations_to_lines(
            response, _answer_lines(response), [good, non_http, mismatched, split]
        )

        assert [cited.line.text for cited in cited_lines] == [
            "- Good [1]",
            "- Non-http [2] mismatched [3]",
            "- Split [4",
            "]",
        ]
        assert cited_lines[0].markers == [good]
        assert cited_lines[0].sources == [good]
        assert cited_lines[1].markers == [non_http]
        assert cited_lines[1].sources == []
        assert all(not cited.markers for cited in cited_lines[2:])
        assert dropped == {
            GroundingCitationDropReason.NON_HTTP_URL: 1,
            GroundingCitationDropReason.MARKER_MISMATCH: 1,
            GroundingCitationDropReason.NOT_ON_ONE_LINE: 1,
        }


class TestLineContent:
    @pytest.mark.ai
    def test_removes_markers_with_the_whitespace_before_them(self) -> None:
        response = "- Claim [1], more [2]."
        markers = [_citation(response, marker, "u") for marker in ("[2]", "[1]")]

        content = _line_content(response, _answer_lines(response)[0], markers)

        assert content == "Claim, more."

    @pytest.mark.ai
    @pytest.mark.parametrize(
        "response",
        [
            "- Claim [1]",
            "* Claim [1]",
            "+ Claim [1]",
            "• Claim [1]",
            "1. Claim [1]",
            "2) Claim [1]",
            "  - Claim [1]",
            "Claim [1]",
        ],
    )
    def test_removes_any_list_marker(self, response: str) -> None:
        marker = _citation(response, "[1]", "u")

        assert _line_content(response, _answer_lines(response)[0], [marker]) == (
            "Claim"
        )

    @pytest.mark.ai
    def test_keeps_a_leading_dash_that_is_part_of_the_text(self) -> None:
        response = "-5% growth [1]"
        marker = _citation(response, "[1]", "u")

        assert _line_content(response, _answer_lines(response)[0], [marker]) == (
            "-5% growth"
        )

    @pytest.mark.ai
    def test_returns_empty_text_for_a_marker_only_line(self) -> None:
        response = "- [1]"
        marker = _citation(response, "[1]", "u")

        assert _line_content(response, _answer_lines(response)[0], [marker]) == ""


class TestGroupLinesBySource:
    @pytest.mark.ai
    def test_groups_line_contents_by_url_in_first_cited_order(self) -> None:
        response = "- A [1][2]\n- B [3]\nHeading\n- [4]\n- C [5]"
        lines = _answer_lines(response)
        one_first = _citation(response, "[1]", "https://one.example", title="One")
        one_again = _citation(response, "[2]", "https://one.example", title="Later")
        two = _citation(response, "[3]", "https://two.example")
        empty = _citation(response, "[4]", "https://three.example")
        one_last = _citation(response, "[5]", "https://one.example")
        cited_lines = [
            _CitedLine(lines[0], [one_first, one_again], [one_first, one_again]),
            _CitedLine(lines[1], [two], [two]),
            _CitedLine(lines[2]),
            _CitedLine(lines[3], [empty], [empty]),
            _CitedLine(lines[4], [one_last], [one_last]),
        ]

        sources, dropped = _group_lines_by_source(response, cited_lines)

        assert sources == [
            _Source(url="https://one.example", title="One", contents={0: "A", 4: "C"}),
            _Source(
                url="https://two.example",
                title="https://two.example",
                contents={1: "B"},
            ),
        ]
        assert dropped == {
            GroundingLineDropReason.NO_CITATION: 1,
            GroundingLineDropReason.NO_CONTENT: 1,
        }

    @pytest.mark.ai
    def test_skips_markers_that_are_not_sources(self) -> None:
        response = "- Claim [1]"
        marker_only = _citation(response, "[1]", "javascript:alert(1)")
        cited_lines = [_CitedLine(_answer_lines(response)[0], [marker_only], [])]

        sources, dropped = _group_lines_by_source(response, cited_lines)

        assert sources == []
        assert dropped == {GroundingLineDropReason.NO_CITATION: 1}


class TestSourceToSearchResult:
    @pytest.mark.ai
    def test_joins_line_contents_into_content_and_snippet(self) -> None:
        source = _Source(
            url="https://one.example", title="One", contents={0: "A", 4: "C"}
        )

        assert source.to_search_result() == WebSearchResult(
            url="https://one.example", title="One", snippet="A\nC", content="A\nC"
        )


class TestIsHttpUrl:
    @pytest.mark.ai
    @pytest.mark.parametrize(
        ("url", "expected"),
        [
            ("https://canonical.example/page", True),
            ("http://canonical.example", True),
            ("ftp://canonical.example/file", False),
            ("javascript:alert(1)", False),
            ("https://", False),
            ("/relative/path", False),
        ],
    )
    def test_accepts_only_absolute_http_urls(self, url: str, expected: bool) -> None:
        assert _is_http_url(url) is expected
