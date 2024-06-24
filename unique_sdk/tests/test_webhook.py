import time

import pytest

import unique_sdk

DUMMY_WEBHOOK_PAYLOAD = """{
  "id": "evt_test_webhook",
  "object": "event"
}"""

DUMMY_WEBHOOK_SECRET = "whsec_test_secret"


def generate_signature(payload: str, secret=DUMMY_WEBHOOK_SECRET):
    return unique_sdk.WebhookSignature._compute_signature(
        payload=payload, secret=secret
    )


class TestWebhookSignature(object):
    def test_raise_on_timestamp_outside_tolerance(self):
        signature = generate_signature(DUMMY_WEBHOOK_PAYLOAD)
        timestamp = int(time.time()) - 15

        with pytest.raises(
            unique_sdk.SignatureVerificationError,
            match="Timestamp outside the tolerance zone",
        ):
            unique_sdk.WebhookSignature.verify_header(
                DUMMY_WEBHOOK_PAYLOAD,
                signature,
                timestamp,
                DUMMY_WEBHOOK_SECRET,
                tolerance=10,
            )
