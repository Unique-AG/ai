import json
import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest

from unique_toolkit.app.schemas import (
    BaseEvent,
    ChatEvent,
    ChatEventPayload,
    Event,
)


@pytest.mark.ai_generated
class TestSchemasAdditional:
    """Additional tests for schemas.py to improve coverage."""

    def test_base_event_from_json_file_success(self):
        """Test BaseEvent.from_json_file() with valid file."""
        test_data = {
            "id": "test_event",
            "event": "test.event",
            "user_id": "user123",
            "company_id": "company456",
        }

        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump(test_data, f)
            temp_path = Path(f.name)

        try:
            # Create a concrete BaseEvent subclass for testing
            class TestEvent(BaseEvent):
                pass

            event = TestEvent.from_json_file(temp_path)
            assert event.id == "test_event"
            assert event.user_id == "user123"
            assert event.company_id == "company456"
        finally:
            temp_path.unlink()

    def test_base_event_from_json_file_not_found(self):
        """Test BaseEvent.from_json_file() with non-existent file."""
        non_existent_path = Path("/non/existent/file.json")

        class TestEvent(BaseEvent):
            pass

        with pytest.raises(FileNotFoundError, match="File not found: .*"):
            TestEvent.from_json_file(non_existent_path)

    def test_base_event_filter_event_default_behavior(self):
        """Test BaseEvent.filter_event() default behavior."""

        class TestEvent(BaseEvent):
            pass

        event = TestEvent(
            id="test", event="test.event", user_id="user", company_id="company"
        )

        # Default behavior should return False (no filtering)
        assert event.filter_event() is False
        assert event.filter_event(filter_options=None) is False

    def test_chat_event_payload_validate_scope_rules_with_value(self):
        """Test ChatEventPayload.validate_scope_rules() with value."""
        with patch("unique_toolkit.app.schemas.parse_uniqueql") as mock_parse:
            # Create a mock Statement object
            from unique_toolkit.smart_rules.compile import Operator, Statement

            mock_statement = Statement(operator=Operator.EQUALS, value="rule")
            mock_parse.return_value = mock_statement

            # Create a ChatEventPayload with raw_scope_rules
            payload_data = {
                "name": "test_event",
                "description": "Test",
                "configuration": {},
                "chatId": "chat1",
                "assistantId": "assistant1",
                "userMessage": {
                    "id": "msg1",
                    "text": "Hello",
                    "createdAt": "2023-01-01T00:00:00Z",
                    "originalText": "Hello",
                    "language": "en",
                },
                "assistantMessage": {"id": "msg2", "createdAt": "2023-01-01T00:01:00Z"},
                "rawScopeRules": {"test": "rule"},
            }

            # This should trigger the validator and call parse_uniqueql
            payload = ChatEventPayload.model_validate(payload_data)
            # Verify parse_uniqueql was called with the raw_scope_rules
            mock_parse.assert_called_once_with({"test": "rule"})
            # The validator should have processed the raw_scope_rules
            assert payload.raw_scope_rules is mock_statement

    def test_chat_event_payload_validate_scope_rules_without_value(self):
        """Test ChatEventPayload.validate_scope_rules() without value."""
        payload_data = {
            "name": "test_event",
            "description": "Test",
            "configuration": {},
            "chatId": "chat1",
            "assistantId": "assistant1",
            "userMessage": {
                "id": "msg1",
                "text": "Hello",
                "createdAt": "2023-01-01T00:00:00Z",
                "originalText": "Hello",
                "language": "en",
            },
            "assistantMessage": {"id": "msg2", "createdAt": "2023-01-01T00:01:00Z"},
        }

        payload = ChatEventPayload.model_validate(payload_data)
        assert payload.raw_scope_rules is None

    def test_chat_event_from_json_file_success(self, base_chat_event_data):
        """Test ChatEvent.from_json_file() with valid file."""
        test_data = base_chat_event_data.model_dump()

        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump(test_data, f)
            temp_path = Path(f.name)

        try:
            chat_event = ChatEvent.from_json_file(temp_path)
            assert chat_event.id == base_chat_event_data.id
            assert chat_event.user_id == base_chat_event_data.user_id
            assert chat_event.company_id == base_chat_event_data.company_id
        finally:
            temp_path.unlink()

    def test_chat_event_from_json_file_not_found(self):
        """Test ChatEvent.from_json_file() with non-existent file."""
        non_existent_path = Path("/non/existent/chat_event.json")

        with pytest.raises(FileNotFoundError, match="File not found: .*"):
            ChatEvent.from_json_file(non_existent_path)

    def test_chat_event_get_initial_debug_info(self, base_chat_event_data):
        """Test ChatEvent.get_initial_debug_info() method."""
        chat_event = base_chat_event_data
        debug_info = chat_event.get_initial_debug_info()

        assert isinstance(debug_info, dict)
        # The method should return a dictionary with debug information
        # The exact structure depends on the implementation

    def test_event_from_json_file_success(self, base_chat_event_data):
        """Test Event.from_json_file() with valid file."""
        test_data = base_chat_event_data.model_dump()

        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump(test_data, f)
            temp_path = Path(f.name)

        try:
            event = Event.from_json_file(temp_path)
            assert event.id == base_chat_event_data.id
            assert event.user_id == base_chat_event_data.user_id
            assert event.company_id == base_chat_event_data.company_id
        finally:
            temp_path.unlink()

    def test_event_from_json_file_not_found(self):
        """Test Event.from_json_file() with non-existent file."""
        non_existent_path = Path("/non/existent/event.json")

        with pytest.raises(FileNotFoundError, match="File not found: .*"):
            Event.from_json_file(non_existent_path)
