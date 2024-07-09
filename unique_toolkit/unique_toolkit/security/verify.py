from http import HTTPStatus

import unique_sdk

from unique_toolkit.event.schema import Event


def verify_signature_and_construct_event(
    headers, payload: bytes, endpoint_secret: str, logger
) -> Event:
    sig_header = headers.get("X-Unique-Signature")
    timestamp = headers.get("X-Unique-Created-At")

    if not sig_header or not timestamp:
        logger.error("⚠️  Webhook signature or timestamp headers missing.")
        return False, HTTPStatus.BAD_REQUEST

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
        return False, HTTPStatus.BAD_REQUEST
