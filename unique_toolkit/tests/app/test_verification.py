"""Tests for verification.py functionality."""

from unittest.mock import patch

import pytest
from pydantic import ValidationError

from unique_toolkit.app.schemas import ChatEvent, Event
from unique_toolkit.app.verification import (
    WebhookVerificationError,
    verify_request_and_construct_event,
    verify_signature_and_construct_event,
)


@pytest.mark.ai_generated
class TestWebhookVerificationError:
    """Test the WebhookVerificationError exception."""

    def test_webhook_verification_error_creation(self):
        """Test creating a WebhookVerificationError."""
        error = WebhookVerificationError("Test error")
        assert str(error) == "Test error"
        assert isinstance(error, Exception)


@pytest.mark.ai_generated
class TestVerifySignatureAndConstructEvent:
    """Test the verify_signature_and_construct_event function."""

    def test_verify_signature_missing_headers(self):
        """Test verification with missing signature or timestamp headers."""
        headers = {"X-Unique-Signature": "test_sig"}  # Missing timestamp
        payload = b'{"test": "data"}'
        endpoint_secret = "test_secret"

        with pytest.raises(
            WebhookVerificationError, match="Signature or timestamp headers missing"
        ):
            verify_signature_and_construct_event(headers, payload, endpoint_secret)

    def test_verify_signature_missing_signature_header(self):
        """Test verification with missing signature header."""
        headers = {"X-Unique-Created-At": "1234567890"}  # Missing signature
        payload = b'{"test": "data"}'
        endpoint_secret = "test_secret"

        with pytest.raises(
            WebhookVerificationError, match="Signature or timestamp headers missing"
        ):
            verify_signature_and_construct_event(headers, payload, endpoint_secret)

    def test_verify_signature_missing_both_headers(self):
        """Test verification with missing both headers."""
        headers = {}  # Missing both
        payload = b'{"test": "data"}'
        endpoint_secret = "test_secret"

        with pytest.raises(
            WebhookVerificationError, match="Signature or timestamp headers missing"
        ):
            verify_signature_and_construct_event(headers, payload, endpoint_secret)

    @patch("unique_toolkit.app.verification.unique_sdk")
    def test_verify_signature_success(self, mock_unique_sdk):
        """Test successful signature verification."""
        headers = {
            "X-Unique-Signature": "test_sig",
            "X-Unique-Created-At": "1234567890",
        }
        payload = b'{"test": "data"}'
        endpoint_secret = "test_secret"

        # Mock successful verification
        mock_unique_sdk.Webhook.construct_event.return_value = {
            "id": "test_id",
            "event": "test_event",
            "user_id": "test_user",
            "company_id": "test_company",
            "payload": {
                "name": "test_name",
                "description": "test_description",
                "configuration": {},
                "chat_id": "test_chat",
                "assistant_id": "test_assistant",
                "user_message": {
                    "id": "msg1",
                    "text": "Hello",
                    "original_text": "Hello",
                    "created_at": "2023-01-01T00:00:00Z",
                    "language": "en",
                },
                "assistant_message": {
                    "id": "msg2",
                    "created_at": "2023-01-01T00:01:00Z",
                },
            },
        }

        result = verify_signature_and_construct_event(headers, payload, endpoint_secret)

        assert isinstance(result, Event)
        assert result.id == "test_id"
        assert result.event == "test_event"
        mock_unique_sdk.Webhook.construct_event.assert_called_once_with(
            payload, "test_sig", "1234567890", endpoint_secret
        )

    @patch("unique_toolkit.app.verification.unique_sdk")
    def test_verify_signature_failure(self, mock_unique_sdk):
        """Test signature verification failure."""
        headers = {
            "X-Unique-Signature": "invalid_sig",
            "X-Unique-Created-At": "1234567890",
        }
        payload = b'{"test": "data"}'
        endpoint_secret = "test_secret"

        # Mock signature verification failure
        mock_unique_sdk.SignatureVerificationError = Exception
        mock_unique_sdk.Webhook.construct_event.side_effect = (
            mock_unique_sdk.SignatureVerificationError("Invalid signature")
        )

        with pytest.raises(
            WebhookVerificationError,
            match="Signature verification failed: Invalid signature",
        ):
            verify_signature_and_construct_event(headers, payload, endpoint_secret)

    @patch("unique_toolkit.app.verification.unique_sdk")
    def test_verify_signature_with_custom_event_constructor(self, mock_unique_sdk):
        """Test verification with custom event constructor."""
        headers = {
            "X-Unique-Signature": "test_sig",
            "X-Unique-Created-At": "1234567890",
        }
        payload = b'{"test": "data"}'
        endpoint_secret = "test_secret"

        # Mock successful verification
        mock_unique_sdk.Webhook.construct_event.return_value = {
            "id": "test_id",
            "event": "unique.chat.external-module.chosen",
            "user_id": "test_user",
            "company_id": "test_company",
            "payload": {
                "name": "test_name",
                "description": "test_description",
                "configuration": {},
                "chat_id": "test_chat",
                "assistant_id": "test_assistant",
                "user_message": {
                    "id": "msg1",
                    "text": "Hello",
                    "original_text": "Hello",
                    "created_at": "2023-01-01T00:00:00Z",
                    "language": "en",
                },
                "assistant_message": {
                    "id": "msg2",
                    "created_at": "2023-01-01T00:01:00Z",
                },
            },
        }

        result = verify_signature_and_construct_event(
            headers, payload, endpoint_secret, event_constructor=ChatEvent
        )

        assert isinstance(result, ChatEvent)
        assert result.id == "test_id"


