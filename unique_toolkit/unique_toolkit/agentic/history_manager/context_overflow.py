"""Keep agent-loop prompts inside the provider's context window.

The local reducer estimates tokens with an OpenAI tokenizer, which can undercount
other providers by 2x or more. ``ContextOverflowGuard`` verifies near-limit
payloads with the provider's own counter before the LLM call and recovers when the
provider still rejects a prompt as too long.
"""

from __future__ import annotations

import asyncio
import time
from collections.abc import Awaitable, Callable
from logging import Logger
from typing import Any, TypeVar

from unique_toolkit.agentic.history_manager.history_manager import HistoryManager
from unique_toolkit.agentic.loop_runner.base import _LoopIterationRunnerKwargs
from unique_toolkit.language_model.infos import LanguageModelInfo
from unique_toolkit.language_model.settings import ModelFamily
from unique_toolkit.protocols.support import SupportsTokenCount

_T = TypeVar("_T")

_CONTEXT_OVERFLOW_SIGNALS = (
    "context_length_exceeded",
    "contextwindowexceedederror",
    "tokenlimitexceeded",
    "maximum context length",
    "prompt is too long",
    "input is too long",
    "too many input tokens",
    "exceeds the maximum number of tokens",
)
_CONTEXT_WINDOW_QUALIFIERS = ("exceed", "too long", "maximum")

CONTEXT_OVERFLOW_TOKEN_BUDGET_FACTOR = 0.7
PROVIDER_COUNT_TARGET_RATIO = 0.95
MAX_PROVIDER_OVERFLOW_REDUCTION_FACTOR = 0.9
APPROXIMATE_TOKENIZER_TRIGGER_RATIO = 0.7
NATIVE_TOKENIZER_TRIGGER_RATIO = 0.85
LOCAL_LIMIT_TRIGGER_RATIO = 0.95
DEFAULT_OUTPUT_TOKEN_RESERVE = 10_000
PROVIDER_TOKEN_COUNT_TIMEOUT_SECONDS = 10

_NATIVE_TOKENIZER_FAMILIES = {
    ModelFamily.OPENAI,
    ModelFamily.DEEPSEEK,
    ModelFamily.QWEN,
}

WITHHELD_TOOL_RESULT_NOTICE = (
    "The combined output of the tool calls made in this step was too large for "
    "the model's context window, so this result was withheld. Do not repeat "
    "these tool calls in parallel. Call them one at a time instead, and narrow "
    "each call (for example a lower result limit, a shorter date range or a "
    "more specific query) so that each result stays small."
)


def is_context_window_exceeded_error(exc: BaseException) -> bool:
    """Return True if *exc* indicates the prompt exceeded the model's context window."""
    error_text = f"{type(exc).__name__} {exc}".lower()
    if any(signal in error_text for signal in _CONTEXT_OVERFLOW_SIGNALS):
        return True
    return "context window" in error_text and any(
        qualifier in error_text for qualifier in _CONTEXT_WINDOW_QUALIFIERS
    )


def supports_provider_token_count(model: LanguageModelInfo) -> bool:
    return model.family == ModelFamily.ANTHROPIC


def provider_context_window(model: LanguageModelInfo) -> int:
    return model.provider_context_window


def provider_count_trigger_tokens(
    model: LanguageModelInfo,
    effective_local_limit: int,
) -> int:
    """Local count at which an authoritative provider count becomes worthwhile."""
    ratio = (
        NATIVE_TOKENIZER_TRIGGER_RATIO
        if model.family in _NATIVE_TOKENIZER_FAMILIES
        else APPROXIMATE_TOKENIZER_TRIGGER_RATIO
    )
    return min(
        int(provider_context_window(model) * ratio),
        int(effective_local_limit * LOCAL_LIMIT_TRIGGER_RATIO),
    )


def provider_input_target(
    model: LanguageModelInfo,
    other_options: dict[str, Any] | None,
) -> int:
    """Maximum provider-counted input while preserving output and safety room."""
    options = other_options or {}
    configured_output = options.get("max_completion_tokens", options.get("max_tokens"))
    output_reserve = (
        configured_output
        if isinstance(configured_output, int) and configured_output >= 0
        else min(
            DEFAULT_OUTPUT_TOKEN_RESERVE,
            model.token_limits.token_limit_output,
        )
    )
    return max(
        1,
        int(provider_context_window(model) * PROVIDER_COUNT_TARGET_RATIO)
        - output_reserve,
    )


def provider_overflow_reduction_factor(provider_count: int, target: int) -> float:
    """Budget multiplier that brings an oversized provider count under *target*."""
    return min(
        MAX_PROVIDER_OVERFLOW_REDUCTION_FACTOR,
        target / provider_count * PROVIDER_COUNT_TARGET_RATIO,
    )


