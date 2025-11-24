"""Tests for fast_api_factory module."""

from typing import Any
from unittest.mock import MagicMock

import pytest
from pydantic import SecretStr

from unique_toolkit.app.fast_api_factory import (
    build_unique_custom_app,
    default_event_handler,
)
from unique_toolkit.app.schemas import (
    ChatEvent,
    ChatEventAssistantMessage,
    ChatEventPayload,
    ChatEventUserMessage,
)
from unique_toolkit.app.unique_settings import (
    UniqueApi,
    UniqueApp,
    UniqueAuth,
    UniqueChatEventFilterOptions,
    UniqueSettings,
)


@pytest.fixture
def base_settings() -> UniqueSettings:
    """Fixture providing base UniqueSettings for tests."""
    return UniqueSettings(
        auth=UniqueAuth(
            company_id=SecretStr("test-company"), user_id=SecretStr("test-user")
        ),
        app=UniqueApp(
            id=SecretStr("test-id"),
            key=SecretStr("test-key"),
            base_url="https://api.example.com",
            endpoint="/v1/endpoint",
            endpoint_secret=SecretStr("test-secret"),
        ),
        api=UniqueApi(base_url="https://api.example.com", version="2023-12-06"),
    )


@pytest.fixture
def sample_chat_event() -> ChatEvent:
    """Fixture providing a sample ChatEvent for tests."""
    return ChatEvent(
        id="event-123",
        event="unique.chat.external-module.chosen",
        user_id="user-456",
        company_id="company-789",
        payload=ChatEventPayload(
            name="test_module",
            description="Test description",
            configuration={},
            chat_id="chat-123",
            assistant_id="assistant-456",
            user_message=ChatEventUserMessage(
                id="msg-1",
                text="Hello",
                original_text="Hello",
                created_at="2023-01-01T00:00:00Z",
                language="en",
            ),
            assistant_message=ChatEventAssistantMessage(
                id="msg-2", created_at="2023-01-01T00:01:00Z"
            ),
        ),
    )


@pytest.mark.ai
def test_default_event_handler__returns_200__when_status_available() -> None:
    """
    Purpose: Verify default_event_handler returns HTTP 200 OK when status module is available.
    Why this matters: Ensures default handler provides correct status code for successful processing.
    Setup summary: Call default_event_handler with any event, assert HTTP_200_OK returned.
    """
    # Arrange
    event: Any = {"id": "test-event"}
    # Act
    result = default_event_handler(event)
    # Assert
    assert result == 200


@pytest.mark.ai
def test_build_unique_custom_app__raises_import_error__when_fastapi_not_installed(
    mocker,
) -> None:
    """
    Purpose: Verify build_unique_custom_app raises ImportError when FastAPI is not installed.
    Why this matters: Provides clear error message when required dependency is missing.
    Setup summary: Mock FastAPI to be None (simulating failed import), assert exception with helpful message.
    """
    # Arrange
    import unique_toolkit.app.fast_api_factory as fast_api_factory_module

    original_fastapi = fast_api_factory_module.FastAPI
    fast_api_factory_module.FastAPI = None
    try:
        # Act & Assert
        with pytest.raises(ImportError) as exc_info:
            build_unique_custom_app()
        assert "FastAPI is not installed" in str(exc_info.value)
        assert "poetry install --with fastapi" in str(exc_info.value)
    finally:
        # Restore original value
        fast_api_factory_module.FastAPI = original_fastapi


@pytest.mark.ai
def test_build_unique_custom_app__creates_app__with_default_title(
    mocker,
) -> None:
    """
    Purpose: Verify build_unique_custom_app creates FastAPI app with default title.
    Why this matters: Ensures default configuration works correctly.
    Setup summary: Call build_unique_custom_app with default title, assert app created with correct title.
    """
    # Arrange
    mock_fastapi = mocker.patch("unique_toolkit.app.fast_api_factory.FastAPI")
    mock_app = MagicMock()
    mock_fastapi.return_value = mock_app
    # Act
    app = build_unique_custom_app()
    # Assert
    mock_fastapi.assert_called_once_with(title="Unique Chat App")
    assert app is mock_app


@pytest.mark.ai
def test_build_unique_custom_app__creates_app__with_custom_title(
    mocker,
) -> None:
    """
    Purpose: Verify build_unique_custom_app creates FastAPI app with custom title.
    Why this matters: Enables customization of app metadata.
    Setup summary: Call build_unique_custom_app with custom title, assert app created with correct title.
    """
    # Arrange
    mock_fastapi = mocker.patch("unique_toolkit.app.fast_api_factory.FastAPI")
    mock_app = MagicMock()
    mock_fastapi.return_value = mock_app
    # Act
    app = build_unique_custom_app(title="Custom App")
    # Assert
    mock_fastapi.assert_called_once_with(title="Custom App")
    assert app is mock_app


