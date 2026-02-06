"""
Tests for elicitation schemas.

This test suite validates the Pydantic models and enums used in the elicitation
module:
1. Enum classes (ElicitationObject, ElicitationMode, ElicitationAction, etc.)
2. Elicitation model with field validation and serialization
3. ElicitationResponseResult, ElicitationList models
4. CreateElicitationParams, RespondToElicitationParams models
"""

from datetime import datetime

import pytest

from unique_toolkit.elicitation.schemas import (
    CreateElicitationParams,
    Elicitation,
    ElicitationAction,
    ElicitationList,
    ElicitationMode,
    ElicitationObject,
    ElicitationResponseResult,
    ElicitationSource,
    ElicitationStatus,
    RespondToElicitationParams,
)

# Enum Tests
# ============================================================================


@pytest.mark.ai
def test_elicitation_object__has_expected_value__enum_definition() -> None:
    """
    Purpose: Verify ElicitationObject enum has correct value.
    Why this matters: Enum must match API contract.
    Setup summary: Access enum value, verify string representation.
    """
    # Arrange & Act & Assert
    assert ElicitationObject.ELICITATION == "elicitation"


@pytest.mark.ai
def test_elicitation_mode__has_all_expected_values__enum_definition() -> None:
    """
    Purpose: Verify ElicitationMode enum has FORM and URL values.
    Why this matters: All supported modes must be defined.
    Setup summary: Access enum values, verify string representations.
    """
    # Arrange & Act & Assert
    assert ElicitationMode.FORM == "FORM"
    assert ElicitationMode.URL == "URL"


@pytest.mark.ai
def test_elicitation_action__has_all_expected_values__enum_definition() -> None:
    """
    Purpose: Verify ElicitationAction enum has all action types.
    Why this matters: All supported actions must be defined.
    Setup summary: Access enum values, verify string representations.
    """
    # Arrange & Act & Assert
    assert ElicitationAction.ACCEPT == "ACCEPT"
    assert ElicitationAction.DECLINE == "DECLINE"
    assert ElicitationAction.CANCEL == "CANCEL"


@pytest.mark.ai
def test_elicitation_status__has_all_expected_values__enum_definition() -> None:
    """
    Purpose: Verify ElicitationStatus enum has all status types.
    Why this matters: All possible statuses must be defined.
    Setup summary: Access enum values, verify string representations.
    """
    # Arrange & Act & Assert
    assert ElicitationStatus.PENDING == "PENDING"
    assert ElicitationStatus.ACCEPTED == "ACCEPTED"
    assert ElicitationStatus.DECLINED == "DECLINED"
    assert ElicitationStatus.CANCELLED == "CANCELLED"
    assert ElicitationStatus.EXPIRED == "EXPIRED"


@pytest.mark.ai
def test_elicitation_source__has_all_expected_values__enum_definition() -> None:
    """
    Purpose: Verify ElicitationSource enum has API and MCP values.
    Why this matters: All supported sources must be defined.
    Setup summary: Access enum values, verify string representations.
    """
    # Arrange & Act & Assert
    assert ElicitationSource.API == "INTERNAL_TOOL"
    assert ElicitationSource.MCP == "MCP_SERVER"


# Elicitation Model Tests
# ============================================================================


@pytest.mark.ai
def test_elicitation__validates_with_required_fields__model_creation() -> None:
    """
    Purpose: Verify Elicitation model validates with all required fields.
    Why this matters: Model must accept valid data with required fields.
    Setup summary: Create model with required fields, verify validation.
    """
    # Arrange
    data = {
        "id": "elic_test123",
        "object": "elicitation",
        "source": "INTERNAL_TOOL",
        "mode": "FORM",
        "status": "PENDING",
        "message": "Please provide input",
        "companyId": "test_company",
        "userId": "test_user",
        "createdAt": "2024-01-01T00:00:00",
    }

    # Act
    elicitation = Elicitation.model_validate(data, by_alias=True)

    # Assert
    assert elicitation.id == "elic_test123"
    assert elicitation.object == ElicitationObject.ELICITATION
    assert elicitation.mode == ElicitationMode.FORM
    assert elicitation.status == ElicitationStatus.PENDING
    assert elicitation.company_id == "test_company"
    assert elicitation.user_id == "test_user"


