"""Tests for dev_util.py filtering functionality added in the last commit."""

import json
from unittest.mock import Mock, patch

import pytest
from pydantic import SecretStr

from unique_toolkit._common.exception import ConfigurationException
from unique_toolkit.app.dev_util import get_event_generator
from unique_toolkit.app.schemas import ChatEvent
from unique_toolkit.app.unique_settings import (
    UniqueApi,
    UniqueApp,
    UniqueAuth,
    UniqueChatEventFilterOptions,
    UniqueSettings,
)


@pytest.fixture
def mock_unique_settings() -> UniqueSettings:
    """Create a mock UniqueSettings instance for testing."""
    auth = UniqueAuth(
        company_id=SecretStr("test-company"), user_id=SecretStr("test-user")
    )
    app = UniqueApp(
        id=SecretStr("test-id"),
        key=SecretStr("test-key"),
        base_url="https://api.example.com",
        endpoint="/v1/endpoint",
        endpoint_secret=SecretStr("test-endpoint-secret"),
    )
    api = UniqueApi(
        base_url="https://api.example.com",
        version="2023-12-06",
    )
    return UniqueSettings(auth=auth, app=app, api=api)


@pytest.fixture
def mock_unique_settings_with_filters() -> UniqueSettings:
    """Create a mock UniqueSettings instance with filter options for testing."""
    auth = UniqueAuth(
        company_id=SecretStr("test-company"), user_id=SecretStr("test-user")
    )
    app = UniqueApp(
        id=SecretStr("test-id"),
        key=SecretStr("test-key"),
        base_url="https://api.example.com",
        endpoint="/v1/endpoint",
        endpoint_secret=SecretStr("test-endpoint-secret"),
    )
    api = UniqueApi(
        base_url="https://api.example.com",
        version="2023-12-06",
    )
    filter_options = UniqueChatEventFilterOptions(
        assistant_ids=["assistant1", "assistant2"],
        references_in_code=["module1", "module2"],
    )
    return UniqueSettings(
        auth=auth, app=app, api=api, chat_event_filter_options=filter_options
    )


@pytest.fixture
def mock_unique_settings_with_assistant_filter_only() -> UniqueSettings:
    """Create a mock UniqueSettings instance with only assistant_id filtering."""
    auth = UniqueAuth(
        company_id=SecretStr("test-company"), user_id=SecretStr("test-user")
    )
    app = UniqueApp(
        id=SecretStr("test-id"),
        key=SecretStr("test-key"),
        base_url="https://api.example.com",
        endpoint="/v1/endpoint",
        endpoint_secret=SecretStr("test-endpoint-secret"),
    )
    api = UniqueApi(
        base_url="https://api.example.com",
        version="2023-12-06",
    )
    filter_options = UniqueChatEventFilterOptions(
        assistant_ids=["assistant1", "assistant2"],
        references_in_code=[],  # Empty list means no filtering by reference
    )
    return UniqueSettings(
        auth=auth, app=app, api=api, chat_event_filter_options=filter_options
    )


@pytest.fixture
def mock_unique_settings_with_empty_filters() -> UniqueSettings:
    """Create a mock UniqueSettings instance with empty filter lists."""
    auth = UniqueAuth(
        company_id=SecretStr("test-company"), user_id=SecretStr("test-user")
    )
    app = UniqueApp(
        id=SecretStr("test-id"),
        key=SecretStr("test-key"),
        base_url="https://api.example.com",
        endpoint="/v1/endpoint",
        endpoint_secret=SecretStr("test-endpoint-secret"),
    )
    api = UniqueApi(
        base_url="https://api.example.com",
        version="2023-12-06",
    )
    filter_options = UniqueChatEventFilterOptions(
        assistant_ids=[],  # Empty list
        references_in_code=[],  # Empty list
    )
    return UniqueSettings(
        auth=auth, app=app, api=api, chat_event_filter_options=filter_options
    )


