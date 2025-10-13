"""
Webhook signature verification for Unique platform.

Extracted from unique_sdk to provide standalone verification without event construction.
"""

import hashlib
import hmac
import logging
import time

_LOGGER = logging.getLogger(__name__)


def is_webhook_signature_valid(
    headers: dict[str, str],
    payload: bytes,
    endpoint_secret: str,
    tolerance: int = 300,
) -> bool:
    """
    Verify webhook signature from Unique platform.

    Args:
        headers: Request headers with X-Unique-Signature and X-Unique-Created-At
        payload: Raw request body bytes
        endpoint_secret: App endpoint secret from Unique platform
        tolerance: Max seconds between timestamp and now (default: 300)

    Returns:
        True if signature is valid, False otherwise
    """
    # Extract headers
    signature = headers.get("X-Unique-Signature") or headers.get("x-unique-signature")
    timestamp_str = headers.get("X-Unique-Created-At") or headers.get(
        "x-unique-created-at"
    )

    if not signature:
        _LOGGER.error("Missing X-Unique-Signature header")
        return False

    if not timestamp_str:
        _LOGGER.error("Missing X-Unique-Created-At header")
        return False

    # Convert timestamp to int
    try:
        timestamp = int(timestamp_str)
    except ValueError:
        _LOGGER.error(f"Invalid timestamp: {timestamp_str}")
        return False

    # Decode payload if bytes
    message = payload.decode("utf-8") if isinstance(payload, bytes) else payload

    # Compute expected signature: HMAC-SHA256(message, secret)
    expected_signature = hmac.new(
        endpoint_secret.encode("utf-8"),
        msg=message.encode("utf-8"),
        digestmod=hashlib.sha256,
    ).hexdigest()

    # Compare signatures (constant-time to prevent timing attacks)
    if not hmac.compare_digest(expected_signature, signature):
        _LOGGER.error("Signature mismatch. Ensure you're using the raw request body.")
        return False

    # Check timestamp tolerance (prevent replay attacks)
    if tolerance and timestamp < time.time() - tolerance:
        _LOGGER.error(
            f"Timestamp outside tolerance ({tolerance}s). Possible replay attack."
        )
        return False

    _LOGGER.debug("✅ Webhook signature verified successfully")
    return True
