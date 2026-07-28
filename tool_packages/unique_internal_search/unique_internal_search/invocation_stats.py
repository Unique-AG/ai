"""Run-scoped collection of language-model invocation usage."""

from collections.abc import Generator, Iterable
from contextlib import contextmanager
from contextvars import ContextVar, Token

from unique_toolkit.language_model.invocation_stats import LanguageModelInvocationStats

_CURRENT_INVOCATION_STATS: ContextVar[list[LanguageModelInvocationStats] | None] = (
    ContextVar("internal_search_invocation_stats", default=None)
)


@contextmanager
def invocation_stats_scope() -> Generator[list[LanguageModelInvocationStats]]:
    """Collect stats for one internal-search run and isolate concurrent runs."""
    invocation_stats: list[LanguageModelInvocationStats] = []
    token: Token[list[LanguageModelInvocationStats] | None] = (
        _CURRENT_INVOCATION_STATS.set(invocation_stats)
    )
    try:
        yield invocation_stats
    finally:
        _CURRENT_INVOCATION_STATS.reset(token)


def record_invocation_stats(
    invocation_stats: Iterable[LanguageModelInvocationStats],
) -> None:
    """Record usage when an internal-search run scope is active."""
    current_invocation_stats = _CURRENT_INVOCATION_STATS.get()
    if current_invocation_stats is not None:
        current_invocation_stats.extend(invocation_stats)
