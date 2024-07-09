def test_message_list_serialization():
    from unique_toolkit.chat import AIMessage, AIMessageList, AIMessageRole

    messages = AIMessageList([AIMessage(role=AIMessageRole.SYSTEM, content="blah")])

    assert messages.model_dump_json() == """[{"role":"system","content":"blah"}]"""
