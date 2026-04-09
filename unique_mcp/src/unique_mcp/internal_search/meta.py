from __future__ import annotations

from collections.abc import Mapping

from pydantic import BaseModel, Field
from unique_toolkit._common.pydantic_helpers import get_configuration_dict
from unique_toolkit.app.unique_settings import ChatContext

_MCP_CHAT_CONTEXT_SENTINEL = "mcp-internal-search"


class InternalSearchRequestMeta(BaseModel):
    model_config = get_configuration_dict(extra="allow")

    user_id: str | None = Field(default=None, alias="unique.app/user-id")
    company_id: str | None = Field(default=None, alias="unique.app/company-id")
    chat_id: str | None = Field(default=None, alias="unique.app/chat-id")
    assistant_id: str | None = Field(default=None, alias="unique.app/assistant-id")
    last_assistant_message_id: str | None = Field(
        default=None,
        alias="unique.app/last-assistant-message-id",
    )
    last_user_message_id: str | None = Field(
        default=None,
        alias="unique.app/last-user-message-id",
    )
    last_user_message_text: str | None = Field(
        default=None,
        alias="unique.app/last-user-message-text",
    )
    parent_chat_id: str | None = Field(
        default=None,
        alias="unique.app/parent-chat-id",
    )
    selected_uploaded_file_ids: list[str] | None = Field(
        default=None,
        alias="unique.app/selected-uploaded-file-ids",
    )
    content_ids: list[str] | None = Field(
        default=None,
        alias="unique.app/content-ids",
    )
    metadata_filter: dict[str, object] | None = Field(
        default=None,
        alias="unique.app/metadata-filter",
    )
    language_model_max_input_tokens: int | None = Field(
        default=None,
        alias="unique.app/language-model-max-input-tokens",
    )

    @classmethod
    def from_request_meta(
        cls, request_meta: Mapping[str, object] | None
    ) -> InternalSearchRequestMeta:
        return cls.model_validate(dict(request_meta or {}))

    def to_chat_context(self) -> ChatContext:
        if self.chat_id is None:
            raise ValueError(
                "Chat internal search requires `unique.app/chat-id` in _meta."
            )

        # ChatService currently expects full chat-shaped context even though MCP
        # internal search only truly needs the chat scope, so we fill the unused
        # message-related fields with an explicit sentinel.
        return ChatContext(
            chat_id=self.chat_id,
            assistant_id=self.assistant_id
            if self.assistant_id is not None
            else _MCP_CHAT_CONTEXT_SENTINEL,
            last_assistant_message_id=self.last_assistant_message_id
            if self.last_assistant_message_id is not None
            else _MCP_CHAT_CONTEXT_SENTINEL,
            last_user_message_id=self.last_user_message_id
            if self.last_user_message_id is not None
            else _MCP_CHAT_CONTEXT_SENTINEL,
            last_user_message_text=self.last_user_message_text
            if self.last_user_message_text is not None
            else _MCP_CHAT_CONTEXT_SENTINEL,
            metadata_filter=self.metadata_filter,
            parent_chat_id=self.parent_chat_id,
        )

    @property
    def chat_content_ids(self) -> list[str] | None:
        return self.selected_uploaded_file_ids or self.content_ids

    @property
    def knowledge_base_content_ids(self) -> list[str] | None:
        return self.content_ids


__all__ = ["InternalSearchRequestMeta"]
