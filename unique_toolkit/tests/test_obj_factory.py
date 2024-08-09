from unique_toolkit.app import (
    Event,
    EventAssistantMessage,
    EventName,
    EventPayload,
    EventUserMessage,
)


def get_event_obj(
    user_id: str,
    company_id: str,
    chat_id: str,
    assistant_id: str,
    user_message_id: str = "user_message_id",
):
    return Event(
        id="some-id",
        event=EventName.EXTERNAL_MODULE_CHOSEN,
        user_id=user_id,
        company_id=company_id,
        payload=EventPayload(
            assistant_id=assistant_id,
            chat_id=chat_id,
            name="module",
            description="module_description",
            configuration={},
            user_message=EventUserMessage(
                id=user_message_id,
                text="Test user message",
                created_at="2021-01-01T00:00:00Z",
                language="DE",
                original_text="Test user message",
            ),
            assistant_message=EventAssistantMessage(
                id="assistant_message_id", created_at="2021-01-01T00:00:00Z"
            ),
        ),
    )
