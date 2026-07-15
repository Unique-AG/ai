"""Shared helpers for structured-output LLM completions."""

from typing import TypeVar

from pydantic import BaseModel
from unique_toolkit._common.validators import LMI
from unique_toolkit.language_model import LanguageModelService
from unique_toolkit.language_model.builder import MessagesBuilder

from unique_web_search.schema import WebSearchDebugInfo

T = TypeVar("T", bound=BaseModel)


class StructuredLlmUnparseableResponseError(Exception):
    """Raised when the LLM returns no parseable structured payload."""


async def complete_structured_llm(
    language_model_service: LanguageModelService,
    language_model: LMI,
    *,
    system_message: str,
    user_message: str,
    response_model: type[T],
    structured_output_enforce_schema: bool = True,
    debug_info: WebSearchDebugInfo | None = None,
    source: str = "web_search_argument_screening",
) -> T:
    """Run a structured completion and return a validated model instance."""
    messages = (
        MessagesBuilder()
        .system_message_append(system_message)
        .user_message_append(user_message)
        .build()
    )

    response = await language_model_service.complete_async(
        messages,
        model_name=language_model.name,
        structured_output_model=response_model,
        structured_output_enforce_schema=structured_output_enforce_schema,
    )

    if debug_info is not None:
        debug_info.add_invocation(
            language_model.name,
            response.usage,
            source=source,
        )

    parsed = response.choices[0].message.parsed
    if parsed is None:
        raise StructuredLlmUnparseableResponseError(
            "LLM structured completion returned no parseable payload"
        )

    return response_model.model_validate(parsed)
