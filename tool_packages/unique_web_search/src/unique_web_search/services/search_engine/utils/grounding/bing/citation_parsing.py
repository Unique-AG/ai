import logging
import re
from collections import Counter
from collections.abc import Sequence
from dataclasses import dataclass, field
from enum import StrEnum
from urllib.parse import urlparse

from unique_search_proxy_core.schema import AnswerSpanCitation

from unique_web_search.services.search_engine.schema import WebSearchResult

_LOGGER = logging.getLogger(__name__)
_LIST_MARKER_PATTERN = re.compile(r"\s*(?:[-*+•]|\d+[.)])\s+")


class GroundingCitationDropReason(StrEnum):
    """Why one citation was left out of the results."""

    INVALID_OFFSETS = "invalid_offsets"
    MARKER_MISMATCH = "marker_mismatch"
    NOT_ON_ONE_LINE = "citation_not_on_one_line"
    NON_HTTP_URL = "non_http_url"


class GroundingLineDropReason(StrEnum):
    """Why one answer line was left out of the results."""

    NO_CITATION = "no_citation"
    NO_CONTENT = "no_content"


class GroundingParseFailureReason(StrEnum):
    """Why an answer produced no results at all."""

    NO_TEXT = "no_text"
    NO_CITATIONS = "no_citations"
    NO_USABLE_CITATIONS = "no_usable_citations"


@dataclass(frozen=True)
class CitationParseResult:
    """Results mapped from a grounded answer, plus the parts that were dropped.

    ``failure`` is set exactly when no result survived.
    """

    results: list[WebSearchResult]
    dropped_citations: Counter[GroundingCitationDropReason] = field(
        default_factory=Counter
    )
    dropped_lines: Counter[GroundingLineDropReason] = field(default_factory=Counter)
    failure: GroundingParseFailureReason | None = None


class BingCitationParser:
    """Map a Grounding with Bing Search answer onto one result per cited source.

    The agent is prompted to answer with one bullet per source, each ending in
    the marker Foundry renders for that source. Foundry returns the answer text
    and, separately, one citation per marker with the marker's character span
    in the answer and the source it points to. For example, this answer::

        - Python 3.14 adds template string literals (PEP 750). 【4:0†source】
        - Free-threaded Python is officially supported. 【4:1†source】

    comes with these citations::

        AnswerSpanCitation(
            url="https://docs.python.org/3/whatsnew/3.14.html",
            title="What's new in Python 3.14",
            marker="【4:0†source】",
            start_index=55,
            end_index=67,
        )
        AnswerSpanCitation(
            url="https://peps.python.org/pep-0779/",
            title="PEP 779",
            marker="【4:1†source】",
            start_index=116,
            end_index=128,
        )

    and is parsed into one result per URL. A result's content is the text of
    the lines citing it, without list markers or citation markers, such as
    ``"Python 3.14 adds template string literals (PEP 750)."``. Result URLs and
    titles come only from citations, never from the answer text.

    The model does not always follow the format, so these deviations are
    accepted:

    - Other list markers (``*``, ``+``, ``•``, ``1.``, ``1)``), indentation, or
      no list marker at all.
    - A marker anywhere in the line; the text after it is kept.
    - Several sources cited on one line; the line is added to each of them.
    - One source cited on several lines; its lines are joined in order.

    Whatever cannot be used is dropped on its own and counted, and the rest is
    kept:

    - A citation whose offsets fall outside the answer, whose span does not
      hold its marker, whose span crosses a line break, or whose URL is not
      http(s). A citation dropped only for its URL still has its marker
      removed from the line text.
    - A line with no usable citation, such as a heading or a preface, or with
      no text left once its markers are removed.
    """

    async def __call__(
        self,
        response: str,
        citations: Sequence[AnswerSpanCitation],
    ) -> CitationParseResult:
        lines = _answer_lines(response)
        if not lines:
            _LOGGER.warning("Grounding response contained no text")
            return CitationParseResult(
                results=[], failure=GroundingParseFailureReason.NO_TEXT
            )
        if not citations:
            _LOGGER.warning("Grounding response contained no citations")
            return CitationParseResult(
                results=[], failure=GroundingParseFailureReason.NO_CITATIONS
            )

        cited_lines, dropped_citations = _assign_citations_to_lines(
            response, lines, citations
        )
        sources, dropped_lines = _group_lines_by_source(response, cited_lines)
        results = [source.to_search_result() for source in sources]

        if dropped_citations or dropped_lines:
            _LOGGER.info(
                "Grounding response parsed with drops result_count=%d "
                "dropped_citations=%s dropped_lines=%s",
                len(results),
                {reason.value: count for reason, count in dropped_citations.items()},
                {reason.value: count for reason, count in dropped_lines.items()},
            )
        if not results:
            _LOGGER.warning("Grounding response had no usable citations")
        return CitationParseResult(
            results=results,
            dropped_citations=dropped_citations,
            dropped_lines=dropped_lines,
            failure=(
                None if results else GroundingParseFailureReason.NO_USABLE_CITATIONS
            ),
        )


