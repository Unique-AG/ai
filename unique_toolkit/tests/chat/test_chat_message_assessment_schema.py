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
    assert parsed.assessment[0].object == "message_assessment"
