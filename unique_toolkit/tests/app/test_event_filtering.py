"""Tests for event filtering functionality added in the last commit."""

import pytest

from unique_toolkit._common.exception import ConfigurationException
from unique_toolkit.app.schemas import ChatEvent
from unique_toolkit.app.unique_settings import UniqueChatEventFilterOptions


class TestChatEventFiltering:
    def test_chat_event_filter_event_no_filtering(
        self, base_chat_event_data: ChatEvent
    ):
        """Test that ChatEvent.filter_event returns False when no filtering is applied."""
        chat_event = base_chat_event_data

        # Test with None filter options
        assert chat_event.filter_event(filter_options=None) is False

        # Test with empty filter options - should raise ConfigurationException
        filter_options = UniqueChatEventFilterOptions()
        with pytest.raises(ConfigurationException, match="No filter options provided"):
            chat_event.filter_event(filter_options=filter_options)

    def test_chat_event_filter_by_assistant_id_included(
        self, base_chat_event_data: ChatEvent
    ):
        """Test that ChatEvent.filter_event returns False when assistant_id is in the filter list."""
        # Modify only the assistantId in the payload
        chat_event = base_chat_event_data
        chat_event.payload.assistant_id = "assistant1"

        # Filter options that include the assistant_id
        filter_options = UniqueChatEventFilterOptions(
            assistant_ids=["assistant1", "assistant2"]
        )
        assert chat_event.filter_event(filter_options=filter_options) is False

    def test_chat_event_filter_by_assistant_id_excluded(
        self, base_chat_event_data: ChatEvent
    ):
        """Test that ChatEvent.filter_event returns True when assistant_id is not in the filter list."""
        # Modify only the assistantId in the payload
        chat_event = base_chat_event_data
        chat_event.payload.assistant_id = "assistant3"  # Not in filter list

        # Filter options that don't include the assistant_id
        filter_options = UniqueChatEventFilterOptions(
            assistant_ids=["assistant1", "assistant2"]
        )
        assert chat_event.filter_event(filter_options=filter_options) is True

    def test_chat_event_filter_by_reference_in_code_included(
        self, base_chat_event_data: ChatEvent
    ):
        """Test that ChatEvent.filter_event returns False when reference name is in the filter list."""
        # Modify only the name in the payload
        chat_event = base_chat_event_data
        chat_event.payload.name = "module1"  # In filter list

        # Filter options that include the reference name
        filter_options = UniqueChatEventFilterOptions(
            references_in_code=["module1", "module2"]
        )
        assert chat_event.filter_event(filter_options=filter_options) is False

    def test_chat_event_filter_by_reference_in_code_excluded(
        self, base_chat_event_data: ChatEvent
    ):
        """Test that ChatEvent.filter_event returns True when reference name is not in the filter list."""
        # Modify only the name in the payload
        chat_event = base_chat_event_data
        chat_event.payload.name = "module3"  # Not in filter list

        # Filter options that don't include the reference name
        filter_options = UniqueChatEventFilterOptions(
            references_in_code=["module1", "module2"]
        )
        assert chat_event.filter_event(filter_options=filter_options) is True

    def test_chat_event_filter_both_criteria_must_match(
        self, base_chat_event_data: ChatEvent
    ):
        """Test that ChatEvent.filter_event requires both assistant_id and reference to match when both filters are set."""
        # Modify both name and assistantId in the payload
        chat_event = base_chat_event_data
        chat_event.payload.name = "module1"  # In filter list
        chat_event.payload.assistant_id = "assistant3"  # Not in filter list

        # Filter options with both assistant_ids and references_in_code
        filter_options = UniqueChatEventFilterOptions(
            assistant_ids=["assistant1", "assistant2"],
            references_in_code=["module1", "module2"],
        )
        # Should be filtered out because assistant_id doesn't match
        assert chat_event.filter_event(filter_options=filter_options) is True

    def test_chat_event_filter_both_criteria_match(
        self, base_chat_event_data: ChatEvent
    ):
        """Test that ChatEvent.filter_event returns False when both assistant_id and reference match."""
        # Modify both name and assistantId in the payload
        chat_event = base_chat_event_data
        chat_event.payload.name = "module1"  # In filter list
        chat_event.payload.assistant_id = "assistant1"  # In filter list

        # Filter options with both assistant_ids and references_in_code
        filter_options = UniqueChatEventFilterOptions(
            assistant_ids=["assistant1", "assistant2"],
            references_in_code=["module1", "module2"],
        )
        # Should not be filtered out because both criteria match
        assert chat_event.filter_event(filter_options=filter_options) is False

    def test_chat_event_filter_empty_lists(self, base_chat_event_data: ChatEvent):
        """Test that ChatEvent.filter_event raises ConfigurationException with empty filter lists."""
        # Modify name and assistantId to any values since we're testing empty filter lists
        chat_event = base_chat_event_data
        chat_event.payload.name = "any_module"
        chat_event.payload.assistant_id = "any_assistant"

        # Filter options with empty lists - should raise ConfigurationException
        filter_options = UniqueChatEventFilterOptions(
            assistant_ids=[], references_in_code=[]
        )
        with pytest.raises(ConfigurationException, match="No filter options provided"):
            chat_event.filter_event(filter_options=filter_options)
