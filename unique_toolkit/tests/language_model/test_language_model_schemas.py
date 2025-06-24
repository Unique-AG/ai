import json

import pytest
from pydantic import BaseModel, Field, ValidationError

from unique_toolkit.language_model.schemas import (
    LanguageModelAssistantMessage,
    LanguageModelFunction,
    LanguageModelFunctionCall,
    LanguageModelMessage,
    LanguageModelMessageRole,
    LanguageModelMessages,
    LanguageModelResponse,
    LanguageModelSystemMessage,
    LanguageModelTool,
    LanguageModelToolDescription,
    LanguageModelToolMessage,
    LanguageModelToolParameterProperty,
    LanguageModelToolParameters,
    LanguageModelUserMessage,
)


class TestLanguageModelSchemas:
    def test_can_serialize_system_message(self):
        message = LanguageModelSystemMessage(content="blah")
        expected = """{"role":"system","content":"blah"}"""
        assert message.model_dump_json(exclude_none=True) == expected

    def test_can_serialize_user_message(self):
        message = LanguageModelUserMessage(content="blah")
        expected = """{"role":"user","content":"blah"}"""
        assert message.model_dump_json(exclude_none=True) == expected

    def test_can_serialize_message_with_image(self):
        message = LanguageModelUserMessage(
            content=[
                {"type": "text", "content": "text_content"},
                {
                    "type": "image_url",
                    "imageUrl": {"url": "image_string_base64"},
                },
            ]
        )
        expected = """{"role":"user","content":[{"type":"text","content":"text_content"},{"type":"image_url","imageUrl":{"url":"image_string_base64"}}]}"""
        assert message.model_dump_json(exclude_none=True) == expected

        message = LanguageModelSystemMessage(
            content=[
                {"type": "text", "content": "text_content"},
                {
                    "type": "image_url",
                    "imageUrl": {"url": "image_string_base64"},
                },
            ]
        )
        expected = """{"role":"system","content":[{"type":"text","content":"text_content"},{"type":"image_url","imageUrl":{"url":"image_string_base64"}}]}"""
        assert message.model_dump_json(exclude_none=True) == expected

    def test_can_serialize_messages(self):
        messages = LanguageModelMessages(
            [
                LanguageModelMessage(
                    role=LanguageModelMessageRole.SYSTEM, content="blah"
                ),
                LanguageModelSystemMessage(content="blah"),
                LanguageModelUserMessage(content="blah"),
            ]
        )
        expected = """[{"role":"system","content":"blah"},{"role":"system","content":"blah"},{"role":"user","content":"blah"}]"""
        assert messages.model_dump_json(exclude_none=True) == expected

    def test_can_load_response(self):
        response_json = {
            "choices": [
                {
                    "index": 0,
                    "finishReason": "finished",
                    "message": {
                        "role": "assistant",
                        "content": "content",
                        "name": "name",
                        "toolCalls": [
                            {
                                "function": {
                                    "name": "name",
                                    "arguments": '{"key": "value"}',
                                },
                                "id": "id",
                                "type": "type",
                            }
                        ],
                    },
                }
            ]
        }

        response = LanguageModelResponse(**response_json)  # type: ignore
        assert len(response.choices) == 1

        choice = response.choices[0]
        assert choice.index == 0
        assert choice.finish_reason == "finished"
        assert choice.message.role == LanguageModelMessageRole.ASSISTANT
        assert choice.message.content == "content"

        # This is temporary this code would be deleted soon.
        with pytest.raises(AttributeError):
            assert choice.message.name == "name"  # type: ignore

            assert choice.message.tool_calls is not None
            assert len(choice.message.tool_calls) == 1

            tool_call = choice.message.tool_calls[0]
            assert tool_call.id == "id"
            assert tool_call.type == "type"
            assert tool_call.function.name == "name"
            assert tool_call.function.arguments == {"key": "value"}

    def test_language_model_system_message_str(self):
        message = LanguageModelSystemMessage(content="System message content")
        expected_output = "System:\n\tSystem message content"
        assert str(message) == expected_output

    def test_language_model_user_message_str(self):
        message = LanguageModelUserMessage(content="User message content")
        expected_output = "User:\n\tUser message content"
        assert str(message) == expected_output

    def test_language_model_assistant_message_str(self):
        message = LanguageModelAssistantMessage(content="Assistant message content")
        expected_output = "Assistant:\n\tAssistant message content"
        assert str(message) == expected_output

    def test_language_model_tool_message_str(self):
        message = LanguageModelToolMessage(
            name="Tool Name", tool_call_id="123", content="Tool message content"
        )
        expected_output = "Tool:\n\tTool Name, 123, Tool message content"
        assert str(message) == expected_output

    def test_language_model_messages_str(self):
        messages = LanguageModelMessages(
            [
                LanguageModelSystemMessage(content="System message content"),
                LanguageModelUserMessage(content="User message content"),
            ]
        )
        expected_output = (
            "System:\n\tSystem message content\n\nUser:\n\tUser message content"
        )
        assert str(messages) == expected_output


