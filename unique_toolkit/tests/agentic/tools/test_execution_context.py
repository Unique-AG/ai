from unittest.mock import Mock

import pytest

from unique_toolkit.agentic.tools.execution_context import (
    ToolExecutionContext,
    disabled_tools_from_event,
    tool_choices_from_event,
)
from unique_toolkit.app.schemas import (
    ChatEvent,
    ChatEventAdditionalParameters,
    ChatEventAssistantMessage,
    ChatEventPayload,
    ChatEventUserMessage,
    EventName,
    UploadedFileInfo,
)
from unique_toolkit.content.service import ContentService


def _chat_event(**payload_overrides: object) -> ChatEvent:
    payload_kwargs: dict[str, object] = {
        "name": "module",
        "description": "desc",
        "chat_id": "chat-1",
        "assistant_id": "asst-1",
        "configuration": {},
        "user_message": ChatEventUserMessage(
            id="umsg-1",
            text="hi",
            created_at="2021-01-01T00:00:00Z",
            language="EN",
            original_text="hi",
        ),
        "assistant_message": ChatEventAssistantMessage(
            id="amsg-1",
            created_at="2021-01-01T00:00:00Z",
        ),
    }
    payload_kwargs.update(payload_overrides)

    return ChatEvent(
        id="evt-1",
        event=EventName.EXTERNAL_MODULE_CHOSEN,
        user_id="user-1",
        company_id="company-1",
        payload=ChatEventPayload(**payload_kwargs),
    )


def test_tool_choices_from_event__reads_payload_field() -> None:
    event = _chat_event(tool_choices=["search"], disabled_tools=["upload"])
    assert tool_choices_from_event(event) == ["search"]
    assert disabled_tools_from_event(event) == ["upload"]


def test_tool_choices_from_event__defaults_to_empty_list() -> None:
    event = _chat_event()
    assert tool_choices_from_event(event) == []
    assert disabled_tools_from_event(event) == []


@pytest.fixture
def mock_content_service_from_event(mocker):
    return mocker.patch(
        "unique_toolkit.content.service.ContentService.from_event",
        return_value=Mock(spec=ContentService),
    )


def test_from_event__copies_turn_snapshot_fields(
    mock_content_service_from_event,
) -> None:
    event = _chat_event(
        name="swot-module",
        metadata_filter={"scope": "x"},
        message_execution_id="exec-1",
        session_config={"swot_analysis": {"company_listing": {}}},
        user_metadata={"region": "eu"},
        tool_parameters={"mode": "full"},
        additional_parameters=ChatEventAdditionalParameters(
            user_space_instructions="",
            selected_uploaded_files=[
                UploadedFileInfo(
                    id="file-1", title="a.pdf", mime_type="application/pdf"
                )
            ],
        ),
    )

    chat_service = Mock()
    language_model_service = Mock()

    ctx = ToolExecutionContext.from_event(
        event,
        chat_service=chat_service,
        language_model_service=language_model_service,
    )

    assert ctx.module_name == "swot-module"
    assert ctx.metadata_filter == {"scope": "x"}
    assert ctx.message_execution_id == "exec-1"
    assert ctx.session_config == {"swot_analysis": {"company_listing": {}}}
    assert ctx.user_metadata == {"region": "eu"}
    assert ctx.tool_parameters == {"mode": "full"}
    assert ctx.selected_uploaded_file_ids == ["file-1"]
    assert ctx.user_message_text == "hi"
    assert ctx.chat_service is chat_service
    assert ctx.language_model_service is language_model_service


def test_from_event__defaults_snapshot_fields_when_absent(
    mock_content_service_from_event,
) -> None:
    event = _chat_event()

    ctx = ToolExecutionContext.from_event(
        event,
        chat_service=Mock(),
        language_model_service=Mock(),
    )

    assert ctx.module_name == "module"
    assert ctx.metadata_filter is None
    assert ctx.message_execution_id is None
    assert ctx.session_config is None
    assert ctx.selected_uploaded_file_ids == []
    assert ctx.tool_parameters == {}
    assert ctx.user_message_text == "hi"


def test_from_event__bootstraps_chat_and_llm_services_when_not_injected(
    mocker, mock_content_service_from_event
) -> None:
    event = _chat_event()
    bootstrapped_chat_service = Mock()
    bootstrapped_llm_service = Mock()
    mocker.patch(
        "unique_toolkit.services.chat_service.ChatService",
        return_value=bootstrapped_chat_service,
    )
    mocker.patch(
        "unique_toolkit.language_model.service.LanguageModelService.from_event",
        return_value=bootstrapped_llm_service,
    )

    ctx = ToolExecutionContext.from_event(event)

    assert ctx.chat_service is bootstrapped_chat_service
    assert ctx.language_model_service is bootstrapped_llm_service


def test_from_event__bootstraps_content_service_when_not_injected(
    mock_content_service_from_event,
) -> None:
    event = _chat_event()

    ctx = ToolExecutionContext.from_event(
        event,
        chat_service=Mock(),
        language_model_service=Mock(),
    )

    mock_content_service_from_event.assert_called_once_with(event)
    assert ctx.content_service is mock_content_service_from_event.return_value


def test_from_event__raises__when_only_chat_service_injected() -> None:
    event = _chat_event()
    with pytest.raises(ValueError, match="must be injected together"):
        ToolExecutionContext.from_event(event, chat_service=Mock())


def test_from_event__raises__when_only_language_model_service_injected() -> None:
    event = _chat_event()
    with pytest.raises(ValueError, match="must be injected together"):
        ToolExecutionContext.from_event(event, language_model_service=Mock())


def test_from_event__builds_message_step_logger_from_chat_service(
    mock_content_service_from_event,
) -> None:
    event = _chat_event()
    chat_service = Mock()

    ctx = ToolExecutionContext.from_event(
        event,
        chat_service=chat_service,
        language_model_service=Mock(),
    )

    assert ctx.message_step_logger is not None
    assert ctx.message_step_logger._chat_service is chat_service


def test_from_services__builds_context_directly_without_event() -> None:
    chat_service = Mock()
    language_model_service = Mock()
    content_service = Mock(spec=ContentService)

    ctx = ToolExecutionContext.from_services(
        chat_service=chat_service,
        language_model_service=language_model_service,
        content_service=content_service,
        module_name="my-module",
        metadata_filter={"scope": "y"},
        selected_uploaded_file_ids=["file-2"],
        tool_parameters={"mode": "quick"},
        user_message_text="hello",
    )

    assert ctx.chat_service is chat_service
    assert ctx.language_model_service is language_model_service
    assert ctx.content_service is content_service
    assert ctx.module_name == "my-module"
    assert ctx.metadata_filter == {"scope": "y"}
    assert ctx.selected_uploaded_file_ids == ["file-2"]
    assert ctx.tool_parameters == {"mode": "quick"}
    assert ctx.user_message_text == "hello"


def test_from_services__defaults_to_empty_lists_and_dicts() -> None:
    ctx = ToolExecutionContext.from_services(
        chat_service=Mock(),
        language_model_service=Mock(),
    )

    assert ctx.selected_uploaded_file_ids == []
    assert ctx.tool_parameters == {}
    assert ctx.module_name == ""
    assert ctx.metadata_filter is None
    assert ctx.content_service is None
    assert ctx.tool_progress_reporter is None
