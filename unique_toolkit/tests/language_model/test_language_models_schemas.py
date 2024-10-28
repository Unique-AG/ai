import pytest
from pydantic import ValidationError

from unique_toolkit.language_model.schemas import (
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
        assert choice.message.name == "name"

        assert choice.message.tool_calls is not None
        assert len(choice.message.tool_calls) == 1

        tool_call = choice.message.tool_calls[0]
        assert tool_call.id == "id"
        assert tool_call.type == "type"
        assert tool_call.function.name == "name"
        assert tool_call.function.arguments == {"key": "value"}

    def test_language_model_tool_raises_validation_error_for_bad_name(self):
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

    def test_language_model_tool_name_pattern_raised_validation_error(self):
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
