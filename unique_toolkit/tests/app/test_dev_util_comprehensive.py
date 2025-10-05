"""Comprehensive tests for dev_util.py functionality to achieve full coverage."""

import json
from unittest.mock import Mock, patch

import pytest
from pydantic import ValidationError

from unique_toolkit.app.dev_util import (
    get_event_generator,
    get_event_name_from_event_class,
    get_event_stream,
    get_sse_client,
    load_event,
    run_demo_with_sse_client,
    run_demo_with_with_saved_event,
)
from unique_toolkit.app.schemas import BaseEvent, ChatEvent, EventName


@pytest.mark.ai_generated
class TestGetEventNameFromEventClass:
    """Test the get_event_name_from_event_class function."""

    def test_get_event_name_from_chat_event(self):
        """Test getting event name from ChatEvent class."""
        result = get_event_name_from_event_class(ChatEvent)
        assert result == EventName.EXTERNAL_MODULE_CHOSEN

    def test_get_event_name_from_other_event_class(self):
        """Test getting event name from other event class."""

        class OtherEvent(BaseEvent):
            pass

        result = get_event_name_from_event_class(OtherEvent)
        assert result is None

    def test_get_event_name_from_base_event(self):
        """Test getting event name from BaseEvent class."""
        result = get_event_name_from_event_class(BaseEvent)
        assert result is None


@pytest.mark.ai_generated
class TestGetSseClient:
    """Test the get_sse_client function."""

    @patch("unique_toolkit.app.dev_util.SSEClient")
    def test_get_sse_client_creation(self, mock_sse_client, base_unique_settings):
        """Test creating SSE client with correct parameters."""
        subscriptions = ["event1", "event2"]

        get_sse_client(base_unique_settings, subscriptions)

        expected_url = "https://api.example.com/public/event-socket/events/stream?subscriptions=event1,event2"
        expected_headers = {
            "Authorization": "Bearer test-key",
            "x-app-id": "test-id",
            "x-company-id": "test-company",
            "x-user-id": "test-user",
            "x-api-version": "2023-12-06",
        }

        mock_sse_client.assert_called_once_with(
            url=expected_url, headers=expected_headers
        )


@pytest.mark.ai_generated
class TestGetEventGenerator:
    """Test the get_event_generator function."""

    def test_get_event_generator_invalid_event_type(self, base_unique_settings):
        """Test get_event_generator with invalid event type."""

        class InvalidEvent(BaseEvent):
            pass

        with pytest.raises(
            ValueError, match="Event model .* is not a valid event model"
        ):
            list(get_event_generator(base_unique_settings, InvalidEvent))

    def test_get_event_generator_base_event_type(self, base_unique_settings):
        """Test get_event_generator with BaseEvent type."""
        with pytest.raises(
            ValueError, match="Event model .* is not a valid event model"
        ):
            list(get_event_generator(base_unique_settings, BaseEvent))

    def test_get_event_generator_none_event_name(self, base_unique_settings):
        """Test get_event_generator with event type that returns None event name."""

        class CustomEvent(BaseEvent):
            pass

        with pytest.raises(
            ValueError, match="Event model .* is not a valid event model"
        ):
            list(get_event_generator(base_unique_settings, CustomEvent))


