from datetime import datetime
from enum import StrEnum
from typing import Any, Optional

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
    id: str
    text: str
    order: int
    key: str | None = None
    chunk_id: str | None = None
    url: str | None = None
    title: str | None = None
    start_page: int | None = None
    end_page: int | None = None

    object: str | None = None
    metadata: ContentMetadata | None = None
    internally_stored_at: datetime | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None


class Content(BaseModel):
    model_config = model_config
    id: str
    key: str
    title: str | None = None
    url: str | None = None
    chunks: list[ContentChunk] = []
    write_url: str | None = None
    read_url: str | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None
    metadata: dict[str, Any] | None = None
    ingestion_config: dict | None = None


class BaseReference(BaseModel):
    model_config = model_config
    name: str
    sequence_number: int
    source: str
    source_id: str
    original_index: list[int] = Field(
        default=[],
        description="List of indices in the ChatMessage original_content this reference refers to. This is usually the id in the functionCallResponse. List type due to implementation in node-chat",
    )


class ContentReference(BaseReference):
    id: str
    message_id: str
    url: str


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
