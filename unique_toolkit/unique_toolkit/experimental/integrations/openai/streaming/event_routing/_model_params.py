"""Apply LanguageModelInfo constraints to experimental streaming requests."""

from __future__ import annotations

import logging
from collections.abc import Mapping, Sequence
from typing import Any

from openai.types.shared_params import Reasoning

from unique_toolkit.chat.responses_api import _attempt_extract_reasoning_from_options
from unique_toolkit.language_model.infos import LanguageModelInfo, LanguageModelName
from unique_toolkit.language_model.schemas import reasoning_effort_to_openai

_LOGGER = logging.getLogger(__name__)

_REASONING_OPTION_KEYS = ("reasoning", "reasoning_effort", "reasoningEffort")


def prepare_chat_completions_model_params(
    model_name: LanguageModelName | str,
    temperature: float,
    other_options: dict[str, Any] | None,
) -> dict[str, Any]:
    """Prepare Chat Completions create() options including clamped temperature.

    Copies ``other_options`` so the caller dict is not mutated, applies
    ``LanguageModelInfo`` temperature/reasoning rules, and writes the clamped
    temperature onto the returned options dict.

    Args:
        model_name (LanguageModelName | str): Model identifier from the caller.
        temperature (float): Requested sampling temperature.
        other_options (dict[str, Any] | None): Extra OpenAI create() kwargs.

    Returns:
        dict[str, Any]: Sanitized create() options including ``temperature``.
    """
    options = dict(other_options) if other_options else {}
    requested_effort = options.get("reasoning_effort")
    temperature, resolved_effort = LanguageModelInfo.from_name(
        model_name
    ).resolve_temp_and_reasoning(temperature, requested_effort)
    if resolved_effort is not None:
        options["reasoning_effort"] = resolved_effort
    else:
        options.pop("reasoning_effort", None)
    options["temperature"] = temperature
    return options


def prepare_responses_model_params(
    model_name: LanguageModelName | str,
    temperature: float,
    reasoning: Reasoning | None,
    other_options: dict[str, Any] | None,
    tools: Sequence[Mapping[str, Any]] | None = None,
) -> dict[str, Any]:
    """Prepare Responses API create() options including clamped temperature.

    Extracts reasoning from ``other_options`` when the explicit argument is
    missing (UniqueAI passes ``reasoning`` that way), applies
    ``LanguageModelInfo`` bounds, and bumps ``minimal`` effort to ``low`` when
    a code-interpreter tool is present. Clamped temperature and resolved
    reasoning are written onto the returned options dict.

    Args:
        model_name (LanguageModelName | str): Model identifier from the caller.
        temperature (float): Requested sampling temperature.
        reasoning (Reasoning | None): Explicit Responses ``reasoning`` payload.
        other_options (dict[str, Any] | None): Extra OpenAI create() kwargs.
        tools (Sequence[Mapping[str, Any]] | None): Converted Responses tools.

    Returns:
        dict[str, Any]: Sanitized create() options including ``temperature``.
    """
    options = dict(other_options) if other_options else {}
    if reasoning is None:
        reasoning = _attempt_extract_reasoning_from_options(options)
    for key in _REASONING_OPTION_KEYS:
        options.pop(key, None)

    requested_effort = reasoning.get("effort") if reasoning is not None else None
    temperature, resolved_effort = LanguageModelInfo.from_name(
        model_name
    ).resolve_temp_and_reasoning(temperature, requested_effort)
    reasoning = _bump_code_interpreter_effort(
        _apply_resolved_reasoning(reasoning, resolved_effort),
        tools,
    )
    options["temperature"] = temperature
    if reasoning is not None:
        options["reasoning"] = reasoning
    return options


def _apply_resolved_reasoning(
    reasoning: Reasoning | None,
    resolved_effort: str | None,
) -> Reasoning | None:
    """Write the resolved effort into a new Responses ``reasoning`` payload."""
    if resolved_effort is not None:
        reasoning = Reasoning(**(reasoning or {}))
        reasoning["effort"] = reasoning_effort_to_openai(resolved_effort)
        return reasoning
    if reasoning is None or "effort" not in reasoning:
        return reasoning
    reasoning = Reasoning(**reasoning)
    del reasoning["effort"]
    if not reasoning:
        return None
    return reasoning


def _bump_code_interpreter_effort(
    reasoning: Reasoning | None,
    tools: Sequence[Mapping[str, Any]] | None,
) -> Reasoning | None:
    """Code interpreter cannot run at ``minimal`` effort; bump to ``low``."""
    if (
        reasoning is None
        or tools is None
        or not any(tool["type"] == "code_interpreter" for tool in tools)
        or reasoning.get("effort") != "minimal"
    ):
        return reasoning

    _LOGGER.warning(
        "Code interpreter cannot be used with `minimal` effort. Switching to `low`."
    )
    reasoning = Reasoning(**reasoning)
    reasoning["effort"] = "low"
    return reasoning
