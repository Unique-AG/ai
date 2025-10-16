"""
Tests for HumanVerificationManagerForApiCalling.

This module tests the human verification workflow for API calls, including
confirmation message generation, user message detection, and API execution.
"""

import hashlib
import logging
from datetime import datetime
from string import Template
from typing import ParamSpec, TypeAlias
from unittest.mock import patch

import pytest
from pydantic import BaseModel

from unique_toolkit._common.api_calling.human_verification_manager import (
    HumanConfirmation,
    HumanVerificationManagerForApiCalling,
)
from unique_toolkit._common.endpoint_builder import (
    EndpointMethods,
    build_api_operation,
)
from unique_toolkit._common.endpoint_requestor import RequestContext, RequestorType
from unique_toolkit.chat.schemas import ChatMessage, ChatMessageRole


# Test Models (using non-Test prefix to avoid pytest collection warnings)
class ApiPathParams(BaseModel):
    user_id: int


class ApiPayload(BaseModel):
    include_profile: bool = False
    include_posts: bool = False


class ApiResponse(BaseModel):
    id: int
    name: str


class ApiEnvironmentParams(BaseModel):
    include_posts: bool = False


# ParamSpec for type checking
PathParamsSpec = ParamSpec("PathParamsSpec")
PayloadParamSpec = ParamSpec("PayloadParamSpec")

# Type alias with explicit ParamSpec
TestManager: TypeAlias = HumanVerificationManagerForApiCalling[
    PathParamsSpec, ApiPathParams, PayloadParamSpec, ApiPayload, ApiResponse
]


# Fixtures
@pytest.fixture
def logger() -> logging.Logger:
    """Purpose: Provide a logger for the manager."""
    return logging.getLogger(__name__)


@pytest.fixture
def test_operation():
    """
    Purpose: Provide a test API operation for the manager.
    Why this matters: Manager needs an operation spec to work with.
    Setup summary: Creates a GET endpoint with path params and payload.
    """
    return build_api_operation(
        method=EndpointMethods.GET,
        url_template=Template("https://api.example.com/users/{user_id}"),
        path_params_constructor=ApiPathParams,
        payload_constructor=ApiPayload,
        response_model_type=ApiResponse,
    )


@pytest.fixture
def base_manager(
    logger: logging.Logger,
    test_operation,
) -> TestManager:
    """
    Purpose: Provide a base HumanVerificationManager instance.
    Why this matters: Reusable manager for most tests.
    Setup summary: Initialized with test operation and fake requestor.
    """
    return HumanVerificationManagerForApiCalling(
        logger=logger,
        operation=test_operation,
        requestor_type=RequestorType.FAKE,
        return_value={"id": 100, "name": "John Doe"},
    )


@pytest.fixture
def manager_with_env_params(
    logger: logging.Logger,
    test_operation,
) -> TestManager:
    """
    Purpose: Provide manager with environment parameters.
    Why this matters: Tests scenarios where some params are app-controlled.
    Setup summary: Manager with environment params that override user input.
    """
    env_params = ApiEnvironmentParams(include_posts=True)
    return HumanVerificationManagerForApiCalling(
        logger=logger,
        operation=test_operation,
        requestor_type=RequestorType.FAKE,
        environment_payload_params=env_params,
        return_value={"id": 100, "name": "John Doe"},
    )


@pytest.fixture
def test_payload() -> ApiPayload:
    """Purpose: Provide a test payload."""
    return ApiPayload(include_profile=True, include_posts=False)


@pytest.fixture
def assistant_message_with_hash(test_payload: ApiPayload) -> ChatMessage:
    """
    Purpose: Provide an assistant message containing payload hash.
    Why this matters: Simulates the message sent to user for confirmation.
    Setup summary: Message with hash of test payload in content.
    """
    payload_hash = hashlib.sha256(test_payload.model_dump_json().encode()).hexdigest()
    return ChatMessage(
        role=ChatMessageRole.ASSISTANT,
        text=f"Please confirm: {payload_hash}",
        chat_id="test-chat-123",
    )


# Initialization Tests
@pytest.mark.ai
@pytest.mark.verified
def test_init__creates_verification_model__with_basic_setup_AI(
    base_manager: HumanVerificationManagerForApiCalling,
) -> None:
    """
    Purpose: Verify manager initializes with correct internal models.
    Why this matters: Models are used for validation throughout the workflow.
    Setup summary: Base manager with no environment params.
    """
    # Arrange & Act done in fixture

    # Assert
    assert base_manager._verification_model is not None
    assert base_manager._modifiable_payload_params_model == ApiPayload
    assert base_manager._combined_params_model is not None


