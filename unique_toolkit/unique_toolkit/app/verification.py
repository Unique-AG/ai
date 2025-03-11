import json
import logging
import os
from typing import Callable, TypeVar

import unique_sdk
from pydantic import ValidationError

from unique_toolkit.app.schemas import Event

logger = logging.getLogger(f"toolkit.{__name__}")


class WebhookVerificationError(Exception):
    """Custom exception for webhook verification errors."""

    pass


T = TypeVar("T")


def verify_signature_and_construct_event(
    headers: dict[str, str],
    payload: bytes,
    endpoint_secret: str,
    logger: logging.Logger = logger,
    event_constructor: Callable[..., T] = Event,
) -> T:
    """
    Verify the signature of a webhook and construct an event object.

    Args:
        headers (Dict[str, str]): The headers of the webhook request.
        payload (bytes): The raw payload of the webhook request.
        endpoint_secret (str): The secret used to verify the webhook signature.
        logger (logging.Logger): A logger instance for logging messages.
        event_constructor (Callable[..., T]): A callable that constructs an event object.
    Returns:
        T: The constructed event object.

    Raises:
        WebhookVerificationError: If there's an error during verification or event construction.
    """

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
        return event_constructor(**event)
    except unique_sdk.SignatureVerificationError as e:
        logger.error("⚠️  Webhook signature verification failed. " + str(e))
        raise WebhookVerificationError(f"Signature verification failed: {str(e)}")


def verify_request_and_construct_event(
    assistant_name: str,
    payload: bytes,
    headers: dict[str, str],
    event_constructor: Callable[..., Event] = Event,
) -> tuple[str, int] | tuple[Event, int]:
    """Check the payload, authenticate and genenrate the event if the payload is correct"""
    logger.info(f"{assistant_name} - received request")

    try:
        payload_decoded = json.loads(payload)
    except json.decoder.JSONDecodeError as e:
        logger.error(f"Error decoding payload: {e}", exc_info=True)
        return "Invalid payload", 400

    endpoint_secret = os.environ.get("ENDPOINT_SECRET", None)
    if endpoint_secret:
        response = verify_signature_and_construct_event(
            headers=headers,  # type: ignore
            payload=payload,
            endpoint_secret=endpoint_secret,
            logger=logger,
            event_constructor=event_constructor,
        )
        if isinstance(response, tuple):
            return response  # Error response
        event = response  # This is an event since it is not a tuple
    else:
        try:
            event = event_constructor(**payload_decoded)
        except ValidationError as e:
            # pydantic errors https://docs.pydantic.dev/2.10/errors/errors/
            logger.error(f"Validation error with model: {e.json()}", exc_info=True)
            raise ValidationError(e)
        except ValueError as e:
            logger.error(f"Error deserializing event: {e}", exc_info=True)
            return "Invalid event", 400

    if not event.payload.name == assistant_name:
        logger.error(
            f"{assistant_name}: Incorrect assistant: {event.payload.name}: Expected {assistant_name}"
        )
        return f"Not {assistant_name} event", 400

    logger.info(f"{assistant_name} - received event")
    return event, 200
