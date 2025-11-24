"""Tests for webhook signature verification module."""

import hashlib
import hmac
import time

import pytest

from unique_toolkit.app.webhook import is_webhook_signature_valid


@pytest.fixture
def valid_secret() -> str:
    """Fixture providing a valid endpoint secret for tests."""
    return "test-endpoint-secret-12345"


@pytest.fixture
def valid_payload() -> bytes:
    """Fixture providing a valid payload for tests."""
    return b'{"event": "test.event", "id": "test-id"}'


@pytest.fixture
def valid_timestamp() -> int:
    """Fixture providing a valid timestamp for tests."""
    return int(time.time())


def generate_signature(payload: bytes, secret: str) -> str:
    """Helper function to generate a valid webhook signature."""
    message = payload.decode("utf-8") if isinstance(payload, bytes) else payload
    return hmac.new(
        secret.encode("utf-8"),
        msg=message.encode("utf-8"),
        digestmod=hashlib.sha256,
    ).hexdigest()


@pytest.mark.ai
def test_is_webhook_signature_valid__returns_true__with_valid_signature(
    valid_secret: str, valid_payload: bytes, valid_timestamp: int
) -> None:
    """
    Purpose: Verify is_webhook_signature_valid returns True with valid signature and timestamp.
    Why this matters: Ensures legitimate webhook requests are accepted.
    Setup summary: Generate valid signature, create headers with signature and timestamp, assert True.
    """
    # Arrange
    signature = generate_signature(valid_payload, valid_secret)
    headers = {
        "X-Unique-Signature": signature,
        "X-Unique-Created-At": str(valid_timestamp),
    }
    # Act
    result = is_webhook_signature_valid(
        headers=headers, payload=valid_payload, endpoint_secret=valid_secret
    )
    # Assert
    assert result is True


@pytest.mark.ai
def test_is_webhook_signature_valid__returns_false__when_signature_missing(
    valid_secret: str, valid_payload: bytes, valid_timestamp: int
) -> None:
    """
    Purpose: Verify is_webhook_signature_valid returns False when signature header is missing.
    Why this matters: Prevents processing of requests without authentication.
    Setup summary: Create headers without signature, assert False.
    """
    # Arrange
    headers = {"X-Unique-Created-At": str(valid_timestamp)}
    # Act
    result = is_webhook_signature_valid(
        headers=headers, payload=valid_payload, endpoint_secret=valid_secret
    )
    # Assert
    assert result is False


@pytest.mark.ai
def test_is_webhook_signature_valid__returns_false__when_timestamp_missing(
    valid_secret: str, valid_payload: bytes
) -> None:
    """
    Purpose: Verify is_webhook_signature_valid returns False when timestamp header is missing.
    Why this matters: Prevents processing of requests without timestamp for replay protection.
    Setup summary: Create headers without timestamp, assert False.
    """
    # Arrange
    signature = generate_signature(valid_payload, valid_secret)
    headers = {"X-Unique-Signature": signature}
    # Act
    result = is_webhook_signature_valid(
        headers=headers, payload=valid_payload, endpoint_secret=valid_secret
    )
    # Assert
    assert result is False


@pytest.mark.ai
def test_is_webhook_signature_valid__returns_false__when_signature_invalid(
    valid_secret: str, valid_payload: bytes, valid_timestamp: int
) -> None:
    """
    Purpose: Verify is_webhook_signature_valid returns False when signature doesn't match.
    Why this matters: Prevents processing of tampered or unauthorized requests.
    Setup summary: Create headers with invalid signature, assert False.
    """
    # Arrange
    headers = {
        "X-Unique-Signature": "invalid-signature-12345",
        "X-Unique-Created-At": str(valid_timestamp),
    }
    # Act
    result = is_webhook_signature_valid(
        headers=headers, payload=valid_payload, endpoint_secret=valid_secret
    )
    # Assert
    assert result is False


@pytest.mark.ai
def test_is_webhook_signature_valid__returns_false__when_timestamp_invalid_format(
    valid_secret: str, valid_payload: bytes
) -> None:
    """
    Purpose: Verify is_webhook_signature_valid returns False when timestamp is not a valid integer.
    Why this matters: Prevents processing of requests with malformed timestamps.
    Setup summary: Create headers with non-numeric timestamp, assert False.
    """
    # Arrange
    signature = generate_signature(valid_payload, valid_secret)
    headers = {
        "X-Unique-Signature": signature,
        "X-Unique-Created-At": "not-a-number",
    }
    # Act
    result = is_webhook_signature_valid(
        headers=headers, payload=valid_payload, endpoint_secret=valid_secret
    )
    # Assert
    assert result is False