class TestGetEventGeneratorFiltering:
    def test_get_event_generator_without_filtering(
        self, mock_unique_settings: UniqueSettings
    ):
        """Test that get_event_generator yields events when no filtering is applied."""
        # Mock SSE events
        mock_sse_events = [
            Mock(
                data=json.dumps(
                    {
                        "id": "event1",
                        "event": "unique.chat.external-module.chosen",
                        "userId": "test-user",
                        "companyId": "test-company",
                        "payload": {
                            "name": "test_module",
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
                            "assistantMessage": {
                                "id": "msg2",
                                "createdAt": "2023-01-01T00:01:00Z",
                            },
                        },
                        "createdAt": 1672531200,
                        "version": "1.0",
                    }
                )
            )
        ]

        with patch("unique_toolkit.app.dev_util.get_sse_client") as mock_sse_client:
            mock_sse_client.return_value = mock_sse_events

            generator = get_event_generator(mock_unique_settings, ChatEvent)
            events = list(generator)

            assert len(events) == 1
            assert events[0].id == "event1"
            assert events[0].payload.assistant_id == "any_assistant"

    def test_get_event_generator_with_assistant_id_filtering(
        self, mock_unique_settings_with_assistant_filter_only: UniqueSettings
    ):
        """Test that get_event_generator filters events by assistant_id only."""
        # Mock SSE events - one that should be filtered out, one that should pass
        mock_sse_events = [
            Mock(
                data=json.dumps(
                    {
                        "id": "event1",
                        "event": "unique.chat.external-module.chosen",
                        "userId": "test-user",
                        "companyId": "test-company",
                        "payload": {
                            "name": "any_module",  # Any module name since we're not filtering by reference
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
                            "assistantMessage": {
                                "id": "msg2",
                                "createdAt": "2023-01-01T00:01:00Z",
                            },
                        },
                        "createdAt": 1672531200,
                        "version": "1.0",
                    }
                )
            ),
            Mock(
                data=json.dumps(
                    {
                        "id": "event2",
                        "event": "unique.chat.external-module.chosen",
                        "userId": "test-user",
                        "companyId": "test-company",
                        "payload": {
                            "name": "any_module",  # Any module name since we're not filtering by reference
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
                            "assistantMessage": {
                                "id": "msg2",
                                "createdAt": "2023-01-01T00:01:00Z",
                            },
                        },
                        "createdAt": 1672531200,
                        "version": "1.0",
                    }
                )
            ),
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
        self, mock_unique_settings_with_filters: UniqueSettings
    ):
        """Test that get_event_generator filters events by reference name."""
        # Mock SSE events - one that should be filtered out, one that should pass
        mock_sse_events = [
            Mock(
                data=json.dumps(
                    {
                        "id": "event1",
                        "event": "unique.chat.external-module.chosen",
                        "userId": "test-user",
                        "companyId": "test-company",
                        "payload": {
                            "name": "module3",  # Not in filter list
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
                            "assistantMessage": {
                                "id": "msg2",
                                "createdAt": "2023-01-01T00:01:00Z",
                            },
                        },
                        "createdAt": 1672531200,
                        "version": "1.0",
                    }
                )
            ),
            Mock(
                data=json.dumps(
                    {
                        "id": "event2",
                        "event": "unique.chat.external-module.chosen",
                        "userId": "test-user",
                        "companyId": "test-company",
                        "payload": {
                            "name": "module1",  # In filter list
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
                            "assistantMessage": {
                                "id": "msg2",
                                "createdAt": "2023-01-01T00:01:00Z",
                            },
                        },
                        "createdAt": 1672531200,
                        "version": "1.0",
                    }
                )
            ),
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
        self, mock_unique_settings_with_filters: UniqueSettings
    ):
        """Test that get_event_generator filters events by both assistant_id and reference name."""
        # Mock SSE events - only one that matches both criteria should pass
        mock_sse_events = [
            Mock(
                data=json.dumps(
                    {
                        "id": "event1",
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
                            "assistantMessage": {
                                "id": "msg2",
                                "createdAt": "2023-01-01T00:01:00Z",
                            },
                        },
                        "createdAt": 1672531200,
                        "version": "1.0",
                    }
                )
            ),
            Mock(
                data=json.dumps(
                    {
                        "id": "event2",
                        "event": "unique.chat.external-module.chosen",
                        "userId": "test-user",
                        "companyId": "test-company",
                        "payload": {
                            "name": "module3",  # Not in filter list
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
                            "assistantMessage": {
                                "id": "msg2",
                                "createdAt": "2023-01-01T00:01:00Z",
                            },
                        },
                        "createdAt": 1672531200,
                        "version": "1.0",
                    }
                )
            ),
            Mock(
                data=json.dumps(
                    {
                        "id": "event3",
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
                            "assistantMessage": {
                                "id": "msg2",
                                "createdAt": "2023-01-01T00:01:00Z",
                            },
                        },
                        "createdAt": 1672531200,
                        "version": "1.0",
                    }
                )
            ),
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
        self, mock_unique_settings: UniqueSettings
    ):
        """Test that get_event_generator works when filter_options is None."""
        # Mock SSE events
        mock_sse_events = [
            Mock(
                data=json.dumps(
                    {
                        "id": "event1",
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
                            "assistantMessage": {
                                "id": "msg2",
                                "createdAt": "2023-01-01T00:01:00Z",
                            },
                        },
                        "createdAt": 1672531200,
                        "version": "1.0",
                    }
                )
            )
        ]

        with patch("unique_toolkit.app.dev_util.get_sse_client") as mock_sse_client:
            mock_sse_client.return_value = mock_sse_events

            generator = get_event_generator(mock_unique_settings, ChatEvent)
            events = list(generator)

            # Event should pass through when filter_options is None
            assert len(events) == 1
            assert events[0].id == "event1"

    def test_get_event_generator_handles_invalid_json(self, mock_unique_settings):
        """Test that get_event_generator handles invalid JSON gracefully."""
        # Mock SSE events with invalid JSON
        mock_sse_events = [
            Mock(data="invalid json"),
            Mock(
                data=json.dumps(
                    {
                        "id": "event1",
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
                            "assistantMessage": {
                                "id": "msg2",
                                "createdAt": "2023-01-01T00:01:00Z",
                            },
                        },
                        "createdAt": 1672531200,
                        "version": "1.0",
                    }
                )
            ),
        ]

        with patch("unique_toolkit.app.dev_util.get_sse_client") as mock_sse_client:
            mock_sse_client.return_value = mock_sse_events

            generator = get_event_generator(mock_unique_settings, ChatEvent)
            events = list(generator)

            # Only the valid event should pass through
            assert len(events) == 1
            assert events[0].id == "event1"

    def test_get_event_generator_handles_validation_errors(
        self, mock_unique_settings: UniqueSettings
    ):
        """Test that get_event_generator handles validation errors gracefully."""
        # Mock SSE events with invalid event data
        mock_sse_events = [
            Mock(
                data=json.dumps(
                    {
                        "id": "event1",
                        "event": "unique.chat.external-module.chosen",
                        "userId": "test-user",
                        "companyId": "test-company",
                        "payload": {
                            # Missing required fields
                            "name": "test_module",
                        },
                    }
                )
            ),
            Mock(
                data=json.dumps(
                    {
                        "id": "event2",
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
                            "assistantMessage": {
                                "id": "msg2",
                                "createdAt": "2023-01-01T00:01:00Z",
                            },
                        },
                        "createdAt": 1672531200,
                        "version": "1.0",
                    }
                )
            ),
        ]

        with patch("unique_toolkit.app.dev_util.get_sse_client") as mock_sse_client:
            mock_sse_client.return_value = mock_sse_events

            generator = get_event_generator(mock_unique_settings, ChatEvent)
            events = list(generator)

            # Only the valid event should pass through
            assert len(events) == 1
            assert events[0].id == "event2"

    def test_get_event_generator_with_empty_filter_lists(
        self, mock_unique_settings_with_empty_filters: UniqueSettings
    ):
        """Test that get_event_generator raises ConfigurationException when both filter lists are empty."""
        # Mock SSE events
        mock_sse_events = [
            Mock(
                data=json.dumps(
                    {
                        "id": "event1",
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
                            "assistantMessage": {
                                "id": "msg2",
                                "createdAt": "2023-01-01T00:01:00Z",
                            },
                        },
                        "createdAt": 1672531200,
                        "version": "1.0",
                    }
                )
            ),
        ]

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
