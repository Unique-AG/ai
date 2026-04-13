from __future__ import annotations

import pytest

from unique_mcp.internal_search.meta import InternalSearchRequestMeta


@pytest.mark.ai
def test_request_meta__allows_extra_fields():
    meta = InternalSearchRequestMeta.from_request_meta(
        {
            "unique.app/chat-id": "chat-1",
            "unique.app/content-ids": ["c1"],
            "custom.extra": "kept",
        }
    )

    assert meta.chat_id == "chat-1"
    assert meta.content_ids == ["c1"]
    assert meta.model_extra == {"custom.extra": "kept"}


@pytest.mark.ai
def test_to_chat_context__raises_when_chat_id_missing():
    meta = InternalSearchRequestMeta.from_request_meta({})

    with pytest.raises(ValueError, match="unique.app/chat-id"):
        _ = meta.to_chat_context()


@pytest.mark.ai
def test_to_chat_context__fills_mcp_placeholders_for_non_search_fields():
    meta = InternalSearchRequestMeta.from_request_meta({"unique.app/chat-id": "chat-1"})

    chat_context = meta.to_chat_context()

    assert chat_context.chat_id == "chat-1"
    assert chat_context.assistant_id == "mcp-internal-search"
    assert chat_context.last_assistant_message_id == "mcp-internal-search"
    assert chat_context.last_user_message_id == "mcp-internal-search"
    assert chat_context.last_user_message_text == "mcp-internal-search"


@pytest.mark.ai
def test_to_chat_context__preserves_explicit_values():
    meta = InternalSearchRequestMeta.from_request_meta(
        {
            "unique.app/chat-id": "chat-1",
            "unique.app/assistant-id": "assistant-1",
            "unique.app/last-assistant-message-id": "am-1",
            "unique.app/last-user-message-id": "um-1",
            "unique.app/last-user-message-text": "hello",
            "unique.app/parent-chat-id": "parent-1",
            "unique.app/metadata-filter": {"kind": "report"},
        }
    )

    chat_context = meta.to_chat_context()

    assert chat_context.chat_id == "chat-1"
    assert chat_context.assistant_id == "assistant-1"
    assert chat_context.last_assistant_message_id == "am-1"
    assert chat_context.last_user_message_id == "um-1"
    assert chat_context.last_user_message_text == "hello"
    assert chat_context.parent_chat_id == "parent-1"
    assert chat_context.metadata_filter == {"kind": "report"}