@pytest.mark.ai
def test_is_webhook_signature_valid__returns_false__when_timestamp_too_old(
    valid_secret: str, valid_payload: bytes
) -> None:
    """
    Purpose: Verify is_webhook_signature_valid returns False when timestamp is outside tolerance.
    Why this matters: Prevents replay attacks using old requests.
    Setup summary: Create headers with old timestamp (beyond default 300s tolerance), assert False.
    """
    # Arrange
    old_timestamp = int(time.time()) - 400  # 400 seconds ago
    signature = generate_signature(valid_payload, valid_secret)
    headers = {
        "X-Unique-Signature": signature,
        "X-Unique-Created-At": str(old_timestamp),
    }
    # Act
    result = is_webhook_signature_valid(
        headers=headers, payload=valid_payload, endpoint_secret=valid_secret
    )
    # Assert
    assert result is False


@pytest.mark.ai
def test_is_webhook_signature_valid__returns_true__when_timestamp_within_tolerance(
    valid_secret: str, valid_payload: bytes
) -> None:
    """
    Purpose: Verify is_webhook_signature_valid returns True when timestamp is within tolerance.
    Why this matters: Allows legitimate requests with slight clock skew.
    Setup summary: Create headers with recent timestamp (within 300s), assert True.
    """
    # Arrange
    recent_timestamp = int(time.time()) - 100  # 100 seconds ago, within tolerance
    signature = generate_signature(valid_payload, valid_secret)
    headers = {
        "X-Unique-Signature": signature,
        "X-Unique-Created-At": str(recent_timestamp),
    }
    # Act
    result = is_webhook_signature_valid(
        headers=headers, payload=valid_payload, endpoint_secret=valid_secret
    )
    # Assert
    assert result is True


@pytest.mark.ai
def test_is_webhook_signature_valid__returns_true__with_custom_tolerance(
    valid_secret: str, valid_payload: bytes
) -> None:
    """
    Purpose: Verify is_webhook_signature_valid respects custom tolerance parameter.
    Why this matters: Enables flexible timestamp validation for different use cases.
    Setup summary: Create headers with timestamp outside default tolerance but within custom tolerance, assert True.
    """
    # Arrange
    custom_tolerance = 600  # 10 minutes
    old_timestamp = int(time.time()) - 400  # 400 seconds ago
    signature = generate_signature(valid_payload, valid_secret)
    headers = {
        "X-Unique-Signature": signature,
        "X-Unique-Created-At": str(old_timestamp),
    }
    # Act
    result = is_webhook_signature_valid(
        headers=headers,
        payload=valid_payload,
        endpoint_secret=valid_secret,
        tolerance=custom_tolerance,
    )
    # Assert
    assert result is True


@pytest.mark.ai
def test_is_webhook_signature_valid__returns_false__with_custom_tolerance_exceeded(
    valid_secret: str, valid_payload: bytes
) -> None:
    """
    Purpose: Verify is_webhook_signature_valid rejects timestamps outside custom tolerance.
    Why this matters: Ensures custom tolerance limits are enforced.
    Setup summary: Create headers with timestamp beyond custom tolerance, assert False.
    """
    # Arrange
    custom_tolerance = 100  # 100 seconds
    old_timestamp = int(time.time()) - 200  # 200 seconds ago, beyond tolerance
    signature = generate_signature(valid_payload, valid_secret)
    headers = {
        "X-Unique-Signature": signature,
        "X-Unique-Created-At": str(old_timestamp),
    }
    # Act
    result = is_webhook_signature_valid(
        headers=headers,
        payload=valid_payload,
        endpoint_secret=valid_secret,
        tolerance=custom_tolerance,
    )
    # Assert
    assert result is False


@pytest.mark.ai
def test_is_webhook_signature_valid__handles_case_insensitive_headers(
    valid_secret: str, valid_payload: bytes, valid_timestamp: int
) -> None:
    """
    Purpose: Verify is_webhook_signature_valid handles case-insensitive header names.
    Why this matters: Ensures compatibility with different HTTP client implementations.
    Setup summary: Create headers with lowercase header names, assert True.
    """
    # Arrange
    signature = generate_signature(valid_payload, valid_secret)
    headers = {
        "x-unique-signature": signature,
        "x-unique-created-at": str(valid_timestamp),
    }
    # Act
    result = is_webhook_signature_valid(
        headers=headers, payload=valid_payload, endpoint_secret=valid_secret
    )
    # Assert
    assert result is True


