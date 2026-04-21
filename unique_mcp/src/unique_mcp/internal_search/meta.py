from __future__ import annotations

from collections.abc import Mapping

from pydantic import BaseModel, Field
from unique_toolkit._common.pydantic_helpers import get_configuration_dict

from unique_mcp.meta_keys import MetaKeys


class InternalSearchRequestMeta(BaseModel):
    """Search-scoping fields from the request ``_meta`` dict.

    Auth and chat context are composed centrally by
    :func:`unique_mcp.unique_injectors.get_unique_settings` and available
    through :class:`~unique_toolkit.app.unique_settings.UniqueSettings`;
    this model only surfaces the four per-call search-scoping keys that the
    providers consume directly.

    Unknown keys are ignored (``extra="ignore"``) so a typo like
    ``unique.app/contnet-ids`` is dropped rather than silently accepted.
    """

    model_config = get_configuration_dict(extra="allow")

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