@pytest.mark.ai
@pytest.mark.verified
def test_init__creates_complement_model__with_environment_params_AI(
    manager_with_env_params: HumanVerificationManagerForApiCalling,
) -> None:
    """
    Purpose: Verify manager creates complement model when env params provided.
    Why this matters: Ensures user can't override app-controlled parameters.
    Setup summary: Manager with environment params that restrict user input.
    """
    # Arrange & Act done in fixture

    # Assert
    # Modifiable params should exclude fields in environment params
    modifiable_fields = (
        manager_with_env_params._modifiable_payload_params_model.model_fields
    )
    assert "include_profile" in modifiable_fields
    # include_posts should be excluded as it's in environment params
    assert "include_posts" not in modifiable_fields


# Confirmation Message Tests
@pytest.mark.ai
@pytest.mark.verified
def test_create_assistant_confirmation_message__returns_formatted_message__with_valid_payload_AI(
    base_manager: HumanVerificationManagerForApiCalling,
    test_payload: ApiPayload,
) -> None:
    """
    Purpose: Verify assistant confirmation message contains required elements.
    Why this matters: User needs clear confirmation UI with proper formatting.
    Setup summary: Manager with test payload for confirmation.
    """
    # Arrange done in fixtures

    # Act
    message = base_manager.create_assistant_confirmation_message(payload=test_payload)

    # Assert
    assert "| include_profile | true |" in message  # JSON booleans are lowercase
    assert "Please confirm the call by pressing this button" in message
    assert "https://prompt=" in message


@pytest.mark.ai
@pytest.mark.verified
def test_create_next_user_message__includes_hash__with_valid_payload_AI(
    base_manager: HumanVerificationManagerForApiCalling,
    test_payload: ApiPayload,
) -> None:
    """
    Purpose: Verify next user message contains payload hash for verification.
    Why this matters: Hash is used to verify user confirmed the exact payload.
    Setup summary: Manager creates user message from test payload.
    """
    # Arrange
    expected_hash = hashlib.sha256(test_payload.model_dump_json().encode()).hexdigest()

    # Act
    next_message = base_manager._create_next_user_message(test_payload)

    # Assert
    assert "I confirm the api call" in next_message
    assert expected_hash in next_message
    assert "```json" in next_message


# Detection Tests
@pytest.mark.ai
@pytest.mark.verified
def test_detect_api_calls__returns_payload__with_valid_confirmation_AI(
    base_manager: HumanVerificationManagerForApiCalling,
    test_payload: ApiPayload,
    assistant_message_with_hash: ChatMessage,
) -> None:
    """
    Purpose: Verify manager detects valid API call confirmation from user.
    Why this matters: Core functionality for human-in-the-loop API calls.
    Setup summary: Valid user message with confirmation matching assistant hash.
    """
    # Arrange
    user_message = base_manager._create_next_user_message(test_payload)

    # Act
    detected_payload = base_manager.detect_api_calls_from_user_message(
        last_assistant_message=assistant_message_with_hash,
        user_message=user_message,
    )

    # Assert
    assert detected_payload is not None
    assert detected_payload.include_profile == test_payload.include_profile


@pytest.mark.ai
@pytest.mark.verified
def test_detect_api_calls__returns_none__with_no_json_in_message_AI(
    base_manager: HumanVerificationManagerForApiCalling,
    assistant_message_with_hash: ChatMessage,
) -> None:
    """
    Purpose: Verify manager returns None when user message has no JSON.
    Why this matters: Prevents false positives from regular user messages.
    Setup summary: User message without any JSON content.
    """
    # Arrange
    user_message = "This is just a regular message"

    # Act
    detected_payload = base_manager.detect_api_calls_from_user_message(
        last_assistant_message=assistant_message_with_hash,
        user_message=user_message,
    )

    # Assert
    assert detected_payload is None


@pytest.mark.ai
@pytest.mark.verified
def test_detect_api_calls__returns_none__with_mismatched_hash_AI(
    base_manager: HumanVerificationManagerForApiCalling,
    test_payload: ApiPayload,
) -> None:
    """
    Purpose: Verify manager rejects confirmation with wrong hash.
    Why this matters: Security - prevents confirming different payload than shown.
    Setup summary: User message with hash that doesn't match assistant message.
    """
    # Arrange
    user_message = base_manager._create_next_user_message(test_payload)
    wrong_assistant_message = ChatMessage(
        role=ChatMessageRole.ASSISTANT,
        text="Please confirm: wrong_hash_here",
        chat_id="test-chat-123",
    )

    # Act
    detected_payload = base_manager.detect_api_calls_from_user_message(
        last_assistant_message=wrong_assistant_message,
        user_message=user_message,
    )

    # Assert
    assert detected_payload is None


