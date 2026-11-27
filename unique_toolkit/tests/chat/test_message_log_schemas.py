"""Tests for the MessageLog/MessageLogEvent schemas in unique_toolkit.chat.schemas.

Covers the "Todo" event type regression (UN-23253): the backend's ``details``
column is untyped JSON, so a write with an unsupported ``type`` value succeeds
server-side but previously failed when re-parsing the response into
``MessageLog`` (see ``create_message_log_async`` / ``update_message_log_async``
in ``unique_toolkit.chat.functions``, both of which do
``return MessageLog(**message_log)`` right after the write).
"""

from unique_toolkit.chat.schemas import (
    MessageLog,
    MessageLogDetails,
    MessageLogEvent,
)


def test_message_log_event_accepts_todo_type_with_status():
    event = MessageLogEvent(type="Todo", text="Set up project", status="done")

    assert event.type == "Todo"
    assert event.status == "done"


def test_message_log_event_status_defaults_to_none():
    event = MessageLogEvent(type="ToolCall", text="Calling a tool")

    assert event.status is None


def test_message_log_round_trips_todo_event_like_functions_return_path():
    """Regression test for UN-23253.

    Mirrors the exact pattern used by ``create_message_log_async`` /
    ``update_message_log_async``: build a ``MessageLogEvent``/``MessageLogDetails``,
    dump it (as if sending it over the wire), then re-parse the raw response
    dict via ``MessageLog(**message_log)``. Before the fix, this raised a
    pydantic ``ValidationError`` because ``"Todo"`` wasn't a valid ``type``.
    """
    event = MessageLogEvent(type="Todo", text="Set up project", status="done")
    details = MessageLogDetails(data=[event])

    raw = {
        "id": "row-1",
        "status": "RUNNING",
        "order": 1,
        "details": details.model_dump(),
    }

    parsed = MessageLog(**raw)

    assert parsed.message_log_id == "row-1"
    assert parsed.details is not None
    assert parsed.details.data is not None
    assert parsed.details.data[0].type == "Todo"
    assert parsed.details.data[0].status == "done"
