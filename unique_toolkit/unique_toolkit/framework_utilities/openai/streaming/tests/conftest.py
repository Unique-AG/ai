"""Shared fixtures for the streaming pipeline tests."""

from __future__ import annotations

import pytest
from pydantic import SecretStr

from unique_toolkit.app.unique_settings import (
    AuthContext,
    ChatContext,
    UniqueApi,
    UniqueApp,
    UniqueSettings,
)


@pytest.fixture
def test_app() -> UniqueApp:
    """
    UniqueApp with deterministic test credentials.
    Uses alias names because UniqueApp fields carry validation_alias.
    """
    return UniqueApp(
        id=SecretStr("test-app-id"),
        key=SecretStr("sk-test-api-key"),
        base_url="http://localhost:8092/",
        endpoint="/v1/endpoint",
        endpoint_secret=SecretStr("test-endpoint-secret"),
    )


@pytest.fixture
def test_api() -> UniqueApi:
    """UniqueApi pointing at the standard local dev URL."""
    return UniqueApi(
        base_url="http://localhost:8092/",
        version="2023-12-06",
    )


@pytest.fixture
def test_auth() -> AuthContext:
    """AuthContext with fixed test identifiers."""
    return AuthContext(
        company_id=SecretStr("test-company-id"),
        user_id=SecretStr("test-user-id"),
    )


@pytest.fixture
def test_chat() -> ChatContext:
    """ChatContext with a chat, assistant and pre-created assistant message."""
    return ChatContext(
        chat_id="test-chat-id",
        assistant_id="test-assistant-id",
        last_assistant_message_id="test-msg-id",
    )


@pytest.fixture
def test_settings(
    test_auth: AuthContext,
    test_chat: ChatContext,
    test_app: UniqueApp,
    test_api: UniqueApi,
) -> UniqueSettings:
    """Full UniqueSettings with all contexts populated."""
    return UniqueSettings(
        auth=test_auth,
        app=test_app,
        api=test_api,
        chat=test_chat,
    )


@pytest.fixture
def test_settings_no_chat(
    test_auth: AuthContext,
    test_app: UniqueApp,
    test_api: UniqueApi,
) -> UniqueSettings:
    """UniqueSettings without a chat context (triggers missing-chat guards)."""
    return UniqueSettings(
        auth=test_auth,
        app=test_app,
        api=test_api,
    )
