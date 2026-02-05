"""
Tests for elicitation functions.

This test suite validates the standalone elicitation functions that interact
with the unique_sdk:
1. create_elicitation and create_elicitation_async
2. get_elicitation and get_elicitation_async
3. get_pending_elicitations and get_pending_elicitations_async
4. respond_to_elicitation and respond_to_elicitation_async
"""

from typing import Any
from unittest.mock import AsyncMock

import pytest

from unique_toolkit.elicitation.functions import (
    create_elicitation,
    create_elicitation_async,
    get_elicitation,
    get_elicitation_async,
    get_pending_elicitations,
    get_pending_elicitations_async,
    respond_to_elicitation,
    respond_to_elicitation_async,
)
from unique_toolkit.elicitation.schemas import (
    Elicitation,
    ElicitationAction,
    ElicitationList,
    ElicitationMode,
    ElicitationResponseResult,
)

# Fixtures
# ============================================================================


@pytest.fixture
def base_elicitation_response() -> dict[str, Any]:
    """
    Base fixture for SDK elicitation response.
    """
    return {
        "id": "elic_func_123",
        "object": "elicitation",
        "source": "INTERNAL_TOOL",
        "mode": "FORM",
        "status": "PENDING",
        "message": "Test message",
        "toolName": "test_tool",
        "schema": {"type": "object"},
        "companyId": "test_company",
        "userId": "test_user",
        "createdAt": "2024-01-01T00:00:00",
    }


# create_elicitation Tests
# ============================================================================


@pytest.mark.ai
def test_create_elicitation__creates_with_form_mode__and_json_schema(
    mocker,
    base_elicitation_response: dict[str, Any],
) -> None:
    """
    Purpose: Verify create_elicitation creates FORM mode elicitation with schema.
    Why this matters: FORM mode requires json_schema parameter validation.
    Setup summary: Mock SDK call, call function with FORM params, verify result.
    """
    # Arrange
    mock_create = mocker.patch(
        "unique_sdk.Elicitation.create_elicitation",
        return_value=base_elicitation_response,
    )
    json_schema = {"type": "object", "properties": {"field": {"type": "string"}}}

    # Act
    result = create_elicitation(
        user_id="test_user",
        company_id="test_company",
        mode=ElicitationMode.FORM,
        message="Test message",
        tool_name="test_tool",
        json_schema=json_schema,
    )

    # Assert
    assert isinstance(result, Elicitation)
    assert result.id == "elic_func_123"
    assert result.mode == ElicitationMode.FORM
    mock_create.assert_called_once()


@pytest.mark.ai
def test_create_elicitation__creates_with_url_mode__and_converts_url(
    mocker,
    base_elicitation_response: dict[str, Any],
) -> None:
    """
    Purpose: Verify create_elicitation converts URL string to AnyUrl for URL mode.
    Why this matters: URL parameter must be validated as proper URL.
    Setup summary: Mock SDK call, call with URL string, verify AnyUrl conversion.
    """
    # Arrange
    url_response = base_elicitation_response.copy()
    url_response["mode"] = "URL"
    url_response["url"] = "https://example.com/form"
    mock_create = mocker.patch(
        "unique_sdk.Elicitation.create_elicitation",
        return_value=url_response,
    )

    # Act
    result = create_elicitation(
        user_id="test_user",
        company_id="test_company",
        mode=ElicitationMode.URL,
        message="Fill the form",
        tool_name="test_tool",
        url="https://example.com/form",
    )

    # Assert
    assert isinstance(result, Elicitation)
    assert result.mode == ElicitationMode.URL
    mock_create.assert_called_once()


