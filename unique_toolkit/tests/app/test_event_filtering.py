"""Tests for event filtering functionality added in the last commit."""

import pytest

from unique_toolkit._common.exception import ConfigurationException
from unique_toolkit.app.schemas import ChatEvent, Event
from unique_toolkit.app.unique_settings import UniqueChatEventFilterOptions


class TestBaseEventFiltering:
    def test_base_event_filter_event_default_behavior(self):
        """Test that BaseEvent.filter_event returns False by default (no filtering)."""
        # Create a minimal BaseEvent instance
        event_data = {
            "id": "test-event",
            "event": "unique.chat.external-module.chosen",
            "userId": "test-user",
            "companyId": "test-company",
            "payload": {
                "name": "test_module",
                "description": "Test description",
                "configuration": {},
                "chatId": "test-chat",
                "assistantId": "test-assistant",
                "userMessage": {
                    "id": "msg1",
                    "text": "Hello",
                    "createdAt": "2023-01-01T00:00:00Z",
                    "originalText": "Hello",
                    "language": "en",
                },
                "assistantMessage": {"id": "msg2", "createdAt": "2023-01-01T00:01:00Z"},
            },
            "createdAt": 1672531200,
            "version": "1.0",
        }

        event = Event.model_validate(event_data)

        # Test with None filter options
        assert event.filter_event(filter_options=None) is False

        # Test with empty filter options - should raise ConfigurationException
        filter_options = UniqueChatEventFilterOptions()
        with pytest.raises(ConfigurationException, match="No filter options provided"):
            event.filter_event(filter_options=filter_options)