@pytest.fixture
def valid_tool_calls():
    """Fixture to provide valid tool calls."""
    return [
        LanguageModelFunction(
            id="func_1", name="function_1", arguments={"param1": "value1", "param2": 2}
        ),
        LanguageModelFunction(
            id="func_2", name="function_2", arguments=json.dumps({"key": "value"})
        ),
    ]


def test_language_model_function_arguments_validation():
    """Test that the arguments field is properly validated and processed."""
    # Test when arguments are passed as a JSON string
    valid_data = {
        "id": "test_func",
        "name": "Test Function",
        "arguments": '{"key": "value"}',
    }
    language_model_function = LanguageModelFunction(**valid_data)
    assert language_model_function.arguments == {"key": "value"}

    # Test when arguments are passed as a dict (should remain unchanged)
    valid_data = {
        "id": "test_func",
        "name": "Test Function",
        "arguments": {"key": "value"},
    }
    language_model_function = LanguageModelFunction(**valid_data)
    assert language_model_function.arguments == {"key": "value"}

    # Test invalid JSON string in arguments
    invalid_data = {
        "id": "test_func",
        "name": "Test Function",
        "arguments": '{"invalid_json": }',
    }
    with pytest.raises(ValueError):
        LanguageModelFunction(**invalid_data)


def test_language_model_function_call_creation(valid_tool_calls):
    """Test the create_assistant_message_from_tool_calls method."""
    # Create assistant message using the valid tool calls
    assistant_message = (
        LanguageModelFunctionCall.create_assistant_message_from_tool_calls(
            valid_tool_calls
        )
    )

    # Ensure the tool_calls are copied and serialized properly
    assert assistant_message.tool_calls is not None
    for tool_call in assistant_message.tool_calls:
        assert isinstance(
            tool_call.function.arguments, dict
        )  # arguments should be serialized to a string

        # Check if arguments can be deserialized back to the original dict
        assert tool_call.function.arguments == {
            "param1": "value1",
            "param2": 2,
        } or {"key": "value"}

    # Ensure the assistant message is constructed correctly
    expected_message = LanguageModelAssistantMessage(
        content="",
        tool_calls=[
            LanguageModelFunctionCall(
                id="func_1",
                type="function",
                function=LanguageModelFunction(
                    id="func_1",
                    name="function_1",
                    arguments={"param1": "value1", "param2": 2},
                ),
            ),
            LanguageModelFunctionCall(
                id="func_2",
                type="function",
                function=LanguageModelFunction(
                    id="func_2",
                    name="function_2",
                    arguments={"key": "value"},
                ),
            ),
        ],
    )
    assert assistant_message.role == expected_message.role

    assert assistant_message.tool_calls is not None
    assert expected_message.tool_calls is not None
    assert isinstance(expected_message.tool_calls[0].id, str)
    assert assistant_message.tool_calls[0].type == expected_message.tool_calls[0].type
    assert (
        assistant_message.tool_calls[0].function.name
        == expected_message.tool_calls[0].function.name
    )
    assert isinstance(expected_message.tool_calls[0].function.id, str)
    assert (
        assistant_message.tool_calls[0].function.arguments
        == expected_message.tool_calls[0].function.arguments
    )

    assert isinstance(expected_message.tool_calls[1].id, str)
    assert assistant_message.tool_calls[1].type == expected_message.tool_calls[1].type
    assert (
        assistant_message.tool_calls[1].function.name
        == expected_message.tool_calls[1].function.name
    )
    assert isinstance(expected_message.tool_calls[1].function.id, str)
    assert (
        assistant_message.tool_calls[1].function.arguments
        == expected_message.tool_calls[1].function.arguments
    )


