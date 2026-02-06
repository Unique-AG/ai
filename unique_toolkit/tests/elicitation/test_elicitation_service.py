"""
Tests for ElicitationService class.

This test suite validates the ElicitationService's ability to:
1. Initialize properly with required and optional parameters
2. Create elicitation requests (sync and async)
3. Retrieve elicitation requests (sync and async)
4. List pending elicitations (sync and async)
5. Respond to elicitation requests (sync and async)
"""

from datetime import datetime
from typing import Any
from unittest.mock import AsyncMock

import pytest

from unique_toolkit.app.schemas import (
    ChatEvent,
    ChatEventPayload,
    Correlation,
    EventName,
)
from unique_toolkit.elicitation.schemas import (
    Elicitation,
    ElicitationAction,
    ElicitationList,
    ElicitationMode,
    ElicitationResponseResult,
)
from unique_toolkit.elicitation.service import ElicitationService

# Fixtures
# ============================================================================


@pytest.fixture
def base_elicitation_data() -> dict[str, Any]:
    """
    Base fixture for elicitation response data.
    """
    return {
        "id": "elic_test123",
        "object": "elicitation",
        "source": "INTERNAL_TOOL",
        "mode": "FORM",
        "status": "PENDING",
        "message": "Please provide your input",
        "toolName": "test_tool",
        "schema": {"type": "object", "properties": {"name": {"type": "string"}}},
        "companyId": "test_company",
        "userId": "test_user",
        "chatId": "test_chat",
        "messageId": "test_message",
        "createdAt": "2024-01-01T00:00:00",
    }


@pytest.fixture
def mock_elicitation(base_elicitation_data: dict[str, Any]) -> Elicitation:
    """
    Mock Elicitation object for testing.
    """
    return Elicitation.model_validate(base_elicitation_data, by_alias=True)


@pytest.fixture
def mock_chat_event() -> ChatEvent:
    """
    Mock ChatEvent for testing from_chat_event classmethod.
    """
    from unique_toolkit.app.schemas import (
        ChatEventAssistantMessage,
        ChatEventUserMessage,
    )

    return ChatEvent(
        id="event_123",
        event=EventName.EXTERNAL_MODULE_CHOSEN,
        created_at=int(datetime.now().timestamp()),
        company_id="test_company",
        user_id="test_user",
        payload=ChatEventPayload(
            name="CHAT_MESSAGE_CREATED",
            description="Test event",
            configuration={},
            chat_id="test_chat",
            assistant_id="test_assistant",
            user_message=ChatEventUserMessage(
                id="user_msg_123",
                text="Test message",
                original_text="Test message",
                created_at="2024-01-01T00:00:00",
                language="en",
            ),
            assistant_message=ChatEventAssistantMessage(
                id="asst_msg_123",
                created_at="2024-01-01T00:00:00",
            ),
            correlation=None,
        ),
    )


# Initialization Tests
# ============================================================================


@pytest.mark.ai
def test_elicitation_service__initializes__with_required_params() -> None:
    """
    Purpose: Verify ElicitationService initializes with required parameters.
    Why this matters: Service must be creatable with minimum required fields.
    Setup summary: Create service with user_id and company_id, verify initialization.
    """
    # Arrange & Act
    service = ElicitationService(user_id="test_user", company_id="test_company")

    # Assert
    assert service._user_id == "test_user"
    assert service._company_id == "test_company"
    assert service._chat_id is None
    assert service._message_id is None


@pytest.mark.ai
def test_elicitation_service__initializes__with_optional_params() -> None:
    """
    Purpose: Verify ElicitationService initializes with optional parameters.
    Why this matters: Service should accept optional chat_id and message_id.
    Setup summary: Create service with all parameters, verify initialization.
    """
    # Arrange & Act
    service = ElicitationService(
        user_id="test_user",
        company_id="test_company",
        chat_id="test_chat",
        message_id="test_message",
    )

    # Assert
    assert service._user_id == "test_user"
    assert service._company_id == "test_company"
    assert service._chat_id == "test_chat"
    assert service._message_id == "test_message"


@pytest.mark.ai
def test_elicitation_service__creates_from_chat_event__with_correlation(
    mock_chat_event: ChatEvent,
) -> None:
    """
    Purpose: Verify from_chat_event creates service with correlation data.
    Why this matters: Service must extract chat and message IDs from correlation.
    Setup summary: Create event with correlation, call from_chat_event, verify fields.
    """
    # Arrange
    mock_chat_event.payload.correlation = Correlation(
        parent_chat_id="parent_chat",
        parent_message_id="parent_message",
        parent_assistant_id="parent_assistant",
    )

    # Act
    service = ElicitationService.from_chat_event(mock_chat_event)

    # Assert
    assert service._company_id == "test_company"
    assert service._user_id == "test_user"
    assert service._chat_id == "parent_chat"
    assert service._message_id == "parent_message"


