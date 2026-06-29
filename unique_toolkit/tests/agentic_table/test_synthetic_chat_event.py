"""Tests for build_synthetic_chat_event."""

import pytest

from unique_toolkit.agentic_table.schemas import (
    DDMetadata,
    MagicTableAction,
    MagicTableEvent,
    MagicTableEventTypes,
    MagicTableUpdateCellPayload,
)
from unique_toolkit.agentic_table.synthetic_chat_event import (
    build_synthetic_chat_event,
)
from unique_toolkit.app.schemas import EventName


def _make_event(*, chat_id: str) -> MagicTableEvent:
    return MagicTableEvent(
        id="evt-1",
        event=MagicTableEventTypes.UPDATE_CELL,
        user_id="user-1",
        company_id="company-1",
        payload=MagicTableUpdateCellPayload(
            name="rfp-agent",
            sheet_name="sheet-1",
            action=MagicTableAction.UPDATE_CELL,
            chat_id=chat_id,
            assistant_id="assistant-1",
            table_id="table-1",
            column_order=0,
            row_order=0,
            data="cell",
            metadata=DDMetadata(),
        ),
    )


def test_build_synthetic_chat_event__uses_placeholder_message_ids() -> None:
    synthetic = build_synthetic_chat_event(_make_event(chat_id="chat-1"))
    assert synthetic.event == EventName.EXTERNAL_MODULE_CHOSEN
    assert synthetic.payload.chat_id == "chat-1"
    assert synthetic.payload.user_message.id == "magic-table-streaming-user"
    assert synthetic.payload.assistant_message.id == "magic-table-streaming-assistant"


def test_build_synthetic_chat_event__requires_chat_id() -> None:
    with pytest.raises(ValueError, match="missing chat_id"):
        build_synthetic_chat_event(_make_event(chat_id=""))