@pytest.mark.ai
def test_elicitation__uses_camelcase_aliases__model_config() -> None:
    """
    Purpose: Verify Elicitation model uses camelCase aliases for serialization.
    Why this matters: API contract requires camelCase field names.
    Setup summary: Create model, dump with aliases, verify camelCase keys.
    """
    # Arrange
    elicitation = Elicitation(
        id="elic_123",
        object=ElicitationObject.ELICITATION,
        source=ElicitationSource.API,
        mode=ElicitationMode.FORM,
        status=ElicitationStatus.PENDING,
        message="Test",
        company_id="test_company",
        user_id="test_user",
        created_at=datetime(2024, 1, 1),
    )

    # Act
    data = elicitation.model_dump(by_alias=True, exclude_none=True)

    # Assert
    assert "companyId" in data
    assert "userId" in data
    assert "createdAt" in data
    assert "company_id" not in data


@pytest.mark.ai
def test_elicitation__uses_schema_alias__for_json_schema_field() -> None:
    """
    Purpose: Verify json_schema field uses "schema" alias in serialization.
    Why this matters: API expects "schema" not "jsonSchema" or "json_schema".
    Setup summary: Create model with json_schema, verify alias in dump.
    """
    # Arrange
    data = {
        "id": "elic_123",
        "object": "elicitation",
        "source": "INTERNAL_TOOL",
        "mode": "FORM",
        "status": "PENDING",
        "message": "Test",
        "schema": {"type": "object"},
        "companyId": "test_company",
        "userId": "test_user",
        "createdAt": "2024-01-01T00:00:00",
    }

    # Act
    elicitation = Elicitation.model_validate(data, by_alias=True)
    dumped = elicitation.model_dump(by_alias=True, exclude_none=True)

    # Assert
    assert elicitation.json_schema == {"type": "object"}
    assert "schema" in dumped
    assert dumped["schema"] == {"type": "object"}


@pytest.mark.ai
def test_elicitation__serializes_datetime__to_iso_format() -> None:
    """
    Purpose: Verify Elicitation serializes datetime fields to ISO format strings.
    Why this matters: API requires ISO 8601 datetime format.
    Setup summary: Create model with datetime, dump, verify ISO string format.
    """
    # Arrange
    elicitation = Elicitation(
        id="elic_123",
        object=ElicitationObject.ELICITATION,
        source=ElicitationSource.API,
        mode=ElicitationMode.FORM,
        status=ElicitationStatus.ACCEPTED,
        message="Test",
        company_id="test_company",
        user_id="test_user",
        created_at=datetime(2024, 1, 15, 10, 30, 45),
        responded_at=datetime(2024, 1, 15, 11, 0, 0),
    )

    # Act
    data = elicitation.model_dump(by_alias=True, mode="json")

    # Assert
    assert data["createdAt"] == "2024-01-15T10:30:45"
    assert data["respondedAt"] == "2024-01-15T11:00:00"


@pytest.mark.ai
def test_elicitation__validates_url_field__as_anyurl() -> None:
    """
    Purpose: Verify url field validates as AnyUrl type.
    Why this matters: URL must be properly validated as valid URL format.
    Setup summary: Create model with valid URL, verify validation.
    """
    # Arrange
    data = {
        "id": "elic_123",
        "object": "elicitation",
        "source": "INTERNAL_TOOL",
        "mode": "URL",
        "status": "PENDING",
        "message": "Fill form",
        "url": "https://example.com/form",
        "companyId": "test_company",
        "userId": "test_user",
        "createdAt": "2024-01-01T00:00:00",
    }

    # Act
    elicitation = Elicitation.model_validate(data, by_alias=True)

    # Assert
    assert str(elicitation.url) == "https://example.com/form"


@pytest.mark.ai
def test_elicitation__allows_optional_fields__to_be_none() -> None:
    """
    Purpose: Verify Elicitation allows optional fields to be None.
    Why this matters: Optional fields must not be required for validation.
    Setup summary: Create model without optional fields, verify None values.
    """
    # Arrange
    data = {
        "id": "elic_123",
        "object": "elicitation",
        "source": "INTERNAL_TOOL",
        "mode": "FORM",
        "status": "PENDING",
        "message": "Test",
        "companyId": "test_company",
        "userId": "test_user",
        "createdAt": "2024-01-01T00:00:00",
    }

    # Act
    elicitation = Elicitation.model_validate(data, by_alias=True)

    # Assert
    assert elicitation.mcp_server_id is None
    assert elicitation.tool_name is None
    assert elicitation.json_schema is None
    assert elicitation.url is None
    assert elicitation.chat_id is None
    assert elicitation.message_id is None


# ElicitationResponseResult Model Tests
# ============================================================================


