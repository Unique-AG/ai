from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from typing import Any, Optional

import unique_sdk
from humps import camelize
from pydantic import BaseModel, ConfigDict, Field

from unique_toolkit._common.config_checker import register_config

# set config to convert camelCase to snake_case
model_config = ConfigDict(
    alias_generator=camelize,
    populate_by_name=True,
    arbitrary_types_allowed=True,
)


class ContentMetadata(BaseModel):
    model_config = ConfigDict(
        alias_generator=camelize,
        populate_by_name=True,
        arbitrary_types_allowed=True,
        extra="allow",
    )
    key: str
    mime_type: str


@register_config()
class ContentChunk(BaseModel):
    model_config = model_config
    id: str = Field(
        default="",
        description="The id of the content this chunk belongs to. The id starts with 'cont_' followed by an alphanumeric string of length 24.",
        examples=["cont_abcdefgehijklmnopqrstuvwx"],
    )
    text: str = Field(default="", description="The text content of the chunk.")
    order: int = Field(
        default=0,
        description="The order of the chunk in the original content. Concatenating the chunks in order will give the original content.",
    )
    key: str | None = Field(
        default=None,
        description="The key of the chunk. For document chunks this is the the filename",
    )
    chunk_id: str | None = Field(
        default=None,
        description="The id of the chunk. The id starts with 'chunk_' followed by an alphanumeric string of length 24.",
        examples=["chunk_abcdefgehijklmnopqrstuv"],
    )
    url: str | None = Field(
        default=None,
        description="For chunk retrieved from the web this is the url of the chunk.",
    )
    title: str | None = Field(
        default=None,
        description="The title of the chunk. For document chunks this is the title of the document.",
    )
    start_page: int | None = Field(
        default=None,
        description="The start page of the chunk. For document chunks this is the start page of the document.",
    )
    end_page: int | None = Field(
        default=None,
        description="The end page of the chunk. For document chunks this is the end page of the document.",
    )

    object: str | None = None
    metadata: ContentMetadata | None = None
    internally_stored_at: datetime | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None

    def to_reference(
        self,
        sequence_number: int,
        *,
        original_index: list[int] | None = None,
        message_id: str = "",
    ) -> ContentReference:
        """Convert this chunk into a :class:`ContentReference` with page-number info.

        When using ``modify_assistant_message`` (the message-update path) instead of
        streaming via ``complete_with_references``, the backend does **not**
        automatically create references from ``searchContext``. This method replicates
        the reference format the backend streaming path produces so page numbers
        appear in the frontend reference chips.

        Conventions applied:

        * **id** — this chunk's content id (``self.id``), aligned with streaming
          reference persistence.
        * **message_id** — optional; set when the reference belongs to a specific
          chat message.
        * **source_id** — ``{content_id}_{chunk_id}`` (matches the backend
          ``ReferenceService`` and ``ReferenceManager`` lookup).
        * **source** — ``"node-ingestion-chunks"``.
        * **name** — document title/key with a `` : 1,2,3`` page-number postfix
          (same format as the backend ``generatePagesPostfix``); if neither title
          nor key is set, ``Content {content_id}`` (matches reference dedup logic).
          Postfix is not doubled when ``title``/``key`` already include it (e.g. after
          ``sort_content_chunks`` / ``merge_content_chunks``).
        * **url** — the chunk's own URL when it has one and is **not**
          internally stored; otherwise ``unique://content/{content_id}``
          (matches the ``internally_stored_at`` guard in the streaming path).

        Args:
            sequence_number: The 1-based sequence number shown in the ``<sup>``
                tag in the message text.
            original_index: Optional list of bracket indices (``[N]``) in the
                message text that this reference corresponds to.
            message_id: The chat message id this reference belongs to, if any.

        Returns:
            A ``ContentReference`` ready to pass to ``modify_assistant_message``.

        Note:
            Implementation delegates to :func:`~unique_toolkit.content.utils.content_chunk_to_reference`
            via a lazy import to avoid a circular import with
            :mod:`unique_toolkit.content.utils`.
        """
        from unique_toolkit.content.utils import content_chunk_to_reference

        return content_chunk_to_reference(
            self,
            sequence_number,
            original_index,
            message_id=message_id,
        )


