import logging
from typing import Optional

import unique_sdk

from unique_toolkit.event.schema import Event


class WebhookVerificationError(Exception):
    """Custom exception for webhook verification errors."""
    pass

def verify_signature_and_construct_event(
    headers: dict[str, str],
    payload: bytes,
    endpoint_secret: str,
    logger: Optional[logging.Logger] = logging.getLogger(__name__),
):
    """
    Verify the signature of a webhook and construct an event object.

    Args:
        headers (Dict[str, str]): The headers of the webhook request.
        payload (bytes): The raw payload of the webhook request.
        endpoint_secret (str): The secret used to verify the webhook signature.
        logger (logging.Logger): A logger instance for logging messages.

    Returns:
        Union[Event, Tuple[Dict[str, bool], int]]: 
            If successful, returns an Event object.
            If unsuccessful, returns a tuple with an error response and HTTP status code.

    Raises:
        WebhookVerificationError: If there's an error during verification or event construction.
    """

    # Only verify the event if there is an endpoint secret defined
    # Otherwise use the basic event deserialized with json
    sig_header = headers.get("X-Unique-Signature")
    timestamp = headers.get("X-Unique-Created-At")

    if not sig_header or not timestamp:
        logger.error("⚠️  Webhook signature or timestamp headers missing.")
        raise WebhookVerificationError("Signature or timestamp headers missing")

    try:
        event = unique_sdk.Webhook.construct_event(
            payload,
            sig_header,
            timestamp,
            endpoint_secret,
        )
        logger.info("✅  Webhook signature verification successful.")
        return Event(**event)
    except unique_sdk.SignatureVerificationError as e:
        logger.error("⚠️  Webhook signature verification failed. " + str(e))
        raise WebhookVerificationError(f"Signature verification failed: {str(e)}")
        