class TestChatEventFiltering:
    def test_chat_event_filter_event_no_filtering(self):
        """Test that ChatEvent.filter_event returns False when no filtering is applied."""
        event_data = {
            "id": "test-event",
            "event": "unique.chat.external-module.chosen",
            "userId": "test-user",
            "companyId": "test-company",
            "payload": {
                "name": "test_module",
                "description": "Test description",
                "configuration": {},
                "chatId": "test-chat",
                "assistantId": "test-assistant",
                "userMessage": {
                    "id": "msg1",
                    "text": "Hello",
                    "createdAt": "2023-01-01T00:00:00Z",
                    "originalText": "Hello",
                    "language": "en",
                },
                "assistantMessage": {"id": "msg2", "createdAt": "2023-01-01T00:01:00Z"},
            },
            "createdAt": 1672531200,
            "version": "1.0",
        }

        chat_event = ChatEvent.model_validate(event_data)

        # Test with None filter options
        assert chat_event.filter_event(filter_options=None) is False

        # Test with empty filter options - should raise ConfigurationException
        filter_options = UniqueChatEventFilterOptions()
        with pytest.raises(ConfigurationException, match="No filter options provided"):
            chat_event.filter_event(filter_options=filter_options)

    def test_chat_event_filter_by_assistant_id_included(self):
        """Test that ChatEvent.filter_event returns False when assistant_id is in the filter list."""
        event_data = {
            "id": "test-event",
            "event": "unique.chat.external-module.chosen",
            "userId": "test-user",
            "companyId": "test-company",
            "payload": {
                "name": "test_module",
                "description": "Test description",
                "configuration": {},
                "chatId": "test-chat",
                "assistantId": "assistant1",
                "userMessage": {
                    "id": "msg1",
                    "text": "Hello",
                    "createdAt": "2023-01-01T00:00:00Z",
                    "originalText": "Hello",
                    "language": "en",
                },
                "assistantMessage": {"id": "msg2", "createdAt": "2023-01-01T00:01:00Z"},
            },
            "createdAt": 1672531200,
            "version": "1.0",
        }

        chat_event = ChatEvent.model_validate(event_data)

        # Filter options that include the assistant_id
        filter_options = UniqueChatEventFilterOptions(
            assistant_ids=["assistant1", "assistant2"]
        )
        assert chat_event.filter_event(filter_options=filter_options) is False

    def test_chat_event_filter_by_assistant_id_excluded(self):
        """Test that ChatEvent.filter_event returns True when assistant_id is not in the filter list."""
        event_data = {
            "id": "test-event",
            "event": "unique.chat.external-module.chosen",
            "userId": "test-user",
            "companyId": "test-company",
            "payload": {
                "name": "test_module",
                "description": "Test description",
                "configuration": {},
                "chatId": "test-chat",
                "assistantId": "assistant3",  # Not in filter list
                "userMessage": {
                    "id": "msg1",
                    "text": "Hello",
                    "createdAt": "2023-01-01T00:00:00Z",
                    "originalText": "Hello",
                    "language": "en",
                },
                "assistantMessage": {"id": "msg2", "createdAt": "2023-01-01T00:01:00Z"},
            },
            "createdAt": 1672531200,
            "version": "1.0",
        }

        chat_event = ChatEvent.model_validate(event_data)

        # Filter options that don't include the assistant_id
        filter_options = UniqueChatEventFilterOptions(
            assistant_ids=["assistant1", "assistant2"]
        )
        assert chat_event.filter_event(filter_options=filter_options) is True

    def test_chat_event_filter_by_reference_in_code_included(self):
        """Test that ChatEvent.filter_event returns False when reference name is in the filter list."""
        event_data = {
            "id": "test-event",
            "event": "unique.chat.external-module.chosen",
            "userId": "test-user",
            "companyId": "test-company",
            "payload": {
                "name": "module1",  # In filter list
                "description": "Test description",
                "configuration": {},
                "chatId": "test-chat",
                "assistantId": "test-assistant",
                "userMessage": {
                    "id": "msg1",
                    "text": "Hello",
                    "createdAt": "2023-01-01T00:00:00Z",
                    "originalText": "Hello",
                    "language": "en",
                },
                "assistantMessage": {"id": "msg2", "createdAt": "2023-01-01T00:01:00Z"},
            },
            "createdAt": 1672531200,
            "version": "1.0",
        }

        chat_event = ChatEvent.model_validate(event_data)

        # Filter options that include the reference name
        filter_options = UniqueChatEventFilterOptions(
            references_in_code=["module1", "module2"]
        )
        assert chat_event.filter_event(filter_options=filter_options) is False

    def test_chat_event_filter_by_reference_in_code_excluded(self):
        """Test that ChatEvent.filter_event returns True when reference name is not in the filter list."""
        event_data = {
            "id": "test-event",
            "event": "unique.chat.external-module.chosen",
            "userId": "test-user",
            "companyId": "test-company",
            "payload": {
                "name": "module3",  # Not in filter list
                "description": "Test description",
                "configuration": {},
                "chatId": "test-chat",
                "assistantId": "test-assistant",
                "userMessage": {
                    "id": "msg1",
                    "text": "Hello",
                    "createdAt": "2023-01-01T00:00:00Z",
                    "originalText": "Hello",
                    "language": "en",
                },
                "assistantMessage": {"id": "msg2", "createdAt": "2023-01-01T00:01:00Z"},
            },
            "createdAt": 1672531200,
            "version": "1.0",
        }

        chat_event = ChatEvent.model_validate(event_data)

        # Filter options that don't include the reference name
        filter_options = UniqueChatEventFilterOptions(
            references_in_code=["module1", "module2"]
        )
        assert chat_event.filter_event(filter_options=filter_options) is True

    def test_chat_event_filter_both_criteria_must_match(self):
        """Test that ChatEvent.filter_event requires both assistant_id and reference to match when both filters are set."""
        event_data = {
            "id": "test-event",
            "event": "unique.chat.external-module.chosen",
            "userId": "test-user",
            "companyId": "test-company",
            "payload": {
                "name": "module1",  # In filter list
                "description": "Test description",
                "configuration": {},
                "chatId": "test-chat",
                "assistantId": "assistant3",  # Not in filter list
                "userMessage": {
                    "id": "msg1",
                    "text": "Hello",
                    "createdAt": "2023-01-01T00:00:00Z",
                    "originalText": "Hello",
                    "language": "en",
                },
                "assistantMessage": {"id": "msg2", "createdAt": "2023-01-01T00:01:00Z"},
            },
            "createdAt": 1672531200,
            "version": "1.0",
        }

        chat_event = ChatEvent.model_validate(event_data)

        # Filter options with both assistant_ids and references_in_code
        filter_options = UniqueChatEventFilterOptions(
            assistant_ids=["assistant1", "assistant2"],
            references_in_code=["module1", "module2"],
        )
        # Should be filtered out because assistant_id doesn't match
        assert chat_event.filter_event(filter_options=filter_options) is True

    def test_chat_event_filter_both_criteria_match(self):
        """Test that ChatEvent.filter_event returns False when both assistant_id and reference match."""
        event_data = {
            "id": "test-event",
            "event": "unique.chat.external-module.chosen",
            "userId": "test-user",
            "companyId": "test-company",
            "payload": {
                "name": "module1",  # In filter list
                "description": "Test description",
                "configuration": {},
                "chatId": "test-chat",
                "assistantId": "assistant1",  # In filter list
                "userMessage": {
                    "id": "msg1",
                    "text": "Hello",
                    "createdAt": "2023-01-01T00:00:00Z",
                    "originalText": "Hello",
                    "language": "en",
                },
                "assistantMessage": {"id": "msg2", "createdAt": "2023-01-01T00:01:00Z"},
            },
            "createdAt": 1672531200,
            "version": "1.0",
        }

        chat_event = ChatEvent.model_validate(event_data)

        # Filter options with both assistant_ids and references_in_code
        filter_options = UniqueChatEventFilterOptions(
            assistant_ids=["assistant1", "assistant2"],
            references_in_code=["module1", "module2"],
        )
        # Should not be filtered out because both criteria match
        assert chat_event.filter_event(filter_options=filter_options) is False

    def test_chat_event_filter_empty_lists(self):
        """Test that ChatEvent.filter_event raises ConfigurationException with empty filter lists."""
        event_data = {
            "id": "test-event",
            "event": "unique.chat.external-module.chosen",
            "userId": "test-user",
            "companyId": "test-company",
            "payload": {
                "name": "any_module",
                "description": "Test description",
                "configuration": {},
                "chatId": "test-chat",
                "assistantId": "any_assistant",
                "userMessage": {
                    "id": "msg1",
                    "text": "Hello",
                    "createdAt": "2023-01-01T00:00:00Z",
                    "originalText": "Hello",
                    "language": "en",
                },
                "assistantMessage": {"id": "msg2", "createdAt": "2023-01-01T00:01:00Z"},
            },
            "createdAt": 1672531200,
            "version": "1.0",
        }

        chat_event = ChatEvent.model_validate(event_data)

        # Filter options with empty lists - should raise ConfigurationException
        filter_options = UniqueChatEventFilterOptions(
            assistant_ids=[], references_in_code=[]
        )
        with pytest.raises(ConfigurationException, match="No filter options provided"):
            chat_event.filter_event(filter_options=filter_options)