@pytest.mark.ai
def test_is_webhook_signature_valid__handles_utf8_payload(
    valid_secret: str, valid_timestamp: int
) -> None:
    """
    Purpose: Verify is_webhook_signature_valid handles UTF-8 encoded payload correctly.
    Why this matters: Ensures compatibility with different payload encodings.
    Setup summary: Create UTF-8 payload, generate signature, assert True.
    """
    # Arrange
    payload_bytes = '{"event": "test.event", "id": "test-id"}'.encode("utf-8")
    signature = generate_signature(payload_bytes, valid_secret)
    headers = {
        "X-Unique-Signature": signature,
        "X-Unique-Created-At": str(valid_timestamp),
    }
    # Act
    result = is_webhook_signature_valid(
        headers=headers, payload=payload_bytes, endpoint_secret=valid_secret
    )
    # Assert
    assert result is True


@pytest.mark.ai
def test_is_webhook_signature_valid__handles_empty_payload(
    valid_secret: str, valid_timestamp: int
) -> None:
    """
    Purpose: Verify is_webhook_signature_valid handles empty payload correctly.
    Why this matters: Ensures edge case handling for minimal requests.
    Setup summary: Create empty payload, generate signature, assert True.
    """
    # Arrange
    empty_payload = b""
    signature = generate_signature(empty_payload, valid_secret)
    headers = {
        "X-Unique-Signature": signature,
        "X-Unique-Created-At": str(valid_timestamp),
    }
    # Act
    result = is_webhook_signature_valid(
        headers=headers, payload=empty_payload, endpoint_secret=valid_secret
    )
    # Assert
    assert result is True


@pytest.mark.ai
def test_is_webhook_signature_valid__handles_zero_tolerance(
    valid_secret: str, valid_payload: bytes
) -> None:
    """
    Purpose: Verify is_webhook_signature_valid handles zero tolerance (disables timestamp check).
    Why this matters: Enables flexibility for testing or special use cases.
    Setup summary: Create headers with very old timestamp but zero tolerance, assert True.
    """
    # Arrange
    very_old_timestamp = int(time.time()) - 10000  # Very old
    signature = generate_signature(valid_payload, valid_secret)
    headers = {
        "X-Unique-Signature": signature,
        "X-Unique-Created-At": str(very_old_timestamp),
    }
    # Act
    result = is_webhook_signature_valid(
        headers=headers,
        payload=valid_payload,
        endpoint_secret=valid_secret,
        tolerance=0,
    )
    # Assert
    assert result is True


@pytest.mark.ai
@pytest.mark.parametrize(
    "header_name",
    ["X-Unique-Signature", "x-unique-signature"],
    ids=["standard", "lowercase"],
)
def test_is_webhook_signature_valid__handles_various_signature_header_cases(
    valid_secret: str, valid_payload: bytes, valid_timestamp: int, header_name: str
) -> None:
    """
    Purpose: Verify is_webhook_signature_valid handles case-insensitive signature header matching.
    Why this matters: Ensures robust header name matching for supported cases.
    Setup summary: Test with standard and lowercase variations of signature header name, assert True for all.
    """
    # Arrange
    signature = generate_signature(valid_payload, valid_secret)
    headers = {header_name: signature, "X-Unique-Created-At": str(valid_timestamp)}
    # Act
    result = is_webhook_signature_valid(
        headers=headers, payload=valid_payload, endpoint_secret=valid_secret
    )
    # Assert
    assert result is True


@pytest.mark.ai
@pytest.mark.parametrize(
    "header_name",
    ["X-Unique-Created-At", "x-unique-created-at"],
    ids=["standard", "lowercase"],
)
def test_is_webhook_signature_valid__handles_various_timestamp_header_cases(
    valid_secret: str, valid_payload: bytes, valid_timestamp: int, header_name: str
) -> None:
    """
    Purpose: Verify is_webhook_signature_valid handles case-insensitive timestamp header matching.
    Why this matters: Ensures robust header name matching for supported cases.
    Setup summary: Test with standard and lowercase variations of timestamp header name, assert True for all.
    """
    # Arrange
    signature = generate_signature(valid_payload, valid_secret)
    headers = {"X-Unique-Signature": signature, header_name: str(valid_timestamp)}
    # Act
    result = is_webhook_signature_valid(
        headers=headers, payload=valid_payload, endpoint_secret=valid_secret
    )
    # Assert
    assert result is True