@pytest.mark.ai
def test_elicitation_response_result__validates_with_success__required_field() -> None:
    """
    Purpose: Verify ElicitationResponseResult validates with success field.
    Why this matters: Model must work with minimum required fields.
    Setup summary: Create model with only success, verify validation.
    """
    # Arrange & Act
    result = ElicitationResponseResult(success=True)

    # Assert
    assert result.success is True
    assert result.message is None


@pytest.mark.ai
def test_elicitation_response_result__includes_optional_message__field() -> None:
    """
    Purpose: Verify ElicitationResponseResult accepts optional message.
    Why this matters: Message field provides additional response context.
    Setup summary: Create model with message, verify both fields.
    """
    # Arrange & Act
    result = ElicitationResponseResult(success=False, message="Error occurred")

    # Assert
    assert result.success is False
    assert result.message == "Error occurred"


@pytest.mark.ai
def test_elicitation_response_result__uses_camelcase__in_serialization() -> None:
    """
    Purpose: Verify ElicitationResponseResult uses camelCase for API.
    Why this matters: API contract requires camelCase field names.
    Setup summary: Create model, dump with aliases, verify no snake_case.
    """
    # Arrange
    result = ElicitationResponseResult(success=True, message="Success")

    # Act
    data = result.model_dump(by_alias=True)

    # Assert
    assert "success" in data
    assert "message" in data


# ElicitationList Model Tests
# ============================================================================


@pytest.mark.ai
def test_elicitation_list__validates_with_empty_list__default_value() -> None:
    """
    Purpose: Verify ElicitationList validates with empty elicitations list.
    Why this matters: Model must handle case with no pending elicitations.
    Setup summary: Create model with empty list, verify validation.
    """
    # Arrange & Act
    elicitation_list = ElicitationList(elicitations=[])

    # Assert
    assert isinstance(elicitation_list.elicitations, list)
    assert len(elicitation_list.elicitations) == 0


@pytest.mark.ai
def test_elicitation_list__validates_list_of_elicitations__complex_data() -> None:
    """
    Purpose: Verify ElicitationList validates list of Elicitation objects.
    Why this matters: Model must properly validate nested elicitation data.
    Setup summary: Create model with multiple elicitations, verify list.
    """
    # Arrange
    elicitation_1 = Elicitation(
        id="elic_1",
        object=ElicitationObject.ELICITATION,
        source=ElicitationSource.API,
        mode=ElicitationMode.FORM,
        status=ElicitationStatus.PENDING,
        message="First",
        company_id="test_company",
        user_id="test_user",
        created_at=datetime.now(),
    )
    elicitation_2 = Elicitation(
        id="elic_2",
        object=ElicitationObject.ELICITATION,
        source=ElicitationSource.MCP,
        mode=ElicitationMode.URL,
        status=ElicitationStatus.PENDING,
        message="Second",
        company_id="test_company",
        user_id="test_user",
        created_at=datetime.now(),
    )

    # Act
    elicitation_list = ElicitationList(elicitations=[elicitation_1, elicitation_2])

    # Assert
    assert len(elicitation_list.elicitations) == 2
    assert elicitation_list.elicitations[0].id == "elic_1"
    assert elicitation_list.elicitations[1].id == "elic_2"


# CreateElicitationParams Model Tests
# ============================================================================


@pytest.mark.ai
def test_create_elicitation_params__validates_with_required_fields__model_creation() -> (
    None
):
    """
    Purpose: Verify CreateElicitationParams validates with required fields.
    Why this matters: Model must accept minimum required parameters.
    Setup summary: Create params with required fields, verify validation.
    """
    # Arrange & Act
    params = CreateElicitationParams(
        mode=ElicitationMode.FORM,
        message="Test message",
        tool_name="test_tool",
    )

    # Assert
    assert params.mode == ElicitationMode.FORM
    assert params.message == "Test message"
    assert params.tool_name == "test_tool"


@pytest.mark.ai
def test_create_elicitation_params__uses_schema_alias__for_json_schema() -> None:
    """
    Purpose: Verify json_schema field uses "schema" alias in params.
    Why this matters: API expects "schema" key for json_schema field.
    Setup summary: Create params with json_schema, verify alias in dump.
    """
    # Arrange
    params = CreateElicitationParams(
        mode=ElicitationMode.FORM,
        message="Test",
        tool_name="test_tool",
        json_schema={"type": "object", "properties": {}},
    )

    # Act
    data = params.model_dump(by_alias=True, exclude_none=True)

    # Assert
    assert "schema" in data
    assert "jsonSchema" not in data
    assert "json_schema" not in data