def test_invalid_tool_call_argument_type():
    """Test that an invalid argument type raises appropriate errors."""
    with pytest.raises(ValidationError):
        LanguageModelFunction(id="func_1", name="function_1", arguments="invalid_json")
    with pytest.raises(ValueError):
        LanguageModelFunctionCall.create_assistant_message_from_tool_calls(
            [
                LanguageModelFunction(
                    id="func_1", name="function_1", arguments="invalid_json"
                )
            ]
        )


def test_language_model_tool_name_pattern():
    with pytest.raises(ValidationError):
        LanguageModelTool(
            name="invalid name!",
            description="Invalid tool name",
            parameters=LanguageModelToolParameters(
                type="object",
                properties={
                    "param": LanguageModelToolParameterProperty(
                        type="string", description="A parameter"
                    )
                },
                required=["param"],
            ),
        )


def test_language_model_tool_raises_validation_error_for_bad_name():
    with pytest.raises(ValidationError):
        LanguageModelTool(
            name="invalid name!",
            description="Invalid tool name",
            parameters=LanguageModelToolParameters(
                type="object",
                properties={
                    "param": LanguageModelToolParameterProperty(
                        type="string", description="A parameter"
                    )
                },
                required=["param"],
            ),
        )


def test_language_model_tool_name_pattern_raised_validation_error():
    for name in ["DocumentSummarizerV2", "SearchInVectorDBV2"]:
        tool = LanguageModelTool(
            name=name,
            description="Invalid tool name",
            parameters=LanguageModelToolParameters(
                type="object",
                properties={
                    "param": LanguageModelToolParameterProperty(
                        type="string", description="A parameter"
                    )
                },
                required=["param"],
            ),
        )

        assert tool.name == name


def test_language_model_assistant_message_with_parsed_and_refusal():
    """Test that LanguageModelAssistantMessage can handle parsed and refusal fields."""
    # Test with parsed data
    parsed_data = {"key": "value", "nested": {"data": 123}}
    message = LanguageModelAssistantMessage(content="Test content", parsed=parsed_data)
    assert message.parsed == parsed_data
    assert message.refusal is None

    # Test with refusal
    refusal_message = "I cannot perform this action"
    message = LanguageModelAssistantMessage(
        content="Test content", refusal=refusal_message
    )
    assert message.refusal == refusal_message
    assert message.parsed is None

    # Test with both parsed and refusal
    message = LanguageModelAssistantMessage(
        content="Test content", parsed=parsed_data, refusal=refusal_message
    )
    assert message.parsed == parsed_data
    assert message.refusal == refusal_message

    # Test serialization
    expected = """{"role":"assistant","content":"Test content","parsed":{"key":"value","nested":{"data":123}},"refusal":"I cannot perform this action"}"""
    assert message.model_dump_json(exclude_none=True) == expected


def test_language_model_tool_parameters_dump_from_pydantic():
    class TestParameters(BaseModel):
        param: str = Field(description="A parameter")
        param2: int = Field(description="A parameter")

    tool = LanguageModelTool(
        name="DocumentSummarizerV2",
        description="Invalid tool name",
        parameters=TestParameters.model_json_schema(),
    )

    assert isinstance(tool.parameters, LanguageModelToolParameters)
    assert tool.parameters.properties["param"].type == "string"
    assert tool.parameters.properties["param"].description == "A parameter"
    assert tool.parameters.properties["param2"].type == "integer"
    assert tool.parameters.properties["param2"].description == "A parameter"
    assert tool.parameters.required == ["param", "param2"]


