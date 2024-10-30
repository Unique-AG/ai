import json

import pytest
from pydantic import ValidationError

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
                        "role": "system",
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
        assert choice.message.role == LanguageModelMessageRole.SYSTEM
        assert choice.message.content == "content"

        # This is temporary this code would be deleted soon.
        with pytest.raises(AttributeError):
            assert choice.message.name == "name"

            assert choice.message.tool_calls is not None
            assert len(choice.message.tool_calls) == 1

            tool_call = choice.message.tool_calls[0]
            assert tool_call.id == "id"
            assert tool_call.type == "type"
            assert tool_call.function.name == "name"
            assert tool_call.function.arguments == {"key": "value"}


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
    print(assistant_message, "what are the assistant messages")

    # Ensure the tool_calls are copied and serialized properly
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