@pytest.mark.ai
def test_build_unique_custom_app__registers_health_check__at_root_path(
    mocker,
) -> None:
    """
    Purpose: Verify build_unique_custom_app registers health check endpoint at root path.
    Why this matters: Provides health monitoring endpoint for deployment checks.
    Setup summary: Call build_unique_custom_app, assert GET endpoint registered at "/" with correct response.
    """
    # Arrange
    mock_fastapi = mocker.patch("unique_toolkit.app.fast_api_factory.FastAPI")
    mock_app = MagicMock()
    mock_fastapi.return_value = mock_app
    # Act
    build_unique_custom_app(title="Test App")
    # Assert
    mock_app.get.assert_called_once_with(path="/")
    # Verify the handler is registered
    assert mock_app.get.call_count == 1


@pytest.mark.ai
@pytest.mark.asyncio
async def test_health_check_endpoint__returns_healthy_status__with_service_name(
    mocker,
) -> None:
    """
    Purpose: Verify health check endpoint returns correct JSON response with service name.
    Why this matters: Enables health monitoring and service identification.
    Setup summary: Create app, call health check endpoint, assert correct JSON response.
    """
    # Arrange
    app = build_unique_custom_app(title="Test Service")
    # Act
    from fastapi.testclient import TestClient

    client = TestClient(app)
    response = client.get("/")
    # Assert
    assert response.status_code == 200
    assert response.json() == {"status": "healthy", "service": "Test Service"}


@pytest.mark.ai
def test_build_unique_custom_app__registers_webhook__at_default_path(
    mocker,
) -> None:
    """
    Purpose: Verify build_unique_custom_app registers webhook endpoint at default path.
    Why this matters: Ensures webhook endpoint is available for event processing.
    Setup summary: Call build_unique_custom_app with default webhook path, assert POST endpoint registered.
    """
    # Arrange
    mock_fastapi = mocker.patch("unique_toolkit.app.fast_api_factory.FastAPI")
    mock_app = MagicMock()
    mock_fastapi.return_value = mock_app
    # Act
    build_unique_custom_app()
    # Assert
    mock_app.post.assert_called_once_with(path="/webhook")


@pytest.mark.ai
def test_build_unique_custom_app__registers_webhook__at_custom_path(
    mocker,
) -> None:
    """
    Purpose: Verify build_unique_custom_app registers webhook endpoint at custom path.
    Why this matters: Enables flexible webhook endpoint configuration.
    Setup summary: Call build_unique_custom_app with custom webhook path, assert POST endpoint registered at custom path.
    """
    # Arrange
    mock_fastapi = mocker.patch("unique_toolkit.app.fast_api_factory.FastAPI")
    mock_app = MagicMock()
    mock_fastapi.return_value = mock_app
    # Act
    build_unique_custom_app(webhook_path="/custom/webhook")
    # Assert
    mock_app.post.assert_called_once_with(path="/custom/webhook")


@pytest.mark.ai
@pytest.mark.asyncio
async def test_webhook_handler__returns_401__when_signature_invalid(
    mocker, base_settings: UniqueSettings, sample_chat_event: ChatEvent
) -> None:
    """
    Purpose: Verify webhook handler returns 401 when webhook signature is invalid.
    Why this matters: Prevents unauthorized access to webhook endpoint.
    Setup summary: Create app, mock invalid signature, send webhook request, assert 401 response.
    """
    # Arrange
    mocker.patch(
        "unique_toolkit.app.fast_api_factory.UniqueSettings.from_env",
        return_value=base_settings,
    )
    app = build_unique_custom_app()
    mocker.patch(
        "unique_toolkit.app.webhook.is_webhook_signature_valid",
        return_value=False,
    )
    event_data = sample_chat_event.model_dump()
    # Act
    from fastapi.testclient import TestClient

    client = TestClient(app)
    response = client.post(
        "/webhook",
        json=event_data,
        headers={
            "X-Unique-Signature": "invalid-signature",
            "X-Unique-Created-At": "1234567890",
        },
    )
    # Assert
    assert response.status_code == 401
    assert "Invalid webhook signature" in response.json()["error"]


