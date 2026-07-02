"""Tests for resolve_tool_services."""

from unittest.mock import Mock, patch

import pytest

from unique_toolkit.agentic.tools.run_context import ToolRunContext
from unique_toolkit.agentic.tools.service_resolution import resolve_tool_services
from unique_toolkit.app.schemas import ChatEvent


@pytest.fixture
def chat_event() -> ChatEvent:
    event = Mock(spec=ChatEvent)
    event.payload = Mock()
    return event


def test_resolve_tool_services__returns_injected_instances__when_both_provided() -> (
    None
):
    chat_service = Mock()
    language_model_service = Mock()
    content_service = Mock()

    resolved = resolve_tool_services(
        event=None,
        chat_service=chat_service,
        language_model_service=language_model_service,
        content_service=content_service,
    )

    assert resolved.chat_service is chat_service
    assert resolved.language_model_service is language_model_service
    assert resolved.content_service is content_service
    assert resolved.event is None
    assert resolved.run_context == ToolRunContext()


def test_resolve_tool_services__bootstraps_from_event__when_services_missing(
    chat_event: ChatEvent,
) -> None:
    chat_service = Mock()
    language_model_service = Mock()
    content_service = Mock()

    with (
        patch(
            "unique_toolkit.services.chat_service.ChatService",
            return_value=chat_service,
        ) as mock_chat_service,
        patch(
            "unique_toolkit.language_model.service.LanguageModelService.from_event",
            return_value=language_model_service,
        ) as mock_llm_from_event,
        patch(
            "unique_toolkit.content.service.ContentService.from_event",
            return_value=content_service,
        ) as mock_content_from_event,
    ):
        resolved = resolve_tool_services(
            event=chat_event,
            chat_service=None,
            language_model_service=None,
        )

    mock_chat_service.assert_called_once_with(chat_event)
    mock_llm_from_event.assert_called_once_with(chat_event)
    mock_content_from_event.assert_called_once_with(chat_event)
    assert resolved.chat_service is chat_service
    assert resolved.language_model_service is language_model_service
    assert resolved.content_service is content_service
    assert resolved.event is chat_event
    assert resolved.run_context.tool_choices == []


def test_resolve_tool_services__does_not_rebuild__when_services_injected(
    chat_event: ChatEvent,
) -> None:
    chat_service = Mock()
    language_model_service = Mock()

    with (
        patch("unique_toolkit.services.chat_service.ChatService") as mock_chat_service,
        patch(
            "unique_toolkit.content.service.ContentService.from_event",
            return_value=Mock(),
        ) as mock_content_from_event,
    ):
        resolved = resolve_tool_services(
            event=chat_event,
            chat_service=chat_service,
            language_model_service=language_model_service,
        )

    mock_chat_service.assert_not_called()
    mock_content_from_event.assert_called_once_with(chat_event)
    assert resolved.chat_service is chat_service
    assert resolved.language_model_service is language_model_service
    assert resolved.event is None


def test_resolve_tool_services__raises__when_only_one_service_provided() -> None:
    with pytest.raises(ValueError, match="must be injected together"):
        resolve_tool_services(
            event=None,
            chat_service=Mock(),
            language_model_service=None,
        )


def test_resolve_tool_services__uses_explicit_run_context_without_event() -> None:
    chat_service = Mock()
    language_model_service = Mock()
    run_context = ToolRunContext(
        selected_uploaded_file_ids=["file-1"],
        session_config={"swot_analysis": {}},
    )

    resolved = resolve_tool_services(
        event=None,
        run_context=run_context,
        chat_service=chat_service,
        language_model_service=language_model_service,
    )

    assert resolved.run_context is run_context
    assert resolved.event is None
    assert resolved.run_context.selected_uploaded_file_ids == ["file-1"]


def test_resolve_tool_services__raises__when_nothing_provided() -> None:
    with pytest.raises(ValueError, match="event or injected chat_service"):
        resolve_tool_services(
            event=None,
            chat_service=None,
            language_model_service=None,
        )
