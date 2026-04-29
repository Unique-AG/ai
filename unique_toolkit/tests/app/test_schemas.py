from unique_toolkit.app.schemas import (
    ChatEvent,
    ChatEventAdditionalParameters,
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
            "additionalParameters": {"translateToLanguage": "en", "contentIdToTranslate": "content_1234", "userSpaceInstructions": "some instructions"}
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
        assert (
            payload.additional_parameters.user_space_instructions == "some instructions"
        )

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
                "additionalParameters": {"translateToLanguage": "en", "contentIdToTranslate": "content_1234", "userSpaceInstructions": "some instructions"}
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
        assert (
            event.payload.additional_parameters.user_space_instructions
            == "some instructions"
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
            "additionalParameters": {"translateToLanguage": "en", "contentIdToTranslate": "content_1234", "userSpaceInstructions": "some instructions"}
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
        assert (
            payload.additional_parameters.user_space_instructions == "some instructions"
        )

    def test_additional_parameters__uploaded_files__object_format_deserialization(self):
        json_data = """{
            "userSpaceInstructions": "",
            "uploadedFiles": [
                {"id": "cont_abc", "title": "Q3 Report.pdf", "mimeType": "application/pdf"}
            ],
            "selectedUploadedFiles": [
                {"id": "cont_abc", "title": "Q3 Report.pdf", "mimeType": "application/pdf"}
            ]
        }"""
        params = ChatEventAdditionalParameters.model_validate_json(json_data)

        assert len(params.uploaded_files) == 1
        assert params.uploaded_files[0].id == "cont_abc"
        assert params.uploaded_files[0].title == "Q3 Report.pdf"
        assert params.uploaded_files[0].mime_type == "application/pdf"
        assert params.uploaded_file_ids == ["cont_abc"]

        assert len(params.selected_uploaded_files) == 1
        assert params.selected_uploaded_files[0].id == "cont_abc"
        assert params.selected_uploaded_file_ids == ["cont_abc"]

    def test_additional_parameters__uploaded_files__defaults_to_empty_list(self):
        json_data = '{"userSpaceInstructions": ""}'
        params = ChatEventAdditionalParameters.model_validate_json(json_data)

        assert params.uploaded_files == []
        assert params.selected_uploaded_files == []


class TestChatEventInitialDebugInfo:
    """Exercise :meth:`ChatEvent.get_initial_debug_info` across payload kinds."""

    def test_get_initial_debug_info__chat_payload__includes_metadata_and_tools(self):
        event = ChatEvent(
            id="ev1",
            event="unique.chat.external-module.chosen",
            user_id="user1",
            company_id="co1",
            payload=ChatEventPayload(
                name="mod_ref",
                description="desc",
                configuration={},
                chat_id="chat1",
                assistant_id="aid",
                user_message=ChatEventUserMessage(
                    id="m1",
                    text="hi",
                    original_text="hi",
                    created_at="2023-01-01T00:00:00Z",
                    language="en",
                ),
                assistant_message=ChatEventAssistantMessage(
                    id="m2",
                    created_at="2023-01-01T00:01:00Z",
                ),
                user_metadata={"k": "v"},
                tool_parameters={"tool": {}},
            ),
        )
        info = event.get_initial_debug_info()
        assert info["user_metadata"] == {"k": "v"}
        assert info["tool_parameters"] == {"tool": {}}
        assert info["chosen_module"] == "mod_ref"
        assert info["assistant"] == {"id": "aid"}

    def test_get_initial_debug_info__magic_table_payload__fills_defaults_for_chat_only_fields(
        self,
    ):
        from unique_sdk.api_resources._agentic_table import MagicTableAction, SheetType

        from unique_toolkit.agentic_table.schemas import (
            MagicTableEvent,
            MagicTableEventTypes,
            MagicTableRerunRowPayload,
            RerunRowMetadata,
        )

        event = MagicTableEvent(
            id="ev1",
            event=MagicTableEventTypes.RERUN_ROW,
            user_id="user1",
            company_id="co1",
            payload=MagicTableRerunRowPayload(
                name="rfp_agent",
                sheet_name="S",
                action=MagicTableAction.RERUN_ROW,
                chat_id="chat-123",
                assistant_id="aid",
                table_id="tid",
                metadata=RerunRowMetadata(
                    source_file_ids=["f1"],
                    row_order=1,
                    sheet_type=SheetType.DEFAULT,
                ),
            ),
        )
        info = event.get_initial_debug_info()
        assert info["user_metadata"] == {}
        assert info["tool_parameters"] == {}
        assert info["chosen_module"] == "rfp_agent"
        assert info["assistant"] == {"id": "aid"}
