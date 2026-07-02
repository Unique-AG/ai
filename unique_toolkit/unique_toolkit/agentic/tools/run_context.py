from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any

from pydantic import BaseModel, ConfigDict, Field
from typing_extensions import Self

from unique_toolkit.app.schemas import ChatEvent


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


class ToolRunContext(BaseModel):
    """Per-turn tool wiring state: tool filtering plus an explicit turn snapshot.

    Turn snapshot fields are populated once from the inbound event (or built
    directly by the orchestrator) so tools do not need to read a live
    ``ChatEvent`` for configuration that does not change during the agent loop.

    The full event is not stored here — only extracted, immutable fields.
    Legacy bootstrap paths keep the event on ``ToolManager`` separately.
    """

    model_config = ConfigDict(frozen=True, arbitrary_types_allowed=True)

    tool_choices: list[str] = Field(default_factory=list)
    disabled_tools: list[str] = Field(default_factory=list)

    module_name: str = ""
    metadata_filter: dict[str, Any] | None = None
    message_execution_id: str | None = None
    session_config: Any | None = None
    selected_uploaded_file_ids: list[str] = Field(default_factory=list)
    user_metadata: dict[str, Any] | None = None
    tool_parameters: dict[str, Any] = Field(default_factory=dict)
    user_message_text: str | None = None

    @classmethod
    def from_chat_event(cls, event: ChatEvent) -> Self:
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

        tool_choices = _as_str_list(getattr(payload, "tool_choices", None))
        disabled_tools = _as_str_list(getattr(payload, "disabled_tools", None))

        module_name = ""
        raw_module_name = getattr(payload, "name", None)
        if isinstance(raw_module_name, str):
            module_name = raw_module_name

        return cls(
            tool_choices=tool_choices,
            disabled_tools=disabled_tools,
            module_name=module_name,
            metadata_filter=metadata_filter,
            message_execution_id=message_execution_id,
            session_config=session_config,
            selected_uploaded_file_ids=selected_uploaded_file_ids_from_event(event),
            user_metadata=user_metadata,
            tool_parameters=tool_parameters,
            user_message_text=user_message_text,
        )
