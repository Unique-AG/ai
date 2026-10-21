import logging
import re
from collections import Counter, defaultdict
from collections.abc import Sequence
from dataclasses import dataclass, field
from typing import Literal, Protocol
from urllib.parse import urlparse

from unique_search_proxy_core.schema import GroundingCitation
from unique_toolkit._common.validators import LMI
from unique_toolkit.language_model.builder import MessagesBuilder
from unique_toolkit.language_model.service import LanguageModelService

from unique_web_search.invocation_stats import collector
from unique_web_search.services.search_engine.schema import WebSearchResult
from unique_web_search.services.search_engine.utils.grounding.models import (
    GroundingSearchResults,
)

_LOGGER = logging.getLogger(__name__)
_JSON_PATTERN = re.compile(r"```json\s*([\s\S]*?)\s*```")
_LIST_MARKER_PATTERN = re.compile(r"\s*(?:[-*+•]|\d+[.)])\s+")


class ResponseParser(Protocol):
    """Protocol for strategies that parse raw agent text into search results."""

    async def __call__(self, response: str) -> list[WebSearchResult]: ...


async def convert_response_to_search_results(
    response: str, conversion_strategies: list[ResponseParser]
) -> list[WebSearchResult]:
    """Try each conversion strategy in order until one parses the response.

    Strategies are attempted sequentially; the first successful result is
    returned. Failures are logged and the next strategy is tried.

    Raises:
        ValueError: If every strategy fails to parse the response.
    """
    for strategy_index, strategy in enumerate(conversion_strategies):
        strategy_name = strategy.__class__.__name__
        is_fallback = strategy_index > 0
        try:
            _LOGGER.info(
                "Trying grounding response parser strategy=%s strategy_index=%d "
                "fallback=%s",
                strategy_name,
                strategy_index,
                is_fallback,
            )
            results = await strategy(response)
            _LOGGER.info(
                "Grounding response parser succeeded strategy=%s strategy_index=%d "
                "fallback=%s result_count=%d result_urls=%s",
                strategy_name,
                strategy_index,
                is_fallback,
                len(results),
                [result.url for result in results],
            )
            return results
        except Exception:
            _LOGGER.exception(
                "Grounding response parser failed strategy=%s strategy_index=%d "
                "fallback=%s",
                strategy_name,
                strategy_index,
                is_fallback,
            )
            continue
    raise ValueError("No conversion strategy found for the response")


class JsonConversionStrategy(ResponseParser):
    """Validate a ``GroundingSearchResults``-shaped JSON response directly.

    Accepts JSON wrapped in a ```json ... ``` code fence or a bare JSON object.

    Raises:
        ValueError: If the response does not contain valid results JSON.
    """

    async def __call__(self, response: str) -> list[WebSearchResult]:
        json_match = _JSON_PATTERN.search(response)
        payload = json_match.group(1) if json_match else response
        return GroundingSearchResults.model_validate_json(
            payload
        ).to_web_search_results()


class LLMParserStrategy(ResponseParser):
    """Fallback parser that uses an LLM to convert free-text into structured results.

    Sends the raw response to a language model with structured-output enforcement
    so it returns a validated ``GroundingSearchResults`` object.

    Raises:
        ValueError: If the LLM response does not contain a valid parsed result.
    """

    def __init__(self, llm: LMI, llm_service: LanguageModelService):
        self.llm = llm
        self.llm_service = llm_service

    async def __call__(self, response: str) -> list[WebSearchResult]:
        system_prompt = """You are a helpful assistant that converts an non-structured response to a structured response."""
        user_prompt = f"""The response is: {response}"""
        messages = (
            MessagesBuilder()
            .system_message_append(system_prompt)
            .user_message_append(user_prompt)
            .build()
        )
        llm_response = await self.llm_service.complete_async(
            messages=messages,
            model_name=self.llm.name,
            structured_output_model=GroundingSearchResults,
            structured_output_enforce_schema=True,
        )
        collector.record_language_model_response(
            model_name=self.llm.name,
            response=llm_response,
            source="web_search.grounding.response_parser",
        )

        if not llm_response.choices[0].message.parsed:
            raise ValueError("No JSON found in the response")

        return GroundingSearchResults.model_validate(
            llm_response.choices[0].message.parsed
        ).to_web_search_results()


GroundingCitationDropReason = Literal[
    "invalid_offsets",
    "marker_mismatch",
    "citation_not_on_one_line",
    "non_http_url",
]
GroundingLineDropReason = Literal["no_citation", "no_content"]
GroundingParseFailureReason = Literal["no_text", "no_citations", "no_usable_citations"]


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