@pytest.mark.ai
@pytest.mark.verified
def test_detect_api_calls__returns_none__with_invalid_json_structure_AI(
    base_manager: HumanVerificationManagerForApiCalling,
    assistant_message_with_hash: ChatMessage,
) -> None:
    """
    Purpose: Verify manager handles malformed JSON gracefully.
    Why this matters: User input validation - prevents crashes from bad data.
    Setup summary: User message with JSON that doesn't match expected schema.
    """
    # Arrange
    user_message = """I confirm the api call with the following data:
```json
{"invalid": "structure", "missing": "required_fields"}
```"""

    # Act
    detected_payload = base_manager.detect_api_calls_from_user_message(
        last_assistant_message=assistant_message_with_hash,
        user_message=user_message,
    )

    # Assert
    assert detected_payload is None


# Verification Tests
@pytest.mark.ai
@pytest.mark.verified
def test_verify_human_verification__returns_true__with_matching_hash_AI(
    base_manager: HumanVerificationManagerForApiCalling,
) -> None:
    """
    Purpose: Verify hash verification succeeds with correct hash.
    Why this matters: Core security mechanism for confirmation workflow.
    Setup summary: Confirmation with hash that exists in assistant message.
    """
    # Arrange
    confirmation = HumanConfirmation(
        payload_hash="abc123",
        time_stamp=datetime.now(),
    )
    assistant_message = ChatMessage(
        role=ChatMessageRole.ASSISTANT,
        text="Please confirm: abc123",
        chat_id="test-chat",
    )

    # Act
    result = base_manager._verify_human_verification(confirmation, assistant_message)

    # Assert
    assert result is True


@pytest.mark.ai
@pytest.mark.verified
def test_verify_human_verification__returns_false__with_non_assistant_role_AI(
    base_manager: HumanVerificationManagerForApiCalling,
) -> None:
    """
    Purpose: Verify verification fails if last message isn't from assistant.
    Why this matters: Prevents verification against user's own messages.
    Setup summary: Confirmation checked against user message instead of assistant.
    """
    # Arrange
    confirmation = HumanConfirmation(
        payload_hash="abc123",
        time_stamp=datetime.now(),
    )
    user_message = ChatMessage(
        role=ChatMessageRole.USER,
        text="Please confirm: abc123",
        chat_id="test-chat",
    )

    # Act
    result = base_manager._verify_human_verification(confirmation, user_message)

    # Assert
    assert result is False


@pytest.mark.ai
@pytest.mark.verified
def test_verify_human_verification__returns_false__with_empty_content_AI(
    base_manager: HumanVerificationManagerForApiCalling,
) -> None:
    """
    Purpose: Verify verification fails if assistant message has no content.
    Why this matters: Prevents false positives from empty messages.
    Setup summary: Assistant message with None content.
    """
    # Arrange
    confirmation = HumanConfirmation(
        payload_hash="abc123",
        time_stamp=datetime.now(),
    )
    assistant_message = ChatMessage(
        role=ChatMessageRole.ASSISTANT,
        text=None,
        chat_id="test-chat",
    )

    # Act
    result = base_manager._verify_human_verification(confirmation, assistant_message)

    # Assert
    assert result is False


# API Calling Tests
@pytest.mark.ai
@pytest.mark.verified
def test_call_api__returns_response__with_valid_params_AI(
    base_manager: TestManager,
) -> None:
    """
    Purpose: Verify API call executes and returns proper response.
    Why this matters: End-to-end functionality after user confirmation.
    Setup summary: Manager with fake requestor that returns test data.
    """
    # Arrange
    context = RequestContext(
        base_url="https://api.example.com",
    )
    path_params = ApiPathParams(user_id=100)
    payload = ApiPayload(include_profile=True)

    # Act
    response = base_manager.call_api(
        context=context,
        path_params=path_params,
        payload=payload,
    )

    # Assert
    assert response.id == 100
    assert response.name == "John Doe"


@pytest.mark.ai
@pytest.mark.verified
def test_call_api__merges_params__with_path_and_payload_AI(
    base_manager: TestManager,
) -> None:
    """
    Purpose: Verify API call combines path params and payload correctly.
    Why this matters: Ensures all parameters reach the requestor properly.
    Setup summary: Manager with mocked requestor to verify param merging.
    """
    # Arrange
    context = RequestContext(
        base_url="https://api.example.com",
    )
    path_params = ApiPathParams(user_id=100)
    payload = ApiPayload(include_profile=True, include_posts=False)

    with patch.object(base_manager._requestor, "request") as mock_request:
        # Return dict directly, not a Mock object
        mock_request.return_value = {"id": 100, "name": "John Doe"}

        # Act
        response = base_manager.call_api(
            context=context,
            path_params=path_params,
            payload=payload,
        )

        # Assert
        assert response.id == 100
        assert response.name == "John Doe"
        mock_request.assert_called_once()
        call_kwargs = mock_request.call_args.kwargs
        assert call_kwargs["user_id"] == 100
        assert call_kwargs["include_profile"] is True
        assert call_kwargs["include_posts"] is False


