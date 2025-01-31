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
    stream_complete,
    stream_complete_async,
)
from unique_toolkit.language_model.infos import LanguageModelName
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
    model_name = LanguageModelName.AZURE_GPT_4_TURBO_1106
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
        model_name=LanguageModelName.AZURE_GPT_4_TURBO_1106,
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
        model_name=LanguageModelName.AZURE_GPT_4_TURBO_1106,
    )

    assert result.choices[0].message.content == "Test response"
    mock_create.assert_called_once()


@patch.object(unique_sdk.Integrated, "chat_stream_completion")
def test_stream_complete_basic(mock_stream):
    mock_stream.return_value = {
        "message": {
            "id": "test_message",
            "previousMessageId": "test_previous_message",
            "role": "ASSISTANT",
            "text": "Streamed response",
            "originalText": "Streamed response original",
        }
    }

    messages = LanguageModelMessages([])
    result = stream_complete(
        company_id="test_company",
        user_id="test_user",
        assistant_message_id="test_assistant_msg",
        user_message_id="test_user_msg",
        chat_id="test_chat",
        assistant_id="test_assistant",
        messages=messages,
        model_name=LanguageModelName.AZURE_GPT_4_TURBO_1106,
    )

    assert result.message.text == "Streamed response"
    mock_stream.assert_called_once()


@pytest.mark.asyncio
@patch.object(unique_sdk.Integrated, "chat_stream_completion_async")
async def test_stream_complete_async_basic(mock_stream):
    mock_stream.return_value = {
        "message": {
            "id": "test_message",
            "previousMessageId": "test_previous_message",
            "role": "ASSISTANT",
            "text": "Streamed response",
            "originalText": "Streamed response original",
        }
    }

    messages = LanguageModelMessages([])
    result = await stream_complete_async(
        company_id="test_company",
        user_id="test_user",
        assistant_message_id="test_assistant_msg",
        user_message_id="test_user_msg",
        chat_id="test_chat",
        assistant_id="test_assistant",
        messages=messages,
        model_name=LanguageModelName.AZURE_GPT_4_TURBO_1106,
    )

    assert result.message.text == "Streamed response"
    mock_stream.assert_called_once()
