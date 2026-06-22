"""Strategies that parse raw agent text into normalized search results."""

from __future__ import annotations

import logging
import re
from collections.abc import Iterator
from typing import Any, Protocol

from pydantic import BaseModel, ValidationError

from unique_search_proxy_core.agent_engines.output_schema import AgentSearchOutput
from unique_search_proxy_core.schema import WebSearchResult

_LOGGER = logging.getLogger(__name__)
_FENCED_JSON_PATTERNS = (
    re.compile(r"```json\s*([\s\S]*?)\s*```", re.IGNORECASE),
    re.compile(r"```\s*([\s\S]*?)\s*```"),
)
_EMBEDDED_JSON_OBJECT_PATTERN = re.compile(r"\{[\s\S]*\}")


class ResponseParser(Protocol):
    """Protocol for strategies that parse raw agent text into search results."""

    async def __call__(self, response: str) -> list[WebSearchResult]: ...


async def convert_response_to_search_results(
    response: str,
    conversion_strategies: list[ResponseParser],
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
                "Trying parsing response with strategy: %s",
                strategy.__class__.__name__,
            )
            return await strategy(response)
        except Exception:
            _LOGGER.exception(
                "Error converting response to search results with strategy: %s",
                strategy.__class__.__name__,
            )
            continue
    raise ValueError("No conversion strategy found for the response")


def _looks_like_json_object(payload: str) -> bool:
    return payload.lstrip().startswith("{")


def _iter_json_payload_candidates(response: str) -> Iterator[str]:
    """Yield JSON payload strings to try, from most to least specific."""
    seen: set[str] = set()

    for pattern in _FENCED_JSON_PATTERNS:
        for match in pattern.finditer(response):
            payload = match.group(1).strip()
            if not payload or not _looks_like_json_object(payload):
                continue
            if payload in seen:
                continue
            seen.add(payload)
            yield payload

    stripped = response.strip()
    if _looks_like_json_object(stripped) and stripped not in seen:
        seen.add(stripped)
        yield stripped

    for match in _EMBEDDED_JSON_OBJECT_PATTERN.finditer(response):
        payload = match.group(0).strip()
        if payload in seen:
            continue
        seen.add(payload)
        yield payload


class JsonConversionStrategy(ResponseParser):
    """Extract JSON from the response and validate it directly.

    Tries, in order:

    * `` ```json ... ``` `` (case-insensitive language tag)
    * `` ``` ... ``` `` (plain fence)
    * the full response when it is a bare JSON object
    * the first embedded ``{...}`` substring

    Each candidate is validated against ``output_schema``; the first match wins.

    Raises:
        ValueError: If no candidate parses as valid structured output.
    """

    def __init__(
        self,
        output_schema: type[AgentSearchOutput] = AgentSearchOutput,
    ) -> None:
        self._output_schema = output_schema

    async def __call__(self, response: str) -> list[WebSearchResult]:
        last_error: Exception | None = None
        found_candidate = False

        for payload in _iter_json_payload_candidates(response):
            found_candidate = True
            try:
                return self._output_schema.model_validate_json(
                    payload,
                ).to_web_search_results()
            except ValidationError as exc:
                last_error = exc
                continue

        if not found_candidate:
            raise ValueError("No JSON found in the response")
        raise ValueError("No valid JSON found in the response") from last_error


class LanguageModelServiceProtocol(Protocol):
    """Minimal surface for structured-output completion used by LLM parsing."""

    async def complete_async(
        self,
        *,
        messages: Any,
        model_name: str,
        structured_output_model: type[BaseModel],
        structured_output_enforce_schema: bool,
    ) -> Any: ...


class LMIProtocol(Protocol):
    """Minimal language-model identity used by LLM parsing."""

    name: str


class LLMParserStrategy(ResponseParser):
    """Fallback parser that uses an LLM to convert free-text into structured results.

    Sends the raw response to a language model with structured-output enforcement
    so it returns a validated ``AgentSearchOutput`` object.

    Raises:
        ValueError: If the LLM response does not contain a valid parsed result.
    """

    def __init__(
        self,
        llm: LMIProtocol,
        llm_service: LanguageModelServiceProtocol,
        output_schema: type[AgentSearchOutput] = AgentSearchOutput,
    ) -> None:
        self.llm = llm
        self.llm_service = llm_service
        self._output_schema = output_schema

    async def __call__(self, response: str) -> list[WebSearchResult]:
        system_prompt = (
            "You are a helpful assistant that converts an non-structured "
            "response to a structured response."
        )
        user_prompt = f"The response is: {response}"
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ]
        llm_response = await self.llm_service.complete_async(
            messages=messages,
            model_name=self.llm.name,
            structured_output_model=self._output_schema,
            structured_output_enforce_schema=True,
        )

        if not llm_response.choices[0].message.parsed:
            raise ValueError("No JSON found in the response")

        return self._output_schema.model_validate(
            llm_response.choices[0].message.parsed,
        ).to_web_search_results()


__all__ = [
    "JsonConversionStrategy",
    "LMIProtocol",
    "LLMParserStrategy",
    "LanguageModelServiceProtocol",
    "ResponseParser",
    "convert_response_to_search_results",
]
