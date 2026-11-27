import logging
import re
from typing import Protocol

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
                "fallback=%s result_count=%d",
                strategy_name,
                strategy_index,
                is_fallback,
                len(results),
            )
            return results
        except Exception as exc:
            # Parse errors can quote the answer text, so only the type is logged.
            _LOGGER.warning(
                "Grounding response parser failed strategy=%s strategy_index=%d "
                "fallback=%s error_type=%s",
                strategy_name,
                strategy_index,
                is_fallback,
                type(exc).__name__,
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
