import logging
from unittest.mock import patch

import pytest
import unique_sdk

from unique_toolkit.content.schemas import ContentChunk
from unique_toolkit.language_model.functions import (
    _add_tools_to_options,
    _prepare_completion_params_util,
    _to_search_context,
    complete,
    complete_async,
)
from unique_toolkit.language_model.infos import LanguageModelInfo, LanguageModelName
from unique_toolkit.language_model.schemas import (
    LanguageModelMessages,
    LanguageModelTool,
    LanguageModelToolParameterProperty,
    LanguageModelToolParameters,
)

# Mock tool for testing
mock_tool = LanguageModelTool(
    name="get_weather",
    description="Get the current weather for a location",
    parameters=LanguageModelToolParameters(
        type="object",
        properties={
            "location": LanguageModelToolParameterProperty(
                type="string", description="The city and state, e.g. San Francisco, CA"
            ),
            "unit": LanguageModelToolParameterProperty(
                type="string",
                description="The unit system to use. Either 'celsius' or 'fahrenheit'.",
                enum=["celsius", "fahrenheit"],
            ),
        },
        required=["location"],
    ),
)


def test_prepare_completion_params_util_basic():
    messages = LanguageModelMessages([])
    model_name = LanguageModelName.AZURE_GPT_4_0613
    temperature = 0.5

    options, model, messages_dict, search_context = _prepare_completion_params_util(
        messages=messages,
        model_name=model_name,
        temperature=temperature,
    )

    assert options == {"temperature": 0.5}
    assert model == model_name.name
    assert messages_dict == []
    assert search_context is None


def test_prepare_completion_params_util_with_tools_and_other_options():
    messages = LanguageModelMessages([])
    other_options = {"max_tokens": 100, "top_p": 0.9}

    options, model, messages_dict, search_context = _prepare_completion_params_util(
        messages=messages,
        model_name="custom_model",
        temperature=0.7,
        tools=[mock_tool],
        other_options=other_options,
    )

    expected_options = {
        "temperature": 0.7,
        "max_tokens": 100,
        "top_p": 0.9,
        "tools": [
            {
                "type": "function",
                "function": mock_tool.model_dump(exclude_none=True),
            }
        ],
    }

    assert options == expected_options
    assert model == "custom_model"
    assert messages_dict == []
    assert search_context is None


def test_add_tools_to_options():
    options = {"existing": "option"}
    result = _add_tools_to_options(options, [mock_tool])

    assert result["existing"] == "option"
    assert "tools" in result
    assert len(result["tools"]) == 1
    assert result["tools"][0]["type"] == "function"
    assert result["tools"][0]["function"]["name"] == "get_weather"


def test_to_search_context():
    chunks = [
        ContentChunk(id="1", chunk_id="1", key="test", order=1, text="test"),
        ContentChunk(id="2", chunk_id="2", key="test2", order=2, text="test2"),
    ]

    result = _to_search_context(chunks)

    assert result is not None
    assert len(result) == 2
    assert result[0]["id"] == "1"
    assert result[1]["id"] == "2"


@patch.object(unique_sdk.ChatCompletion, "create")
def test_complete_basic(mock_create):
    mock_create.return_value = {
        "choices": [
            {
                "index": 0,
                "finishReason": "completed",
                "message": {
                    "content": "Test response",
                    "role": "assistant",
                },
            }
        ]
    }

    messages = LanguageModelMessages([])
    result = complete(
        company_id="test_company",
        messages=messages,
        model_name=LanguageModelName.AZURE_GPT_4_0613,
    )

    assert result.choices[0].message.content == "Test response"
    mock_create.assert_called_once()


@pytest.mark.asyncio
@patch.object(unique_sdk.ChatCompletion, "create_async")
async def test_complete_async_basic(mock_create):
    mock_create.return_value = {
        "choices": [
            {
                "index": 0,
                "finishReason": "completed",
                "message": {
                    "content": "Test response",
                    "role": "assistant",
                },
            }
        ]
    }

    messages = LanguageModelMessages([])
    result = await complete_async(
        company_id="test_company",
        user_id="test_user",
        messages=messages,
        model_name=LanguageModelName.AZURE_GPT_4_0613,
    )

    assert result.choices[0].message.content == "Test response"
    mock_create.assert_called_once()


