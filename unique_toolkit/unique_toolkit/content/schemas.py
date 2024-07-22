from datetime import datetime

from humps import camelize
from pydantic import BaseModel, ConfigDict

# set config to convert camelCase to snake_case
model_config = ConfigDict(alias_generator=camelize, populate_by_name=True, arbitrary_types_allowed=True)


class ContentMetadata(BaseModel):
    model_config = model_config
    key: str
    mime_type: str

class ContentChunk(BaseModel):
    model_config = model_config
    id: str
    text: str
    key: str | None = None
    chunk_id: str | None = None
    url: str | None = None
    title: str | None = None
    order: int
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

class SearchResult(BaseModel):
    """Schema corresponding to unique_sdk.SearchResult"""
    id: str
    chunkId: str
    key: str
    text: str
    title: str | None = None
    url: str | None = None
    startPage: int | None = None
    endPage: int | None = None
    order: int
    object: str | None = None