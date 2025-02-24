import json
from unittest.mock import patch

import pytest
import unique_sdk
from pydantic import BaseModel

from tests.test_obj_factory import get_event_obj
from unique_toolkit.language_model.functions import (
    _add_response_format_to_options,
    _prepare_completion_params_util,
)
from unique_toolkit.language_model.infos import LanguageModelName
from unique_toolkit.language_model.schemas import (
    LanguageModelMessage,
    LanguageModelMessageRole,
    LanguageModelMessages,
    LanguageModelResponse,
    LanguageModelTool,
    LanguageModelToolParameterProperty,
    LanguageModelToolParameters,
)
from unique_toolkit.language_model.service import LanguageModelService

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


class PydanticModel(BaseModel):
    name: str
    age: int


class TestLanguageModelServiceUnit:
    @pytest.fixture(autouse=True)
    def setup(self):
        self.event = get_event_obj(
            user_id="test_user",
            company_id="test_company",
            assistant_id="test_assistant",
            chat_id="test_chat",
        )
        self.service = LanguageModelService(self.event)

    @patch.object(unique_sdk.ChatCompletion, "create")
    def test_complete(self, mock_create):
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
        model_name = LanguageModelName.AZURE_GPT_4_TURBO_1106

        result = self.service.complete(messages, model_name)

        assert isinstance(result, LanguageModelResponse)
        assert result.choices[0].message.content == "Test response"
        mock_create.assert_called_once_with(
            company_id="test_company",
            model=model_name.name,
            messages=[],
            timeout=240000,
            options={
                "temperature": 0.0,
            },
        )

    @patch.object(unique_sdk.ChatCompletion, "create")
    def test_complete_with_custom_model(self, mock_create):
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
        model_name = "My Custom Model"

        result = self.service.complete(messages, model_name)

        assert isinstance(result, LanguageModelResponse)
        assert result.choices[0].message.content == "Test response"
        mock_create.assert_called_once_with(
            company_id="test_company",
            model=model_name,
            messages=[],
            timeout=240000,
            options={
                "temperature": 0.0,
            },
        )

    @patch.object(unique_sdk.ChatCompletion, "create")
    def test_complete_with_tool(self, mock_create):
        messages = LanguageModelMessages(
            [
                LanguageModelMessage(
                    role=LanguageModelMessageRole.USER,
                    content="What's the weather in New York?",
                )
            ]
        )

        mock_create.return_value = {
            "choices": [
                {
                    "index": 0,
                    "message": {
                        "role": "assistant",
                        "content": "The weather in New York is 70 degrees Fahrenheit.",
                        "toolCalls": [
                            {
                                "id": "test_tool_id",
                                "type": "function",
                                "function": {
                                    "id": "test_function_id",
                                    "name": "get_weather",
                                    "arguments": '{"location": "New York, NY","unit": "fahrenheit"}',
                                },
                            },
                        ],
                    },
                    "finishReason": "function_call",
                }
            ],
        }

        response = self.service.complete(
            messages=messages,
            model_name=LanguageModelName.AZURE_GPT_35_TURBO_0125,
            tools=[mock_tool],
        )

        assert response.choices[0].message.tool_calls is not None
        assert response.choices[0].message.tool_calls[0].function.name == "get_weather"
        arguments = response.choices[0].message.tool_calls[0].function.arguments
        assert arguments is not None
        if isinstance(arguments, str):
            arguments = json.loads(arguments)
        assert "New York, NY" in arguments.values()

    @pytest.mark.asyncio
    @patch.object(unique_sdk.ChatCompletion, "create_async")
    async def test_complete_async(self, mock_create):
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
        model_name = LanguageModelName.AZURE_GPT_4_TURBO_1106

        result = await self.service.complete_async(messages, model_name)

        assert isinstance(result, LanguageModelResponse)
        assert result.choices[0].message.content == "Test response"
        mock_create.assert_called_once_with(
            company_id="test_company",
            model=model_name.name,
            messages=[],
            timeout=240000,
            options={
                "temperature": 0.0,
            },
        )

    @pytest.mark.asyncio
    @patch.object(unique_sdk.ChatCompletion, "create_async")
    async def test_complete_async_with_custom_model(self, mock_create):
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
        model_name = "My custom model"

        result = await self.service.complete_async(messages, model_name)

        assert isinstance(result, LanguageModelResponse)
        assert result.choices[0].message.content == "Test response"
        mock_create.assert_called_once_with(
            company_id="test_company",
            model=model_name,
            messages=[],
            timeout=240000,
            options={
                "temperature": 0.0,
            },
        )

    @pytest.mark.asyncio
    @patch.object(unique_sdk.ChatCompletion, "create_async")
    async def test_error_handling_complete_async(self, mock_create):
        mock_create.side_effect = Exception("API Error")
        with pytest.raises(Exception, match="API Error"):
            await self.service.complete_async(
                LanguageModelMessages([]), LanguageModelName.AZURE_GPT_4_TURBO_1106
            )

    @pytest.mark.asyncio
    @patch.object(unique_sdk.ChatCompletion, "create_async")
    async def test_complete_with_tool_async(self, mock_create):
        messages = LanguageModelMessages(
            [
                LanguageModelMessage(
                    role=LanguageModelMessageRole.USER,
                    content="What's the weather in New York?",
                )
            ]
        )

        mock_create.return_value = {
            "choices": [
                {
                    "index": 0,
                    "message": {
                        "role": "assistant",
                        "content": "The weather in New York is 70 degrees Fahrenheit.",
                        "toolCalls": [
                            {
                                "id": "test_tool_id",
                                "type": "function",
                                "function": {
                                    "id": "test_function_id",
                                    "name": "get_weather",
                                    "arguments": '{"location": "New York, NY","unit": "fahrenheit"}',
                                },
                            },
                        ],
                    },
                    "finishReason": "function_call",
                }
            ],
        }

        response = await self.service.complete_async(
            messages=messages,
            model_name=LanguageModelName.AZURE_GPT_35_TURBO_0125,
            tools=[mock_tool],
        )
        assert response.choices[0].message.tool_calls is not None
        assert response.choices[0].message.tool_calls[0].function.name == "get_weather"
        arguments = response.choices[0].message.tool_calls[0].function.arguments
        assert arguments is not None
        if isinstance(arguments, str):
            arguments = json.loads(arguments)
        assert "New York, NY" in arguments.values()

    def testprepare_completion_params_util_basic(self):
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

    def testprepare_completion_params_util_with_tools_and_other_options(self):
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

    @patch.object(unique_sdk.ChatCompletion, "create")
    def test_complete_with_other_options(self, mock_create):
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
        model_name = LanguageModelName.AZURE_GPT_4_TURBO_1106
        other_options = {"max_tokens": 100, "top_p": 0.9}

        result = self.service.complete(
            messages, model_name, other_options=other_options
        )

        assert isinstance(result, LanguageModelResponse)
        assert result.choices[0].message.content == "Test response"
        mock_create.assert_called_once_with(
            company_id="test_company",
            model=model_name.name,
            messages=[],
            timeout=240000,
            options={
                "temperature": 0.0,
                "max_tokens": 100,
                "top_p": 0.9,
            },
        )

    @pytest.mark.asyncio
    @patch.object(unique_sdk.ChatCompletion, "create_async")
    async def test_complete_async_with_other_options(self, mock_create):
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
        model_name = LanguageModelName.AZURE_GPT_4_TURBO_1106
        other_options = {"best_of": 2, "stop": ["\n"]}

        result = await self.service.complete_async(
            messages, model_name, other_options=other_options
        )

        assert isinstance(result, LanguageModelResponse)
        assert result.choices[0].message.content == "Test response"
        mock_create.assert_called_once_with(
            company_id="test_company",
            model=model_name.name,
            messages=[],
            timeout=240000,
            options={
                "temperature": 0.0,
                "best_of": 2,
                "stop": ["\n"],
            },
        )

    def test_add_output_schema_from_pydantic_enforce_schema(self):
        options = {}
        options = _add_response_format_to_options(
            options, PydanticModel, structured_output_enforce_schema=True
        )
        assert options["responseFormat"] == {
            "type": "json_schema",
            "json_schema": {
                "name": "PydanticModel",
                "strict": True,
                "schema": PydanticModel.model_json_schema(),
            },
        }

    def test_add_output_schema_from_pydantic_no_enforce_schema(self):
        options = {}
        options = _add_response_format_to_options(
            options, PydanticModel, structured_output_enforce_schema=False
        )
        assert options["responseFormat"] == {
            "type": "json_schema",
            "json_schema": {
                "name": "PydanticModel",
                "strict": False,
                "schema": PydanticModel.model_json_schema(),
            },
        }