@pytest.mark.ai
def test_create_elicitation_params__converts_url_string__to_anyurl() -> None:
    """
    Purpose: Verify url parameter converts string to AnyUrl type.
    Why this matters: URL validation must happen at param creation.
    Setup summary: Create params with URL string, verify AnyUrl type.
    """
    # Arrange & Act
    params = CreateElicitationParams(
        mode=ElicitationMode.URL,
        message="Fill form",
        tool_name="test_tool",
        url="https://example.com/form",
    )

    # Assert
    assert str(params.url) == "https://example.com/form"


@pytest.mark.ai
def test_create_elicitation_params__excludes_none__in_model_dump() -> None:
    """
    Purpose: Verify model_dump excludes None values for optional fields.
    Why this matters: API should not receive null values for unset fields.
    Setup summary: Create params without optional fields, dump, verify no nulls.
    """
    # Arrange
    params = CreateElicitationParams(
        mode=ElicitationMode.FORM,
        message="Test",
        tool_name="test_tool",
    )

    # Act
    data = params.model_dump(by_alias=True, exclude_none=True)

    # Assert
    assert "externalElicitationId" not in data
    assert "chatId" not in data
    assert "messageId" not in data
    assert "expiresInSeconds" not in data
    assert "metadata" not in data


@pytest.mark.ai
def test_create_elicitation_params__includes_all_optional_fields__when_provided() -> (
    None
):
    """
    Purpose: Verify all optional fields are included when provided.
    Why this matters: All parameters must be properly serialized.
    Setup summary: Create params with all fields, dump, verify all present.
    """
    # Arrange
    params = CreateElicitationParams(
        mode=ElicitationMode.FORM,
        message="Test",
        tool_name="test_tool",
        json_schema={"type": "object"},
        external_elicitation_id="ext_123",
        chat_id="chat_123",
        message_id="msg_123",
        expires_in_seconds=3600,
        metadata={"key": "value"},
    )

    # Act
    data = params.model_dump(by_alias=True, exclude_none=True)

    # Assert
    assert "externalElicitationId" in data
    assert "chatId" in data
    assert "messageId" in data
    assert "expiresInSeconds" in data
    assert "metadata" in data


# RespondToElicitationParams Model Tests
# ============================================================================


@pytest.mark.ai
def test_respond_to_elicitation_params__validates_with_required_fields__model_creation() -> (
    None
):
    """
    Purpose: Verify RespondToElicitationParams validates with required fields.
    Why this matters: Model must accept minimum required response parameters.
    Setup summary: Create params without content, verify validation.
    """
    # Arrange & Act
    params = RespondToElicitationParams(
        elicitation_id="elic_123",
        action=ElicitationAction.DECLINE,
    )

    # Assert
    assert params.elicitation_id == "elic_123"
    assert params.action == ElicitationAction.DECLINE
    assert params.content is None


@pytest.mark.ai
def test_respond_to_elicitation_params__accepts_content__for_accept_action() -> None:
    """
    Purpose: Verify content field accepts dict with multiple types.
    Why this matters: Content must support str, int, bool, list types.
    Setup summary: Create params with complex content, verify validation.
    """
    # Arrange
    content: dict[str, str | int | bool | list[str]] = {
        "name": "John",
        "age": 30,
        "active": True,
        "tags": ["tag1", "tag2"],
    }

    # Act
    params = RespondToElicitationParams(
        elicitation_id="elic_123",
        action=ElicitationAction.ACCEPT,
        content=content,
    )

    # Assert
    assert params.content is not None
    assert params.content["name"] == "John"
    assert params.content["age"] == 30
    assert params.content["active"] is True
    assert params.content["tags"] == ["tag1", "tag2"]


@pytest.mark.ai
def test_respond_to_elicitation_params__uses_camelcase__in_serialization() -> None:
    """
    Purpose: Verify RespondToElicitationParams uses camelCase for API.
    Why this matters: API contract requires camelCase field names.
    Setup summary: Create params, dump with aliases, verify camelCase keys.
    """
    # Arrange
    params = RespondToElicitationParams(
        elicitation_id="elic_123",
        action=ElicitationAction.ACCEPT,
        content={"field": "value"},
    )

    # Act
    data = params.model_dump(by_alias=True, exclude_none=True)

    # Assert
    assert "elicitationId" in data
    assert "action" in data
    assert "content" in data
    assert "elicitation_id" not in data
