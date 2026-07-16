import logging
import re
from typing import Protocol, Self

from unique_toolkit._common.validators import LMI
from unique_toolkit.language_model.builder import MessagesBuilder
from unique_toolkit.language_model.invocation_stats import LanguageModelInvocationStats
from unique_toolkit.language_model.schemas import LanguageModelTokenUsage
from unique_toolkit.language_model.service import LanguageModelService

from unique_web_search.services.search_engine.schema import WebSearchResult
from unique_web_search.services.search_engine.utils.grounding.models import (
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
    for strategy in conversion_strategies:
        try:
            _LOGGER.info(
                f"Trying parsing response with strategy: {strategy.__class__.__name__}"
            )
            return await strategy(response)
        except Exception as e:
            _LOGGER.exception(f"Error converting response to search results: {e}")
            continue
    raise ValueError("No conversion strategy found for the response")


class JsonConversionStrategy(ResponseParser):
    """Extract a fenced JSON block from the response and validate it directly.

    Expects the response to contain a ``GroundingSearchResults``-shaped
    JSON object wrapped in a ```json ... ``` code fence.

    Raises:
        ValueError: If no JSON code fence is found in the response.
    """

    async def __call__(self, response: str) -> list[WebSearchResult]:
        json_match = _JSON_PATTERN.search(response)
        if not json_match:
            raise ValueError("No JSON found in the response")
        return GroundingSearchResults.model_validate_json(
            json_match.group(1)
        ).to_web_search_results()


class LLMParserStrategy(ResponseParser):
    """Fallback parser that uses an LLM to convert free-text into structured results.

    Sends the raw response to a language model with structured-output enforcement
    so it returns a validated ``GroundingSearchResults`` object.

    Raises:
        ValueError: If the LLM response does not contain a valid parsed result.
    """

    def __init__(
        self,
        llm: LMI,
        llm_service: LanguageModelService,
        *,
        invocation_stats: list[LanguageModelInvocationStats] | None = None,
    ):
        self.llm = llm
        self.llm_service = llm_service
        self.invocation_stats = invocation_stats

    def with_invocation_stats(
        self, invocation_stats: list[LanguageModelInvocationStats]
    ) -> Self:
        """Return a copy bound to a run-scoped stats accumulator."""
        return LLMParserStrategy(
            self.llm,
            self.llm_service,
            invocation_stats=invocation_stats,
        )

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

        if self.invocation_stats is not None and isinstance(
            llm_response.usage, LanguageModelTokenUsage
        ):
            self.invocation_stats.append(
                LanguageModelInvocationStats.from_usage(
                    self.llm.name,
                    llm_response.usage,
                    source="web_search_grounding_parser",
                )
            )

        if not llm_response.choices[0].message.parsed:
            raise ValueError("No JSON found in the response")

        return GroundingSearchResults.model_validate(
            llm_response.choices[0].message.parsed
        ).to_web_search_results()