@pytest.mark.ai
def test_elicitation_service__creates_from_chat_event__without_correlation(
    mock_chat_event: ChatEvent,
) -> None:
    """
    Purpose: Verify from_chat_event creates service without correlation.
    Why this matters: Service must use payload chat_id and assistant message id.
    Setup summary: Create event without correlation, call from_chat_event, verify fields.
    """
    # Arrange
    mock_chat_event.payload.correlation = None

    # Act
    service = ElicitationService.from_chat_event(mock_chat_event)

    # Assert
    assert service._company_id == "test_company"
    assert service._user_id == "test_user"
    assert service._chat_id == "test_chat"
    assert service._message_id == "asst_msg_123"


@pytest.mark.ai
def test_elicitation_service__creates_from_correlation__with_correlation_object() -> (
    None
):
    """
    Purpose: Verify from_correlation creates service from Correlation object.
    Why this matters: Service should support creation from correlation data.
    Setup summary: Create correlation object, call from_correlation, verify fields.
    """
    # Arrange
    correlation = Correlation(
        parent_chat_id="parent_chat",
        parent_message_id="parent_message",
        parent_assistant_id="parent_assistant",
    )

    # Act
    service = ElicitationService.from_correlation(
        company_id="test_company",
        user_id="test_user",
        correlation=correlation,
    )

    # Assert
    assert service._company_id == "test_company"
    assert service._user_id == "test_user"
    assert service._chat_id == "parent_chat"
    assert service._message_id == "parent_message"


@pytest.mark.ai
def test_elicitation_service__creates_from_chat_and_message__with_ids() -> None:
    """
    Purpose: Verify from_chat_and_message creates service from direct IDs.
    Why this matters: Service should support creation from explicit IDs.
    Setup summary: Call from_chat_and_message with IDs, verify fields.
    """
    # Arrange & Act
    service = ElicitationService.from_chat_and_message(
        company_id="test_company",
        user_id="test_user",
        chat_id="test_chat",
        message_id="test_message",
    )

    # Assert
    assert service._company_id == "test_company"
    assert service._user_id == "test_user"
    assert service._chat_id == "test_chat"
    assert service._message_id == "test_message"


# Create Methods Tests
# ============================================================================


@pytest.mark.ai
def test_elicitation_service__create__with_form_mode(
    mocker,
    base_elicitation_data: dict[str, Any],
) -> None:
    """
    Purpose: Verify create() method works with FORM mode and json_schema.
    Why this matters: FORM mode is a core elicitation type requiring schema.
    Setup summary: Mock SDK call, call create with FORM mode, verify response.
    """
    # Arrange
    mock_create = mocker.patch(
        "unique_sdk.Elicitation.create_elicitation",
        return_value=base_elicitation_data,
    )
    service = ElicitationService(
        user_id="test_user",
        company_id="test_company",
        chat_id="test_chat",
        message_id="test_message",
    )
    json_schema = {"type": "object", "properties": {"name": {"type": "string"}}}

    # Act
    result = service.create(
        mode=ElicitationMode.FORM,
        message="Please provide input",
        tool_name="test_tool",
        json_schema=json_schema,
    )

    # Assert
    assert isinstance(result, Elicitation)
    assert result.id == "elic_test123"
    assert result.mode == ElicitationMode.FORM
    mock_create.assert_called_once()
    call_kwargs = mock_create.call_args.kwargs
    assert call_kwargs["user_id"] == "test_user"
    assert call_kwargs["company_id"] == "test_company"
    assert call_kwargs["mode"] == "FORM"


@pytest.mark.ai
def test_elicitation_service__create__with_url_mode(
    mocker,
    base_elicitation_data: dict[str, Any],
) -> None:
    """
    Purpose: Verify create() method works with URL mode.
    Why this matters: URL mode is a core elicitation type requiring URL.
    Setup summary: Mock SDK call, call create with URL mode, verify response.
    """
    # Arrange
    url_data = base_elicitation_data.copy()
    url_data["mode"] = "URL"
    url_data["url"] = "https://example.com/form"
    mock_create = mocker.patch(
        "unique_sdk.Elicitation.create_elicitation",
        return_value=url_data,
    )
    service = ElicitationService(user_id="test_user", company_id="test_company")

    # Act
    result = service.create(
        mode=ElicitationMode.URL,
        message="Please fill out the form",
        tool_name="test_tool",
        url="https://example.com/form",
    )

    # Assert
    assert isinstance(result, Elicitation)
    assert result.mode == ElicitationMode.URL
    mock_create.assert_called_once()