@pytest.mark.ai_generated
class TestGetEventStream:
    """Test the get_event_stream function."""

    @patch("unique_toolkit.app.dev_util.get_event_generator")
    def test_get_event_stream_with_string_config(self, mock_get_event_generator):
        """Test get_event_stream with string configuration."""
        mock_generator = Mock()
        mock_get_event_generator.return_value = mock_generator

        result = get_event_stream(ChatEvent, "test_config.json")

        mock_get_event_generator.assert_called_once()
        assert result == mock_generator

    @patch("unique_toolkit.app.dev_util.get_event_generator")
    def test_get_event_stream_with_unique_settings(
        self, mock_get_event_generator, base_unique_settings
    ):
        """Test get_event_stream with UniqueSettings object."""

        mock_generator = Mock()
        mock_get_event_generator.return_value = mock_generator

        result = get_event_stream(ChatEvent, base_unique_settings)

        mock_get_event_generator.assert_called_once_with(
            base_unique_settings, ChatEvent
        )
        assert result == mock_generator

    @patch("unique_toolkit.app.dev_util.get_event_generator")
    def test_get_event_stream_with_none_config(self, mock_get_event_generator):
        """Test get_event_stream with None configuration."""
        mock_generator = Mock()
        mock_get_event_generator.return_value = mock_generator

        result = get_event_stream(ChatEvent, None)

        mock_get_event_generator.assert_called_once()
        assert result == mock_generator

    @patch("unique_toolkit.app.dev_util.get_event_generator")
    def test_get_event_stream_default_parameters(self, mock_get_event_generator):
        """Test get_event_stream with default parameters."""
        mock_generator = Mock()
        mock_get_event_generator.return_value = mock_generator

        result = get_event_stream()

        mock_get_event_generator.assert_called_once()
        assert result == mock_generator


@pytest.mark.ai_generated
class TestRunDemoWithSseClient:
    """Test the run_demo_with_sse_client function."""

    @patch("unique_toolkit.app.dev_util.init_unique_sdk")
    @patch("unique_toolkit.app.dev_util.get_event_generator")
    def test_run_demo_with_sync_handler(
        self, mock_get_event_generator, mock_init_sdk, base_unique_settings
    ):
        """Test run_demo_with_sse_client with sync handler."""
        mock_event = Mock()
        mock_get_event_generator.return_value = [mock_event]

        handler_called = False

        def sync_handler(event):
            nonlocal handler_called
            handler_called = True
            assert event == mock_event

        run_demo_with_sse_client(base_unique_settings, sync_handler, ChatEvent)

        assert handler_called
        mock_init_sdk.assert_called_once_with(unique_settings=base_unique_settings)
        mock_get_event_generator.assert_called_once_with(
            base_unique_settings, ChatEvent
        )

    @patch("unique_toolkit.app.dev_util.init_unique_sdk")
    @patch("unique_toolkit.app.dev_util.get_event_generator")
    def test_run_demo_with_async_handler(
        self, mock_get_event_generator, mock_init_sdk, base_unique_settings
    ):
        """Test run_demo_with_sse_client with async handler."""
        mock_event = Mock()
        mock_get_event_generator.return_value = [mock_event]

        handler_called = False

        async def async_handler(event):
            nonlocal handler_called
            handler_called = True
            assert event == mock_event

        run_demo_with_sse_client(base_unique_settings, async_handler, ChatEvent)

        assert handler_called
        mock_init_sdk.assert_called_once_with(unique_settings=base_unique_settings)
        mock_get_event_generator.assert_called_once_with(
            base_unique_settings, ChatEvent
        )

    @patch("unique_toolkit.app.dev_util.init_unique_sdk")
    def test_run_demo_with_none_event_name(self, mock_init_sdk, base_unique_settings):
        """Test run_demo_with_sse_client with event type that returns None event name."""

        class CustomEvent(BaseEvent):
            pass

        def handler(event):
            pass

        run_demo_with_sse_client(base_unique_settings, handler, CustomEvent)

        # Should return early without calling init_unique_sdk or get_event_generator
        mock_init_sdk.assert_not_called()


