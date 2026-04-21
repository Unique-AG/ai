from __future__ import annotations

from collections.abc import Mapping

from pydantic import AliasChoices, BaseModel, Field
from unique_toolkit._common.pydantic_helpers import get_configuration_dict

from unique_mcp.meta_keys import META_FLAT_ALIASES, MetaKeys


def _alias(canonical: str) -> AliasChoices | str:
    """Build a pydantic alias for ``canonical``, adding the camelCase fallback if any.

    We accept both forms unconditionally on the pydantic model. The
    ``enable_mcp_metadata_fallback_un_19145`` feature flag still governs
    whether the fallback is honoured for auth/chat context composition in
    :mod:`unique_mcp.unique_injectors`; the internal-search model happily
    takes whichever key the host emits for scoping fields.
    """
    flat = META_FLAT_ALIASES.get(canonical)
    if flat is None:
        return canonical
    return AliasChoices(canonical, flat)


class InternalSearchRequestMeta(BaseModel):
    """Parses request ``_meta`` fields consumed by the internal-search tools.

    Auth and chat context are composed centrally via
    :func:`unique_mcp.unique_injectors.get_unique_settings`; this model only
    surfaces the per-call **search-scoping** extras (content ids, metadata
    filter, token budget, selected uploaded files) and keeps the
    identity/chat identifiers around for convenience.
    """

    model_config = get_configuration_dict(extra="allow")

    user_id: str | None = Field(
        default=None,
        validation_alias=_alias(MetaKeys.USER_ID),
    )
    company_id: str | None = Field(
        default=None,
        validation_alias=_alias(MetaKeys.COMPANY_ID),
    )
    chat_id: str | None = Field(
        default=None,
        validation_alias=_alias(MetaKeys.CHAT_ID),
    )
    assistant_id: str | None = Field(
        default=None,
        validation_alias=MetaKeys.ASSISTANT_ID,
    )
    last_assistant_message_id: str | None = Field(
        default=None,
        validation_alias=MetaKeys.LAST_ASSISTANT_MESSAGE_ID,
    )
    last_user_message_id: str | None = Field(
        default=None,
        validation_alias=_alias(MetaKeys.USER_MESSAGE_ID),
    )
    last_user_message_text: str | None = Field(
        default=None,
        validation_alias=MetaKeys.LAST_USER_MESSAGE_TEXT,
    )
    parent_chat_id: str | None = Field(
        default=None,
        validation_alias=MetaKeys.PARENT_CHAT_ID,
    )
    selected_uploaded_file_ids: list[str] | None = Field(
        default=None,
        validation_alias=MetaKeys.SELECTED_UPLOADED_FILE_IDS,
    )
    content_ids: list[str] | None = Field(
        default=None,
        validation_alias=MetaKeys.CONTENT_IDS,
    )
    metadata_filter: dict[str, object] | None = Field(
        default=None,
        validation_alias=MetaKeys.METADATA_FILTER,
    )
    language_model_max_input_tokens: int | None = Field(
        default=None,
        validation_alias=MetaKeys.LANGUAGE_MODEL_MAX_INPUT_TOKENS,
    )

    @classmethod
    def from_request_meta(
        cls, request_meta: Mapping[str, object] | None
    ) -> InternalSearchRequestMeta:
        return cls.model_validate(dict(request_meta or {}))

    @property
    def chat_content_ids(self) -> list[str] | None:
        return self.selected_uploaded_file_ids or self.content_ids

    @property
    def knowledge_base_content_ids(self) -> list[str] | None:
        return self.content_ids


__all__ = ["InternalSearchRequestMeta"]