@pytest.mark.ai
def test_elicitation_service__create__with_all_optional_params(
    mocker,
    base_elicitation_data: dict[str, Any],
) -> None:
    """
    Purpose: Verify create() accepts all optional parameters.
    Why this matters: All optional parameters should be properly passed through.
    Setup summary: Mock SDK call, call create with all params, verify call.
    """
    # Arrange
    mock_create = mocker.patch(
        "unique_sdk.Elicitation.create_elicitation",
        return_value=base_elicitation_data,
    )
    service = ElicitationService(
        user_id="test_user",
        company_id="test_company",
        chat_id="test_chat",
        message_id="test_message",
    )
    metadata = {"key": "value"}

    # Act
    result = service.create(
        mode=ElicitationMode.FORM,
        message="Please provide input",
        tool_name="test_tool",
        json_schema={"type": "object"},
        external_elicitation_id="ext_123",
        expires_in_seconds=3600,
        metadata=metadata,
    )

    # Assert
    assert isinstance(result, Elicitation)
    mock_create.assert_called_once()
    call_kwargs = mock_create.call_args.kwargs
    assert "externalElicitationId" in call_kwargs
    assert "expiresInSeconds" in call_kwargs
    assert "metadata" in call_kwargs


@pytest.mark.ai
@pytest.mark.asyncio
async def test_elicitation_service__create_async__mirrors_sync(
    mocker,
    base_elicitation_data: dict[str, Any],
) -> None:
    """
    Purpose: Verify create_async() behaves same as sync version.
    Why this matters: Async version must provide same functionality.
    Setup summary: Mock async SDK call, call create_async, verify response.
    """
    # Arrange
    mock_create_async = mocker.patch(
        "unique_sdk.Elicitation.create_elicitation_async",
        new_callable=AsyncMock,
        return_value=base_elicitation_data,
    )
    service = ElicitationService(user_id="test_user", company_id="test_company")

    # Act
    result = await service.create_async(
        mode=ElicitationMode.FORM,
        message="Please provide input",
        tool_name="test_tool",
        json_schema={"type": "object"},
    )

    # Assert
    assert isinstance(result, Elicitation)
    assert result.id == "elic_test123"
    mock_create_async.assert_called_once()


# Get Methods Tests
# ============================================================================


@pytest.mark.ai
def test_elicitation_service__get__retrieves_by_id(
    mocker,
    base_elicitation_data: dict[str, Any],
) -> None:
    """
    Purpose: Verify get() retrieves elicitation by ID.
    Why this matters: Core functionality for retrieving elicitation details.
    Setup summary: Mock SDK call, call get with ID, verify response.
    """
    # Arrange
    mock_get = mocker.patch(
        "unique_sdk.Elicitation.get_elicitation",
        return_value=base_elicitation_data,
    )
    service = ElicitationService(user_id="test_user", company_id="test_company")

    # Act
    result = service.get(elicitation_id="elic_test123")

    # Assert
    assert isinstance(result, Elicitation)
    assert result.id == "elic_test123"
    mock_get.assert_called_once_with(
        user_id="test_user",
        company_id="test_company",
        elicitation_id="elic_test123",
    )


@pytest.mark.ai
@pytest.mark.asyncio
async def test_elicitation_service__get_async__mirrors_sync(
    mocker,
    base_elicitation_data: dict[str, Any],
) -> None:
    """
    Purpose: Verify get_async() behaves same as sync version.
    Why this matters: Async version must provide same functionality.
    Setup summary: Mock async SDK call, call get_async, verify response.
    """
    # Arrange
    mock_get_async = mocker.patch(
        "unique_sdk.Elicitation.get_elicitation_async",
        new_callable=AsyncMock,
        return_value=base_elicitation_data,
    )
    service = ElicitationService(user_id="test_user", company_id="test_company")

    # Act
    result = await service.get_async(elicitation_id="elic_test123")

    # Assert
    assert isinstance(result, Elicitation)
    assert result.id == "elic_test123"
    mock_get_async.assert_called_once()


# List Pending Methods Tests
# ============================================================================


@pytest.mark.ai
def test_elicitation_service__list_pending__returns_list(
    mocker,
    base_elicitation_data: dict[str, Any],
) -> None:
    """
    Purpose: Verify list_pending() returns ElicitationList.
    Why this matters: Core functionality for listing pending elicitations.
    Setup summary: Mock SDK call with multiple elicitations, verify response.
    """
    # Arrange
    elicitation_data_2 = base_elicitation_data.copy()
    elicitation_data_2["id"] = "elic_test456"
    mock_list = mocker.patch(
        "unique_sdk.Elicitation.get_pending_elicitations",
        return_value={"elicitations": [base_elicitation_data, elicitation_data_2]},
    )
    service = ElicitationService(user_id="test_user", company_id="test_company")

    # Act
    result = service.list_pending()

    # Assert
    assert isinstance(result, ElicitationList)
    assert len(result.elicitations) == 2
    assert result.elicitations[0].id == "elic_test123"
    assert result.elicitations[1].id == "elic_test456"
    mock_list.assert_called_once_with(
        user_id="test_user",
        company_id="test_company",
    )