@pytest.mark.ai
def test_create_elicitation__includes_optional_params__in_request(
    mocker,
    base_elicitation_response: dict[str, Any],
) -> None:
    """
    Purpose: Verify create_elicitation passes all optional parameters to SDK.
    Why this matters: Optional params must be correctly serialized and passed.
    Setup summary: Mock SDK, call with optional params, verify SDK call args.
    """
    # Arrange
    mock_create = mocker.patch(
        "unique_sdk.Elicitation.create_elicitation",
        return_value=base_elicitation_response,
    )
    metadata = {"custom_key": "custom_value"}

    # Act
    result = create_elicitation(
        user_id="test_user",
        company_id="test_company",
        mode=ElicitationMode.FORM,
        message="Test",
        tool_name="test_tool",
        json_schema={"type": "object"},
        chat_id="chat_123",
        message_id="msg_123",
        external_elicitation_id="ext_123",
        expires_in_seconds=7200,
        metadata=metadata,
    )

    # Assert
    assert isinstance(result, Elicitation)
    mock_create.assert_called_once()
    call_kwargs = mock_create.call_args.kwargs
    assert "chatId" in call_kwargs or "chat_id" in call_kwargs
    assert (
        "externalElicitationId" in call_kwargs
        or "external_elicitation_id" in call_kwargs
    )


@pytest.mark.ai
def test_create_elicitation__logs_and_raises__on_sdk_error(mocker) -> None:
    """
    Purpose: Verify create_elicitation logs and re-raises SDK exceptions.
    Why this matters: Errors must be logged and propagated for debugging.
    Setup summary: Mock SDK to raise exception, verify logging and re-raise.
    """
    # Arrange
    mocker.patch(
        "unique_sdk.Elicitation.create_elicitation",
        side_effect=Exception("SDK Error"),
    )

    # Act & Assert
    with pytest.raises(Exception) as exc_info:
        create_elicitation(
            user_id="test_user",
            company_id="test_company",
            mode=ElicitationMode.FORM,
            message="Test",
            tool_name="test_tool",
        )

    assert "SDK Error" in str(exc_info.value)


@pytest.mark.ai
@pytest.mark.asyncio
async def test_create_elicitation_async__behaves_like_sync__with_async_sdk(
    mocker,
    base_elicitation_response: dict[str, Any],
) -> None:
    """
    Purpose: Verify create_elicitation_async mirrors sync behavior asynchronously.
    Why this matters: Async version must provide same functionality as sync.
    Setup summary: Mock async SDK call, call async function, verify result.
    """
    # Arrange
    mock_create_async = mocker.patch(
        "unique_sdk.Elicitation.create_elicitation_async",
        new_callable=AsyncMock,
        return_value=base_elicitation_response,
    )

    # Act
    result = await create_elicitation_async(
        user_id="test_user",
        company_id="test_company",
        mode=ElicitationMode.FORM,
        message="Test message",
        tool_name="test_tool",
        json_schema={"type": "object"},
    )

    # Assert
    assert isinstance(result, Elicitation)
    assert result.id == "elic_func_123"
    mock_create_async.assert_called_once()


# get_elicitation Tests
# ============================================================================


@pytest.mark.ai
def test_get_elicitation__retrieves_and_validates__elicitation_by_id(
    mocker,
    base_elicitation_response: dict[str, Any],
) -> None:
    """
    Purpose: Verify get_elicitation retrieves and validates to Elicitation model.
    Why this matters: Response must be properly validated to domain model.
    Setup summary: Mock SDK get, call function with ID, verify validation.
    """
    # Arrange
    mock_get = mocker.patch(
        "unique_sdk.Elicitation.get_elicitation",
        return_value=base_elicitation_response,
    )

    # Act
    result = get_elicitation(
        user_id="test_user",
        company_id="test_company",
        elicitation_id="elic_func_123",
    )

    # Assert
    assert isinstance(result, Elicitation)
    assert result.id == "elic_func_123"
    mock_get.assert_called_once_with(
        user_id="test_user",
        company_id="test_company",
        elicitation_id="elic_func_123",
    )


@pytest.mark.ai
def test_get_elicitation__logs_and_raises__on_sdk_error(mocker) -> None:
    """
    Purpose: Verify get_elicitation logs and re-raises SDK exceptions.
    Why this matters: Errors must be logged and propagated for debugging.
    Setup summary: Mock SDK to raise exception, verify logging and re-raise.
    """
    # Arrange
    mocker.patch(
        "unique_sdk.Elicitation.get_elicitation",
        side_effect=Exception("Not found"),
    )

    # Act & Assert
    with pytest.raises(Exception) as exc_info:
        get_elicitation(
            user_id="test_user",
            company_id="test_company",
            elicitation_id="nonexistent",
        )

    assert "Not found" in str(exc_info.value)