class ContextOverflowGuard:
    """Preflight provider token-budget verification and overflow retry policy."""

    def __init__(
        self,
        *,
        logger: Logger,
        history_manager: HistoryManager,
        token_counter: object,
        model: LanguageModelInfo,
    ) -> None:
        self._logger = logger
        self._history_manager = history_manager
        self._token_counter = token_counter
        self._model = model

    async def preflight_token_budget(
        self,
        kwargs: _LoopIterationRunnerKwargs,
        recompose: Callable[[], Awaitable[None]],
    ) -> None:
        """Verify near-limit payloads using the provider's tokenizer before the LLM call."""
        if not supports_provider_token_count(self._model):
            return
        if not isinstance(self._token_counter, SupportsTokenCount):
            return

        local_count = self._history_manager.last_token_count
        effective_limit = self._history_manager.effective_token_limit
        trigger = provider_count_trigger_tokens(self._model, effective_limit)
        if local_count < trigger:
            return

        target = provider_input_target(self._model, kwargs.get("other_options"))
        provider_count = await self._try_provider_token_count(kwargs)
        if provider_count is None or provider_count <= target:
            return

        self._logger.warning(
            f"Provider token count {provider_count} exceeds the safe input target "
            f"{target}. Reducing tool results before the LLM call."
        )
        reduction_factor = provider_overflow_reduction_factor(provider_count, target)
        self._history_manager.tighten_token_budget(reduction_factor)
        await recompose()

        reduced_count = await self._try_provider_token_count(kwargs)
        if reduced_count is None or reduced_count <= target:
            return

        if not self._history_manager.withhold_latest_tool_call_results(
            WITHHELD_TOOL_RESULT_NOTICE
        ):
            self._logger.warning(
                f"Provider token count remains above target ({reduced_count} > "
                f"{target}), but there are no tool results to withhold."
            )
            return

        self._logger.warning(
            "Provider token count remains above target after reduction. "
            "Withholding the latest tool-call batch."
        )
        await recompose()

        withheld_count = await self._try_provider_token_count(kwargs)
        if withheld_count is None or withheld_count <= target:
            return

        self._logger.warning(
            f"Provider token count {withheld_count} still exceeds the safe input "
            f"target {target} after withholding. Reducing history further."
        )
        self._history_manager.tighten_token_budget(
            provider_overflow_reduction_factor(withheld_count, target)
        )
        await recompose()

    async def retry_after_overflow(
        self,
        exc: Exception,
        *,
        recompose: Callable[[], Awaitable[None]],
        run_iteration: Callable[[], Awaitable[_T]],
    ) -> _T:
        """Retry an oversized LLM call by tightening the budget or withholding the latest tool batch."""
        self._logger.warning(
            "LLM call exceeded the context window. Retrying with a tighter token budget.",
            exc_info=exc,
        )
        self._history_manager.tighten_token_budget(CONTEXT_OVERFLOW_TOKEN_BUDGET_FACTOR)
        await recompose()
        try:
            return await run_iteration()
        except Exception as retry_exc:
            if not is_context_window_exceeded_error(retry_exc):
                raise
            if not self._history_manager.withhold_latest_tool_call_results(
                WITHHELD_TOOL_RESULT_NOTICE
            ):
                raise
            self._logger.warning(
                "LLM call still exceeded the context window. Retrying with the "
                "latest tool call results withheld."
            )
            await recompose()
            return await run_iteration()

    async def _try_provider_token_count(
        self, kwargs: _LoopIterationRunnerKwargs
    ) -> int | None:
        counter = self._token_counter
        if not isinstance(counter, SupportsTokenCount):
            return None
        started_at = time.perf_counter()
        try:
            count = await asyncio.wait_for(
                counter.count_tokens_async(
                    messages=kwargs["messages"],
                    model_name=self._model.name,
                    temperature=kwargs.get("temperature", 0.0),
                    tools=kwargs.get("tools"),
                    other_options=kwargs.get("other_options"),
                ),
                timeout=PROVIDER_TOKEN_COUNT_TIMEOUT_SECONDS,
            )
        except Exception:
            elapsed_ms = (time.perf_counter() - started_at) * 1000
            self._logger.warning(
                f"Provider token counting failed after {elapsed_ms:.0f} ms. "
                "Continuing with the local token budget.",
                exc_info=True,
            )
            return None
        elapsed_ms = (time.perf_counter() - started_at) * 1000
        self._logger.info(
            f"Provider token count for {self._model.name}: {count} tokens "
            f"in {elapsed_ms:.0f} ms."
        )
        return count if count > 0 else None
