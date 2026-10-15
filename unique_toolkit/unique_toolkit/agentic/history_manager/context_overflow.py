from typing import Any

from unique_toolkit.language_model.infos import LanguageModelInfo
from unique_toolkit.language_model.settings import ModelFamily

_CONTEXT_OVERFLOW_SIGNALS = (
    "context_length_exceeded",
    "contextwindowexceedederror",
    "tokenlimitexceeded",
    "maximum context length",
    "context window",
    "prompt is too long",
    "input is too long",
    "too many input tokens",
    "exceeds the maximum number of tokens",
)

CONTEXT_OVERFLOW_TOKEN_BUDGET_FACTOR = 0.7
PROVIDER_COUNT_TARGET_RATIO = 0.95
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

_CLAUDE_CONTEXT_WINDOWS = {
    "claude-3-7-sonnet": 200_000,
    "claude-3-7-sonnet-thinking": 200_000,
    "claude-haiku-4-5": 200_000,
    "claude-opus-4": 200_000,
    "claude-opus-4-1": 200_000,
    "claude-opus-4-5": 200_000,
    "claude-opus-4-6": 200_000,
    "claude-sonnet-4": 200_000,
    "claude-sonnet-4-5": 200_000,
    "claude-sonnet-4-6": 200_000,
    "claude-fable-5": 1_000_000,
    "claude-haiku-5-5": 1_000_000,
    "claude-opus-4-7": 1_000_000,
    "claude-opus-4-8": 1_000_000,
    "claude-opus-5": 1_000_000,
    "claude-opus-5-5": 1_000_000,
    "claude-sonnet-5": 1_000_000,
    "claude-sonnet-5-5": 1_000_000,
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
    return any(signal in error_text for signal in _CONTEXT_OVERFLOW_SIGNALS)


def supports_provider_token_count(model: LanguageModelInfo) -> bool:
    return model.family == ModelFamily.ANTHROPIC


def provider_context_window(model: LanguageModelInfo) -> int:
    if model.family == ModelFamily.ANTHROPIC:
        known_window = _CLAUDE_CONTEXT_WINDOWS.get(model.version)
        if known_window is None:
            model_name = str(model.name)
            known_window = next(
                (
                    window
                    for version, window in sorted(
                        _CLAUDE_CONTEXT_WINDOWS.items(),
                        key=lambda item: len(item[0]),
                        reverse=True,
                    )
                    if version in model_name
                ),
                None,
            )
        if known_window is not None:
            return known_window
    return model.token_limits.token_limit_input


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
