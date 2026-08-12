"""Tests for the ChatMessageAssessment schema in unique_toolkit.chat.schemas.

Regression test for UN-24145: the backend never populates ``object`` on an
assessment nested inside a chat message (the shape returned by
``get_full_history_async()`` / ``GET /messages``) — only a separate,
standalone ``/message-assessment`` endpoint synthesizes it via a server-side
``@Transform`` decorator. Since ``object`` was previously required with no
default, ``ChatMessage.model_validate(msg)`` in
``unique_toolkit.chat.functions`` (used by ``get_full_history_async`` /
``get_full_history``) raised a pydantic ``ValidationError`` for any chat
with an assessed message.
"""

from unique_toolkit.chat.schemas import ChatMessage


def test_chat_message_validates_assessment_without_object():
    raw_message = {
        "id": "message1",
        "chatId": "chat1",
        "text": "Some content",
        "role": "assistant",
        "assessment": [
            {
                "id": "assessment1",
                "messageId": "message1",
                "status": "DONE",
                "type": "HALLUCINATION",
                "isVisible": True,
            }
        ],
    }

    parsed = ChatMessage.model_validate(raw_message)

    assert parsed.assessment is not None
    assert parsed.assessment[0].object == "message-assessment"


def test_chat_message_accepts_unexpected_assessment_object_value():
    """``object`` is a cosmetic discriminator no caller branches on, so an
    unexpected value must not abort history parsing — the field is typed
    ``str`` rather than ``Literal`` precisely to avoid re-introducing the
    UN-24145 failure mode for a value nothing reads.
    """
    raw_message = {
        "id": "message1",
        "chatId": "chat1",
        "text": "Some content",
        "role": "assistant",
        "assessment": [
            {
                "id": "assessment1",
                "object": "some_unexpected_value",
                "messageId": "message1",
                "status": "DONE",
                "type": "HALLUCINATION",
                "isVisible": True,
            }
        ],
    }

    parsed = ChatMessage.model_validate(raw_message)

    assert parsed.assessment is not None
    assert parsed.assessment[0].object == "some_unexpected_value"
