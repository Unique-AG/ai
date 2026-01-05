import hashlib
import hmac
import json
import time
from collections import OrderedDict
from typing import Union

import unique_sdk
from unique_sdk.api_resources._event import Event


class Webhook:
    DEFAULT_TOLERANCE = 300

    @staticmethod
    def construct_event(
        message: Union[str, bytes],
        sig_header: str,
        timestamp: Union[str, int],
        secret: str,
        tolerance=DEFAULT_TOLERANCE,
    ):
        if isinstance(message, bytes) and hasattr(message, "decode"):
            message = message.decode("utf-8")

        if isinstance(timestamp, str):
            try:
                timestamp = int(timestamp)
            except ValueError:
                raise unique_sdk.SignatureVerificationError(
                    "Invalid timestamp (%s). Timestamp must be an integer." % timestamp,
                    sig_header,
                    message,
                )

        WebhookSignature.verify_header(
            message,  # type: ignore
            sig_header,
            timestamp,
            secret,
            tolerance,
        )

        data = json.loads(message, object_pairs_hook=OrderedDict)
        event = Event.construct_from(
            data, user_id=data["userId"], company_id=data["companyId"]
        )

        return event


class WebhookSignature:
    @staticmethod
    def _compute_signature(payload: str, secret: str):
        mac = hmac.new(
            secret.encode("utf-8"),
            msg=payload.encode("utf-8"),
            digestmod=hashlib.sha256,
        )
        return mac.hexdigest()

    @classmethod
    def verify_header(
        cls,
        message: str,
        signature: str,
        timestamp: int,
        secret: str,
        tolerance: int = 0,
    ):
        if not signature:
            raise unique_sdk.SignatureVerificationError(
                "Signature header is missing.",
                message,
            )

        if not timestamp:
            raise unique_sdk.SignatureVerificationError(
                "Timestamp header is missing.",
                message,
            )

        expected_signature = cls._compute_signature(message, secret)

        if not hmac.compare_digest(expected_signature, signature):
            raise unique_sdk.SignatureVerificationError(
                "No signatures found matching the expected signature for payload. "
                "Are you passing the raw body you received from Unique? "
                "https://unique.ch/docs/webhooks/signatures",
                signature,
                message,
            )

        if tolerance and timestamp < time.time() - tolerance:
            raise unique_sdk.SignatureVerificationError(
                "Timestamp outside the tolerance zone (%d)" % timestamp,
                signature,
                message,
            )

        return True
