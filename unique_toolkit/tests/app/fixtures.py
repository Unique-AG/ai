"""Test data fixtures for app tests."""

from typing import Any, Dict

import pytest
from pydantic import SecretStr

from unique_toolkit.app.schemas import (
    ChatEvent,
)
from unique_toolkit.app.unique_settings import (
    UniqueApi,
    UniqueApp,
    UniqueAuth,
    UniqueSettings,
)


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


@pytest.fixture
def base_unique_settings() -> UniqueSettings:
    """Base UniqueSettings that can be modified for specific tests."""
    auth = UniqueAuth(
        company_id=SecretStr("test-company"), user_id=SecretStr("test-user")
    )
    app = UniqueApp(
        id=SecretStr("test-id"),
        key=SecretStr("test-key"),
        base_url="https://api.example.com",
        endpoint="/v1/endpoint",
        endpoint_secret=SecretStr("test-endpoint-secret"),
    )
    api = UniqueApi(
        base_url="https://api.example.com",
        version="2023-12-06",
    )
    return UniqueSettings(auth=auth, app=app, api=api)
