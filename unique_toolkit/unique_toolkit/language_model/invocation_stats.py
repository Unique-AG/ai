"""Per-invocation LLM usage stats with model identity.

Lives in its own module (not ``schemas.py``) because it needs
``LanguageModelName`` from ``infos.py``, which itself imports from
``schemas.py``.

:class:`InvocationStatsCollector` collects those stats for one namespaced
run. ``record_token_usage`` swallows all exceptions around parsing and
:meth:`LanguageModelInvocationStats.from_usage`: usage is optional
billing metadata and must not abort a tool run.
"""

import logging
from collections.abc import Iterable, Iterator
from contextlib import contextmanager
from contextvars import ContextVar, Token
from typing import Annotated, Any, Self

from humps import camelize
from pydantic import BaseModel, BeforeValidator, ConfigDict

from unique_toolkit.language_model.infos import LanguageModelName
from unique_toolkit.language_model.model_costs import calculate_invocation_cost_usd
from unique_toolkit.language_model.schemas import LanguageModelTokenUsage

_LOGGER = logging.getLogger(__name__)

# `protected_namespaces=()` allows the `model_name` field name.
model_config = ConfigDict(
    alias_generator=camelize,
    populate_by_name=True,
    protected_namespaces=(),
)


def _normalize_model_name(value: object) -> object:
    """Canonicalize model_name: known names become the enum, customs stay str.

    Pydantic's smart union keeps string inputs as `str` even when they match a
    `LanguageModelName` value, so without this the same model could appear as
    enum or str depending on the caller.
    """
    if isinstance(value, str) and not isinstance(value, LanguageModelName):
        value = value.strip()
        if not value:
            raise ValueError("model_name must be a non-empty model name")
        try:
            return LanguageModelName(value)
        except ValueError:
            return value
    return value


def _validate_source(value: object) -> object:
    if isinstance(value, str):
        value = value.strip()
        if not value:
            raise ValueError("source must be a non-empty string")
    return value


ModelName = Annotated[LanguageModelName | str, BeforeValidator(_normalize_model_name)]
Source = Annotated[str, BeforeValidator(_validate_source)]


class LanguageModelInvocationStats(BaseModel):
    """Usage of a single LLM invocation, tied to the model that served it."""

    model_config = model_config

    model_name: ModelName
    token_usage: LanguageModelTokenUsage
    source: Source  # e.g. "main_loop", tool/evaluation/postprocessor name
    cost_usd: float | None = None

    @classmethod
    def from_usage(
        cls,
        model_name: LanguageModelName | str,
        token_usage: LanguageModelTokenUsage,
        source: str,
    ) -> Self:
        return cls(
            model_name=model_name,
            token_usage=token_usage,
            source=source,
            cost_usd=calculate_invocation_cost_usd(str(model_name), token_usage),
        )


class InvocationStatsCollector:
    """Run-scoped collector with a namespaced ContextVar so nested tools don't mix.

    Instantiate once per namespace and share that instance.
    """

    def __init__(self, namespace: str) -> None:
        self._namespace = namespace
        self._var: ContextVar[list[LanguageModelInvocationStats] | None] = ContextVar(
            f"{namespace}_invocation_stats", default=None
        )

    @contextmanager
    def scope(self) -> Iterator[list[LanguageModelInvocationStats]]:
        """Collect stats for one run and isolate concurrent runs."""
        invocation_stats: list[LanguageModelInvocationStats] = []
        token: Token[list[LanguageModelInvocationStats] | None] = self._var.set(
            invocation_stats
        )
        try:
            yield invocation_stats
        finally:
            self._var.reset(token)

    def record_invocation_stats(
        self,
        invocation_stats: Iterable[LanguageModelInvocationStats],
    ) -> None:
        """Record already-built stats when a run scope is active. No-op otherwise."""
        current_invocation_stats = self._var.get()
        if current_invocation_stats is not None:
            current_invocation_stats.extend(invocation_stats)

    def record_token_usage(
        self,
        *,
        model_name: str,
        usage: Any,
        source: str,
    ) -> None:
        """Record provider usage when a run scope and usage are available.

        Swallows all exceptions: this metadata is optional and must not abort
        the calling tool.
        """
        invocation_stats = self._var.get()
        if invocation_stats is None or usage is None:
            return

        try:
            token_usage = LanguageModelTokenUsage.model_validate(usage)
            invocation_stats.append(
                LanguageModelInvocationStats.from_usage(
                    model_name=model_name,
                    token_usage=token_usage,
                    source=source,
                )
            )
        except Exception:
            _LOGGER.warning(
                "Unable to parse %s token usage for %s",
                self._namespace,
                source,
                exc_info=True,
            )

    def record_language_model_response(
        self,
        *,
        model_name: str,
        response: Any,
        source: str,
    ) -> None:
        """Record usage from ``.usage``, ``.usage_metadata``, or ``response_metadata``."""
        usage = getattr(response, "usage", None)
        if usage is None:
            usage = getattr(response, "usage_metadata", None)
        if usage is None:
            response_metadata = getattr(response, "response_metadata", None)
            if isinstance(response_metadata, dict):
                usage = response_metadata.get("token_usage")

        self.record_token_usage(model_name=model_name, usage=usage, source=source)
