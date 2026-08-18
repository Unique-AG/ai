"""Tests for experimental streaming LanguageModelInfo temperature resolution."""

from __future__ import annotations

import pytest

from unique_toolkit.experimental.integrations.openai.streaming.event_routing._model_params import (
    prepare_chat_completions_model_params,
    prepare_responses_model_params,
)
from unique_toolkit.language_model.infos import LanguageModelName


@pytest.mark.ai
@pytest.mark.parametrize(
    ("model_name", "requested", "expected_temperature"),
    [
        (LanguageModelName.AZURE_GPT_5_2025_0807, 0.5, 1.0),
        (LanguageModelName.LITELLM_OPENAI_GPT_5, 0.5, 1.0),
        ("AZURE_GPT_5_2025_0807", 0.5, 1.0),
        ("litellm:openai-gpt-5", 0.5, 1.0),
        ("test-model", 0.5, 0.5),
    ],
)
def test_AI_prepare_chat_completions_model_params__clamps_gpt5_temperature(
    model_name: LanguageModelName | str,
    requested: float,
    expected_temperature: float,
) -> None:
    """
    Purpose: Chat Completions prep applies LanguageModelInfo temperature bounds.
    Why this matters: GPT-5 rejects any temperature other than 1.0. Spaces
      configured with 0.5 must be clamped before the API call (UN-23221).
    Setup summary: Prepare params for GPT-5 and a custom model; assert GPT-5
      is clamped to 1.0 and the custom model keeps 0.5.
    """
    options = prepare_chat_completions_model_params(model_name, requested, None)
    assert options["temperature"] == expected_temperature


@pytest.mark.ai
def test_AI_prepare_chat_completions_model_params__clamps_and_overwrites_temperature() -> (
    None
):
    """
    Purpose: Chat Completions prep writes the clamped temperature onto options
      so a competing ``other_options`` value cannot win.
    Why this matters: UniqueAI may merge additional LLM options into the
      create() kwargs. That merge must not restore an out-of-bounds value.
    Setup summary: Prepare GPT-5 params with temperature 0.5 and other_options
      temperature 0.5; assert the returned dict has 1.0 and the original is
      unchanged.
    """
    original = {"temperature": 0.5, "user": "space-1"}

    options = prepare_chat_completions_model_params(
        "AZURE_GPT_5_2025_0807", 0.5, original
    )

    assert options["temperature"] == 1.0
    assert options["user"] == "space-1"
    assert original == {"temperature": 0.5, "user": "space-1"}


@pytest.mark.ai
def test_AI_prepare_chat_completions_model_params__custom_model_keeps_temperature() -> (
    None
):
    """
    Purpose: Models without declared bounds keep the requested temperature.
    Why this matters: Clamping must be model-specific; a global force to 1.0
      would change sampling for models that accept 0.5.
    Setup summary: Prepare params for a custom model at 0.5; assert 0.5.
    """
    options = prepare_chat_completions_model_params("test-model", 0.5, None)

    assert options["temperature"] == 0.5
    assert "reasoning_effort" not in options


@pytest.mark.ai
def test_AI_prepare_responses_model_params__clamps_and_strips_overrides() -> None:
    """
    Purpose: Responses prep clamps GPT-5 temperature onto the options dict and
      keeps resolved reasoning there after extracting it from other_options.
    Why this matters: UniqueAI passes ``reasoning`` inside other_options. If
      those keys are merged after clamping, the API still sees temperature 0.5.
    Setup summary: Prepare GPT-5 params with other_options temperature 0.5;
      assert clamped temperature and reasoning on the returned dict.
    """
    original = {"temperature": 0.5, "reasoning": {"effort": "low"}}

    options = prepare_responses_model_params(
        "AZURE_GPT_5_2025_0807", 0.5, None, original
    )

    assert options["temperature"] == 1.0
    assert options["reasoning"]["effort"] == "low"
    assert original == {"temperature": 0.5, "reasoning": {"effort": "low"}}


@pytest.mark.ai
def test_AI_prepare_responses_model_params__code_interpreter_bumps_minimal() -> None:
    """
    Purpose: Code interpreter plus GPT-5 default ``minimal`` effort is bumped
      to ``low``.
    Why this matters: The Responses API rejects code interpreter at minimal
      effort; the old node-chat path already switches to low.
    Setup summary: Prepare GPT-5 params with a code_interpreter tool and no
      explicit effort; assert effort is ``low``.
    """
    options = prepare_responses_model_params(
        "AZURE_GPT_5_2025_0807",
        0.5,
        None,
        None,
        tools=[{"type": "code_interpreter"}],
    )

    assert options["reasoning"]["effort"] == "low"
