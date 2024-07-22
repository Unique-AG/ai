from unique_toolkit.language_model.schemas import (
    LanguageModelMessage,
    LanguageModelMessageList,
    LanguageModelMessageRole,
    LanguageModelSystemMessage,
    LanguageModelUserMessage,
)


def test_system_message_serialization():
    message = LanguageModelSystemMessage(content="blah")
    expected = """{"role":"system","content":"blah"}"""
    assert message.model_dump_json(exclude_none=True) == expected


def test_user_message_serialization():
    message = LanguageModelUserMessage(content="blah")
    expected = """{"role":"user","content":"blah"}"""
    assert message.model_dump_json(exclude_none=True) == expected


def test_message_list_serialization():

    messages = LanguageModelMessageList(
        [
            LanguageModelMessage(role=LanguageModelMessageRole.SYSTEM, content="blah"),
            LanguageModelSystemMessage(content="blah"),
            LanguageModelUserMessage(content="blah"),
        ]
    )
    expected = """[{"role":"system","content":"blah"},{"role":"system","content":"blah"},{"role":"user","content":"blah"}]"""
    assert messages.model_dump_json(exclude_none=True) == expected