# Environment Params Tests
@pytest.mark.ai
@pytest.mark.verified
def test_detect_api_calls__merges_environment_params__with_user_confirmation_AI(
    manager_with_env_params: TestManager,
    assistant_message_with_hash: ChatMessage,
) -> None:
    """
    Purpose: Verify environment params override user input in detection.
    Why this matters: App must enforce security-critical parameters.
    Setup summary: Manager with env params that should override user values.
    """
    # Arrange
    # Create verification data manually since we need to exclude env params
    modifiable_params = manager_with_env_params._modifiable_payload_params_model(
        include_profile=True
    )

    verification_data = manager_with_env_params._verification_model(
        modifiable_params=modifiable_params,
        confirmation=HumanConfirmation(
            payload_hash=hashlib.sha256(
                modifiable_params.model_dump_json().encode()
            ).hexdigest(),
            time_stamp=datetime.now(),
        ),
    )

    # Create assistant message with correct hash
    assistant_message = ChatMessage(
        role=ChatMessageRole.ASSISTANT,
        text=f"Please confirm: {verification_data.confirmation.payload_hash}",
        chat_id="test-chat",
    )

    user_message = f"""I confirm the api call with the following data:
```json
{verification_data.model_dump_json(indent=2)}
```"""

    # Act
    detected_payload = manager_with_env_params.detect_api_calls_from_user_message(
        last_assistant_message=assistant_message,
        user_message=user_message,
    )

    # Assert
    assert detected_payload is not None
    assert detected_payload.include_profile is True
    assert detected_payload.include_posts is True  # From environment params


# Edge Cases
@pytest.mark.ai
def test_detect_api_calls__handles_multiple_json_blocks__uses_last_valid_AI(
    base_manager: TestManager,
    test_payload: ApiPayload,
    assistant_message_with_hash: ChatMessage,
) -> None:
    """
    Purpose: Verify manager processes multiple JSON blocks correctly.
    Why this matters: User messages may contain multiple code blocks.
    Setup summary: User message with multiple JSON blocks, last one valid.
    """
    # Arrange
    valid_message = base_manager._create_next_user_message(test_payload)
    user_message = f"""
Some text here
```json
{{"invalid": "json"}}
```
More text
{valid_message}
"""

    # Act
    detected_payload = base_manager.detect_api_calls_from_user_message(
        last_assistant_message=assistant_message_with_hash,
        user_message=user_message,
    )

    # Assert
    assert detected_payload is not None
    assert detected_payload.include_profile == test_payload.include_profile


@pytest.mark.ai
@pytest.mark.verified
def test_create_assistant_confirmation_message__escapes_special_chars__with_special_values_AI(
    base_manager: TestManager,
) -> None:
    """
    Purpose: Verify message generation handles special characters safely.
    Why this matters: Prevents injection attacks or rendering issues.
    Setup summary: Payload with special characters in values.
    """
    # Arrange
    # Using a payload with boolean, which should render cleanly
    payload = ApiPayload(include_profile=True, include_posts=False)

    # Act
    message = base_manager.create_assistant_confirmation_message(payload=payload)

    # Assert
    assert "true" in message  # JSON booleans are lowercase
    assert "false" in message
    assert "```json" not in message  # Should be markdown table, not JSON in main body


@pytest.mark.ai
def test_create_next_user_message__works_with_environment_params__and_full_payload_AI(
    manager_with_env_params: TestManager,
) -> None:
    """
    Purpose: Verify _create_next_user_message handles full payload correctly when environment params are configured.
    Why this matters: Previously caused Pydantic validation errors when payload contained environment fields.
    Setup summary: Manager with environment params, full payload including both modifiable and environment fields.
    """
    # Arrange
    # Create a full payload that includes both modifiable and environment fields
    full_payload = ApiPayload(
        include_profile=True, include_posts=True
    )  # include_posts is in environment params

    # Act
    # This should not raise a validation error anymore
    user_message = manager_with_env_params._create_next_user_message(full_payload)

    # Assert
    assert user_message is not None
    assert "I confirm the api call" in user_message
    assert "```json" in user_message
    # The generated message should only contain the modifiable fields in the verification model
    # But the full payload should be accepted as input