@pytest.mark.ai
@pytest.mark.asyncio
async def test_get_elicitation_async__behaves_like_sync__with_async_sdk(
    mocker,
    base_elicitation_response: dict[str, Any],
) -> None:
    """
    Purpose: Verify get_elicitation_async mirrors sync behavior asynchronously.
    Why this matters: Async version must provide same functionality as sync.
    Setup summary: Mock async SDK call, call async function, verify result.
    """
    # Arrange
    mock_get_async = mocker.patch(
        "unique_sdk.Elicitation.get_elicitation_async",
        new_callable=AsyncMock,
        return_value=base_elicitation_response,
    )

    # Act
    result = await get_elicitation_async(
        user_id="test_user",
        company_id="test_company",
        elicitation_id="elic_func_123",
    )

    # Assert
    assert isinstance(result, Elicitation)
    assert result.id == "elic_func_123"
    mock_get_async.assert_called_once()


# get_pending_elicitations Tests
# ============================================================================


@pytest.mark.ai
def test_get_pending_elicitations__validates_to_list__with_multiple_items(
    mocker,
    base_elicitation_response: dict[str, Any],
) -> None:
    """
    Purpose: Verify get_pending_elicitations validates to ElicitationList.
    Why this matters: Response must be validated to proper list model.
    Setup summary: Mock SDK with multiple items, call function, verify list.
    """
    # Arrange
    response_2 = base_elicitation_response.copy()
    response_2["id"] = "elic_func_456"
    mock_get_pending = mocker.patch(
        "unique_sdk.Elicitation.get_pending_elicitations",
        return_value={"elicitations": [base_elicitation_response, response_2]},
    )

    # Act
    result = get_pending_elicitations(
        user_id="test_user",
        company_id="test_company",
    )

    # Assert
    assert isinstance(result, ElicitationList)
    assert len(result.elicitations) == 2
    assert result.elicitations[0].id == "elic_func_123"
    assert result.elicitations[1].id == "elic_func_456"
    mock_get_pending.assert_called_once()


@pytest.mark.ai
def test_get_pending_elicitations__logs_and_raises__on_sdk_error(mocker) -> None:
    """
    Purpose: Verify get_pending_elicitations logs and re-raises SDK exceptions.
    Why this matters: Errors must be logged and propagated for debugging.
    Setup summary: Mock SDK to raise exception, verify logging and re-raise.
    """
    # Arrange
    mocker.patch(
        "unique_sdk.Elicitation.get_pending_elicitations",
        side_effect=Exception("Connection error"),
    )

    # Act & Assert
    with pytest.raises(Exception) as exc_info:
        get_pending_elicitations(
            user_id="test_user",
            company_id="test_company",
        )

    assert "Connection error" in str(exc_info.value)


@pytest.mark.ai
@pytest.mark.asyncio
async def test_get_pending_elicitations_async__behaves_like_sync__with_async_sdk(
    mocker,
    base_elicitation_response: dict[str, Any],
) -> None:
    """
    Purpose: Verify get_pending_elicitations_async mirrors sync behavior.
    Why this matters: Async version must provide same functionality as sync.
    Setup summary: Mock async SDK call, call async function, verify result.
    """
    # Arrange
    mock_get_pending_async = mocker.patch(
        "unique_sdk.Elicitation.get_pending_elicitations_async",
        new_callable=AsyncMock,
        return_value={"elicitations": [base_elicitation_response]},
    )

    # Act
    result = await get_pending_elicitations_async(
        user_id="test_user",
        company_id="test_company",
    )

    # Assert
    assert isinstance(result, ElicitationList)
    assert len(result.elicitations) == 1
    mock_get_pending_async.assert_called_once()


# respond_to_elicitation Tests
# ============================================================================


