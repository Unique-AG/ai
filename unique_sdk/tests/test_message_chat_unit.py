"""Unit tests for ``Message`` / ``Space`` chat shapes (public message & chat DTO parity)."""

from __future__ import annotations

import unique_sdk


def test_AI_message_create_accepts_user_role_and_optional_payload_keys():
    """Public create message allows USER or ASSISTANT and optional gpt/debug/completed."""
    params: unique_sdk.Message.CreateParams = {
        "chatId": "chat_1",
        "assistantId": "ast_1",
        "role": "USER",
        "text": "hello",
    }
    assert params["role"] == "USER"


def test_AI_message_reference_optional_fields():
    """Reference DTO marks description, url, originalIndex as optional."""
    minimal: unique_sdk.Message.Reference = {
        "name": "doc",
        "sequenceNumber": 0,
        "sourceId": "s1",
        "source": "search",
    }
    full: unique_sdk.Message.Reference = {
        "name": "doc",
        "sequenceNumber": 0,
        "sourceId": "s1",
        "source": "search",
        "description": None,
        "url": None,
        "originalIndex": [0, 1],
    }
    assert "description" not in minimal
    assert full["originalIndex"] == [0, 1]


def test_AI_space_chat_result_allows_object_tag():
    """Create-chat responses may include an object discriminator."""
    chat: unique_sdk.Space.ChatResult = {
        "id": "chat_1",
        "title": "t",
        "createdAt": "2025-01-01T00:00:00.000Z",
        "object": "chat",
    }
    assert chat["object"] == "chat"


def test_AI_space_message_includes_user_aborted_at():
    """Message payloads may include userAbortedAt (public message DTO)."""
    row: unique_sdk.Space.Message = {
        "id": "msg_1",
        "chatId": "chat_1",
        "text": None,
        "originalText": None,
        "role": "ASSISTANT",
        "debugInfo": None,
        "gptRequest": None,
        "completedAt": None,
        "createdAt": None,
        "updatedAt": None,
        "startedStreamingAt": None,
        "stoppedStreamingAt": None,
        "userAbortedAt": None,
        "references": None,
        "assessment": None,
    }
    assert row["userAbortedAt"] is None