def test_resolve_temp_and_reasoning_clamps_temperature():
    """Test that temperature is clamped to the model's declared bounds when no reasoning."""
    # AZURE_GPT_51 has temperature_bounds min=0.0, max=1.0 (switchable model)
    model = LanguageModelName.AZURE_GPT_51_2025_1113

    assert LanguageModelInfo.resolve_temp_and_reasoning(model, 0.12345, None) == (
        0.12,
        None,
    )
    assert LanguageModelInfo.resolve_temp_and_reasoning(model, 0.996, None) == (
        1.0,
        None,
    )
    assert LanguageModelInfo.resolve_temp_and_reasoning(model, 2.0, None) == (1.0, None)
    assert LanguageModelInfo.resolve_temp_and_reasoning(model, -0.5, None) == (
        0.0,
        None,
    )


def test_resolve_temp_and_reasoning_unknown_model_passthrough():
    """Unknown model names: both temperature and reasoning_effort are returned unchanged."""
    assert LanguageModelInfo.resolve_temp_and_reasoning(
        "some-custom-model", 0.7, None
    ) == (0.7, None)
    assert LanguageModelInfo.resolve_temp_and_reasoning(
        "some-custom-model", 0.7, "none"
    ) == (0.7, "none")
    # temperature > 1 passes through (no clamping for unknown models)
    assert LanguageModelInfo.resolve_temp_and_reasoning(
        "some-custom-model", 1.5, None
    ) == (1.5, None)
    # even out-of-range values pass through unchanged
    assert LanguageModelInfo.resolve_temp_and_reasoning(
        "some-custom-model", 2.5, None
    ) == (2.5, None)
    assert LanguageModelInfo.resolve_temp_and_reasoning(
        "some-custom-model", -0.1, None
    ) == (-0.1, None)
    # active reasoning also passes through unchanged
    assert LanguageModelInfo.resolve_temp_and_reasoning(
        "some-custom-model", 0.0, "medium"
    ) == (0.0, "medium")


def test_resolve_temp_and_reasoning_boundless_known_model_allows_up_to_2():
    """Models without declared temperature_bounds fall back to [0, 2], not [0, 1]."""
    boundless_model = LanguageModelName.AZURE_GPT_4o_2024_1120
    # temperature in (1, 2] should pass through unchanged
    assert LanguageModelInfo.resolve_temp_and_reasoning(boundless_model, 1.5, None) == (
        1.5,
        None,
    )
    # temperature > 2 is clamped to 2.0 with a warning
    assert LanguageModelInfo.resolve_temp_and_reasoning(boundless_model, 2.5, None) == (
        2.0,
        None,
    )
    # temperature < 0 is clamped to 0.0
    assert LanguageModelInfo.resolve_temp_and_reasoning(
        boundless_model, -0.1, None
    ) == (0.0, None)


def test_resolve_temp_and_reasoning_forces_1_when_reasoning_active():
    """Test that active reasoning forces temperature to 1.0."""
    thinking_model = LanguageModelName.AZURE_GPT_54_PRO_2026_0305
    assert LanguageModelInfo.resolve_temp_and_reasoning(
        thinking_model, 0.0, "medium"
    ) == (
        1.0,
        "medium",
    )
    assert LanguageModelInfo.resolve_temp_and_reasoning(
        thinking_model, 0.5, "high"
    ) == (
        1.0,
        "high",
    )

    # Switchable model with active reasoning also gets temperature=1.0
    switchable_model = LanguageModelName.AZURE_GPT_51_2025_1113
    assert LanguageModelInfo.resolve_temp_and_reasoning(
        switchable_model, 0.0, "low"
    ) == (
        1.0,
        "low",
    )

    # reasoning_effort='none' on switchable model → clamping applies
    assert LanguageModelInfo.resolve_temp_and_reasoning(
        switchable_model, 0.5, "none"
    ) == (
        0.5,
        "none",
    )


def test_resolve_temp_and_reasoning_fixes_thinking_only_model_with_none_effort():
    """Scenario 3 catches 'none' for thinking-only models and falls back to first supported effort.

    reasoning_effort=None means "not provided" (e.g. Chat Completions path) and must
    NOT trigger the fallback.
    """
    # AZURE_GPT_54_PRO supports ["low", "medium", "high"] — "none" is not in the list
    thinking_model = LanguageModelName.AZURE_GPT_54_PRO_2026_0305

    # Passing "none" → not in supported list, falls back to first supported effort ("low")
    temp, effort = LanguageModelInfo.resolve_temp_and_reasoning(
        thinking_model, 0.0, "none"
    )
    assert temp == 1.0
    assert effort == "low"

    # Passing None → not provided; temperature is clamped to 1.0 by bounds but effort stays None
    temp, effort = LanguageModelInfo.resolve_temp_and_reasoning(
        thinking_model, 0.5, None
    )
    assert temp == 1.0
    assert effort is None