@pytest.mark.ai_generated
class TestLoadEvent:
    """Test the load_event function."""

    def test_load_event_success(self, tmp_path):
        """Test successful loading of event from file."""
        event_data = {
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

        file_path = tmp_path / "event.json"
        file_path.write_text(json.dumps(event_data))

        result = load_event(file_path, ChatEvent)

        assert isinstance(result, ChatEvent)
        assert result.id == "test_id"
        assert result.event == "unique.chat.external-module.chosen"

    def test_load_event_file_not_found(self, tmp_path):
        """Test loading event from non-existent file."""
        file_path = tmp_path / "nonexistent.json"

        with pytest.raises(FileNotFoundError):
            load_event(file_path, ChatEvent)


@pytest.mark.ai_generated
class TestRunDemoWithWithSavedEvent:
    """Test the run_demo_with_with_saved_event function."""

    @patch("unique_toolkit.app.dev_util.init_unique_sdk")
    def test_run_demo_with_saved_event_sync_handler(
        self, mock_init_sdk, base_unique_settings, tmp_path
    ):
        """Test run_demo_with_with_saved_event with sync handler."""
        event_data = {
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

        file_path = tmp_path / "event.json"
        file_path.write_text(json.dumps(event_data))

        handler_called = False

        def sync_handler(event):
            nonlocal handler_called
            handler_called = True
            assert isinstance(event, ChatEvent)
            assert event.id == "test_id"

        run_demo_with_with_saved_event(
            base_unique_settings, sync_handler, ChatEvent, file_path
        )

        assert handler_called
        mock_init_sdk.assert_called_once_with(unique_settings=base_unique_settings)

    @patch("unique_toolkit.app.dev_util.init_unique_sdk")
    def test_run_demo_with_saved_event_async_handler(
        self, mock_init_sdk, base_unique_settings, tmp_path
    ):
        """Test run_demo_with_with_saved_event with async handler."""
        event_data = {
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

        file_path = tmp_path / "event.json"
        file_path.write_text(json.dumps(event_data))

        handler_called = False

        async def async_handler(event):
            nonlocal handler_called
            handler_called = True
            assert isinstance(event, ChatEvent)
            assert event.id == "test_id"

        run_demo_with_with_saved_event(
            base_unique_settings, async_handler, ChatEvent, file_path
        )

        assert handler_called
        mock_init_sdk.assert_called_once_with(unique_settings=base_unique_settings)

    @patch("unique_toolkit.app.dev_util.init_unique_sdk")
    def test_run_demo_with_saved_event_none_event_name(
        self, mock_init_sdk, base_unique_settings, tmp_path
    ):
        """Test run_demo_with_with_saved_event with event type that returns None event name."""

        class CustomEvent(BaseEvent):
            pass

        event_data = {
            "id": "test_id",
            "event": "test_event",
            "user_id": "test_user",
            "company_id": "test_company",
        }
        file_path = tmp_path / "event.json"
        file_path.write_text(json.dumps(event_data))

        def handler(event):
            pass

        run_demo_with_with_saved_event(
            base_unique_settings, handler, CustomEvent, file_path
        )

        # The function actually calls init_unique_sdk even when event_name is None
        # This is the actual behavior of the function
        mock_init_sdk.assert_called_once_with(unique_settings=base_unique_settings)

    @patch("unique_toolkit.app.dev_util.init_unique_sdk")
    def test_run_demo_with_saved_event_none_event(
        self, mock_init_sdk, base_unique_settings, tmp_path
    ):
        """Test run_demo_with_with_saved_event with None event."""
        file_path = tmp_path / "event.json"
        file_path.write_text(json.dumps({"invalid": "data"}))  # Invalid event data

        def handler(event):
            pass

        with pytest.raises(ValidationError):
            run_demo_with_with_saved_event(
                base_unique_settings, handler, ChatEvent, file_path
            )

    @patch("unique_toolkit.app.dev_util.init_unique_sdk")
    @patch("unique_toolkit.app.dev_util.load_event")
    def test_run_demo_with_saved_event_load_event_returns_none(
        self, mock_load_event, mock_init_sdk, base_unique_settings, tmp_path
    ):
        """Test run_demo_with_with_saved_event when load_event returns None (covers line 175)."""
        mock_load_event.return_value = None

        file_path = tmp_path / "event.json"
        file_path.write_text(json.dumps({"test": "data"}))

        def handler(event):
            pass

        with pytest.raises(ValueError, match="Event not found in .*"):
            run_demo_with_with_saved_event(
                base_unique_settings, handler, ChatEvent, file_path
            )
