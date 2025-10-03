"""Test data fixtures for app tests."""

from typing import Any, Dict

import pytest

from unique_toolkit.app.schemas import ChatEvent


@pytest.fixture
def base_chat_event_data() -> ChatEvent:
    """Base chat event that can be modified for specific tests."""
    event_data: Dict[str, Any] = {
        "id": "test-event",
        "event": "unique.chat.external-module.chosen",
        "userId": "test-user",
        "companyId": "test-company",
        "payload": {
            "name": "test_module",
            "description": "Test description",
            "configuration": {},
            "chatId": "test-chat",
            "assistantId": "test-assistant",
            "userMessage": {
                "id": "msg1",
                "text": "Hello",
                "createdAt": "2023-01-01T00:00:00Z",
                "originalText": "Hello",
                "language": "en",
            },
            "assistantMessage": {"id": "msg2", "createdAt": "2023-01-01T00:01:00Z"},
        },
        "createdAt": 1672531200,
        "version": "1.0",
    }
    return ChatEvent.model_validate(event_data)