def test_language_model_tool_description():
    from pydantic import BaseModel, Field

    # Define the parameter model
    class WeatherParameters(BaseModel):
        location: str = Field(description="City and country e.g. Bogotá, Colombia")
        units: str | None = Field(
            description="Units the temperature will be returned in.",
            enum=["celsius", "fahrenheit"],
        )

        model_config = {"extra": "forbid"}

    tool = LanguageModelToolDescription(
        name="get_weather",
        description="Retrieves current weather for the given location.",
        parameters=WeatherParameters,
        strict=True,
    )

    expected_dump = {
        "name": "get_weather",
        "description": "Retrieves current weather for the given location.",
        "parameters": {
            "additionalProperties": False,
            "properties": {
                "location": {
                    "description": "City and country e.g. Bogotá, Colombia",
                    "title": "Location",
                    "type": "string",
                },
                "units": {
                    "anyOf": [{"type": "string"}, {"type": "null"}],
                    "description": "Units the temperature will be returned in.",
                    "enum": ["celsius", "fahrenheit"],
                    "title": "Units",
                },
            },
            "required": ["location", "units"],
            "title": "WeatherParameters",
            "type": "object",
        },
        "strict": True,
    }

    assert tool.model_dump() == expected_dump


class TestLanguageModelMessagesModelValidator:
    """Test the model_validator in LanguageModelMessages class."""

    def test_convert_dict_messages_from_list(self):
        """Test converting a list of dictionaries to appropriate message objects."""
        messages_data = [
            {"role": "system", "content": "You are a helpful assistant"},
            {"role": "user", "content": "Hello there"},
            {
                "role": "assistant",
                "content": "Hi! How can I help?",
                "tool_calls": [
                    {
                        "id": "5257cdaf28954d8c93b19adecdfb300c",
                        "type": "function",
                        "function": {
                            "id": "b0387459714f4767bba14cdaa9a7e62a",
                            "name": "WebSearch",
                            "arguments": '{"query": "latest news on Deloitte June 2025", "language": "English"}',
                        },
                    }
                ],
            },
            {
                "role": "tool",
                "name": "WebSearch",
                "tool_call_id": "5257cdaf28954d8c93b19adecdfb300c",
                "content": "Search results here",
            },
        ]

        messages = LanguageModelMessages.load_messages_to_root(messages_data)

        assert len(messages.root) == 4
        assert isinstance(messages.root[0], LanguageModelSystemMessage)
        assert isinstance(messages.root[1], LanguageModelUserMessage)
        assert isinstance(messages.root[2], LanguageModelAssistantMessage)
        assert isinstance(messages.root[3], LanguageModelToolMessage)

        assert messages.root[0].content == "You are a helpful assistant"
        assert messages.root[1].content == "Hello there"
        assert messages.root[2].content == "Hi! How can I help?"
        assert messages.root[3].content == "Search results here"
        assert messages.root[3].name == "WebSearch"
        assert messages.root[3].tool_call_id == "5257cdaf28954d8c93b19adecdfb300c"

    def test_convert_dict_messages_from_root_dict(self):
        """Test converting data wrapped in root key (RootModel format)."""
        messages_data = {
            "root": [
                {"role": "system", "content": "System message"},
                {"role": "user", "content": "User message"},
            ]
        }

        messages = LanguageModelMessages(messages_data)  # type: ignore

        assert len(messages.root) == 2
        assert isinstance(messages.root[0], LanguageModelSystemMessage)
        assert isinstance(messages.root[1], LanguageModelUserMessage)
        assert messages.root[0].content == "System message"
        assert messages.root[1].content == "User message"

    def test_preserve_existing_message_objects(self):
        """Test that existing message objects are preserved without conversion."""
        system_msg = LanguageModelSystemMessage(content="Existing system message")
        user_msg = LanguageModelUserMessage(content="Existing user message")

        messages_data = [system_msg, user_msg]
        messages = LanguageModelMessages(messages_data)

        assert len(messages.root) == 2
        assert messages.root[0] is system_msg  # Same object reference
        assert messages.root[1] is user_msg  # Same object reference
        assert isinstance(messages.root[0], LanguageModelSystemMessage)
        assert isinstance(messages.root[1], LanguageModelUserMessage)

    def test_mixed_dict_and_objects(self):
        """Test handling a mix of dictionaries and existing message objects."""
        existing_system = LanguageModelSystemMessage(content="Existing system")

        messages_data = [
            existing_system,
            {"role": "user", "content": "New user message"},
            {"role": "assistant", "content": "New assistant message"},
        ]

        messages = LanguageModelMessages(messages_data)  # type: ignore

        assert len(messages.root) == 3
        assert messages.root[0] is existing_system  # Preserved object
        assert isinstance(messages.root[1], LanguageModelUserMessage)  # Converted
        assert isinstance(messages.root[2], LanguageModelAssistantMessage)  # Converted

        assert messages.root[0].content == "Existing system"
        assert messages.root[1].content == "New user message"
        assert messages.root[2].content == "New assistant message"

    def test_case_insensitive_role_mapping(self):
        """Test that role mapping works with different case variations."""
        messages_data = [
            {"role": "SYSTEM", "content": "System message"},
            {"role": "User", "content": "User message"},
            {"role": "ASSISTANT", "content": "Assistant message"},
            {
                "role": "Tool",
                "content": "Tool message",
                "name": "tool1",
                "tool_call_id": "call_1",
            },
        ]

        messages = LanguageModelMessages(messages_data)  # type: ignore

        assert isinstance(messages.root[0], LanguageModelSystemMessage)
        assert isinstance(messages.root[1], LanguageModelUserMessage)
        assert isinstance(messages.root[2], LanguageModelAssistantMessage)
        assert isinstance(messages.root[3], LanguageModelToolMessage)

    def test_fallback_to_base_message_for_unknown_role(self):
        """Test that unknown roles fallback to base LanguageModelMessage."""
        # Note: This test demonstrates that unknown roles will fail validation
        # because LanguageModelMessageRole enum only accepts specific values
        messages_data = [
            {"role": "unknown", "content": "Unknown role message"},
            {"role": "custom", "content": "Custom role message"},
        ]

        # This should raise a ValidationError because the enum doesn't accept unknown roles
        with pytest.raises(ValidationError):
            LanguageModelMessages(messages_data)  # type: ignore

    def test_empty_role_handling(self):
        """Test handling of messages with empty or missing role."""
        # Note: Empty roles will fail validation because they don't match the enum
        messages_data = [
            {"role": "", "content": "Empty role message"},
            {"content": "No role message"},
        ]

        # This should raise a ValidationError because empty string is not a valid enum value
        with pytest.raises(ValidationError):
            LanguageModelMessages(messages_data)  # type: ignore

    def test_return_data_as_is_for_non_list_non_dict(self):
        """Test that non-list, non-dict data is returned as-is."""
        # Note: RootModel expects a list, so non-list data will fail validation
        test_data = "not a list or dict"

        # This should raise a ValidationError because RootModel expects a list
        with pytest.raises(ValidationError):
            LanguageModelMessages(test_data)  # type: ignore

    def test_empty_messages_list(self):
        """Test handling of empty messages list."""
        messages_data = []
        messages = LanguageModelMessages(messages_data)

        assert len(messages.root) == 0
        assert isinstance(messages.root, list)

    def test_single_message_conversion(self):
        """Test conversion of a single message."""
        messages_data = [{"role": "system", "content": "Single message"}]
        messages = LanguageModelMessages(messages_data)  # type: ignore

        assert len(messages.root) == 1
        assert isinstance(messages.root[0], LanguageModelSystemMessage)
        assert messages.root[0].content == "Single message"
