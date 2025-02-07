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
    def test_event_user_message_deserialization(self):
        json_data = '{"id": "msg1", "text": "Hello", "createdAt": "2023-01-01T00:00:00Z", "originalText": "Hello", "language": "en"}'
        user_message = EventUserMessage.model_validate_json(json_data)

        assert user_message.id == "msg1"
        assert user_message.text == "Hello"
        assert user_message.created_at == "2023-01-01T00:00:00Z"

    def test_event_assistant_message_deserialization(self):
        json_data = '{"id": "msg2", "createdAt": "2023-01-01T00:01:00Z"}'
        assistant_message = EventAssistantMessage.model_validate_json(json_data)

        assert assistant_message.id == "msg2"
        assert assistant_message.created_at == "2023-01-01T00:01:00Z"

    def test_event_payload_deserialization(self):
        json_data = """{
            "name": "unique.chat.external-module.chosen",
            "description": "Test description",
            "configuration": {"key": "value"},
            "chatId": "chat1",
            "assistantId": "assistant1",
            "userMessage": {
                "id": "msg1",
                "text": "Hello",
                "createdAt": "2023-01-01T00:00:00Z",
                "originalText": "Hello",
                "language": "en"
            },
            "assistantMessage": {
                "id": "msg2",
                "createdAt": "2023-01-01T00:01:00Z"
            },
            "text": "Optional text",
            "additionalParameters": {"translateToLanguage": "en", "contentIdToTranslate": "content_1234"}
        }"""
        payload = EventPayload.model_validate_json(json_data)

        assert payload.name == EventName.EXTERNAL_MODULE_CHOSEN
        assert payload.description == "Test description"
        assert payload.configuration == {"key": "value"}
        assert payload.chat_id == "chat1"
        assert payload.assistant_id == "assistant1"
        assert payload.user_message.id == "msg1"
        assert payload.assistant_message.id == "msg2"
        assert payload.text == "Optional text"
        assert payload.additional_parameters is not None
        assert payload.additional_parameters.translate_to_language == "en"
        assert payload.additional_parameters.content_id_to_translate == "content_1234"

    def test_event_deserialization(self):
        json_data = """{
            "id": "event1",
            "event": "unique.chat.external-module.chosen",
            "userId": "user1",
            "companyId": "company1",
            "payload": {
                "name": "test_module",
                "description": "Test description",
                "configuration": {"key": "value"},
                "chatId": "chat1",
                "assistantId": "assistant1",
                "userMessage": {
                    "id": "msg1",
                    "text": "Hello",
                    "createdAt": "2023-01-01T00:00:00Z",
                    "originalText": "Hello",
                    "language": "en"
                },
                "assistantMessage": {
                    "id": "msg2",
                    "createdAt": "2023-01-01T00:01:00Z"
                },
                "text": "Optional text",
                "additionalParameters": {"translateToLanguage": "en", "contentIdToTranslate": "content_1234"}
            },
            "createdAt": 1672531200,
            "version": "1.0"
        }"""
        event = Event.model_validate_json(json_data)

        assert event.id == "event1"
        assert event.event == EventName.EXTERNAL_MODULE_CHOSEN
        assert event.user_id == "user1"
        assert event.company_id == "company1"
        assert event.payload.name == "test_module"
        assert event.payload.chat_id == "chat1"
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

    def test_snake_case_conversion(self):
        json_data = """{
            "id": "event1",
            "event": "unique.chat.external-module.chosen",
            "userId": "user1",
            "companyId": "company1",
            "payload": {
                "name": "test_module",
                "description": "Test",
                "configuration": {},
                "chatId": "chat1",
                "assistantId": "assistant1",
                "userMessage": {
                    "id": "msg1",
                    "text": "Hello",
                    "createdAt": "2023-01-01T00:00:00Z",
                    "originalText": "Hello",
                    "language": "en"
                },
                "assistantMessage": {
                    "id": "msg2",
                    "createdAt": "2023-01-01T00:01:00Z"
                }
            }
        }"""
        event = Event.model_validate_json(json_data)

        assert hasattr(event, "user_id")
        assert hasattr(event, "company_id")
        assert hasattr(event.payload, "chat_id")
        assert hasattr(event.payload, "assistant_id")
        assert hasattr(event.payload.user_message, "created_at")

    def test_chat_event_user_message_deserialization(self):
        json_data = '{"id": "msg1", "text": "Hello", "createdAt": "2023-01-01T00:00:00Z", "originalText": "Hello", "language": "en"}'
        user_message = ChatEventUserMessage.model_validate_json(json_data)

        assert user_message.id == "msg1"
        assert user_message.text == "Hello"
        assert user_message.created_at == "2023-01-01T00:00:00Z"

    def test_chat_event_assistant_message_deserialization(self):
        json_data = '{"id": "msg2", "createdAt": "2023-01-01T00:01:00Z"}'
        assistant_message = ChatEventAssistantMessage.model_validate_json(json_data)

        assert assistant_message.id == "msg2"
        assert assistant_message.created_at == "2023-01-01T00:01:00Z"

    def test_chat_event_payload_deserialization(self):
        json_data = """{
            "name": "unique.chat.external-module.chosen",
            "description": "Test description",
            "configuration": {"key": "value"},
            "chatId": "chat1",
            "assistantId": "assistant1",
            "userMessage": {
                "id": "msg1",
                "text": "Hello",
                "createdAt": "2023-01-01T00:00:00Z",
                "originalText": "Hello",
                "language": "en"
            },
            "assistantMessage": {
                "id": "msg2",
                "createdAt": "2023-01-01T00:01:00Z"
            },
            "text": "Optional text",
            "additionalParameters": {"translateToLanguage": "en", "contentIdToTranslate": "content_1234"}
        }"""
        payload = ChatEventPayload.model_validate_json(json_data)

        assert payload.name == EventName.EXTERNAL_MODULE_CHOSEN
        assert payload.description == "Test description"
        assert payload.configuration == {"key": "value"}
        assert payload.chat_id == "chat1"
        assert payload.assistant_id == "assistant1"
        assert payload.user_message.id == "msg1"
        assert payload.assistant_message.id == "msg2"
        assert payload.text == "Optional text"
        assert payload.additional_parameters is not None
        assert payload.additional_parameters.translate_to_language == "en"
        assert payload.additional_parameters.content_id_to_translate == "content_1234"