class Content(BaseModel):
    model_config = model_config
    id: str = Field(
        default="",
        description="The id of the content. The id starts with 'cont_' followed by an alphanumeric string of length 24.",
        examples=["cont_abcdefgehijklmnopqrstuvwx"],
    )
    key: str = Field(
        default="",
        description="The key of the content. For documents this is the the filename",
    )
    title: str | None = Field(
        default=None,
        description="The title of the content. For documents this is the title of the document.",
    )
    url: str | None = None
    chunks: list[ContentChunk] = []
    write_url: str | None = None
    read_url: str | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None
    expired_at: datetime | None = None
    metadata: dict[str, Any] | None = None
    ingestion_config: dict | None = None
    applied_ingestion_config: dict | None = None
    ingestion_state: str | None = None


class ContentReference(BaseModel):
    model_config = model_config
    id: str = Field(
        default="",
        description="The id of the content reference. Can be empty on the ChatMessage Object",
    )
    message_id: str = Field(
        default="",
        description="The id of the message that this reference belongs to. Can be empty on the ChatMessage Object",
    )
    name: str
    sequence_number: int
    source: str
    source_id: str
    url: str
    original_index: list[int] = Field(
        default=[],
        description="List of indices in the ChatMessage original_text this reference refers to. This is usually the id in the functionCallResponse. List type due to implementation in node-chat",
    )

    @classmethod
    def from_sdk_reference(
        cls, reference: unique_sdk.Message.Reference | unique_sdk.Space.Reference
    ) -> "ContentReference":
        kwargs = {
            "name": reference["name"],
            "url": reference["url"],
            "sequence_number": reference["sequenceNumber"],
            "source": reference["source"],
            "source_id": reference["sourceId"],
        }
        if "originalIndex" in reference:
            kwargs["original_index"] = reference["originalIndex"]

        return cls.model_validate(kwargs)


class ContentSearchType(StrEnum):
    COMBINED = "COMBINED"
    VECTOR = "VECTOR"


class ContentSearchResult(BaseModel):
    """Schema corresponding to unique_sdk.SearchResult"""

    id: str
    text: str
    order: int
    chunkId: str | None = None
    key: str | None = None
    title: str | None = None
    url: str | None = None
    startPage: int | None = None
    endPage: int | None = None
    object: str | None = None


class ContentUploadInput(BaseModel):
    key: str
    title: str
    mime_type: str

    owner_type: Optional[str] = None
    owner_id: Optional[str] = None
    byte_size: Optional[int] = None


class ContentRerankerConfig(BaseModel):
    model_config = model_config
    deployment_name: str = Field(serialization_alias="deploymentName")
    options: dict | None = None


class ContentInfo(BaseModel):
    model_config = model_config
    id: str
    object: str
    key: str
    url: str | None = None
    title: str | None = None
    metadata: dict[str, Any] | None = None
    byte_size: int
    mime_type: str
    owner_id: str
    created_at: datetime
    updated_at: datetime
    expires_at: datetime | None = None
    deleted_at: datetime | None = None
    expired_at: datetime | None = None


class PaginatedContentInfos(BaseModel):
    model_config = model_config
    object: str
    content_infos: list[ContentInfo]
    total_count: int


class BaseFolderInfo(BaseModel):
    model_config = model_config
    id: str
    name: str
    parent_id: str | None


class FolderInfo(BaseFolderInfo):
    model_config = model_config
    ingestion_config: dict[str, Any]
    created_at: str | None
    updated_at: str | None
    external_id: str | None


class DeleteContentResponse(BaseModel):
    model_config = model_config
    content_id: str
    object: str
