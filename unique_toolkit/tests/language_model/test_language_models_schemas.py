from unique_toolkit.language_model.schemas import (
    LanguageModelMessage,
    LanguageModelMessageRole,
    LanguageModelMessages,
    LanguageModelResponse,
    LanguageModelSystemMessage,
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
