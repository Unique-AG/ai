"""
Tests for elicitation exceptions.

This test suite validates the exception classes used in the elicitation module:
1. Base _ElicitationException
2. ElicitationDeclinedException
3. ElicitationCancelledException
4. ElicitationExpiredException
5. ElicitationFailedException
"""

import pytest

from unique_toolkit.elicitation.exceptions import (
    ElicitationCancelledException,
    ElicitationDeclinedException,
    ElicitationExpiredException,
    ElicitationFailedException,
    _ElicitationException,
)

# Base Exception Tests
# ============================================================================


@pytest.mark.ai
def test_elicitation_exception__creates_with_context__message_formatting() -> None:
    """
    Purpose: Verify _ElicitationException formats message with context.
    Why this matters: Context provides debugging information for failures.
    Setup summary: Create exception with context, verify message format.
    """
    # Arrange
    context = "Tool xyz failed"

    # Act
    exception = _ElicitationException(context=context)

    # Assert
    message = str(exception)
    assert "Exception Context: Tool xyz failed" in message
    assert "Instruction:" in message


@pytest.mark.ai
def test_elicitation_exception__creates_without_context__instruction_only() -> None:
    """
    Purpose: Verify _ElicitationException works without context.
    Why this matters: Context is optional, instruction alone should work.
    Setup summary: Create exception without context, verify message.
    """
    # Arrange & Act
    exception = _ElicitationException()

    # Assert
    message = str(exception)
    assert "Exception Context:" not in message
    assert "Instruction:" in message
    assert "failed to finish the elicitation process" in message


@pytest.mark.ai
def test_elicitation_exception__has_default_instruction__class_attribute() -> None:
    """
    Purpose: Verify _ElicitationException has default INSTRUCTION attribute.
    Why this matters: Default instruction provides guidance to AI/users.
    Setup summary: Access INSTRUCTION attribute, verify content.
    """
    # Arrange & Act & Assert
    assert hasattr(_ElicitationException, "INSTRUCTION")
    assert (
        "failed to finish the elicitation process" in _ElicitationException.INSTRUCTION
    )
    assert "inform the user" in _ElicitationException.INSTRUCTION.lower()


@pytest.mark.ai
def test_elicitation_exception__accepts_custom_instruction__override() -> None:
    """
    Purpose: Verify _ElicitationException accepts custom instruction.
    Why this matters: Subclasses should be able to customize instructions.
    Setup summary: Create exception with custom instruction, verify message.
    """
    # Arrange
    custom_instruction = "Custom guidance for this error"

    # Act
    exception = _ElicitationException(
        context="Test context",
        instruction=custom_instruction,
    )

    # Assert
    message = str(exception)
    assert "Custom guidance for this error" in message


# ElicitationDeclinedException Tests
# ============================================================================


@pytest.mark.ai
def test_elicitation_declined_exception__has_specific_instruction__class_attribute() -> (
    None
):
    """
    Purpose: Verify ElicitationDeclinedException has decline-specific instruction.
    Why this matters: Instruction must guide user on declined elicitation.
    Setup summary: Access INSTRUCTION attribute, verify decline content.
    """
    # Arrange & Act & Assert
    assert hasattr(ElicitationDeclinedException, "INSTRUCTION")
    assert "declined" in ElicitationDeclinedException.INSTRUCTION.lower()
    assert "chose not to provide" in ElicitationDeclinedException.INSTRUCTION.lower()


@pytest.mark.ai
def test_elicitation_declined_exception__creates_with_context__message() -> None:
    """
    Purpose: Verify ElicitationDeclinedException formats message with context.
    Why this matters: Exception must provide specific context for decline.
    Setup summary: Create exception with context, verify message.
    """
    # Arrange
    context = "User declined form submission"

    # Act
    exception = ElicitationDeclinedException(context=context)

    # Assert
    message = str(exception)
    assert "Exception Context: User declined form submission" in message
    assert "declined the elicitation request" in message


@pytest.mark.ai
def test_elicitation_declined_exception__inherits_from_base__exception_hierarchy() -> (
    None
):
    """
    Purpose: Verify ElicitationDeclinedException inherits from base exception.
    Why this matters: Exception hierarchy must be correct for catching.
    Setup summary: Create exception, verify isinstance check.
    """
    # Arrange & Act
    exception = ElicitationDeclinedException()

    # Assert
    assert isinstance(exception, _ElicitationException)
    assert isinstance(exception, Exception)


# ElicitationCancelledException Tests
# ============================================================================


@pytest.mark.ai
def test_elicitation_cancelled_exception__has_specific_instruction__class_attribute() -> (
    None
):
    """
    Purpose: Verify ElicitationCancelledException has cancel-specific instruction.
    Why this matters: Instruction must guide user on cancelled elicitation.
    Setup summary: Access INSTRUCTION attribute, verify cancel content.
    """
    # Arrange & Act & Assert
    assert hasattr(ElicitationCancelledException, "INSTRUCTION")
    assert "cancelled" in ElicitationCancelledException.INSTRUCTION.lower()
    assert "chose not to provide" in ElicitationCancelledException.INSTRUCTION.lower()


@pytest.mark.ai
def test_elicitation_cancelled_exception__creates_with_context__message() -> None:
    """
    Purpose: Verify ElicitationCancelledException formats message with context.
    Why this matters: Exception must provide specific context for cancellation.
    Setup summary: Create exception with context, verify message.
    """
    # Arrange
    context = "User cancelled authentication flow"

    # Act
    exception = ElicitationCancelledException(context=context)

    # Assert
    message = str(exception)
    assert "Exception Context: User cancelled authentication flow" in message
    assert "cancelled the elicitation request" in message