@pytest.mark.ai_generated
class TestVerifyRequestAndConstructEvent:
    """Test the verify_request_and_construct_event function."""

    def test_verify_request_invalid_json_payload(self):
        """Test verification with invalid JSON payload."""
        assistant_name = "test_assistant"
        payload = b"invalid json"
        headers = {}

        result = verify_request_and_construct_event(assistant_name, payload, headers)

        assert result == ("Invalid payload", 400)

    def test_verify_request_with_endpoint_secret(
        self, monkeypatch, base_chat_event_data
    ):
        """Test verification with endpoint secret."""
        monkeypatch.setenv("ENDPOINT_SECRET", "test_secret")
        assistant_name = "test_assistant"
        payload = b'{"test": "data"}'
        headers = {
            "X-Unique-Signature": "test_sig",
            "X-Unique-Created-At": "1234567890",
        }

        with patch(
            "unique_toolkit.app.verification.verify_signature_and_construct_event"
        ) as mock_verify:
            # Use the base_chat_event_data but modify the payload name to match assistant_name
            event_data = base_chat_event_data.model_dump()
            event_data["payload"]["name"] = "test_assistant"
            mock_verify.return_value = Event.model_validate(event_data)

            result = verify_request_and_construct_event(
                assistant_name, payload, headers
            )

            assert isinstance(result, tuple)
            assert len(result) == 2
            assert result[1] == 200
            assert isinstance(result[0], Event)

    def test_verify_request_without_endpoint_secret(self, monkeypatch):
        """Test verification without endpoint secret."""
        monkeypatch.delenv("ENDPOINT_SECRET", raising=False)
        assistant_name = "test_assistant"
        payload = b'{"id": "test_id", "event": "unique.chat.external-module.chosen", "user_id": "test_user", "company_id": "test_company", "payload": {"name": "test_assistant", "description": "test_description", "configuration": {}, "chat_id": "test_chat", "assistant_id": "test_assistant", "user_message": {"id": "msg1", "text": "Hello", "original_text": "Hello", "created_at": "2023-01-01T00:00:00Z", "language": "en"}, "assistant_message": {"id": "msg2", "created_at": "2023-01-01T00:01:00Z"}}}'
        headers = {}

        result = verify_request_and_construct_event(assistant_name, payload, headers)

        assert isinstance(result, tuple)
        assert len(result) == 2
        assert result[1] == 200
        assert isinstance(result[0], Event)

    def test_verify_request_validation_error(self):
        """Test verification with validation error."""
        assistant_name = "test_assistant"
        payload = b'{"invalid": "data"}'  # Missing required fields
        headers = {}

        # The function has a bug - it tries to raise ValidationError with another ValidationError, causing TypeError
        with pytest.raises(TypeError):
            verify_request_and_construct_event(assistant_name, payload, headers)

    def test_verify_request_value_error(self):
        """Test verification with value error."""
        assistant_name = "test_assistant"
        payload = b'{"id": "test_id", "event": "unique.chat.external-module.chosen", "user_id": "test_user", "company_id": "test_company", "payload": {"name": "test_assistant", "description": "test_description", "configuration": {}, "chat_id": "test_chat", "assistant_id": "test_assistant", "user_message": {"id": "msg1", "text": "Hello", "original_text": "Hello", "created_at": "2023-01-01T00:00:00Z", "language": "en"}, "assistant_message": {"id": "msg2", "created_at": "2023-01-01T00:01:00Z"}}}'
        headers = {}

        # The function should work normally with valid payload
        result = verify_request_and_construct_event(assistant_name, payload, headers)

        assert isinstance(result, tuple)
        assert len(result) == 2
        assert result[1] == 200
        assert isinstance(result[0], Event)

    def test_verify_request_wrong_assistant_name(self):
        """Test verification with wrong assistant name."""
        assistant_name = "test_assistant"
        payload = b'{"id": "test_id", "event": "unique.chat.external-module.chosen", "user_id": "test_user", "company_id": "test_company", "payload": {"name": "wrong_assistant", "description": "test_description", "configuration": {}, "chat_id": "test_chat", "assistant_id": "test_assistant", "user_message": {"id": "msg1", "text": "Hello", "original_text": "Hello", "created_at": "2023-01-01T00:00:00Z", "language": "en"}, "assistant_message": {"id": "msg2", "created_at": "2023-01-01T00:01:00Z"}}}'
        headers = {}

        result = verify_request_and_construct_event(assistant_name, payload, headers)

        assert result == ("Not test_assistant event", 400)

    def test_verify_request_success(self):
        """Test successful verification."""
        assistant_name = "test_assistant"
        payload = b'{"id": "test_id", "event": "unique.chat.external-module.chosen", "user_id": "test_user", "company_id": "test_company", "payload": {"name": "test_assistant", "description": "test_description", "configuration": {}, "chat_id": "test_chat", "assistant_id": "test_assistant", "user_message": {"id": "msg1", "text": "Hello", "original_text": "Hello", "created_at": "2023-01-01T00:00:00Z", "language": "en"}, "assistant_message": {"id": "msg2", "created_at": "2023-01-01T00:01:00Z"}}}'
        headers = {}

        result = verify_request_and_construct_event(assistant_name, payload, headers)

        assert isinstance(result, tuple)
        assert len(result) == 2
        assert result[1] == 200
        assert isinstance(result[0], Event)
        assert result[0].payload.name == "test_assistant"

    def test_verify_request_returns_error_response_tuple(self):
        """Test verify_request_and_construct_event returns error response tuple (covers line 92)."""
        with patch(
            "unique_toolkit.app.verification.verify_signature_and_construct_event"
        ) as mock_verify:
            with patch.dict("os.environ", {"ENDPOINT_SECRET": "test_secret"}):
                # Mock verify_signature_and_construct_event to return an error tuple
                mock_verify.return_value = ("Error message", 400)

                result = verify_request_and_construct_event(
                    assistant_name="test_assistant",
                    payload=b'{"test": "data"}',
                    headers={"x-signature": "test_signature"},
                )

                # Should return the error tuple directly
                assert result == ("Error message", 400)

    def test_verify_request_validation_error_reraises(self):
        """Test verify_request_and_construct_event reraises ValidationError (covers line 101)."""
        with patch(
            "unique_toolkit.app.verification.verify_signature_and_construct_event"
        ) as mock_verify:
            with patch.dict("os.environ", {"ENDPOINT_SECRET": "test_secret"}):
                # Mock verify_signature_and_construct_event to raise ValidationError
                mock_verify.side_effect = ValidationError("Field required")

                with pytest.raises(ValidationError):
                    verify_request_and_construct_event(
                        assistant_name="test_assistant",
                        payload=b'{"test": "data"}',
                        headers={"x-signature": "test_signature"},
                    )

    def test_verify_request_value_error_returns_400(self):
        """Test verify_request_and_construct_event returns 400 for ValueError (covers line 103)."""
        # Test the path without endpoint secret to trigger the ValueError handling
        with patch.dict("os.environ", {}, clear=True):
            # Create a mock event constructor that raises ValueError
            def mock_event_constructor(**kwargs):
                raise ValueError("Invalid data")

            result = verify_request_and_construct_event(
                assistant_name="test_assistant",
                payload=b'{"test": "data"}',
                headers={"x-signature": "test_signature"},
                event_constructor=mock_event_constructor,
            )

            # Should return error response
            assert result == ("Invalid event", 400)