@pytest.mark.ai
@pytest.mark.asyncio
async def test_elicitation_service__list_pending_async__mirrors_sync(
    mocker,
    base_elicitation_data: dict[str, Any],
) -> None:
    """
    Purpose: Verify list_pending_async() behaves same as sync version.
    Why this matters: Async version must provide same functionality.
    Setup summary: Mock async SDK call, call list_pending_async, verify response.
    """
    # Arrange
    mock_list_async = mocker.patch(
        "unique_sdk.Elicitation.get_pending_elicitations_async",
        new_callable=AsyncMock,
        return_value={"elicitations": [base_elicitation_data]},
    )
    service = ElicitationService(user_id="test_user", company_id="test_company")

    # Act
    result = await service.list_pending_async()

    # Assert
    assert isinstance(result, ElicitationList)
    assert len(result.elicitations) == 1
    mock_list_async.assert_called_once()


# Respond Methods Tests
# ============================================================================


@pytest.mark.ai
def test_elicitation_service__respond__with_accept_action(mocker) -> None:
    """
    Purpose: Verify respond() works with ACCEPT action and content.
    Why this matters: ACCEPT is the primary response action requiring content.
    Setup summary: Mock SDK call, call respond with ACCEPT, verify parameters.
    """
    # Arrange
    mock_respond = mocker.patch(
        "unique_sdk.Elicitation.respond_to_elicitation",
        return_value={"success": True, "message": "Accepted"},
    )
    service = ElicitationService(user_id="test_user", company_id="test_company")
    content = {"name": "John Doe", "age": 30}

    # Act
    result = service.respond(
        elicitation_id="elic_test123",
        action=ElicitationAction.ACCEPT,
        content=content,
    )

    # Assert
    assert isinstance(result, ElicitationResponseResult)
    assert result.success is True
    mock_respond.assert_called_once()
    call_kwargs = mock_respond.call_args.kwargs
    assert call_kwargs["user_id"] == "test_user"
    assert call_kwargs["company_id"] == "test_company"


@pytest.mark.ai
def test_elicitation_service__respond__with_decline_action(mocker) -> None:
    """
    Purpose: Verify respond() works with DECLINE action.
    Why this matters: DECLINE is a valid response action without content.
    Setup summary: Mock SDK call, call respond with DECLINE, verify call.
    """
    # Arrange
    mock_respond = mocker.patch(
        "unique_sdk.Elicitation.respond_to_elicitation",
        return_value={"success": True, "message": "Declined"},
    )
    service = ElicitationService(user_id="test_user", company_id="test_company")

    # Act
    result = service.respond(
        elicitation_id="elic_test123",
        action=ElicitationAction.DECLINE,
    )

    # Assert
    assert isinstance(result, ElicitationResponseResult)
    assert result.success is True
    mock_respond.assert_called_once()


@pytest.mark.ai
def test_elicitation_service__respond__with_cancel_action(mocker) -> None:
    """
    Purpose: Verify respond() works with CANCEL action.
    Why this matters: CANCEL is a valid response action without content.
    Setup summary: Mock SDK call, call respond with CANCEL, verify call.
    """
    # Arrange
    mock_respond = mocker.patch(
        "unique_sdk.Elicitation.respond_to_elicitation",
        return_value={"success": True, "message": "Cancelled"},
    )
    service = ElicitationService(user_id="test_user", company_id="test_company")

    # Act
    result = service.respond(
        elicitation_id="elic_test123",
        action=ElicitationAction.CANCEL,
    )

    # Assert
    assert isinstance(result, ElicitationResponseResult)
    assert result.success is True
    mock_respond.assert_called_once()


@pytest.mark.ai
@pytest.mark.asyncio
async def test_elicitation_service__respond_async__mirrors_sync(mocker) -> None:
    """
    Purpose: Verify respond_async() behaves same as sync version.
    Why this matters: Async version must provide same functionality.
    Setup summary: Mock async SDK call, call respond_async, verify response.
    """
    # Arrange
    mock_respond_async = mocker.patch(
        "unique_sdk.Elicitation.respond_to_elicitation_async",
        new_callable=AsyncMock,
        return_value={"success": True, "message": "Accepted"},
    )
    service = ElicitationService(user_id="test_user", company_id="test_company")

    # Act
    result = await service.respond_async(
        elicitation_id="elic_test123",
        action=ElicitationAction.ACCEPT,
        content={"name": "John"},
    )

    # Assert
    assert isinstance(result, ElicitationResponseResult)
    assert result.success is True
    mock_respond_async.assert_called_once()