@dataclass(frozen=True)
class _AnswerLine:
    """A non-empty line of the answer, with its offsets into the answer."""

    start: int
    end: int
    text: str

    def contains(self, citation: AnswerSpanCitation) -> bool:
        return self.start <= citation.start_index and citation.end_index <= self.end


@dataclass
class _CitedLine:
    """An answer line and the verified citations whose markers are on it.

    ``markers`` holds all of them, since every marker is removed from the text.
    ``sources`` holds the ones whose URL can become a result.
    """

    line: _AnswerLine
    markers: list[AnswerSpanCitation] = field(default_factory=list)
    sources: list[AnswerSpanCitation] = field(default_factory=list)


@dataclass
class _Source:
    """A cited URL and the content of every line that cites it."""

    url: str
    title: str
    # Keyed by line index, so a line citing the same URL twice is added once.
    contents: dict[int, str] = field(default_factory=dict)

    def to_search_result(self) -> WebSearchResult:
        content = "\n".join(self.contents.values())
        return WebSearchResult(
            url=self.url, title=self.title, snippet=content, content=content
        )


def _answer_lines(response: str) -> list[_AnswerLine]:
    """Split the answer into its non-empty lines, keeping their offsets."""
    lines: list[_AnswerLine] = []
    offset = 0
    for raw_line in response.splitlines(keepends=True):
        text = raw_line.rstrip("\r\n")
        if text.strip():
            lines.append(_AnswerLine(start=offset, end=offset + len(text), text=text))
        offset += len(raw_line)
    return lines


def _assign_citations_to_lines(
    response: str,
    lines: Sequence[_AnswerLine],
    citations: Sequence[AnswerSpanCitation],
) -> tuple[list[_CitedLine], Counter[GroundingCitationDropReason]]:
    """Attach each verified citation to the line its marker is on.

    Returns every line, cited or not, and the dropped citations counted by
    reason.
    """
    cited_lines = [_CitedLine(line) for line in lines]
    dropped: Counter[GroundingCitationDropReason] = Counter()
    for citation in citations:
        reason = _marker_drop_reason(response, citation)
        if reason is not None:
            dropped[reason] += 1
            continue
        cited_line = _line_containing(cited_lines, citation)
        if cited_line is None:
            dropped[GroundingCitationDropReason.NOT_ON_ONE_LINE] += 1
            continue
        cited_line.markers.append(citation)
        if not _is_http_url(citation.url):
            dropped[GroundingCitationDropReason.NON_HTTP_URL] += 1
            continue
        cited_line.sources.append(citation)
    return cited_lines, dropped


def _marker_drop_reason(
    response: str, citation: AnswerSpanCitation
) -> GroundingCitationDropReason | None:
    """Return why the citation's span does not hold its marker, or ``None`` if it does."""
    if not (0 <= citation.start_index < citation.end_index <= len(response)):
        return GroundingCitationDropReason.INVALID_OFFSETS
    if response[citation.start_index : citation.end_index] != citation.marker:
        return GroundingCitationDropReason.MARKER_MISMATCH
    return None


def _line_containing(
    cited_lines: Sequence[_CitedLine], citation: AnswerSpanCitation
) -> _CitedLine | None:
    """Return the line holding the citation's whole span, if there is one."""
    return next((cited for cited in cited_lines if cited.line.contains(citation)), None)


def _is_http_url(url: str) -> bool:
    parsed_url = urlparse(url)
    return parsed_url.scheme in {"http", "https"} and bool(parsed_url.netloc)


def _group_lines_by_source(
    response: str,
    cited_lines: Sequence[_CitedLine],
) -> tuple[list[_Source], Counter[GroundingLineDropReason]]:
    """Add each line's content to every source it cites.

    Returns the sources in the order they are first cited, and the dropped
    lines counted by reason.
    """
    sources: dict[str, _Source] = {}
    dropped: Counter[GroundingLineDropReason] = Counter()
    for index, cited_line in enumerate(cited_lines):
        if not cited_line.sources:
            dropped[GroundingLineDropReason.NO_CITATION] += 1
            continue
        content = _line_content(response, cited_line.line, cited_line.markers)
        if not content:
            dropped[GroundingLineDropReason.NO_CONTENT] += 1
            continue
        for citation in cited_line.sources:
            source = sources.setdefault(
                citation.url,
                _Source(url=citation.url, title=citation.title or citation.url),
            )
            source.contents[index] = content
    return list(sources.values()), dropped


def _line_content(
    response: str,
    line: _AnswerLine,
    markers: Sequence[AnswerSpanCitation],
) -> str:
    """Return the line text without its list marker and citation markers.

    Each marker is removed together with the whitespace before it, so
    ``"- Claim 【4:0†source】."`` becomes ``"Claim."``.
    """
    list_marker = _LIST_MARKER_PATTERN.match(line.text)
    cursor = line.start + (list_marker.end() if list_marker else 0)
    parts: list[str] = []
    for citation in sorted(markers, key=lambda item: item.start_index):
        parts.append(response[cursor : citation.start_index].rstrip())
        cursor = max(cursor, citation.end_index)
    parts.append(response[cursor : line.end])
    return "".join(parts).strip()
