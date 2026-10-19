import logging
import re
from collections.abc import Sequence
from dataclasses import dataclass
from typing import Protocol

from unique_search_proxy_core.schema import GroundingCitation
from unique_toolkit._common.validators import LMI
from unique_toolkit.language_model.builder import MessagesBuilder
from unique_toolkit.language_model.service import LanguageModelService

from unique_web_search.invocation_stats import collector
from unique_web_search.services.search_engine.schema import WebSearchResult
from unique_web_search.services.search_engine.utils.grounding.models import (
    CitedGroundingSearchResults,
    GroundingSearchResults,
)

_LOGGER = logging.getLogger(__name__)
_JSON_PATTERN = re.compile(r"```json\s*([\s\S]*?)\s*```")


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


@dataclass(frozen=True, slots=True)
class _CitationSource:
    source_id: str
    url: str
    title: str


_SOURCE_TAG_PATTERN = re.compile(r"\[SOURCE_\d+\]")


def _replace_citations_with_source_ids(
    response: str,
    citations: Sequence[GroundingCitation],
) -> tuple[str, dict[str, _CitationSource]]:
    """Replace authoritative annotation spans with stable source identifiers."""
    sources_by_url: dict[str, _CitationSource] = {}
    replacements: list[tuple[int, int, str]] = []

    for citation in sorted(
        citations,
        key=lambda item: (item.start_index, item.end_index),
    ):
        if not (0 <= citation.start_index < citation.end_index <= len(response)):
            continue
        if response[citation.start_index : citation.end_index] != citation.marker:
            continue

        source = sources_by_url.get(citation.url)
        if source is None:
            source = _CitationSource(
                source_id=f"SOURCE_{len(sources_by_url)}",
                url=citation.url,
                title=citation.title or citation.url,
            )
            sources_by_url[citation.url] = source
        replacements.append(
            (
                citation.start_index,
                citation.end_index,
                f"[{source.source_id}]",
            )
        )

    cited_response = response
    for start_index, end_index, source_id in reversed(replacements):
        cited_response = (
            cited_response[:start_index] + source_id + cited_response[end_index:]
        )

    return cited_response, {
        source.source_id: source for source in sources_by_url.values()
    }


def _fallback_cited_results(
    cited_response: str,
    sources: dict[str, _CitationSource],
) -> list[WebSearchResult]:
    """Preserve cited prose deterministically if LLM structuring fails."""
    paragraphs = [
        paragraph.strip()
        for paragraph in re.split(r"\n\s*\n", cited_response)
        if paragraph.strip()
    ]
    shared_paragraphs = [
        paragraph
        for paragraph in paragraphs
        if not _SOURCE_TAG_PATTERN.search(paragraph)
    ]
    results: list[WebSearchResult] = []
    for source in sources.values():
        source_tag = f"[{source.source_id}]"
        source_paragraphs = [
            paragraph for paragraph in paragraphs if source_tag in paragraph
        ]
        selected_paragraphs = [*shared_paragraphs, *source_paragraphs]
        if not selected_paragraphs:
            selected_paragraphs = paragraphs
        content = "\n\n".join(
            _SOURCE_TAG_PATTERN.sub("", paragraph).strip()
            for paragraph in selected_paragraphs
        )
        results.append(
            WebSearchResult(
                url=source.url,
                title=source.title,
                snippet=content[:500],
                content=content,
            )
        )
    return results


class CitationAwareLLMParserStrategy:
    """Structure cited prose while keeping provider URLs outside model control."""

    def __init__(self, llm: LMI, llm_service: LanguageModelService):
        self.llm = llm
        self.llm_service = llm_service

    async def __call__(
        self,
        response: str,
        citations: Sequence[GroundingCitation],
    ) -> list[WebSearchResult]:
        cited_response, sources = _replace_citations_with_source_ids(
            response,
            citations,
        )
        if not sources:
            raise ValueError("No valid grounding citations found in the response")

        source_catalog = "\n".join(
            f"- {source.source_id}: {source.title}" for source in sources.values()
        )
        system_prompt = """Convert cited web research into structured search results.
Preserve every relevant detail from the response.
Return exactly one result for every SOURCE_n identifier in the source catalog.
Use source_id values exactly as provided. Never create, alter, or omit a source id."""
        user_prompt = (
            f"Source catalog:\n{source_catalog}\n\nCited response:\n{cited_response}"
        )
        messages = (
            MessagesBuilder()
            .system_message_append(system_prompt)
            .user_message_append(user_prompt)
            .build()
        )
        try:
            llm_response = await self.llm_service.complete_async(
                messages=messages,
                model_name=self.llm.name,
                structured_output_model=CitedGroundingSearchResults,
                structured_output_enforce_schema=True,
            )
            collector.record_language_model_response(
                model_name=self.llm.name,
                response=llm_response,
                source="web_search.grounding.citation_parser",
            )

            parsed = llm_response.choices[0].message.parsed
            if not parsed:
                raise ValueError("No structured citation response returned")

            cited_results = CitedGroundingSearchResults.model_validate(parsed)
            results_by_source: dict[str, WebSearchResult] = {}
            for result in cited_results.results:
                source = sources.get(result.source_id)
                if source is None:
                    raise ValueError(f"Unknown grounding source id: {result.source_id}")
                if result.source_id in results_by_source:
                    raise ValueError(
                        f"Duplicate grounding source id: {result.source_id}"
                    )
                results_by_source[result.source_id] = WebSearchResult(
                    url=source.url,
                    title=source.title,
                    snippet="\n".join(result.key_facts),
                    content=result.detailed_answer,
                )

            missing_source_ids = sources.keys() - results_by_source.keys()
            if missing_source_ids:
                raise ValueError(
                    "Structured response omitted grounding source ids: "
                    f"{sorted(missing_source_ids)}"
                )

            return list(results_by_source.values())
        except Exception:
            _LOGGER.exception(
                "Citation structuring failed; preserving cited prose deterministically"
            )
            return _fallback_cited_results(cited_response, sources)
