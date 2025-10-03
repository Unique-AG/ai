"""Tests for dev_util.py filtering functionality added in the last commit."""

import json
from unittest.mock import Mock, patch

import pytest

from unique_toolkit._common.exception import ConfigurationException
from unique_toolkit.app.dev_util import get_event_generator
from unique_toolkit.app.schemas import ChatEvent
from unique_toolkit.app.unique_settings import (
    UniqueChatEventFilterOptions,
    UniqueSettings,
)


@pytest.fixture
def mock_unique_settings_with_filters(
    base_unique_settings: UniqueSettings,
) -> UniqueSettings:
    """Create a mock UniqueSettings instance with filter options for testing."""
    filter_options = UniqueChatEventFilterOptions(
        assistant_ids=["assistant1", "assistant2"],
        references_in_code=["module1", "module2"],
    )
    return UniqueSettings(
        auth=base_unique_settings.auth,
        app=base_unique_settings.app,
        api=base_unique_settings.api,
        chat_event_filter_options=filter_options,
    )


@pytest.fixture
def mock_unique_settings_with_assistant_filter_only(
    base_unique_settings: UniqueSettings,
) -> UniqueSettings:
    """Create a mock UniqueSettings instance with only assistant_id filtering."""
    filter_options = UniqueChatEventFilterOptions(
        assistant_ids=["assistant1", "assistant2"],
        references_in_code=[],  # Empty list means no filtering by reference
    )
    return UniqueSettings(
        auth=base_unique_settings.auth,
        app=base_unique_settings.app,
        api=base_unique_settings.api,
        chat_event_filter_options=filter_options,
    )


@pytest.fixture
def mock_unique_settings_with_empty_filters(
    base_unique_settings: UniqueSettings,
) -> UniqueSettings:
    """Create a mock UniqueSettings instance with empty filter lists."""
    filter_options = UniqueChatEventFilterOptions(
        assistant_ids=[],  # Empty list
        references_in_code=[],  # Empty list
    )
    return UniqueSettings(
        auth=base_unique_settings.auth,
        app=base_unique_settings.app,
        api=base_unique_settings.api,
        chat_event_filter_options=filter_options,
    )


