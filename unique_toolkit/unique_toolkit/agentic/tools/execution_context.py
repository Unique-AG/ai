from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

from typing_extensions import Self

from unique_toolkit.app.schemas import ChatEvent

if TYPE_CHECKING:
    from unique_toolkit.agentic.message_log_manager.service import MessageStepLogger
    from unique_toolkit.agentic.tools.tool_progress_reporter import ToolProgressReporter
    from unique_toolkit.content.service import ContentService
    from unique_toolkit.language_model.service import LanguageModelService
    from unique_toolkit.services.chat_service import ChatService


def _as_str_list(value: object) -> list[str]:
    if isinstance(value, list):
        return [str(item) for item in value]
    return []


def _as_dict(value: object) -> dict[str, Any]:
    if isinstance(value, dict):
        return dict(value)
    if isinstance(value, Mapping):
        return dict(value)
    return {}


def selected_uploaded_file_ids_from_event(event: ChatEvent) -> list[str]:
    """Extract selected uploaded file IDs from a chat event payload."""
    payload = event.payload
    if (
        hasattr(payload, "additional_parameters")
        and payload.additional_parameters is not None
    ):
        selected = getattr(
            payload.additional_parameters, "selected_uploaded_file_ids", None
        )
        if isinstance(selected, Sequence) and not isinstance(selected, (str, bytes)):
            return [str(file_id) for file_id in selected]
    return []


def tool_choices_from_event(event: ChatEvent) -> list[str]:
    return _as_str_list(getattr(event.payload, "tool_choices", None))


def disabled_tools_from_event(event: ChatEvent) -> list[str]:
    return _as_str_list(getattr(event.payload, "disabled_tools", None))


@dataclass(frozen=True)
class ToolExecutionContext:
    """Per-turn wiring passed into every tool ``run()`` call.

      Carries live services (shared across the agent loop) and an immutable
    turn snapshot extracted from the inbound event. The full ``ChatEvent`` is
      never stored.
    """

    chat_service: ChatService
    language_model_service: LanguageModelService
    message_step_logger: MessageStepLogger
    content_service: ContentService | None = None
    tool_progress_reporter: ToolProgressReporter | None = None
    module_name: str = ""
    metadata_filter: dict[str, Any] | None = None
    message_execution_id: str | None = None
    session_config: Any | None = None
    selected_uploaded_file_ids: list[str] = field(default_factory=list)
    user_metadata: dict[str, Any] | None = None
    tool_parameters: dict[str, Any] = field(default_factory=dict)
    user_message_text: str | None = None

    @classmethod
    def from_event(
        cls,
        event: ChatEvent,
        *,
        tool_progress_reporter: ToolProgressReporter | None = None,
        chat_service: ChatService | None = None,
        language_model_service: LanguageModelService | None = None,
        content_service: ContentService | None = None,
    ) -> Self:
        from unique_toolkit.agentic.message_log_manager.service import MessageStepLogger
        from unique_toolkit.content.service import ContentService
        from unique_toolkit.language_model.service import LanguageModelService
        from unique_toolkit.services.chat_service import ChatService

        if (chat_service is None) != (language_model_service is None):
            raise ValueError(
                "chat_service and language_model_service must be injected together; "
                "supplying only one is not supported."
            )

        if chat_service is None:
            chat_service = ChatService(event)
            language_model_service = LanguageModelService.from_event(event)

        if content_service is None:
            content_service = ContentService.from_event(event)

        assert chat_service is not None
        assert language_model_service is not None

        snapshot = _turn_snapshot_from_event(event)

        return cls(
            chat_service=chat_service,
            language_model_service=language_model_service,
            message_step_logger=MessageStepLogger(chat_service=chat_service),
            content_service=content_service,
            tool_progress_reporter=tool_progress_reporter,
            **snapshot,
        )

    @classmethod
    def from_services(
        cls,
        *,
        chat_service: ChatService,
        language_model_service: LanguageModelService,
        tool_progress_reporter: ToolProgressReporter | None = None,
        content_service: ContentService | None = None,
        module_name: str = "",
        metadata_filter: dict[str, Any] | None = None,
        message_execution_id: str | None = None,
        session_config: Any | None = None,
        selected_uploaded_file_ids: list[str] | None = None,
        user_metadata: dict[str, Any] | None = None,
        tool_parameters: dict[str, Any] | None = None,
        user_message_text: str | None = None,
    ) -> Self:
        from unique_toolkit.agentic.message_log_manager.service import MessageStepLogger

        return cls(
            chat_service=chat_service,
            language_model_service=language_model_service,
            message_step_logger=MessageStepLogger(chat_service=chat_service),
            content_service=content_service,
            tool_progress_reporter=tool_progress_reporter,
            module_name=module_name,
            metadata_filter=metadata_filter,
            message_execution_id=message_execution_id,
            session_config=session_config,
            selected_uploaded_file_ids=selected_uploaded_file_ids or [],
            user_metadata=user_metadata,
            tool_parameters=tool_parameters or {},
            user_message_text=user_message_text,
        )


def _turn_snapshot_from_event(event: ChatEvent) -> dict[str, Any]:
    payload = event.payload
    user_message_text: str | None = None
    if hasattr(payload, "user_message") and payload.user_message is not None:
        text = getattr(payload.user_message, "text", None)
        original_text = getattr(payload.user_message, "original_text", None)
        if isinstance(text, str) and text:
            user_message_text = text
        elif isinstance(original_text, str):
            user_message_text = original_text

    session_config: Any | None = None
    if hasattr(payload, "session_config"):
        raw_session_config = payload.session_config
        if raw_session_config is not None and not isinstance(
            raw_session_config, (str, bytes)
        ):
            session_config = raw_session_config

    message_execution_id: str | None = None
    if hasattr(payload, "message_execution_id"):
        raw_message_execution_id = payload.message_execution_id
        if isinstance(raw_message_execution_id, str):
            message_execution_id = raw_message_execution_id

    user_metadata: dict[str, Any] | None = None
    if hasattr(payload, "user_metadata"):
        raw_user_metadata = payload.user_metadata
        if isinstance(raw_user_metadata, dict):
            user_metadata = dict(raw_user_metadata)

    tool_parameters: dict[str, Any] = {}
    if hasattr(payload, "tool_parameters"):
        tool_parameters = _as_dict(payload.tool_parameters)

    metadata_filter: dict[str, Any] | None = None
    if hasattr(payload, "metadata_filter"):
        raw_metadata_filter = payload.metadata_filter
        if isinstance(raw_metadata_filter, dict):
            metadata_filter = dict(raw_metadata_filter)

    module_name = ""
    raw_module_name = getattr(payload, "name", None)
    if isinstance(raw_module_name, str):
        module_name = raw_module_name

    return {
        "module_name": module_name,
        "metadata_filter": metadata_filter,
        "message_execution_id": message_execution_id,
        "session_config": session_config,
        "selected_uploaded_file_ids": selected_uploaded_file_ids_from_event(event),
        "user_metadata": user_metadata,
        "tool_parameters": tool_parameters,
        "user_message_text": user_message_text,
    }
