from datetime import datetime
from enum import StrEnum
from typing import Any, Optional

import unique_sdk
from humps import camelize
from pydantic import BaseModel, ConfigDict, Field

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
    metadata: dict[str, Any] | None = None
    ingestion_config: dict | None = None


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
        description="List of indices in the ChatMessage original_content this reference refers to. This is usually the id in the functionCallResponse. List type due to implementation in node-chat",
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


class FolderInfo(BaseModel):
    model_config = model_config
    id: str
    name: str
    ingestion_config: dict[str, Any]
    createdAt: str | None
    updatedAt: str | None
    parentId: str | None
    externalId: str | None


class DeleteContentResponse(BaseModel):
    model_config = model_config
    content_id: str
    object: str