@pytest.mark.ai
def test_elicitation_cancelled_exception__inherits_from_base__exception_hierarchy() -> (
    None
):
    """
    Purpose: Verify ElicitationCancelledException inherits from base exception.
    Why this matters: Exception hierarchy must be correct for catching.
    Setup summary: Create exception, verify isinstance check.
    """
    # Arrange & Act
    exception = ElicitationCancelledException()

    # Assert
    assert isinstance(exception, _ElicitationException)
    assert isinstance(exception, Exception)


# ElicitationExpiredException Tests
# ============================================================================


@pytest.mark.ai
def test_elicitation_expired_exception__has_specific_instruction__class_attribute() -> (
    None
):
    """
    Purpose: Verify ElicitationExpiredException has expire-specific instruction.
    Why this matters: Instruction must guide user on expired elicitation.
    Setup summary: Access INSTRUCTION attribute, verify expire content.
    """
    # Arrange & Act & Assert
    assert hasattr(ElicitationExpiredException, "INSTRUCTION")
    assert "expired" in ElicitationExpiredException.INSTRUCTION.lower()
    assert "timed out" in ElicitationExpiredException.INSTRUCTION.lower()


@pytest.mark.ai
def test_elicitation_expired_exception__creates_with_context__message() -> None:
    """
    Purpose: Verify ElicitationExpiredException formats message with context.
    Why this matters: Exception must provide specific context for expiration.
    Setup summary: Create exception with context, verify message.
    """
    # Arrange
    context = "Elicitation expired after 1 hour"

    # Act
    exception = ElicitationExpiredException(context=context)

    # Assert
    message = str(exception)
    assert "Exception Context: Elicitation expired after 1 hour" in message
    assert "expired without receiving a response" in message


@pytest.mark.ai
def test_elicitation_expired_exception__inherits_from_base__exception_hierarchy() -> (
    None
):
    """
    Purpose: Verify ElicitationExpiredException inherits from base exception.
    Why this matters: Exception hierarchy must be correct for catching.
    Setup summary: Create exception, verify isinstance check.
    """
    # Arrange & Act
    exception = ElicitationExpiredException()

    # Assert
    assert isinstance(exception, _ElicitationException)
    assert isinstance(exception, Exception)


# ElicitationFailedException Tests
# ============================================================================


@pytest.mark.ai
def test_elicitation_failed_exception__has_specific_instruction__class_attribute() -> (
    None
):
    """
    Purpose: Verify ElicitationFailedException has failure-specific instruction.
    Why this matters: Instruction must guide user on general failures.
    Setup summary: Access INSTRUCTION attribute, verify failure content.
    """
    # Arrange & Act & Assert
    assert hasattr(ElicitationFailedException, "INSTRUCTION")
    assert "failed" in ElicitationFailedException.INSTRUCTION.lower()
    assert (
        "issue obtaining the required information"
        in ElicitationFailedException.INSTRUCTION.lower()
    )


@pytest.mark.ai
def test_elicitation_failed_exception__creates_with_context__message() -> None:
    """
    Purpose: Verify ElicitationFailedException formats message with context.
    Why this matters: Exception must provide specific context for failures.
    Setup summary: Create exception with context, verify message.
    """
    # Arrange
    context = "Network error during elicitation creation"

    # Act
    exception = ElicitationFailedException(context=context)

    # Assert
    message = str(exception)
    assert "Exception Context: Network error during elicitation creation" in message
    assert "failed to be created or received a response" in message


@pytest.mark.ai
def test_elicitation_failed_exception__inherits_from_base__exception_hierarchy() -> (
    None
):
    """
    Purpose: Verify ElicitationFailedException inherits from base exception.
    Why this matters: Exception hierarchy must be correct for catching.
    Setup summary: Create exception, verify isinstance check.
    """
    # Arrange & Act
    exception = ElicitationFailedException()

    # Assert
    assert isinstance(exception, _ElicitationException)
    assert isinstance(exception, Exception)


# Edge Cases and Integration Tests
# ============================================================================


@pytest.mark.ai
def test_all_exceptions__are_catchable_as_base__exception_handling() -> None:
    """
    Purpose: Verify all elicitation exceptions can be caught as base type.
    Why this matters: Generic exception handling must work for all types.
    Setup summary: Raise each exception, catch as base, verify caught.
    """
    # Arrange
    exceptions = [
        ElicitationDeclinedException("test"),
        ElicitationCancelledException("test"),
        ElicitationExpiredException("test"),
        ElicitationFailedException("test"),
    ]

    # Act & Assert
    for exc in exceptions:
        with pytest.raises(_ElicitationException):
            raise exc


@pytest.mark.ai
def test_exception_message__includes_both_context_and_instruction__formatting() -> None:
    """
    Purpose: Verify exception message includes both context and instruction.
    Why this matters: Complete error information aids in debugging.
    Setup summary: Create exception with context, verify both parts in message.
    """
    # Arrange
    context = "API rate limit exceeded"

    # Act
    exception = ElicitationFailedException(context=context)
    message = str(exception)

    # Assert
    assert "Exception Context: API rate limit exceeded" in message
    assert "Instruction:" in message
    # Message should contain context and instruction parts
    assert "failed to be created or received a response" in message
