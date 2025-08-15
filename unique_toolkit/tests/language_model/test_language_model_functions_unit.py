from unittest.mock import patch

import pytest
import unique_sdk

from unique_toolkit.content.schemas import ContentChunk
from unique_toolkit.language_model.functions import (
    _add_tools_to_options,
    _clamp_temperature,
    _prepare_completion_params_util,
    _to_search_context,
    complete,
    complete_async,
)
from unique_toolkit.language_model.infos import LanguageModelName, TemperatureBounds
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
        messages=messages,
        model_name=LanguageModelName.AZURE_GPT_4_0613,
    )

    assert result.choices[0].message.content == "Test response"
    mock_create.assert_called_once()


def test_clamp_temperature_no_bounds():
    """Test temperature clamping when no bounds are set."""
    # Test with no bounds set - should just round to 2 decimal places
    bounds = TemperatureBounds()
    
    # Test exact rounding
    assert _clamp_temperature(0.555, bounds) == 0.56
    assert _clamp_temperature(0.554, bounds) == 0.55
    
    # Test no rounding needed
    assert _clamp_temperature(0.5, bounds) == 0.5
    assert _clamp_temperature(1.0, bounds) == 1.0
    
    # Test extreme values with no bounds
    assert _clamp_temperature(-1.0, bounds) == -1.0
    assert _clamp_temperature(100.0, bounds) == 100.0


def test_clamp_temperature_bounds_clamping():
    """Test temperature clamping when bounds enforce limits."""
    # Test with both min and max bounds
    bounds = TemperatureBounds(min_temperature=0.1, max_temperature=0.8)
    
    # Test clamping below minimum
    assert _clamp_temperature(0.05, bounds) == 0.1
    assert _clamp_temperature(-0.5, bounds) == 0.1
    
    # Test clamping above maximum
    assert _clamp_temperature(0.9, bounds) == 0.8
    assert _clamp_temperature(2.0, bounds) == 0.8
    
    # Test values within bounds (should be unchanged, just rounded)
    assert _clamp_temperature(0.5, bounds) == 0.5
    assert _clamp_temperature(0.555, bounds) == 0.56
    
    # Test exact boundary values
    assert _clamp_temperature(0.1, bounds) == 0.1
    assert _clamp_temperature(0.8, bounds) == 0.8


def test_clamp_temperature_partial_bounds_and_edge_cases():
    """Test temperature clamping with only min or max bounds and edge cases."""
    # Test with only minimum bound
    min_only_bounds = TemperatureBounds(min_temperature=0.2)
    assert _clamp_temperature(0.1, min_only_bounds) == 0.2
    assert _clamp_temperature(0.5, min_only_bounds) == 0.5
    assert _clamp_temperature(1.5, min_only_bounds) == 1.5
    
    # Test with only maximum bound  
    max_only_bounds = TemperatureBounds(max_temperature=0.7)
    assert _clamp_temperature(0.1, max_only_bounds) == 0.1
    assert _clamp_temperature(0.5, max_only_bounds) == 0.5
    assert _clamp_temperature(1.0, max_only_bounds) == 0.7

    # Test very precise rounding cases
    bounds = TemperatureBounds(min_temperature=0.0, max_temperature=1.0)
    assert _clamp_temperature(0.12345, bounds) == 0.12
    assert _clamp_temperature(0.996, bounds) == 1.0
    assert _clamp_temperature(0.999, bounds) == 1.0
    assert _clamp_temperature(0.9999999999999999, bounds) == 1.0
    assert _clamp_temperature(0.0000000000000001, bounds) == 0.0