class CitationBulletParserStrategy:
    """Group cited lines by authoritative source without another model call.

    Bullets are the expected format, but cited prose lines are accepted too so
    a formatting slip does not drop sources whose URLs Foundry already cited.

    A citation or line that fails validation is dropped on its own; everything
    that passes is kept.
    """

    async def __call__(
        self,
        response: str,
        citations: Sequence[GroundingCitation],
    ) -> CitationParseResult:
        lines = _nonempty_lines_with_offsets(response)
        if not lines:
            _LOGGER.warning("Grounding response contained no text")
            return CitationParseResult(results=[], failure="no_text")
        if not citations:
            _LOGGER.warning("Grounding response contained no citations")
            return CitationParseResult(results=[], failure="no_citations")

        dropped_citations: Counter[GroundingCitationDropReason] = Counter()
        markers_by_line: dict[int, list[GroundingCitation]] = defaultdict(list)
        sources_by_line: dict[int, list[GroundingCitation]] = defaultdict(list)
        for citation in citations:
            line_index = _locate_citation(response, lines, citation)
            if isinstance(line_index, str):
                dropped_citations[line_index] += 1
                _LOGGER.warning(
                    "Dropped grounding citation reason=%s url=%s",
                    line_index,
                    citation.url,
                )
                continue
            markers_by_line[line_index].append(citation)
            if not _is_http_url(citation.url):
                dropped_citations["non_http_url"] += 1
                _LOGGER.warning(
                    "Dropped grounding citation reason=non_http_url url=%s",
                    citation.url,
                )
                continue
            sources_by_line[line_index].append(citation)

        dropped_lines: Counter[GroundingLineDropReason] = Counter()
        content_by_url: dict[str, list[str]] = {}
        citation_by_url: dict[str, GroundingCitation] = {}
        for index, (line_start, line_end, line) in enumerate(lines):
            line_sources = sources_by_line[index]
            if not line_sources:
                dropped_lines["no_citation"] += 1
                continue

            list_marker = _LIST_MARKER_PATTERN.match(line)
            content = _line_text_without_citations(
                response,
                start=line_start + (list_marker.end() if list_marker else 0),
                end=line_end,
                citations=sorted(
                    markers_by_line[index], key=lambda item: item.start_index
                ),
            )
            if not content:
                dropped_lines["no_content"] += 1
                continue

            line_urls: set[str] = set()
            for citation in line_sources:
                if citation.url in line_urls:
                    continue
                line_urls.add(citation.url)
                citation_by_url.setdefault(citation.url, citation)
                content_by_url.setdefault(citation.url, []).append(content)

        results: list[WebSearchResult] = []
        for url, content_lines in content_by_url.items():
            citation = citation_by_url[url]
            content = "\n".join(content_lines)
            results.append(
                WebSearchResult(
                    url=url,
                    title=citation.title or url,
                    snippet=content,
                    content=content,
                )
            )

        if dropped_citations or dropped_lines:
            _LOGGER.info(
                "Grounding response parsed with drops result_count=%d "
                "dropped_citations=%s dropped_lines=%s",
                len(results),
                dict(dropped_citations),
                dict(dropped_lines),
            )
        if not results:
            _LOGGER.warning("Grounding response had no usable citations")
        return CitationParseResult(
            results=results,
            dropped_citations=dropped_citations,
            dropped_lines=dropped_lines,
            failure=None if results else "no_usable_citations",
        )


def _locate_citation(
    response: str,
    lines: Sequence[tuple[int, int, str]],
    citation: GroundingCitation,
) -> int | GroundingCitationDropReason:
    """Return the index of the line holding the citation's verified marker.

    Returns the drop reason instead when the marker cannot be verified.
    """
    if not (0 <= citation.start_index < citation.end_index <= len(response)):
        return "invalid_offsets"
    if response[citation.start_index : citation.end_index] != citation.marker:
        return "marker_mismatch"
    matching_lines = [
        index
        for index, (line_start, line_end, _) in enumerate(lines)
        if line_start <= citation.start_index and citation.end_index <= line_end
    ]
    if len(matching_lines) != 1:
        return "citation_not_on_one_line"
    return matching_lines[0]


def _is_http_url(url: str) -> bool:
    parsed_url = urlparse(url)
    return parsed_url.scheme in {"http", "https"} and bool(parsed_url.netloc)


def _line_text_without_citations(
    response: str,
    *,
    start: int,
    end: int,
    citations: Sequence[GroundingCitation],
) -> str:
    """Return the line text with each citation marker and its leading space removed."""
    parts: list[str] = []
    cursor = start
    for citation in citations:
        parts.append(response[cursor : citation.start_index].rstrip())
        cursor = max(cursor, citation.end_index)
    parts.append(response[cursor:end])
    return "".join(parts).strip()


def _nonempty_lines_with_offsets(
    response: str,
) -> list[tuple[int, int, str]]:
    """Return non-empty physical lines with offsets into the original response."""
    lines: list[tuple[int, int, str]] = []
    offset = 0
    for raw_line in response.splitlines(keepends=True):
        line = raw_line.rstrip("\r\n")
        if line.strip():
            lines.append((offset, offset + len(line), line))
        offset += len(raw_line)
    return lines