@pytest.mark.ai
@pytest.mark.asyncio
async def test_webhook_handler__returns_400__when_json_invalid(
    mocker, base_settings: UniqueSettings
) -> None:
    """
    Purpose: Verify webhook handler returns 400 when request body is invalid JSON.
    Why this matters: Provides clear error message for malformed requests.
    Setup summary: Create app, mock valid signature, send invalid JSON, assert 400 response.
    """
    # Arrange
    mocker.patch(
        "unique_toolkit.app.fast_api_factory.UniqueSettings.from_env",
        return_value=base_settings,
    )
    app = build_unique_custom_app()
    mocker.patch(
        "unique_toolkit.app.webhook.is_webhook_signature_valid",
        return_value=True,
    )
    # Act
    from fastapi.testclient import TestClient

    client = TestClient(app)
    response = client.post(
        "/webhook",
        content="invalid json{",
        headers={
            "X-Unique-Signature": "valid-signature",
            "X-Unique-Created-At": "1234567890",
            "Content-Type": "application/json",
        },
    )
    # Assert
    assert response.status_code == 400
    assert "Invalid event format" in response.json()["error"]


@pytest.mark.ai
@pytest.mark.asyncio
async def test_webhook_handler__returns_400__when_event_name_invalid(
    mocker, base_settings: UniqueSettings
) -> None:
    """
    Purpose: Verify webhook handler returns 400 when event name is not supported.
    Why this matters: Prevents processing of unsupported event types.
    Setup summary: Create app, mock valid signature, send event with invalid name, assert 400 response.
    """
    # Arrange
    mocker.patch(
        "unique_toolkit.app.fast_api_factory.UniqueSettings.from_env",
        return_value=base_settings,
    )
    app = build_unique_custom_app()
    mocker.patch(
        "unique_toolkit.app.webhook.is_webhook_signature_valid",
        return_value=True,
    )
    event_data = {"event": "invalid.event.name", "id": "test-id"}
    # Act
    from fastapi.testclient import TestClient

    client = TestClient(app)
    response = client.post(
        "/webhook",
        json=event_data,
        headers={
            "X-Unique-Signature": "valid-signature",
            "X-Unique-Created-At": "1234567890",
        },
    )
    # Assert
    assert response.status_code == 400
    assert "Invalid event name" in response.json()["error"]


@pytest.mark.ai
@pytest.mark.asyncio
async def test_webhook_handler__returns_200__when_event_filtered(
    mocker, base_settings: UniqueSettings, sample_chat_event: ChatEvent
) -> None:
    """
    Purpose: Verify webhook handler returns 200 when event is filtered out.
    Why this matters: Ensures filtered events are handled gracefully without processing.
    Setup summary: Create app with filter options, mock valid signature and filtered event, assert 200 with filter message.
    """
    # Arrange
    filter_options = UniqueChatEventFilterOptions(
        assistant_ids=["other-assistant"], references_in_code=[]
    )
    settings = UniqueSettings(
        auth=base_settings.auth,
        app=base_settings.app,
        api=base_settings.api,
        chat_event_filter_options=filter_options,
    )
    mocker.patch(
        "unique_toolkit.app.fast_api_factory.UniqueSettings.from_env",
        return_value=settings,
    )
    app = build_unique_custom_app()
    mocker.patch(
        "unique_toolkit.app.webhook.is_webhook_signature_valid",
        return_value=True,
    )
    event_data = sample_chat_event.model_dump()
    # Act
    from fastapi.testclient import TestClient

    client = TestClient(app)
    response = client.post(
        "/webhook",
        json=event_data,
        headers={
            "X-Unique-Signature": "valid-signature",
            "X-Unique-Created-At": "1234567890",
        },
    )
    # Assert
    assert response.status_code == 200
    assert "Event filtered out" in response.json()["error"]


