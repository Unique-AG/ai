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


def test_resolve_temp_and_reasoning_unknown_model_fallback():
    """Test that unknown (custom) model names use safe defaults."""
    assert LanguageModelInfo.resolve_temp_and_reasoning(
        "some-custom-model", 0.7, None
    ) == (
        0.0,
        None,
    )
    assert LanguageModelInfo.resolve_temp_and_reasoning(
        "some-custom-model", 0.7, "none"
    ) == (0.0, "none")
    assert LanguageModelInfo.resolve_temp_and_reasoning(
        "some-custom-model", 0.0, "medium"
    ) == (1.0, "medium")


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
    """Test that thinking-only models have reasoning_effort='none' corrected to their default.

    reasoning_effort=None means "not provided" (e.g. Chat Completions path) and must
    NOT trigger the fallback. Only the explicit string "none" (caller actively disabled
    reasoning) should be corrected.
    """
    # AZURE_GPT_54_PRO has temperature_bounds=(1.0, 1.0) and default reasoning_effort="medium"
    thinking_model = LanguageModelName.AZURE_GPT_54_PRO_2026_0305

    # Passing "none" → should be corrected to the model's default ("medium")
    temp, effort = LanguageModelInfo.resolve_temp_and_reasoning(
        thinking_model, 0.0, "none"
    )
    assert temp == 1.0
    assert effort == "medium"

    # Passing None → not provided; temperature is clamped to 1.0 but effort stays None
    temp, effort = LanguageModelInfo.resolve_temp_and_reasoning(
        thinking_model, 0.5, None
    )
    assert temp == 1.0
    assert effort is None


def test_resolve_temp_and_reasoning_warns_on_unsupported_effort(caplog):
    """Warning is logged when reasoning_effort is not in supported_reasoning_efforts."""
    # gpt-5.4-pro supports ["low", "medium", "high"] — "minimal" is not in the list
    thinking_model = LanguageModelName.AZURE_GPT_54_PRO_2026_0305

    with caplog.at_level(logging.WARNING, logger="unique_toolkit.language_model.infos"):
        temp, effort = LanguageModelInfo.resolve_temp_and_reasoning(
            thinking_model, 1.0, "minimal"
        )

    assert "not supported" in caplog.text
    # The effort is still passed through (not corrected) since it is active reasoning
    assert temp == 1.0
    assert effort == "minimal"


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