class TestGetEventGeneratorFiltering:
    def test_get_event_generator_without_filtering(
        self, base_unique_settings: UniqueSettings, base_chat_event_data: ChatEvent
    ):
        """Test that get_event_generator yields events when no filtering is applied."""
        # Modify only what we need for this test
        event = base_chat_event_data.model_copy(deep=True)
        event.payload.assistant_id = "any_assistant"
        sse_event_json = json.dumps(event.model_dump(by_alias=True))

        # Mock SSE events using raw JSON strings
        mock_sse_events = [Mock(data=sse_event_json)]

        with patch("unique_toolkit.app.dev_util.get_sse_client") as mock_sse_client:
            mock_sse_client.return_value = mock_sse_events

            generator = get_event_generator(base_unique_settings, ChatEvent)
            events = list(generator)

            assert len(events) == 1
            assert events[0].id == "test-event"
            assert events[0].payload.assistant_id == "any_assistant"

    def test_get_event_generator_with_assistant_id_filtering(
        self,
        mock_unique_settings_with_assistant_filter_only: UniqueSettings,
        base_chat_event_data: ChatEvent,
    ):
        """Test that get_event_generator filters events by assistant_id only."""
        # Create events with different assistant IDs - modify only what we need
        event1 = base_chat_event_data.model_copy(deep=True)
        event1.id = "event1"
        event1.payload.assistant_id = "assistant3"  # Not in filter list
        event1.payload.name = "any_module"

        event2 = base_chat_event_data.model_copy(deep=True)
        event2.id = "event2"
        event2.payload.assistant_id = "assistant1"  # In filter list
        event2.payload.name = "any_module"

        # Mock SSE events using raw JSON strings
        mock_sse_events = [
            Mock(data=json.dumps(event1.model_dump(by_alias=True))),
            Mock(data=json.dumps(event2.model_dump(by_alias=True))),
        ]

        with patch("unique_toolkit.app.dev_util.get_sse_client") as mock_sse_client:
            mock_sse_client.return_value = mock_sse_events

            generator = get_event_generator(
                mock_unique_settings_with_assistant_filter_only, ChatEvent
            )
            events = list(generator)

            # Only the second event should pass through (assistant1 is in filter list)
            assert len(events) == 1
            assert events[0].id == "event2"
            assert events[0].payload.assistant_id == "assistant1"

    def test_get_event_generator_with_reference_filtering(
        self,
        mock_unique_settings_with_filters: UniqueSettings,
        base_chat_event_data: ChatEvent,
    ):
        """Test that get_event_generator filters events by reference name."""
        # Create events with different module names - modify only what we need
        event1 = base_chat_event_data.model_copy(deep=True)
        event1.id = "event1"
        event1.payload.name = "module3"  # Not in filter list
        event1.payload.assistant_id = "assistant1"

        event2 = base_chat_event_data.model_copy(deep=True)
        event2.id = "event2"
        event2.payload.name = "module1"  # In filter list
        event2.payload.assistant_id = "assistant1"

        # Mock SSE events using raw JSON strings
        mock_sse_events = [
            Mock(data=json.dumps(event1.model_dump(by_alias=True))),
            Mock(data=json.dumps(event2.model_dump(by_alias=True))),
        ]

        with patch("unique_toolkit.app.dev_util.get_sse_client") as mock_sse_client:
            mock_sse_client.return_value = mock_sse_events

            generator = get_event_generator(
                mock_unique_settings_with_filters, ChatEvent
            )
            events = list(generator)

            # Only the second event should pass through (module1 is in filter list)
            assert len(events) == 1
            assert events[0].id == "event2"
            assert events[0].payload.name == "module1"

    def test_get_event_generator_with_both_filters(
        self,
        mock_unique_settings_with_filters: UniqueSettings,
        base_chat_event_data: ChatEvent,
    ):
        """Test that get_event_generator filters events by both assistant_id and reference name."""
        # Create events with mixed criteria - modify only what we need
        event1 = base_chat_event_data.model_copy(deep=True)
        event1.id = "event1"
        event1.payload.name = "module1"  # In filter list
        event1.payload.assistant_id = "assistant3"  # Not in filter list

        event2 = base_chat_event_data.model_copy(deep=True)
        event2.id = "event2"
        event2.payload.name = "module3"  # Not in filter list
        event2.payload.assistant_id = "assistant1"  # In filter list

        event3 = base_chat_event_data.model_copy(deep=True)
        event3.id = "event3"
        event3.payload.name = "module1"  # In filter list
        event3.payload.assistant_id = "assistant1"  # In filter list

        # Mock SSE events using raw JSON strings
        mock_sse_events = [
            Mock(data=json.dumps(event1.model_dump(by_alias=True))),
            Mock(data=json.dumps(event2.model_dump(by_alias=True))),
            Mock(data=json.dumps(event3.model_dump(by_alias=True))),
        ]

        with patch("unique_toolkit.app.dev_util.get_sse_client") as mock_sse_client:
            mock_sse_client.return_value = mock_sse_events

            generator = get_event_generator(
                mock_unique_settings_with_filters, ChatEvent
            )
            events = list(generator)

            # Only the third event should pass through (both criteria match)
            assert len(events) == 1
            assert events[0].id == "event3"
            assert events[0].payload.assistant_id == "assistant1"
            assert events[0].payload.name == "module1"

    def test_get_event_generator_with_none_filter_options(
        self, base_unique_settings: UniqueSettings, base_chat_event_data: ChatEvent
    ):
        """Test that get_event_generator works when filter_options is None."""
        # Modify only what we need for this test
        event = base_chat_event_data.model_copy(deep=True)
        event.payload.assistant_id = "any_assistant"
        sse_event_json = json.dumps(event.model_dump(by_alias=True))

        # Mock SSE events using raw JSON strings
        mock_sse_events = [Mock(data=sse_event_json)]

        with patch("unique_toolkit.app.dev_util.get_sse_client") as mock_sse_client:
            mock_sse_client.return_value = mock_sse_events

            generator = get_event_generator(base_unique_settings, ChatEvent)
            events = list(generator)

            # Event should pass through when filter_options is None
            assert len(events) == 1
            assert events[0].id == "test-event"

    def test_get_event_generator_handles_invalid_json(
        self, base_unique_settings: UniqueSettings, base_chat_event_data: ChatEvent
    ):
        """Test that get_event_generator handles invalid JSON gracefully."""
        # Create events with invalid data - modify only what we need
        event = base_chat_event_data.model_copy(deep=True)
        valid_event_json = json.dumps(event.model_dump(by_alias=True))

        # Mock SSE events with invalid JSON
        mock_sse_events = [Mock(data="invalid json"), Mock(data=valid_event_json)]

        with patch("unique_toolkit.app.dev_util.get_sse_client") as mock_sse_client:
            mock_sse_client.return_value = mock_sse_events

            generator = get_event_generator(base_unique_settings, ChatEvent)
            events = list(generator)

            # Only the valid event should pass through
            assert len(events) == 1
            assert events[0].id == "test-event"

    def test_get_event_generator_handles_validation_errors(
        self, base_unique_settings: UniqueSettings, base_chat_event_data: ChatEvent
    ):
        """Test that get_event_generator handles validation errors gracefully."""
        # Create events with validation errors - modify only what we need
        invalid_event_data = {
            "id": "event1",
            "event": "unique.chat.external-module.chosen",
            "userId": "test-user",
            "companyId": "test-company",
            "payload": {
                # Missing required fields
                "name": "test_module",
            },
        }

        valid_event = base_chat_event_data.model_copy(deep=True)
        valid_event.id = "event2"
        valid_event_json = json.dumps(valid_event.model_dump(by_alias=True))

        # Mock SSE events with invalid event data
        mock_sse_events = [
            Mock(data=json.dumps(invalid_event_data)),
            Mock(data=valid_event_json),
        ]

        with patch("unique_toolkit.app.dev_util.get_sse_client") as mock_sse_client:
            mock_sse_client.return_value = mock_sse_events

            generator = get_event_generator(base_unique_settings, ChatEvent)
            events = list(generator)

            # Only the valid event should pass through
            assert len(events) == 1
            assert events[0].id == "event2"

    def test_get_event_generator_with_empty_filter_lists(
        self,
        mock_unique_settings_with_empty_filters: UniqueSettings,
        base_chat_event_data: ChatEvent,
    ):
        """Test that get_event_generator raises ConfigurationException when both filter lists are empty."""
        # Modify only what we need for this test
        event = base_chat_event_data.model_copy(deep=True)
        event.payload.assistant_id = "any_assistant"
        sse_event_json = json.dumps(event.model_dump(by_alias=True))

        # Mock SSE events
        mock_sse_events = [Mock(data=sse_event_json)]

        with patch("unique_toolkit.app.dev_util.get_sse_client") as mock_sse_client:
            mock_sse_client.return_value = mock_sse_events

            generator = get_event_generator(
                mock_unique_settings_with_empty_filters, ChatEvent
            )

            # Should raise ConfigurationException when both filter lists are empty
            with pytest.raises(
                ConfigurationException, match="No filter options provided"
            ):
                list(generator)