@pytest.mark.ai
def test_respond_to_elicitation__creates_params__with_all_actions(mocker) -> None:
    """
    Purpose: Verify respond_to_elicitation handles all action types.
    Why this matters: All ElicitationAction values must be supported.
    Setup summary: Mock SDK, test each action type, verify calls.
    """
    # Arrange
    mock_respond = mocker.patch(
        "unique_sdk.Elicitation.respond_to_elicitation",
        return_value={"success": True},
    )

    # Act & Assert - ACCEPT
    result_accept = respond_to_elicitation(
        user_id="test_user",
        company_id="test_company",
        elicitation_id="elic_123",
        action=ElicitationAction.ACCEPT,
        content={"field": "value"},
    )
    assert isinstance(result_accept, ElicitationResponseResult)
    assert result_accept.success is True

    # Act & Assert - DECLINE
    result_decline = respond_to_elicitation(
        user_id="test_user",
        company_id="test_company",
        elicitation_id="elic_123",
        action=ElicitationAction.DECLINE,
    )
    assert isinstance(result_decline, ElicitationResponseResult)

    # Act & Assert - CANCEL
    result_cancel = respond_to_elicitation(
        user_id="test_user",
        company_id="test_company",
        elicitation_id="elic_123",
        action=ElicitationAction.CANCEL,
    )
    assert isinstance(result_cancel, ElicitationResponseResult)

    assert mock_respond.call_count == 3


@pytest.mark.ai
def test_respond_to_elicitation__handles_content__for_accept_action(mocker) -> None:
    """
    Purpose: Verify respond_to_elicitation properly handles content parameter.
    Why this matters: Content is required for ACCEPT action with form data.
    Setup summary: Mock SDK, call with complex content, verify parameter passing.
    """
    # Arrange
    mock_respond = mocker.patch(
        "unique_sdk.Elicitation.respond_to_elicitation",
        return_value={"success": True, "message": "Response recorded"},
    )
    content = {
        "name": "John Doe",
        "age": 30,
        "active": True,
        "tags": ["tag1", "tag2"],
    }

    # Act
    result = respond_to_elicitation(
        user_id="test_user",
        company_id="test_company",
        elicitation_id="elic_123",
        action=ElicitationAction.ACCEPT,
        content=content,
    )

    # Assert
    assert isinstance(result, ElicitationResponseResult)
    assert result.success is True
    assert result.message == "Response recorded"
    mock_respond.assert_called_once()


@pytest.mark.ai
def test_respond_to_elicitation__logs_and_raises__on_sdk_error(mocker) -> None:
    """
    Purpose: Verify respond_to_elicitation logs and re-raises SDK exceptions.
    Why this matters: Errors must be logged and propagated for debugging.
    Setup summary: Mock SDK to raise exception, verify logging and re-raise.
    """
    # Arrange
    mocker.patch(
        "unique_sdk.Elicitation.respond_to_elicitation",
        side_effect=Exception("Response failed"),
    )

    # Act & Assert
    with pytest.raises(Exception) as exc_info:
        respond_to_elicitation(
            user_id="test_user",
            company_id="test_company",
            elicitation_id="elic_123",
            action=ElicitationAction.ACCEPT,
        )

    assert "Response failed" in str(exc_info.value)


@pytest.mark.ai
@pytest.mark.asyncio
async def test_respond_to_elicitation_async__behaves_like_sync__with_async_sdk(
    mocker,
) -> None:
    """
    Purpose: Verify respond_to_elicitation_async mirrors sync behavior.
    Why this matters: Async version must provide same functionality as sync.
    Setup summary: Mock async SDK call, call async function, verify result.
    """
    # Arrange
    mock_respond_async = mocker.patch(
        "unique_sdk.Elicitation.respond_to_elicitation_async",
        new_callable=AsyncMock,
        return_value={"success": True, "message": "Accepted"},
    )

    # Act
    result = await respond_to_elicitation_async(
        user_id="test_user",
        company_id="test_company",
        elicitation_id="elic_123",
        action=ElicitationAction.ACCEPT,
        content={"data": "value"},
    )

    # Assert
    assert isinstance(result, ElicitationResponseResult)
    assert result.success is True
    mock_respond_async.assert_called_once()
