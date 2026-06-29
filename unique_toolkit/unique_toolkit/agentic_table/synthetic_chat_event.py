"""Synthetic :class:`ChatEvent` for magic-table runs with chat-typed toolkit APIs."""

from unique_toolkit.agentic_table.schemas import MagicTableEvent
from unique_toolkit.app.schemas import (
    ChatEvent,
    ChatEventAssistantMessage,
    ChatEventPayload,
    ChatEventUserMessage,
    EventName,
)
from unique_toolkit.app.unique_settings import (
    MAGIC_TABLE_STREAMING_ASSISTANT_MESSAGE_ID,
    MAGIC_TABLE_STREAMING_USER_MESSAGE_ID,
)

_MAGIC_TABLE_STREAMING_MESSAGE_CREATED_AT = "1970-01-01T00:00:00Z"


def build_synthetic_chat_event(
    event: MagicTableEvent,
    *,
    event_id: str | None = None,
    description: str = "magic-table",
) -> ChatEvent:
    """Build a :class:`ChatEvent` for evaluators/tools that still require chat typing.

    Discouraged for new code: prefer :meth:`UniqueContext.from_magic_table_event`
    and ``Service.from_context(...)`` / :meth:`ToolManager.from_run_context`
    so callers do not depend on a fabricated chat envelope.

    Magic-table runs create messages dynamically; placeholder message ids are
    sufficient for search tooling and hallucination evaluation scoping.
    """
    payload = event.payload
    chat_id = payload.chat_id
    if not chat_id:
        msg = (
            "Magic-table event is missing chat_id; "
            "chat-scoped services cannot be built."
        )
        raise ValueError(msg)
    return ChatEvent(
        id=event_id or event.id,
        event=EventName.EXTERNAL_MODULE_CHOSEN,
        user_id=event.user_id,
        company_id=event.company_id,
        payload=ChatEventPayload(
            name=payload.name,
            chat_id=chat_id,
            assistant_id=payload.assistant_id,
            description=description,
            configuration=payload.configuration,
            metadata_filter=payload.metadata_filter,
            correlation=payload.correlation,
            user_message=ChatEventUserMessage(
                id=MAGIC_TABLE_STREAMING_USER_MESSAGE_ID,
                text="",
                original_text="",
                created_at=_MAGIC_TABLE_STREAMING_MESSAGE_CREATED_AT,
                language="EN",
            ),
            assistant_message=ChatEventAssistantMessage(
                id=MAGIC_TABLE_STREAMING_ASSISTANT_MESSAGE_ID,
                created_at=_MAGIC_TABLE_STREAMING_MESSAGE_CREATED_AT,
            ),
        ),
    )
