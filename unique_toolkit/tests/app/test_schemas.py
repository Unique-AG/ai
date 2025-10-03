from unique_toolkit.app.schemas import (
    ChatEventAssistantMessage,
    ChatEventPayload,
    ChatEventUserMessage,
    Event,
    EventAssistantMessage,
    EventName,
    EventPayload,
    EventUserMessage,
)


class TestEventSchemas:
    def test_event_user_message_deserialization(self, base_user_message_json):
        """Test EventUserMessage deserialization from JSON."""
        user_message = EventUserMessage.model_validate_json(base_user_message_json)

        assert user_message.id == "msg1"
        assert user_message.text == "Hello"
        assert user_message.created_at == "2023-01-01T00:00:00Z"

    def test_event_assistant_message_deserialization(self, base_assistant_message_json):
        """Test EventAssistantMessage deserialization from JSON."""
        assistant_message = EventAssistantMessage.model_validate_json(
            base_assistant_message_json
        )

        assert assistant_message.id == "msg2"
        assert assistant_message.created_at == "2023-01-01T00:01:00Z"

    def test_event_payload_deserialization(self, base_event_payload_json):
        """Test EventPayload deserialization from JSON."""
        payload = EventPayload.model_validate_json(base_event_payload_json)

        assert payload.name == EventName.EXTERNAL_MODULE_CHOSEN
        assert payload.description == "Test description"
        assert payload.configuration == {"key": "value"}
        assert payload.chat_id == "test-chat"
        assert payload.assistant_id == "test-assistant"
        assert payload.user_message.id == "msg1"
        assert payload.assistant_message.id == "msg2"
        assert payload.text == "Optional text"
        assert payload.additional_parameters is not None
        assert payload.additional_parameters.translate_to_language == "en"
        assert payload.additional_parameters.content_id_to_translate == "content_1234"

    def test_event_deserialization(self, base_event_json):
        """Test complete Event deserialization from JSON."""
        event = Event.model_validate_json(base_event_json)

        assert event.id == "event1"
        assert event.event == EventName.EXTERNAL_MODULE_CHOSEN
        assert event.user_id == "user1"
        assert event.company_id == "company1"
        assert event.payload.name == "test_module"
        assert event.payload.chat_id == "test-chat"
        assert event.payload.user_message.text == "Hello"
        assert event.payload.assistant_message.created_at == "2023-01-01T00:01:00Z"
        assert event.payload.text == "Optional text"
        assert event.payload.additional_parameters is not None
        assert event.payload.additional_parameters.translate_to_language == "en"
        assert (
            event.payload.additional_parameters.content_id_to_translate
            == "content_1234"
        )
        assert event.created_at == 1672531200
        assert event.version == "1.0"

    def test_snake_case_conversion(self, minimal_event_json):
        """Test that camelCase JSON fields are converted to snake_case attributes."""
        event = Event.model_validate_json(minimal_event_json)

        assert hasattr(event, "user_id")
        assert hasattr(event, "company_id")
        assert hasattr(event.payload, "chat_id")
        assert hasattr(event.payload, "assistant_id")
        assert hasattr(event.payload.user_message, "created_at")

    def test_chat_event_user_message_deserialization(self, base_user_message_json):
        """Test ChatEventUserMessage deserialization from JSON."""
        user_message = ChatEventUserMessage.model_validate_json(base_user_message_json)

        assert user_message.id == "msg1"
        assert user_message.text == "Hello"
        assert user_message.created_at == "2023-01-01T00:00:00Z"

    def test_chat_event_assistant_message_deserialization(
        self, base_assistant_message_json
    ):
        """Test ChatEventAssistantMessage deserialization from JSON."""
        assistant_message = ChatEventAssistantMessage.model_validate_json(
            base_assistant_message_json
        )

        assert assistant_message.id == "msg2"
        assert assistant_message.created_at == "2023-01-01T00:01:00Z"

    def test_chat_event_payload_deserialization(self, base_event_payload_json):
        """Test ChatEventPayload deserialization from JSON."""
        payload = ChatEventPayload.model_validate_json(base_event_payload_json)

        assert payload.name == EventName.EXTERNAL_MODULE_CHOSEN
        assert payload.description == "Test description"
        assert payload.configuration == {"key": "value"}
        assert payload.chat_id == "test-chat"
        assert payload.assistant_id == "test-assistant"
        assert payload.user_message.id == "msg1"
        assert payload.assistant_message.id == "msg2"
        assert payload.text == "Optional text"
        assert payload.additional_parameters is not None
        assert payload.additional_parameters.translate_to_language == "en"
        assert payload.additional_parameters.content_id_to_translate == "content_1234"