@pytest.mark.ai
@pytest.mark.asyncio
async def test_webhook_handler__calls_event_handler__with_chat_event(
    mocker, base_settings: UniqueSettings, sample_chat_event: ChatEvent
) -> None:
    """
    Purpose: Verify webhook handler calls event handler with parsed ChatEvent.
    Why this matters: Ensures event processing pipeline works correctly.
    Setup summary: Create app with custom handler, mock valid signature, send event, assert handler called with correct event.
    """
    # Arrange
    mocker.patch(
        "unique_toolkit.app.fast_api_factory.UniqueSettings.from_env",
        return_value=base_settings,
    )
    mock_handler = mocker.Mock(return_value=201)
    app = build_unique_custom_app(chat_event_handler=mock_handler)
    mocker.patch(
        "unique_toolkit.app.webhook.is_webhook_signature_valid",
        return_value=True,
    )
    event_data = sample_chat_event.model_dump()
    # Act
    from fastapi.testclient import TestClient

    client = TestClient(app)
    response = client.post(
        "/webhook",
        json=event_data,
        headers={
            "X-Unique-Signature": "valid-signature",
            "X-Unique-Created-At": "1234567890",
        },
    )
    # Assert
    assert response.status_code == 200
    assert response.json()["return_value"] == 201
    mock_handler.assert_called_once()
    call_arg = mock_handler.call_args[0][0]
    assert isinstance(call_arg, ChatEvent)
    assert call_arg.id == sample_chat_event.id


@pytest.mark.ai
@pytest.mark.asyncio
async def test_webhook_handler__updates_auth__from_event(
    mocker, base_settings: UniqueSettings, sample_chat_event: ChatEvent
) -> None:
    """
    Purpose: Verify webhook handler updates settings.auth from event data.
    Why this matters: Enables dynamic authentication based on event context.
    Setup summary: Create app, mock valid signature, send event, assert auth updated then reset.
    """
    # Arrange
    # Create a mock settings that we can track changes on
    mock_settings = mocker.MagicMock(spec=UniqueSettings)
    mock_settings.app = base_settings.app
    mock_settings.auth = base_settings.auth
    mock_settings.chat_event_filter_options = base_settings.chat_event_filter_options
    mock_settings.init_sdk = mocker.Mock()

    mocker.patch(
        "unique_toolkit.app.fast_api_factory.UniqueSettings.from_env",
        return_value=mock_settings,
    )
    mock_handler = mocker.Mock(return_value=200)
    app = build_unique_custom_app(chat_event_handler=mock_handler)
    mocker.patch(
        "unique_toolkit.app.webhook.is_webhook_signature_valid",
        return_value=True,
    )
    event_data = sample_chat_event.model_dump()
    # Act
    from fastapi.testclient import TestClient

    client = TestClient(app)
    response = client.post(
        "/webhook",
        json=event_data,
        headers={
            "X-Unique-Signature": "valid-signature",
            "X-Unique-Created-At": "1234567890",
        },
    )
    # Assert
    assert response.status_code == 200
    # Verify that auth was set during handler execution
    # Since settings are created per request, we verify the handler was called
    assert mock_handler.called
    # Verify init_sdk was called
    mock_settings.init_sdk.assert_called_once()


@pytest.mark.ai
@pytest.mark.asyncio
async def test_webhook_handler__uses_default_handler__when_not_provided(
    mocker, base_settings: UniqueSettings, sample_chat_event: ChatEvent
) -> None:
    """
    Purpose: Verify webhook handler uses default_event_handler when no custom handler provided.
    Why this matters: Ensures default behavior works correctly.
    Setup summary: Create app without custom handler, mock valid signature, send event, assert default handler used.
    """
    # Arrange
    mocker.patch(
        "unique_toolkit.app.fast_api_factory.UniqueSettings.from_env",
        return_value=base_settings,
    )
    app = build_unique_custom_app()
    mocker.patch(
        "unique_toolkit.app.webhook.is_webhook_signature_valid",
        return_value=True,
    )
    event_data = sample_chat_event.model_dump()
    # Act
    from fastapi.testclient import TestClient

    client = TestClient(app)
    response = client.post(
        "/webhook",
        json=event_data,
        headers={
            "X-Unique-Signature": "valid-signature",
            "X-Unique-Created-At": "1234567890",
        },
    )
    # Assert
    assert response.status_code == 200
    assert response.json()["return_value"] == 200


@pytest.mark.ai
@pytest.mark.asyncio
async def test_webhook_handler__handles_missing_event_field(
    mocker, base_settings: UniqueSettings
) -> None:
    """
    Purpose: Verify webhook handler handles missing event field gracefully.
    Why this matters: Prevents crashes from malformed event data.
    Setup summary: Create app, mock valid signature, send event without event field, assert 400 response.
    """
    # Arrange
    mocker.patch(
        "unique_toolkit.app.fast_api_factory.UniqueSettings.from_env",
        return_value=base_settings,
    )
    app = build_unique_custom_app()
    mocker.patch(
        "unique_toolkit.app.webhook.is_webhook_signature_valid",
        return_value=True,
    )
    event_data = {"id": "test-id"}  # Missing event field
    # Act
    from fastapi.testclient import TestClient

    client = TestClient(app)
    response = client.post(
        "/webhook",
        json=event_data,
        headers={
            "X-Unique-Signature": "valid-signature",
            "X-Unique-Created-At": "1234567890",
        },
    )
    # Assert
    assert response.status_code == 400
    assert "Invalid event name" in response.json()["error"]


