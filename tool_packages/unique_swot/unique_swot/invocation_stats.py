"""Run-scoped collection of SWOT language-model invocation usage."""

import logging
from collections.abc import Iterator
from contextlib import contextmanager
from contextvars import ContextVar, Token
from typing import Any

from pydantic import ValidationError
from unique_toolkit.language_model.invocation_stats import LanguageModelInvocationStats
from unique_toolkit.language_model.schemas import LanguageModelTokenUsage

_LOGGER = logging.getLogger(__name__)

_CURRENT_INVOCATION_STATS: ContextVar[list[LanguageModelInvocationStats] | None] = (
    ContextVar("swot_invocation_stats", default=None)
)


@contextmanager
def invocation_stats_scope() -> Iterator[list[LanguageModelInvocationStats]]:
    """Collect stats for one SWOT run and isolate concurrent runs."""
    invocation_stats: list[LanguageModelInvocationStats] = []
    token: Token[list[LanguageModelInvocationStats] | None] = (
        _CURRENT_INVOCATION_STATS.set(invocation_stats)
    )
    try:
        yield invocation_stats
    finally:
        _CURRENT_INVOCATION_STATS.reset(token)


def record_token_usage(
    *,
    model_name: str,
    usage: Any,
    source: str,
) -> None:
    """Record provider usage when both a run scope and usage are available."""
    invocation_stats = _CURRENT_INVOCATION_STATS.get()
    if invocation_stats is None or usage is None:
        return

    try:
        token_usage = LanguageModelTokenUsage.model_validate(usage)
    except ValidationError:
        _LOGGER.warning(
            "Unable to parse SWOT token usage for %s",
            source,
            exc_info=True,
        )
        return

    invocation_stats.append(
        LanguageModelInvocationStats.from_usage(
            model_name=model_name,
            token_usage=token_usage,
            source=source,
        )
    )


def record_language_model_response(
    *,
    model_name: str,
    response: Any,
    source: str,
) -> None:
    """Record usage from a Unique Toolkit language-model response."""
    record_token_usage(
        model_name=model_name,
        usage=getattr(response, "usage", None),
        source=source,
    )