def test_resolve_temp_and_reasoning_drops_effort_for_non_reasoning_model(caplog):
    """Scenario 2: model with supported_reasoning_efforts=None warns and drops the effort."""
    # GPT-4o does not participate in the reasoning_effort paradigm
    model = LanguageModelName.AZURE_GPT_4o_2024_1120

    with caplog.at_level(logging.WARNING, logger="unique_toolkit.language_model.infos"):
        temp, effort = LanguageModelInfo.resolve_temp_and_reasoning(
            model, 0.7, "medium"
        )

    assert "does not support reasoning_effort" in caplog.text
    assert effort is None
    assert temp == 0.7


def test_resolve_temp_and_reasoning_warns_on_unsupported_effort(caplog):
    """Scenario 3: unsupported effort is warned about and corrected to first supported effort."""
    # gpt-5.4-pro supports ["low", "medium", "high"] — "minimal" is not in the list
    thinking_model = LanguageModelName.AZURE_GPT_54_PRO_2026_0305

    with caplog.at_level(logging.WARNING, logger="unique_toolkit.language_model.infos"):
        temp, effort = LanguageModelInfo.resolve_temp_and_reasoning(
            thinking_model, 0.5, "minimal"
        )

    assert "not supported" in caplog.text
    # Falls back to the first (lightest) supported effort; active reasoning forces temp to 1.0
    assert temp == 1.0
    assert effort == "low"


def test_resolve_temp_and_reasoning_warns_on_out_of_bounds_temperature(caplog):
    """Warning is logged when temperature is outside model bounds (no reasoning)."""
    # AZURE_GPT_51 has temperature_bounds [0.0, 1.0]
    model = LanguageModelName.AZURE_GPT_51_2025_1113

    with caplog.at_level(logging.WARNING, logger="unique_toolkit.language_model.infos"):
        temp, effort = LanguageModelInfo.resolve_temp_and_reasoning(model, 2.5, None)

    assert "out of bounds" in caplog.text
    assert temp == 1.0  # clamped to max
    assert effort is None


def test_resolve_temp_and_reasoning_no_warning_for_valid_effort(caplog):
    """No warning is logged when reasoning_effort is valid for the model."""
    # gpt-5.4-pro supports ["low", "medium", "high"]
    thinking_model = LanguageModelName.AZURE_GPT_54_PRO_2026_0305

    with caplog.at_level(logging.WARNING, logger="unique_toolkit.language_model.infos"):
        temp, effort = LanguageModelInfo.resolve_temp_and_reasoning(
            thinking_model, 0.0, "high"
        )

    assert "not supported" not in caplog.text
    assert temp == 1.0
    assert effort == "high"


def test_supported_reasoning_efforts_set_correctly():
    """Verify that supported_reasoning_efforts is assigned correctly for key models."""
    # gpt-5 family (original) supports minimal
    gpt5 = LanguageModelInfo.from_name(LanguageModelName.AZURE_GPT_5_2025_0807)
    assert gpt5.supported_reasoning_efforts == ["minimal", "low", "medium", "high"]

    # gpt-5-pro only supports high
    gpt5_pro = LanguageModelInfo.from_name(LanguageModelName.AZURE_GPT_5_PRO_2025_1006)
    assert gpt5_pro.supported_reasoning_efforts == ["high"]

    # gpt-5.1 and greater support none but not minimal
    gpt51 = LanguageModelInfo.from_name(LanguageModelName.AZURE_GPT_51_2025_1113)
    assert gpt51.supported_reasoning_efforts == ["none", "low", "medium", "high"]
    assert "minimal" not in gpt51.supported_reasoning_efforts

    # Thinking-only variants do not include none
    gpt54_pro = LanguageModelInfo.from_name(
        LanguageModelName.AZURE_GPT_54_PRO_2026_0305
    )
    assert gpt54_pro.supported_reasoning_efforts == ["low", "medium", "high"]
    assert "none" not in gpt54_pro.supported_reasoning_efforts

    # o-series
    o3 = LanguageModelInfo.from_name(LanguageModelName.AZURE_o3_2025_0416)
    assert o3.supported_reasoning_efforts == ["low", "medium", "high"]

    # o1-mini has no reasoning_effort support (None)
    o1_mini = LanguageModelInfo.from_name(LanguageModelName.AZURE_o1_MINI_2024_0912)
    assert o1_mini.supported_reasoning_efforts is None

    # Third-party models (DeepSeek, Qwen) have None
    deepseek = LanguageModelInfo.from_name(LanguageModelName.LITELLM_DEEPSEEK_R1)
    assert deepseek.supported_reasoning_efforts is None