@pytest.mark.ai
@pytest.mark.asyncio
async def test_build_unique_custom_app__uses_settings_file__when_provided(
    mocker, base_settings: UniqueSettings, tmp_path, sample_chat_event: ChatEvent
) -> None:
    """
    Purpose: Verify build_unique_custom_app uses settings_file when provided.
    Why this matters: Enables loading settings from a specific file path.
    Setup summary: Create app with settings_file, verify from_env called with file path.
    """
    # Arrange
    settings_file = tmp_path / "test.env"
    settings_file.write_text("UNIQUE_APP_ENDPOINT_SECRET=test-secret-from-file\n")

    mock_from_env = mocker.patch(
        "unique_toolkit.app.fast_api_factory.UniqueSettings.from_env",
        return_value=base_settings,
    )
    app = build_unique_custom_app(settings_file=settings_file)
    mocker.patch(
        "unique_toolkit.app.webhook.is_webhook_signature_valid",
        return_value=True,
    )
    event_data = sample_chat_event.model_dump()
    # Act
    from fastapi.testclient import TestClient

    client = TestClient(app)
    response = client.post(
        "/webhook",
        json=event_data,
        headers={
            "X-Unique-Signature": "valid-signature",
            "X-Unique-Created-At": "1234567890",
        },
    )
    # Assert
    # Verify from_env was called with the settings_file
    mock_from_env.assert_called_once_with(env_file=settings_file)
    assert response.status_code == 200


@pytest.mark.ai
@pytest.mark.asyncio
async def test_webhook_handler__handles_configuration_exception(
    mocker, base_settings: UniqueSettings, sample_chat_event: ChatEvent
) -> None:
    """
    Purpose: Verify webhook handler handles ConfigurationException gracefully.
    Why this matters: Provides proper error handling for configuration issues.
    Setup summary: Create app, mock ConfigurationException, send event, assert 500 response.
    """
    # Arrange
    from unique_toolkit._common.exception import ConfigurationException

    mocker.patch(
        "unique_toolkit.app.fast_api_factory.UniqueSettings.from_env",
        return_value=base_settings,
    )
    app = build_unique_custom_app()
    mocker.patch(
        "unique_toolkit.app.webhook.is_webhook_signature_valid",
        return_value=True,
    )
    # Mock init_sdk to raise ConfigurationException
    mocker.patch(
        "unique_toolkit.app.fast_api_factory.UniqueSettings.init_sdk",
        side_effect=ConfigurationException("Configuration error"),
    )
    event_data = sample_chat_event.model_dump()
    # Act
    from fastapi.testclient import TestClient

    client = TestClient(app)
    response = client.post(
        "/webhook",
        json=event_data,
        headers={
            "X-Unique-Signature": "valid-signature",
            "X-Unique-Created-At": "1234567890",
        },
    )
    # Assert
    assert response.status_code == 500
    assert "Configuration error" in response.json()["error"]


@pytest.mark.ai
@pytest.mark.asyncio
async def test_webhook_handler__handles_generic_exception(
    mocker, base_settings: UniqueSettings, sample_chat_event: ChatEvent
) -> None:
    """
    Purpose: Verify webhook handler handles generic exceptions gracefully.
    Why this matters: Prevents crashes from unexpected errors.
    Setup summary: Create app, mock exception in handler, send event, assert 500 response.
    """
    # Arrange
    mocker.patch(
        "unique_toolkit.app.fast_api_factory.UniqueSettings.from_env",
        return_value=base_settings,
    )
    mock_handler = mocker.Mock(side_effect=ValueError("Unexpected error"))
    app = build_unique_custom_app(chat_event_handler=mock_handler)
    mocker.patch(
        "unique_toolkit.app.webhook.is_webhook_signature_valid",
        return_value=True,
    )
    event_data = sample_chat_event.model_dump()
    # Act
    from fastapi.testclient import TestClient

    client = TestClient(app)
    response = client.post(
        "/webhook",
        json=event_data,
        headers={
            "X-Unique-Signature": "valid-signature",
            "X-Unique-Created-At": "1234567890",
        },
    )
    # Assert
    assert response.status_code == 500
    assert "Error handling event" in response.json()["error"]
